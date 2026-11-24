"""Block / street U-net for Sanborn plates (14 November 2026). Runs offline on this machine (PyTorch + DirectML).

    cd data/sanborn
    PY=../../tools/sanborn/unet/.venv/Scripts/python.exe
    $PY ../../tools/sanborn/unet/unet.py train NAME PLATE[:val] ... [--iters 3000]   -> unet_data/models/NAME.pt, NAME.json
    $PY ../../tools/sanborn/unet/unet.py predict NAME PLATE                          -> unet_data/PLATE_pred_NAME.png (0-255 = P(block))

Training pairs come from make_labels.py (PLATE_img.jpg, PLATE_label.png: 0 street, 1 block, 255 ignore). A plate given
as PLATE:val is held out whole and PLATE:all is trained on whole; otherwise the right-hand quarter of each plate is held out, so the score is always on
ground the network has not seen. The network sees the scan and the guide (today's blocks and centre lines through a rough placement). In training the
guide is moved up to 8 m at random and pieces of it are erased, so it cannot be copied: the edge has to be found in
the picture. Each check also scores the held-out ground with the guide moved 5 m. Random 384 px crops, flips,
quarter turns, colour jitter. Loss: cross-entropy over
the labelled pixels, streets weighted 3 to 1 and every pixel weighted by its nearness to a verified (green) edge, plus
a second task: the third output draws the verified edges (load_edge).

23 November 2026 (Ben: "let's try training on a number of them"; data/sanborn/bench_2026-11-23/train). New options;
without them the trainer does what it did before, except the --no-guide fix below and that an option it does not know
is now an error (a slip such as --seeds would otherwise be read as a plate):

    $PY unet.py train NAME --data DIR [PLATE[:val] ...] [--seed S] [--weights N=w[,N=w]] [--out MODELDIR]
                [--iters 3000] [--val-every 250]

  --data DIR   read the plates from a data folder (data/sanborn/train_v2/): DIR/N/img.jpg (half-size scan, as
               make_labels.py's N_img.jpg), label.png (0 street, 1 block, 255 not taught), edge.png (the verified
               edges, as N_edge.png; missing or empty: the third output is not taught on that plate), valmask.png
               (optional, 1 = validation, never trained on) and meta.json; DIR/manifest.json lists them. No plate
               given: every plate in the manifest. The guide is blank (the data folder has none): --data implies
               --no-guide. Plates 44 and 90 are refused (44 is the benchmark, 90 the next truth plate).
               PLATE (no suffix): trained on its pixels outside valmask.png, scored on those inside. PLATE:val: the
               whole plate is validation. (PLATE:all is refused where a valmask.png exists.)
  --seed S     seeds Python's random, numpy and torch (the weights' start), and the crop sampler. Without it the
               sampler starts from 0 as before and torch is not seeded.
  --weights    per-plate sampling weights, e.g. --weights 60B=0.5,79=0.5 (others 1): with --data each crop first
               picks a plate with probability w / sum(w), then a crop on it, so the share of crops per plate is the
               weight's share (default: equal per plate). The crops drawn per plate are in the model json.
  keep-best    with --data the validation pixels are scored every --val-every iterations (default 250) and at the
               end: NAME.pt is the best (by iou_street on the validation pixels pooled over the plates, then
               accuracy), NAME_last.pt the last. A training crop never overlaps a validation pixel: a crop that
               would is drawn again (integral image of valmask.png; checked in bench_2026-11-23/train/trainer).
               Without validation pixels NAME.pt is the last.
  --out DIR    where NAME.pt / NAME_last.pt / NAME.json go (default data/sanborn/train_v2_runs/models/; never inside
               unet_data/, where the batch's own models are). The json and the .pt files go to a temporary file that
               is then renamed, so a run killed part way never leaves a half-written file.
  model json   seed, the data folder, its manifest.json sha256 (and content_sha256), the git commit (and whether tools/sanborn/unet has
               changes), this file's sha256, every plate with its source (meta.json), weight, the sha256 of each
               file read, the pixels trained and scored, the crops drawn, the best iteration and the val history.
  --no-guide   (21 Nov) the guide channels blank. Fixed 23 Nov (ml_review M8): the guide is no longer moved and no
               255 squares are pasted into it in training (in use it is always zeros). --legacy-noguide gives the
               21 Nov recipe (only without --data).
  Saved weights with --data are CPU tensors (torch.load(..., weights_only=True) loads them; ml_review M8).
"""
import hashlib, json, os, random, subprocess, sys, time
import numpy as np
import cv2
import torch, torch.nn as nn, torch.nn.functional as F
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
import _ws  # noqa: E402
DATA = _ws.DATA + 'unet_data/'; CROP, BATCH = 384, 8
NOGUIDE = '--no-guide' in sys.argv   # 21 Nov 2026: a network for plates that were never placed; the guide channels are blank in training and in use
LEGACY_NOGUIDE = '--legacy-noguide' in sys.argv   # 23 Nov 2026: the 21 Nov blank-guide recipe (guide moved, 255 squares pasted)
FORBIDDEN = ('44', '90')   # 44: Ben's ground truth, the benchmark; 90: his planned second truth plate. Never trained on or used to choose a checkpoint
VAL_EVERY, MAX_TRIES = 250, 20000

def device():
    try:
        import torch_directml as d
        k = max(range(d.device_count()), key=lambda i: ('RX' in d.device_name(i)) + ('NVIDIA' in d.device_name(i)))
        print('device', d.device_name(k), flush=True); device.name = d.device_name(k).strip('\x00'); return d.device(k)
    except Exception:
        device.name = 'cuda' if torch.cuda.is_available() else 'cpu'
        return torch.device(device.name)
device.name = None

# GroupNorm, not BatchNorm: with BatchNorm on the DirectML backend the held-out score fell while the training loss fell (14 Nov 2026)
def block(i, o): return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.GroupNorm(8, o), nn.ReLU(inplace=True), nn.Conv2d(o, o, 3, padding=1), nn.GroupNorm(8, o), nn.ReLU(inplace=True))
class UNet(nn.Module):
    def __init__(self, classes=3, base=32, depth=4, in_ch=5):       # outputs: street, block, and (third) the verified-edge line
        super().__init__()
        ch = [base * 2 ** k for k in range(depth + 1)]
        self.down = nn.ModuleList([block(in_ch if k == 0 else ch[k - 1], ch[k]) for k in range(depth + 1)])
        self.up = nn.ModuleList([nn.ConvTranspose2d(ch[k + 1], ch[k], 2, stride=2) for k in range(depth)])
        self.dec = nn.ModuleList([block(2 * ch[k], ch[k]) for k in range(depth)])
        self.out = nn.Conv2d(base, classes, 1)
    def forward(self, x):
        skips = []
        for k, d in enumerate(self.down):
            x = d(x if k == 0 else F.max_pool2d(x, 2)); skips.append(x)
        for k in reversed(range(len(self.up))):
            x = self.dec[k](torch.cat([self.up[k](x), skips[k]], 1))
        return self.out(x)

def load(plate):
    """image with the guide stacked on: R, G, B, today's blocks, today's centre lines (5 channels)"""
    img = cv2.imread(DATA + f'{plate}_img.jpg')[:, :, ::-1]; g = cv2.imread(DATA + f'{plate}_guide.png')
    if NOGUIDE: g = g * 0
    return np.dstack([img, g[:, :, 0], g[:, :, 1]]), cv2.imread(DATA + f'{plate}_label.png', 0)
def load_edge(plate, lab):
    """Ben, 14 November 2026: apply the green limits. Returns (weight map, edge target) at the label's size.
    The verified edges (make_labels.py N_edge.png) drive the training two ways: every labelled pixel is weighted by
    1 + EDGE_W * exp(-d / EDGE_D), d its distance to the nearest verified edge, so a mistake at a block line costs
    several times one in the middle of a block; and the network's third output must draw the verified edges (target:
    the edge 3 px thick; 255 = not scored, where the label is blank and no verified edge runs)."""
    return edge_maps(cv2.imread(DATA + f'{plate}_edge.png', 0), lab)
def edge_maps(e, lab):
    """load_edge's maps from the edge image e (None: no edges known)"""
    if e is None: return np.ones(lab.shape, np.float32), np.full(lab.shape, 255, np.uint8)
    d = cv2.distanceTransform((e == 0).astype(np.uint8), cv2.DIST_L2, 3)
    wmap = (1.0 + EDGE_W * np.exp(-d / EDGE_D)).astype(np.float32)
    tgt = (cv2.dilate(e, np.ones((3, 3), np.uint8)) > 0).astype(np.uint8); tgt[(lab == 255) & (tgt == 0)] = 255
    return wmap, tgt
EDGE_W, EDGE_D, EDGE_POS, EDGE_LOSS = 6.0, 4.0, 12.0, 1.0
SHIFT = 20          # px at half size (about 8 m): how far the guide is moved at random in training
def shift_guide(x, dx, dy):
    out = x.copy(); out[:, :, 3:] = np.roll(x[:, :, 3:], (dy, dx), (0, 1)); return out
def norm(a): return torch.from_numpy(np.ascontiguousarray(a.transpose(0, 3, 1, 2))).float() / 255.0

def predict_full(net, dev, img, tile=768, pad=64):
    """P(block) for a whole image, by overlapping tiles (the outer pad of each tile is thrown away)"""
    h, w = img.shape[:2]; out = np.zeros((h, w), np.float32); edge = np.zeros((h, w), np.float32); step = tile - 2 * pad
    im = cv2.copyMakeBorder(img, pad, pad + tile, pad, pad + tile, cv2.BORDER_REFLECT)
    net.eval()
    with torch.no_grad():
        for y in range(0, h, step):
            for x in range(0, w, step):
                o = net(norm(im[None, y:y + tile, x:x + tile]).to(dev))
                p = F.softmax(o[:, :2], 1)[0, 1].cpu().numpy()[pad:pad + step, pad:pad + step]
                out[y:y + step, x:x + step] = p[:min(step, h - y), :min(step, w - x)]
                q = torch.sigmoid(o[0, 2]).cpu().numpy()[pad:pad + step, pad:pad + step]
                edge[y:y + step, x:x + step] = q[:min(step, h - y), :min(step, w - x)]
    predict_full.edge = edge                     # P(verified-edge line), the third output
    return out

def score(p, lab, etgt=None, eprob=None):
    m = lab != 255; pr = p[m] > 0.5; gt = lab[m] == 1
    iou = lambda a, b: float((a & b).sum() / max(1, (a | b).sum()))
    out = dict(pixels=int(m.sum()), accuracy=round(float((pr == gt).mean()), 4), iou_block=round(iou(pr, gt), 4), iou_street=round(iou(~pr, ~gt), 4))
    if etgt is not None and (etgt == 1).any():
        # the green limits: how much of the verified edge the predicted street/block boundary reaches within 2 px, and how
        # much of it the edge output draws
        b = cv2.morphologyEx((p > 0.5).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
        near_b = cv2.dilate(b.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0; ve = etgt == 1
        out['green_edge_met_by_boundary'] = round(float(near_b[ve].mean()), 4)
        if eprob is not None: out['green_edge_drawn'] = round(float((cv2.dilate((eprob > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)[ve].mean()), 4)
    return out

def train(name, plates, iters):
    dev = device(); rng = np.random.default_rng(0); tr, va = [], []
    for spec in plates:
        p, _, whole = spec.partition(':'); img, lab = load(p); wm, et = load_edge(p, lab); cut = int(img.shape[1] * 0.75)
        if whole == 'val': va.append((p, img, lab, et))
        elif whole == 'all': tr.append((img, lab, wm, et))          # PLATE:all trains on the whole plate (another plate is held out)
        else: tr.append((img[:, :cut], lab[:, :cut], wm[:, :cut], et[:, :cut])); va.append((p, img[:, cut:], lab[:, cut:], et[:, cut:]))
    wt = torch.tensor([3.0, 1.0]).to(dev)        # streets are about an eighth of the labelled ground
    net = UNet().to(dev); opt = torch.optim.Adam(net.parameters(), 1e-3); t0 = time.time(); hist = []
    for it in range(1, iters + 1):
        xs, ys, ws, es = [], [], [], []
        while len(xs) < BATCH:
            img, lab, wm, et = tr[rng.integers(len(tr))]; y = rng.integers(0, img.shape[0] - CROP); x = rng.integers(0, img.shape[1] - CROP)
            a, b = img[y:y + CROP, x:x + CROP].copy(), lab[y:y + CROP, x:x + CROP]; c_, e_ = wm[y:y + CROP, x:x + CROP], et[y:y + CROP, x:x + CROP]
            if (b != 255).mean() < 0.2: continue
            if not NOGUIDE or LEGACY_NOGUIDE:              # 23 Nov: a blank guide is not moved, and gets no 255 squares (in use it is all zeros)
                dx, dy = rng.integers(-SHIFT, SHIFT + 1, 2)            # the guide comes from a rough placement: move it, and erase a piece
                gy0, gx0 = np.clip(y + dy, 0, img.shape[0] - CROP), np.clip(x + dx, 0, img.shape[1] - CROP)
                a[:, :, 3:] = img[gy0:gy0 + CROP, gx0:gx0 + CROP, 3:]
                if rng.random() < 0.5:
                    ey, ex, eh, ew = rng.integers(0, CROP - 64), rng.integers(0, CROP - 64), rng.integers(48, 160), rng.integers(48, 160)
                    a[ey:ey + eh, ex:ex + ew, 3:] = 0 if rng.random() < 0.5 else 255
            k = rng.integers(4); a, b, c_, e_ = np.rot90(a, k), np.rot90(b, k), np.rot90(c_, k), np.rot90(e_, k)
            if rng.random() < 0.5: a, b, c_, e_ = a[:, ::-1], b[:, ::-1], c_[:, ::-1], e_[:, ::-1]
            a = a.astype(np.float32); a[:, :, :3] = np.clip(a[:, :, :3] * rng.uniform(0.8, 1.2) + rng.uniform(-20, 20) + rng.normal(0, 3, 3), 0, 255)
            xs.append(a); ys.append(b); ws.append(c_); es.append(e_)
        for g in opt.param_groups: g['lr'] = 1e-3 * 0.5 * (1 + np.cos(np.pi * it / iters))
        net.train(); out = net(norm(np.stack(xs)).to(dev))
        yt = torch.from_numpy(np.stack(ys).astype(np.int64)).to(dev); wtm = torch.from_numpy(np.ascontiguousarray(np.stack(ws))).to(dev)
        ce = F.cross_entropy(out[:, :2], yt, weight=wt, ignore_index=255, reduction='none'); ok = (yt != 255).float()
        seg = (ce * wtm * ok).sum() / (wtm * ok).sum().clamp(min=1.0)                 # labelled pixels, weighted by nearness to a verified edge
        en = np.stack(es); ev = torch.from_numpy((en != 255).astype(np.float32)).to(dev); etn = torch.from_numpy((en == 1).astype(np.float32)).to(dev)
        bce = F.binary_cross_entropy_with_logits(out[:, 2], etn, reduction='none') * (1.0 + (EDGE_POS - 1.0) * etn)
        loss = seg + EDGE_LOSS * (bce * ev).sum() / ev.sum().clamp(min=1.0)           # plus: draw the verified edges
        opt.zero_grad(); loss.backward(); opt.step()
        if it % 250 == 0 or it == iters:
            sc = {}
            for p, img, lab, et in va:
                pp = predict_full(net, dev, shift_guide(img, 12, -12)); sh = score(pp, lab, et, predict_full.edge)
                pp = predict_full(net, dev, img); sc[p] = dict(score(pp, lab, et, predict_full.edge), guide_shifted_12px=sh['iou_street'], green_edge_met_guide_shifted=sh.get('green_edge_met_by_boundary'))
            hist.append(dict(iter=it, loss=round(float(loss), 4), minutes=round((time.time() - t0) / 60, 1), val=sc)); print(json.dumps(hist[-1]), flush=True)
    os.makedirs(DATA + 'models', exist_ok=True)
    torch.save(net.state_dict(), DATA + f'models/{name}.pt')
    json.dump(dict(name=name, plates=plates, iters=iters, crop=CROP, batch=BATCH, no_guide=NOGUIDE, legacy_noguide=LEGACY_NOGUIDE, history=hist), open(DATA + f'models/{name}.json', 'w', encoding='utf8', newline='\n'), indent=1)


# ====================================================================== 23 Nov 2026: the data folder (--data), seeds, keep-best
def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()

def seed_all(s):
    """Python's random, numpy's global state and torch's generator (the weights' start)"""
    random.seed(s); np.random.seed(s); torch.manual_seed(s)

def git_state():
    """the repo's commit and the files of tools/sanborn/unet that differ from it (the staged code is not committed)"""
    repo = os.path.normpath(os.path.join(_ws.CODE, '..', '..'))
    def g(*a):
        try: return subprocess.run(['git', '-C', repo] + list(a), capture_output=True, text=True, timeout=30).stdout.strip()
        except Exception as e: return f'git failed: {e}'
    return dict(commit=g('rev-parse', 'HEAD'), branch=g('rev-parse', '--abbrev-ref', 'HEAD'), unet_dir_changes=g('status', '--porcelain', '--', 'tools/sanborn/unet').splitlines())

def parse_weights(specs):
    """--weights 60B=0.5,79=0.5 (the option may be given more than once)"""
    w = {}
    for s in specs:
        for part in s.split(','):
            if not part.strip(): continue
            k, _, v = part.partition('=')
            if not _ or float(v) < 0: sys.exit(f'--weights: {part!r} is not N=w with w >= 0')
            w[k.strip().upper()] = float(v)
    return w

def read_manifest(root):
    f = os.path.join(root, 'manifest.json')
    if not os.path.exists(f): return None, None
    return json.load(open(f, encoding='utf8')), sha256(f)

def content_sha(man):
    """the manifest's content_sha256 (sha256 of json.dumps(plates, sort_keys=True)), checked against its plates"""
    if not man or not isinstance(man.get('plates'), dict): return None
    c = hashlib.sha256(json.dumps(man['plates'], sort_keys=True).encode()).hexdigest()
    if man.get('content_sha256') not in (None, c): sys.exit(f'manifest.json: content_sha256 {str(man.get("content_sha256"))[:12]} is not that of its plates ({c[:12]}): it was edited by hand')
    return c

def write_json(path, obj):
    """json written whole or not at all (integrator, 24 Nov; review-code 3): a temporary file, then os.replace, tried
    again for up to 10 s if Windows refuses the replace (a reader has the file open)"""
    tmp = f'{path}.{os.getpid()}.tmp'
    with open(tmp, 'w', encoding='utf8', newline='\n') as f: json.dump(obj, f, indent=1)
    replace_retry(tmp, path)

def replace_retry(tmp, path):
    for k in range(50):
        try: os.replace(tmp, path); return
        except PermissionError:
            if k == 49: raise
            time.sleep(0.2)

def save_state(state, path):
    """torch.save written whole or not at all (a temporary file, then os.replace)"""
    tmp = f'{path}.{os.getpid()}.tmp'; torch.save(state, tmp); replace_retry(tmp, path)

def out_dir(o):
    """--out of a --data run (default data/sanborn/train_v2_runs/models); never inside unet_data, where the batch's own
    models are (integrator, 24 Nov; review-code 6)"""
    d = os.path.abspath(o['--out'][-1]) if '--out' in o else os.path.abspath(_ws.DATA + 'train_v2_runs/models')
    u = os.path.normcase(os.path.abspath(DATA)).rstrip('\\/'); n = os.path.normcase(d).rstrip('\\/')
    if n == u or n.startswith(u + os.sep): sys.exit(f'--out {d}: a --data run never writes into unet_data (the batch\'s own models are there)')
    return d

def val_every_arg(o, default):
    v = int(o['--val-every'][-1]) if '--val-every' in o else default
    if v < 1: sys.exit('--val-every must be 1 or more')
    return v

def manifest_entry(man, plate):
    """the manifest's entry of a plate: {'plates': {N: {...}}} or {'plates': [{'plate': N, ...}]}"""
    if not man: return None
    P = man.get('plates', man)
    if isinstance(P, dict): return P.get(plate)
    if isinstance(P, list): return next((e for e in P if isinstance(e, dict) and str(e.get('plate')) == plate), None)
    return None

def manifest_sha(entry, fname):
    """the sha256 the manifest gives a file: files: {name: sha} or {name: {sha256: ...}}, or [{name|file, sha256}]"""
    if not entry: return None
    if fname == 'meta.json' and isinstance(entry.get('meta_sha256'), str): return entry['meta_sha256']   # integrator, 24 Nov (review-code 7): make_labels_v2 keeps meta.json's hash here
    F = entry.get('files', {})
    if isinstance(F, dict):
        v = F.get(fname); return v if isinstance(v, str) else (v or {}).get('sha256')
    if isinstance(F, list):
        e = next((e for e in F if isinstance(e, dict) and (e.get('name') == fname or e.get('file') == fname)), None)
        return e.get('sha256') if e else None
    return None

def plate_files(root, plate, man, names):
    """sha256 of each file read from DIR/plate, checked against the manifest (a mismatch stops the run: the data
    folder changed after its manifest was made)"""
    entry = manifest_entry(man, plate); out = {}
    for n in names:
        f = os.path.join(root, plate, n)
        if not os.path.exists(f): continue
        s = sha256(f); m = manifest_sha(entry, n)
        if m is not None and m != s: sys.exit(f'{plate}/{n}: sha256 {s[:12]} is not the manifest\'s {m[:12]}: the data folder changed after its manifest; refusing to train')
        out[n] = dict(sha256=s, in_manifest=m is not None)
    return out, entry

def plate_list(root, specs, man):
    if not specs:
        P = (man or {}).get('plates', {})
        specs = list(P) if isinstance(P, dict) else [str(e.get('plate')) for e in P if isinstance(e, dict)]
        if not specs: specs = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))
    out = []
    for s in specs:
        p, _, how = s.partition(':'); p = p.upper()
        if p in FORBIDDEN: sys.exit(f'plate {p} may not be used in training or to choose a checkpoint (FORBIDDEN = {FORBIDDEN})')
        if how not in ('', 'val', 'all'): sys.exit(f'{s}: the suffix must be :val or :all')
        if not os.path.isdir(os.path.join(root, p)): sys.exit(f'no plate folder {os.path.join(root, p)}')
        out.append((p, how))
    return out

def box_sum(ii, y0, x0, y1, x1):
    """sum of a mask over rows y0..y1-1, columns x0..x1-1 from its integral image (cv2.integral), clipped to the mask"""
    H, W = ii.shape[0] - 1, ii.shape[1] - 1
    y0, x0, y1, x1 = max(0, y0), max(0, x0), min(H, y1), min(W, x1)
    if y0 >= y1 or x0 >= x1: return 0
    return int(ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0])

def bbox(mask):
    ys, xs = np.nonzero(mask.any(1))[0], np.nonzero(mask.any(0))[0]
    return int(ys[0]), int(ys[-1]) + 1, int(xs[0]), int(xs[-1]) + 1

def read_valmask(root, plate, shape):
    f = os.path.join(root, plate, 'valmask.png')
    if not os.path.exists(f): return None
    v = cv2.imread(f, 0)
    if v.shape != shape: sys.exit(f'{plate}/valmask.png is {v.shape}, the label {shape}')
    v = v > 0
    return v if v.any() else None

def read_meta(root, plate):
    f = os.path.join(root, plate, 'meta.json')
    return json.load(open(f, encoding='utf8')) if os.path.exists(f) else {}

def meta_scale(meta):
    """the plate's scale in feet to the inch from its meta.json: scale_ft_per_inch, ft_per_inch, or scale (a number or {ft_per_inch})"""
    for k in ('scale_ft_per_inch', 'ft_per_inch'):
        if isinstance(meta.get(k), (int, float)): return meta[k]
    s = meta.get('scale')
    return s if isinstance(s, (int, float)) else (s.get('ft_per_inch') if isinstance(s, dict) else None)

def load_data(root, plate):
    """a plate of the data folder as load() + load_edge() give it: x (h, w, 5: R, G, B and the blank guide), the label,
    the edge weight map and target. edge.png missing or empty: no verified edges known, so the third output is not
    taught on the plate (weights 1, target 255), as load_edge does without N_edge.png"""
    d = os.path.join(root, plate); im = cv2.imread(os.path.join(d, 'img.jpg')); lab = cv2.imread(os.path.join(d, 'label.png'), 0)
    if im is None or lab is None: sys.exit(f'{plate}: img.jpg or label.png missing in {d}')
    if lab.shape != im.shape[:2]: sys.exit(f'{plate}: label.png {lab.shape} and img.jpg {im.shape[:2]} differ in size')
    bad = np.setdiff1d(np.unique(lab), [0, 1, 255])
    if len(bad): sys.exit(f'{plate}/label.png has values {bad.tolist()} (only 0, 1, 255)')
    e = cv2.imread(os.path.join(d, 'edge.png'), 0)
    if e is not None and e.shape != lab.shape: sys.exit(f'{plate}: edge.png {e.shape} and label.png {lab.shape} differ in size')
    edge_known = e is not None and bool(e.any())
    wm, et = edge_maps(e if edge_known else None, lab)
    z = np.zeros(lab.shape, np.uint8)
    return np.dstack([im[:, :, ::-1], z, z]), lab, wm, et, edge_known

def crop_ok_share(rng, lab, vint, n=2000):
    """share of random crop positions the sampler accepts (>= 20% taught, no validation pixel)"""
    H, W = lab.shape; ok = 0
    for _ in range(n):
        y, x = rng.integers(0, H - CROP), rng.integers(0, W - CROP)
        if vint is not None and box_sum(vint, y, x, y + CROP, x + CROP): continue
        ok += (lab[y:y + CROP, x:x + CROP] != 255).mean() >= 0.2
    return ok / n

def draw_crop(rng, P):
    """(y, x) of a training crop on plate P: at least 20% taught pixels, and not one validation pixel (P['vint'], the
    integral image of valmask; such a crop is drawn again, so a training crop cannot overlap the validation ground)"""
    lab, vint = P['lab'], P['vint']; H, W = lab.shape
    for _ in range(MAX_TRIES):
        y = rng.integers(0, H - CROP); x = rng.integers(0, W - CROP)
        if vint is not None and box_sum(vint, y, x, y + CROP, x + CROP): continue
        if (lab[y:y + CROP, x:x + CROP] != 255).mean() < 0.2: continue
        return y, x
    raise RuntimeError(f'plate {P["plate"]}: no usable crop in {MAX_TRIES} tries')

def counts(p, lab):
    """pixel counts on the scored pixels (lab != 255) for pooling the score over plates"""
    m = lab != 255; pr = p[m] > 0.5; gt = lab[m] == 1
    return np.array([m.sum(), (pr == gt).sum(), (pr & gt).sum(), (pr | gt).sum(), (~pr & ~gt).sum(), (~pr | ~gt).sum()], np.int64)

def pooled(c):
    return dict(pixels=int(c[0]), accuracy=round(float(c[1] / max(1, c[0])), 6), iou_block=round(float(c[2] / max(1, c[3])), 6), iou_street=round(float(c[4] / max(1, c[5])), 6))

def cpu_state(net): return {k: v.detach().to('cpu') for k, v in net.state_dict().items()}

def train_data(name, root, specs, iters, seed, weights, outdir, val_every):
    """--data: the plates of a data folder, keep-best on the validation pixels (see the docstring)"""
    root = os.path.abspath(root); man, man_sha = read_manifest(root)
    if man is None: print('WARNING: no manifest.json in', root, flush=True)
    if seed is not None: seed_all(seed)
    rng = np.random.default_rng(0 if seed is None else seed); dev = device(); tr, va, rec = [], [], []
    for p, how in plate_list(root, specs, man):
        x, lab, wm, et, edge_known = load_data(root, p); vm = read_valmask(root, p, lab.shape); meta = read_meta(root, p)
        files, entry = plate_files(root, p, man, ('img.jpg', 'label.png', 'edge.png', 'valmask.png', 'meta.json'))
        if how == 'all' and vm is not None: sys.exit(f'{p}:all: the plate has a valmask.png; refusing to train on its validation pixels')
        if how == 'val': vm = np.ones(lab.shape, bool)
        r = dict(plate=p, spec=p + (':' + how if how else ''), source=meta.get('source', (entry or {}).get('source', 'unknown')), weight=weights.get(p, 1.0),
                 size=list(lab.shape[::-1]), taught_px=int((lab != 255).sum()), edge_target='edge.png' if edge_known else 'none (edge.png missing or empty)', files=files,
                 scale_ft_per_inch=meta_scale(meta))
        if vm is not None:
            y0, y1, x0, x1 = bbox(vm); lv = lab[y0:y1, x0:x1].copy(); lv[~vm[y0:y1, x0:x1]] = 255; ev = et[y0:y1, x0:x1].copy(); ev[~vm[y0:y1, x0:x1]] = 255
            va.append(dict(plate=p, x=np.ascontiguousarray(x[y0:y1, x0:x1]), lab=lv, et=ev)); r['val_box'] = [x0, y0, x1, y1]; r['val_px'] = int((lv != 255).sum())
        if how != 'val':
            vint = cv2.integral(vm.astype(np.uint8)) if vm is not None else None
            tl = lab.copy()
            if vm is not None: tl[vm] = 255   # (belt and braces: a crop never reaches them, see draw_crop)
            P = dict(plate=p, x=x, lab=tl, wm=wm, et=et, vint=vint); r['train_px'] = int((tl != 255).sum())
            r['crop_ok_share'] = round(crop_ok_share(np.random.default_rng(12345), tl, vint), 4)
            if r['crop_ok_share'] == 0: sys.exit(f'plate {p}: no crop position has 20% taught pixels outside the validation ground')
            if r['weight'] > 0: tr.append(P)
            else: print(f'{p}: weight 0, not sampled', flush=True)
        rec.append(r); print(json.dumps({k: v for k, v in r.items() if k != 'files'}), flush=True)
    if not tr: sys.exit('no training plate')
    unknown = set(weights) - {r['plate'] for r in rec}
    if unknown: sys.exit(f'--weights names plates not in the run: {sorted(unknown)}')
    w = np.array([weights.get(P['plate'], 1.0) for P in tr], float); prob = w / w.sum(); drawn = np.zeros(len(tr), int)
    os.makedirs(outdir, exist_ok=True); mem_load = mem_now(); print(json.dumps(dict(stored_gb=round(sum(P['x'].nbytes + P['lab'].nbytes + P['wm'].nbytes + P['et'].nbytes for P in tr) / 1e9, 3), process=mem_load)), flush=True)
    wt = torch.tensor([3.0, 1.0]).to(dev)
    net = UNet().to(dev); opt = torch.optim.Adam(net.parameters(), 1e-3); t0 = time.time(); hist = []; best = None
    info = dict(name=name, kind='area', mode='data', data=root, manifest_sha256=man_sha, manifest_content_sha256=content_sha(man), seed=seed, git=git_state(), trainer=dict(file=os.path.abspath(__file__), sha256=sha256(__file__)),
                torch=torch.__version__, device=device.name, argv=sys.argv[1:], iters=iters, crop=CROP, batch=BATCH, no_guide=True, guide_moved_or_erased=False, val_every=val_every,
                select_by='iou_street on the validation pixels pooled over the plates, then accuracy', sampling='plate first (probability weight / sum), then a crop on it',
                val_scope='each plate\'s validation pixels predicted from their own bounding box (no scan beyond it); eval_v2 predicts the whole plate, which moved IoU street by about 0.01 on 1A (review-code test_valcontext): checkpoints closer than that are within tiling noise',
                load=dict(stored_bytes=int(sum(P['x'].nbytes + P['lab'].nbytes + P['wm'].nbytes + P['et'].nbytes for P in tr)), process_after_load=mem_load), plates=rec)
    def save_json():
        info.update(crops_drawn={P['plate']: int(n) for P, n in zip(tr, drawn)}, best=best and dict(iter=best[0], iou_street=round(best[1][0], 6), accuracy=round(best[1][1], 6)), history=hist, minutes=round((time.time() - t0) / 60, 2), process_peak=mem_now())
        write_json(os.path.join(outdir, name + '.json'), info)
    tt, nt = 0.0, 0   # time in training steps (crops, forward, backward) since the last check
    for it in range(1, iters + 1):
        ti = time.time()
        xs, ys, ws, es = [], [], [], []
        while len(xs) < BATCH:
            i = int(rng.integers(len(tr))) if np.all(w == w[0]) else int(rng.choice(len(tr), p=prob)); P = tr[i]; y, x = draw_crop(rng, P); drawn[i] += 1
            a, b = P['x'][y:y + CROP, x:x + CROP].copy(), P['lab'][y:y + CROP, x:x + CROP]; c_, e_ = P['wm'][y:y + CROP, x:x + CROP], P['et'][y:y + CROP, x:x + CROP]
            k = rng.integers(4); a, b, c_, e_ = np.rot90(a, k), np.rot90(b, k), np.rot90(c_, k), np.rot90(e_, k)
            if rng.random() < 0.5: a, b, c_, e_ = a[:, ::-1], b[:, ::-1], c_[:, ::-1], e_[:, ::-1]
            a = a.astype(np.float32); a[:, :, :3] = np.clip(a[:, :, :3] * rng.uniform(0.8, 1.2) + rng.uniform(-20, 20) + rng.normal(0, 3, 3), 0, 255)
            xs.append(a); ys.append(b); ws.append(c_); es.append(e_)
        for g in opt.param_groups: g['lr'] = 1e-3 * 0.5 * (1 + np.cos(np.pi * it / iters))
        net.train(); out = net(norm(np.stack(xs)).to(dev))
        yt = torch.from_numpy(np.stack(ys).astype(np.int64)).to(dev); wtm = torch.from_numpy(np.ascontiguousarray(np.stack(ws))).to(dev)
        ce = F.cross_entropy(out[:, :2], yt, weight=wt, ignore_index=255, reduction='none'); ok = (yt != 255).float()
        seg = (ce * wtm * ok).sum() / (wtm * ok).sum().clamp(min=1.0)
        en = np.stack(es); ev = torch.from_numpy((en != 255).astype(np.float32)).to(dev); etn = torch.from_numpy((en == 1).astype(np.float32)).to(dev)
        bce = F.binary_cross_entropy_with_logits(out[:, 2], etn, reduction='none') * (1.0 + (EDGE_POS - 1.0) * etn)
        loss = seg + EDGE_LOSS * (bce * ev).sum() / ev.sum().clamp(min=1.0)
        opt.zero_grad(); loss.backward(); opt.step(); tt += time.time() - ti; nt += 1
        if it % val_every == 0 or it == iters:
            h = dict(iter=it, loss=round(float(loss), 4), minutes=round((time.time() - t0) / 60, 2)); h['train_s_per_iter'] = round(tt / max(1, nt), 3); tv = time.time()
            if va:
                c = np.zeros(6, np.int64); sc = {}
                for V in va:
                    pp = predict_full(net, dev, V['x']); c += counts(pp, V['lab']); sc[V['plate']] = score(pp, V['lab'], V['et'], predict_full.edge)
                h['val'] = sc; h['val_pooled'] = pooled(c); key = (c[4] / max(1, c[5]), c[1] / max(1, c[0]))
                if best is None or key > best[1]:
                    best = (it, (float(key[0]), float(key[1]))); save_state(cpu_state(net), os.path.join(outdir, name + '.pt')); h['best'] = True   # the key kept unrounded (review-code 12)
            h['val_s'] = round(time.time() - tv, 2); hist.append(h); print(json.dumps(h), flush=True); save_json(); tt, nt = 0.0, 0
    save_state(cpu_state(net), os.path.join(outdir, name + '_last.pt'))
    if not va: save_state(cpu_state(net), os.path.join(outdir, name + '.pt')); info['note'] = 'no validation pixels: NAME.pt is the last'
    save_json(); print('wrote', os.path.join(outdir, name + '.pt'), 'best', info['best'], flush=True)

def mem_now():
    """this process's memory (Windows: working set, its peak, and private bytes), GB"""
    try:
        import ctypes, ctypes.wintypes as wt
        class PMC(ctypes.Structure):
            _fields_ = [('cb', wt.DWORD), ('PageFaultCount', wt.DWORD), ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t), ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPagedPoolUsage', ctypes.c_size_t), ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t), ('PagefileUsage', ctypes.c_size_t),
                        ('PeakPagefileUsage', ctypes.c_size_t), ('PrivateUsage', ctypes.c_size_t)]
        c = PMC(); c.cb = ctypes.sizeof(PMC); k = ctypes.windll.kernel32; ps = ctypes.windll.psapi
        ps.GetProcessMemoryInfo.argtypes = [wt.HANDLE, ctypes.POINTER(PMC), wt.DWORD]; k.GetCurrentProcess.restype = wt.HANDLE
        ps.GetProcessMemoryInfo(k.GetCurrentProcess(), ctypes.byref(c), c.cb)
        return dict(working_set_gb=round(c.WorkingSetSize / 1e9, 3), peak_working_set_gb=round(c.PeakWorkingSetSize / 1e9, 3), private_gb=round(c.PrivateUsage / 1e9, 3), peak_private_gb=round(c.PeakPagefileUsage / 1e9, 3))
    except Exception as e:
        return dict(error=str(e))

def predict(name, plate):
    dev = device(); net = UNet(); net.load_state_dict(torch.load(DATA + f'models/{name}.pt', map_location='cpu')); net.to(dev)
    img, _ = load(plate); p = predict_full(net, dev, img)
    cv2.imwrite(DATA + f'{plate}_pred_{name}.png', (p * 255).astype(np.uint8)); cv2.imwrite(DATA + f'{plate}_edgepred_{name}.png', (predict_full.edge * 255).astype(np.uint8))
    print('wrote', f'{plate}_pred_{name}.png', p.shape)

VALUED = ('--iters', '--data', '--seed', '--weights', '--out', '--val-every')
FLAGS = ('--no-guide', '--legacy-noguide')
def parse(argv):
    """positional words and options; an option this file does not know is an error"""
    pos, opt, k = [], {}, 0
    while k < len(argv):
        a = argv[k]
        if a in VALUED:
            if k + 1 >= len(argv): sys.exit(f'{a} needs a value')
            opt.setdefault(a, []).append(argv[k + 1]); k += 2
        elif a in FLAGS: opt[a] = [True]; k += 1
        elif a.startswith('--'): sys.exit(f'unknown option {a} (known: {", ".join(VALUED + FLAGS)})')
        else: pos.append(a); k += 1
    return pos, opt

if __name__ == '__main__':
    a, o = parse(sys.argv[1:])
    it = int(o['--iters'][-1]) if '--iters' in o else 3000
    if not a or a[0] not in ('train', 'predict'): sys.exit(__doc__)
    if '--data' in o:
        if a[0] != 'train': sys.exit('--data is for train')
        if LEGACY_NOGUIDE: sys.exit('--legacy-noguide is not for --data')
        train_data(a[1], o['--data'][-1], a[2:], it, int(o['--seed'][-1]) if '--seed' in o else None, parse_weights(o.get('--weights', [])),
                   out_dir(o), val_every_arg(o, VAL_EVERY))
    else:
        for k in ('--seed', '--weights', '--out', '--val-every'):
            if k in o: sys.exit(f'{k} is for --data (the unet_data plates train as before)')
        train(a[1], a[2:], it) if a[0] == 'train' else predict(a[1], a[2])
