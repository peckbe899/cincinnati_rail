"""A U-net that finds the block lines (the green lines) on a Sanborn plate (14 November 2026).

    cd data/sanborn
    PY=../../tools/sanborn/unet/.venv/Scripts/python.exe
    $PY ../../tools/sanborn/unet/edgenet.py train NAME PLATE ... PLATE:val [--iters 3000]   -> unet_data/models/NAME.pt, NAME.json
    $PY ../../tools/sanborn/unet/edgenet.py predict NAME PLATE                              -> unet_data/PLATE_lines_NAME.png (full size, 0-255)

Ben, 14 November 2026: teach the U-nets to find where the green lines are. The first attempt (unet.py's third output)
drew 92% of the green edges but only 7% of what it drew was one: it marked lot lines, pipes and lettering too. It worked
at half size, was told nothing about what is NOT a block line, and was weighted 12 to 1 toward drawing.
This network is built for the one job:
- full size: a block line is 3 or 4 px wide on the scan; at half size it is one pixel;
- input: the scan (3), the black/grey ink image (make_labels.ink_image: colour bands and tints removed), the guide
  (today's block outlines and centre lines through the rough placement, moved up to JIT px at random in training), and
  (15 Nov, second try) the area network's street / block prediction: a block line has street on one side, which a
  railway, a creek bank or a lot line does not;
- target: the verified edges (unet_data/N_verified.json), drawn LINE px wide;
- what is not a block line: every other ink pixel on taught ground (lot lines, pipes, house numbers, lettering) is a
  negative and counts NEG_INK times a blank-paper pixel, so "black line" alone is not enough;
- not scored: off the paper, ground the label leaves blank (unverified edges run there, and nothing says whether a line
  there is a block line), and a GAP px margin beside each verified edge (the line's own width varies);
- loss: weighted cross-entropy plus a Dice term on the line, so it is drawn thin and whole.
Score, on plates held out whole: precision (share of what it draws that is within TOL px of a verified edge, on taught
ground) and recall (share of verified edge length it draws within TOL px).

23 November 2026 (data/sanborn/bench_2026-11-23/train). New options, as unet.py's (see there); without them the trainer
does what it did before, except that under --no-guide the blank guide is no longer moved or blanked at random (no
effect on the input, only on the random draws; --legacy-noguide keeps the old draws) and an unknown option is an error:

    $PY edgenet.py train NAME --data DIR [PLATE[:val] ...] [--seed S] [--weights N=w,...] [--out MODELDIR]
                [--iters 3000] [--val-every 250]

  --data DIR   the plates of a data folder: the full-size scan cufp/22-N.jpg (or DIR/N/full.jpg if there is one),
               DIR/N/lines.png (full size: 1 line, 0 not, 255 not scored; for a labelled plate it is what load()
               builds), DIR/N/area_in.png (half size, P(block) * 255: the 7th input; missing: 128, as load() without
               the area map), DIR/N/valmask.png (optional, half size, 1 = validation) and meta.json. The guide is
               blank. --area is not used (the 7th input is area_in.png). Plates 44 and 90 are refused.
  memory       a plate is held as one uint8 array H x W x 5 (R, G, B, the 7th input at full size, the target): 5 bytes
               a pixel against 12 for load() (7 channels, target, float32 weights). The ink image is made per crop
               from the crop's own scan (ink_image works pixel by pixel, so it is the same as from the whole scan),
               the blank guide channels are zeros, and the weights (1, NEG_INK on ink that is not a line, POS on the
               line) are made per crop from the crop's ink and target, as load() makes them for the whole plate.
  keep-best    F1 of precision and recall (score(), pooled over the plates' validation pixels) every --val-every
               iterations and at the end: NAME.pt is the best, NAME_last.pt the last. The validation ground is
               predicted from its own bounding box (no training ground around it). A training crop never overlaps
               a validation pixel: the full-size crop is tested against the half-size valmask's integral image with
               one half-size pixel to spare on every side (the nearest-neighbour resize puts full-size row Y on
               half-size row floor(Y h / H), which lies in [Y//2 - 1, Y//2]); such a crop is drawn again.
  model json   as unet.py's, plus each plate's area_in provenance from its meta.json.
"""
import json, os, sys, time
import numpy as np
import cv2
import torch, torch.nn.functional as F
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
import _ws  # noqa: E402
from unet import UNet, device  # noqa: E402
import unet as U_  # noqa: E402   (23 Nov: the data folder helpers)
SP = _ws.DATA; DATA = SP + 'unet_data/'; CROP, BATCH, LINE, GAP, TOL, JIT, NEG_INK, POS = 448, 6, 3, 4, 3, 24, 4.0, 3.0
NOGUIDE = '--no-guide' in sys.argv   # 21 Nov 2026: for plates that were never placed, the guide channels are blank (see unet.py); --area NAME names the area network
LEGACY_NOGUIDE = '--legacy-noguide' in sys.argv
AREA = sys.argv[sys.argv.index('--area') + 1] if '--area' in sys.argv else 'edge_v1'       # the area network whose street / block prediction is the seventh input (15 Nov 2026)

def ink_image(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV); gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))
    return np.where(ink, gray, 255).astype(np.uint8), ink

def load(plate):
    """x: H x W x 6 uint8 (R, G, B, ink, guide block outline, guide centre lines); t: 1 line, 0 not, 255 not scored; w: weights"""
    full = cv2.imread(SP + f'cufp/22-{plate}.jpg'); H, W = full.shape[:2]
    inkimg, ink = ink_image(full)
    g = cv2.imread(DATA + f'{plate}_guide.png'); gb = cv2.resize(g[:, :, 0], (W, H), interpolation=cv2.INTER_NEAREST); gc = cv2.resize(g[:, :, 1], (W, H), interpolation=cv2.INTER_NEAREST)
    gedge = cv2.morphologyEx(gb, cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8))          # today's block outlines, rough
    sp = cv2.imread(DATA + f'{plate}_pred_{AREA}.png', 0)             # the area network's P(block), half size: which side of a line is street
    sp = cv2.resize(sp, (W, H), interpolation=cv2.INTER_LINEAR) if sp is not None else np.full((H, W), 128, np.uint8)
    if NOGUIDE: gedge, gc = gedge * 0, gc * 0
    x = np.dstack([full[:, :, ::-1], inkimg, gedge, gc, sp])
    lab = cv2.resize(cv2.imread(DATA + f'{plate}_label.png', 0), (W, H), interpolation=cv2.INTER_NEAREST)
    line = np.zeros((H, W), np.uint8); vf = DATA + f'{plate}_verified.json'
    for a, b in (json.load(open(vf, encoding='utf8')) if os.path.exists(vf) else []):
        cv2.line(line, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), 1, LINE)
    alpha = cv2.resize(np.load(SP + f'cufp/{plate}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
    near = cv2.dilate(line, np.ones((2 * (LINE + GAP) + 1, 2 * (LINE + GAP) + 1), np.uint8)) > 0
    t = np.where(line > 0, 1, 0).astype(np.uint8)
    t[(lab == 255) & ~near] = 255                     # blank ground: not scored (but a verified edge and its sides are)
    t[near & (line == 0)] = 255                       # the margin beside a verified edge
    t[~alpha] = 255
    wgt = np.ones((H, W), np.float32); wgt[ink & (t == 0)] = NEG_INK; wgt[t == 1] = POS
    return x, t, wgt

def norm(a): return torch.from_numpy(np.ascontiguousarray(a.transpose(0, 3, 1, 2))).float() / 255.0

def predict_full(net, dev, x, tile=1024, pad=96):
    h, w = x.shape[:2]; out = np.zeros((h, w), np.float32); step = tile - 2 * pad
    im = cv2.copyMakeBorder(x, pad, pad + tile, pad, pad + tile, cv2.BORDER_REFLECT); net.eval()
    with torch.no_grad():
        for y in range(0, h, step):
            for xx in range(0, w, step):
                p = F.softmax(net(norm(im[None, y:y + tile, xx:xx + tile]).to(dev)), 1)[0, 1].cpu().numpy()[pad:pad + step, pad:pad + step]
                out[y:y + step, xx:xx + step] = p[:min(step, h - y), :min(step, w - xx)]
    return out

def score(p, t):
    pr = p > 0.5; k = np.ones((2 * TOL + 1, 2 * TOL + 1), np.uint8); line = t == 1; scored = t != 255
    near_line = cv2.dilate(line.astype(np.uint8), k) > 0; near_pr = cv2.dilate(pr.astype(np.uint8), k) > 0
    drawn = pr & (scored | near_line)                 # what it draws where there is an answer
    return dict(precision=round(float((drawn & near_line).sum() / max(1, drawn.sum())), 4), recall=round(float((line & near_pr).sum() / max(1, line.sum())), 4),
                drawn_share_of_plate=round(float(pr.mean()), 4), line_share_of_plate=round(float(line.mean()), 4))

def train(name, plates, iters):
    dev = device(); rng = np.random.default_rng(0); tr, va = [], []
    for spec in plates:
        p, _, how = spec.partition(':'); x, t, wg = load(p); print(p, x.shape, 'line px', int((t == 1).sum()), 'scored', round(float((t != 255).mean()), 2), flush=True)
        (va if how == 'val' else tr).append((p, x, t, wg))
    net = UNet(classes=2, in_ch=7).to(dev); opt = torch.optim.Adam(net.parameters(), 1e-3); t0 = time.time(); hist = []
    for it in range(1, iters + 1):
        xs, ts, ws = [], [], []
        while len(xs) < BATCH:
            _, x, t, wg = tr[rng.integers(len(tr))]; y = rng.integers(JIT, x.shape[0] - CROP - JIT); xx = rng.integers(JIT, x.shape[1] - CROP - JIT)
            b = t[y:y + CROP, xx:xx + CROP]
            if (b == 1).sum() < 60 and rng.random() < 0.8: continue          # mostly crops that have a line in them
            a = x[y:y + CROP, xx:xx + CROP].copy()
            if not NOGUIDE or LEGACY_NOGUIDE:                                    # 23 Nov: a blank guide is neither moved nor blanked (it is zeros)
                dy, dx = rng.integers(-JIT, JIT + 1, 2)
                a[:, :, 4:6] = x[y + dy:y + dy + CROP, xx + dx:xx + dx + CROP, 4:6]  # the guide is only roughly placed
                if rng.random() < 0.3: a[:, :, 4:6] = 0                              # and sometimes missing: the line has to be found on the print
            if rng.random() < 0.15: a[:, :, 6] = 128                             # and sometimes no area prediction either
            c = wg[y:y + CROP, xx:xx + CROP]; k = rng.integers(4); a, b, c = np.rot90(a, k), np.rot90(b, k), np.rot90(c, k)
            if rng.random() < 0.5: a, b, c = a[:, ::-1], b[:, ::-1], c[:, ::-1]
            a = a.astype(np.float32); a[:, :, :3] = np.clip(a[:, :, :3] * rng.uniform(0.85, 1.15) + rng.uniform(-15, 15), 0, 255)
            xs.append(a); ts.append(b); ws.append(c)
        for g_ in opt.param_groups: g_['lr'] = 1e-3 * 0.5 * (1 + np.cos(np.pi * it / iters))
        net.train(); out = net(norm(np.stack(xs)).to(dev)); tn = np.stack(ts)
        yt = torch.from_numpy(np.where(tn == 255, 0, tn).astype(np.int64)).to(dev); ok = torch.from_numpy((tn != 255).astype(np.float32)).to(dev)
        wt = torch.from_numpy(np.ascontiguousarray(np.stack(ws))).to(dev) * ok
        ce = (F.cross_entropy(out, yt, reduction='none') * wt).sum() / wt.sum().clamp(min=1.0)
        pl = F.softmax(out, 1)[:, 1] * ok; tl = yt.float() * ok
        dice = 1 - (2 * (pl * tl).sum() + 1) / (pl.sum() + tl.sum() + 1)
        loss = ce + dice
        opt.zero_grad(); loss.backward(); opt.step()
        if it % 500 == 0 or it == iters:
            sc = {p: score(predict_full(net, dev, x), t) for p, x, t, _ in va}
            hist.append(dict(iter=it, loss=round(float(loss), 4), minutes=round((time.time() - t0) / 60, 1), val=sc)); print(json.dumps(hist[-1]), flush=True)
            torch.save(net.state_dict(), DATA + f'models/{name}.pt')
            json.dump(dict(name=name, plates=plates, iters=iters, crop=CROP, batch=BATCH, line_px=LINE, tol_px=TOL, no_guide=NOGUIDE, legacy_noguide=LEGACY_NOGUIDE, history=hist), open(DATA + f'models/{name}.json', 'w', encoding='utf8', newline='\n'), indent=1)


# ====================================================================== 23 Nov 2026: the data folder (--data), seeds, keep-best
def scan_path(root, plate):
    f = os.path.join(root, plate, 'full.jpg')
    return f if os.path.exists(f) else SP + f'cufp/22-{plate}.jpg'

def pack(full_bgr, area_half, t):
    """one plate as H x W x 5 uint8: R, G, B, the 7th input (area_half resized as load() resizes the area map, or 128
    where there is none) and the target. full_bgr is consumed (pass a fresh array)"""
    H, W = full_bgr.shape[:2]; S = np.empty((H, W, 5), np.uint8)
    S[:, :, :3] = full_bgr[:, :, ::-1]
    S[:, :, 3] = cv2.resize(area_half, (W, H), interpolation=cv2.INTER_LINEAR) if area_half is not None else 128
    S[:, :, 4] = t
    return S

def build(S, y0, y1, x0, x1):
    """the 7-channel input, target and weights of S[y0:y1, x0:x1], as load() gives them for that window: R, G, B,
    ink, blank guide (2), 7th input; weights 1, NEG_INK on ink that is not a line, POS on the line"""
    a = S[y0:y1, x0:x1]; h, w = a.shape[:2]
    inkimg, ink = ink_image(np.ascontiguousarray(a[:, :, 2::-1]))
    x = np.zeros((h, w, 7), np.uint8); x[:, :, :3] = a[:, :, :3]; x[:, :, 3] = inkimg; x[:, :, 6] = a[:, :, 3]
    t = a[:, :, 4].copy(); wg = np.ones((h, w), np.float32); wg[ink & (t == 0)] = NEG_INK; wg[t == 1] = POS
    return x, t, wg

def load_data(root, plate):
    d = os.path.join(root, plate); full = cv2.imread(scan_path(root, plate))
    if full is None: sys.exit(f'{plate}: no scan {scan_path(root, plate)}')
    H, W = full.shape[:2]; t = cv2.imread(os.path.join(d, 'lines.png'), 0)
    if t is None: sys.exit(f'{plate}: no lines.png in {d}')
    if t.shape != (H, W): sys.exit(f'{plate}: lines.png is {t.shape[::-1]}, the scan {(W, H)}')
    bad = np.setdiff1d(np.unique(t), [0, 1, 255])
    if len(bad): sys.exit(f'{plate}/lines.png has values {bad.tolist()} (only 0, 1, 255)')
    a = cv2.imread(os.path.join(d, 'area_in.png'), 0)
    if a is not None and a.shape != (H // 2, W // 2): print(f'WARNING {plate}: area_in.png is {a.shape[::-1]}, half the scan is {(W // 2, H // 2)}', flush=True)
    return pack(full, a, t), a is not None

def overlaps_val(vint, y, x, C):
    """does the full-size crop rows y..y+C-1, columns x..x+C-1 touch a validation pixel (half-size integral image, one
    half-size pixel to spare on each side)"""
    return U_.box_sum(vint, y // 2 - 1, x // 2 - 1, (y + C - 1) // 2 + 2, (x + C - 1) // 2 + 2) > 0

def draw_crop(rng, P):
    """(y, x) of a training crop: never on the validation ground; mostly crops with a line in them (as train())"""
    S, vint = P['S'], P['vint']; H, W = S.shape[:2]
    for _ in range(U_.MAX_TRIES):
        y = rng.integers(JIT, H - CROP - JIT); x = rng.integers(JIT, W - CROP - JIT)
        if vint is not None and overlaps_val(vint, y, x, CROP): continue
        if (S[y:y + CROP, x:x + CROP, 4] == 1).sum() < 60 and rng.random() < 0.8: continue
        return y, x
    raise RuntimeError(f'plate {P["plate"]}: no usable crop in {U_.MAX_TRIES} tries')

def line_counts(p, t, vm=None):
    """score()'s counts (drawn, drawn near a line, line, line near the drawing), for pooling over plates; vm: only
    these pixels may count as drawn"""
    pr = p > 0.5
    if vm is not None: pr &= vm
    k = np.ones((2 * TOL + 1, 2 * TOL + 1), np.uint8); line = t == 1; scored = t != 255
    near_line = cv2.dilate(line.astype(np.uint8), k) > 0; near_pr = cv2.dilate(pr.astype(np.uint8), k) > 0
    drawn = pr & (scored | near_line)
    return np.array([drawn.sum(), (drawn & near_line).sum(), line.sum(), (line & near_pr).sum()], np.int64)

def prf(c):
    P = c[1] / max(1, c[0]); R = c[3] / max(1, c[2]); return dict(precision=round(float(P), 6), recall=round(float(R), 6), f1=round(float(2 * P * R / max(1e-12, P + R)), 6), drawn_px=int(c[0]), line_px=int(c[2]))

def train_data(name, root, specs, iters, seed, weights, outdir, val_every):
    root = os.path.abspath(root); man, man_sha = U_.read_manifest(root)
    if man is None: print('WARNING: no manifest.json in', root, flush=True)
    if seed is not None: U_.seed_all(seed)
    rng = np.random.default_rng(0 if seed is None else seed); dev = device(); tr, va, rec = [], [], []; T0 = time.time()
    for p, how in U_.plate_list(root, specs, man):
        S, has_area = load_data(root, p); H, W = S.shape[:2]; meta = U_.read_meta(root, p)
        files, entry = U_.plate_files(root, p, man, ('lines.png', 'area_in.png', 'valmask.png', 'meta.json', 'full.jpg'))
        files['scan'] = dict(path=scan_path(root, p), sha256=U_.sha256(scan_path(root, p)))
        vh = U_.read_valmask(root, p, (H // 2, W // 2)) if os.path.exists(os.path.join(root, p, 'valmask.png')) else None
        if how == 'all' and vh is not None: sys.exit(f'{p}:all: the plate has a valmask.png; refusing to train on its validation pixels')
        if how == 'val': vh = np.ones((H // 2, W // 2), bool)
        t = S[:, :, 4]
        r = dict(plate=p, spec=p + (':' + how if how else ''), source=meta.get('source', (entry or {}).get('source', 'unknown')), weight=weights.get(p, 1.0), size=[W, H],
                 line_px=int((t == 1).sum()), scored_share=round(float((t != 255).mean()), 4), area_in='area_in.png' if has_area else 'none (128)',
                 area_in_meta=meta.get('area_in') or (meta.get('files') or {}).get('area_in.png'), files=files,
                 scale_ft_per_inch=U_.meta_scale(meta))
        if vh is not None:
            vf = cv2.resize(vh.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0   # as load() resizes the label
            y0, y1, x0, x1 = U_.bbox(vf); xv, tv, _ = build(S, y0, y1, x0, x1); mv = vf[y0:y1, x0:x1]; tv[~mv] = 255
            va.append(dict(plate=p, x=xv, t=tv, vm=mv)); r['val_box'] = [x0, y0, x1, y1]; r['val_line_px'] = int((tv == 1).sum()); r['val_scored_px'] = int((tv != 255).sum()); del vf
        if how != 'val':
            vint = cv2.integral(vh.astype(np.uint8)) if vh is not None else None
            if r['weight'] > 0: tr.append(dict(plate=p, S=S, vint=vint))
            r['train_line_px'] = int((t == 1).sum()) - r.get('val_line_px', 0)
        else: del S
        rec.append(r); print(json.dumps({k: v for k, v in r.items() if k != 'files'}), flush=True)
    if not tr: sys.exit('no training plate')
    unknown = set(weights) - {r['plate'] for r in rec}
    if unknown: sys.exit(f'--weights names plates not in the run: {sorted(unknown)}')
    load_s = round(time.time() - T0, 1); mem = U_.mem_now()
    print(json.dumps(dict(loaded_s=load_s, stored_gb=round(sum(P['S'].nbytes for P in tr) / 1e9, 3), process=mem)), flush=True)
    w = np.array([weights.get(P['plate'], 1.0) for P in tr], float); prob = w / w.sum(); drawn = np.zeros(len(tr), int)
    os.makedirs(outdir, exist_ok=True)
    net = UNet(classes=2, in_ch=7).to(dev); opt = torch.optim.Adam(net.parameters(), 1e-3); t0 = time.time(); hist = []; best = None
    info = dict(name=name, kind='lines', mode='data', data=root, manifest_sha256=man_sha, seed=seed, git=U_.git_state(), trainer=dict(file=os.path.abspath(__file__), sha256=U_.sha256(__file__), unet=os.path.abspath(U_.__file__), unet_sha256=U_.sha256(U_.__file__)),
                torch=torch.__version__, device=device.name, argv=sys.argv[1:], iters=iters, crop=CROP, batch=BATCH, line_px=LINE, tol_px=TOL, no_guide=True, guide_moved_or_blanked=False,
                val_every=val_every, select_by='F1 of precision and recall (score()) on the validation pixels pooled over the plates', sampling='plate first (probability weight / sum), then a crop on it',
                load=dict(seconds=load_s, stored_bytes=int(sum(P['S'].nbytes for P in tr)), process_after_load=mem), plates=rec)
    def save_json():
        info.update(crops_drawn={P['plate']: int(n) for P, n in zip(tr, drawn)}, best=best and dict(iter=best[0], f1=best[1]), history=hist, minutes=round((time.time() - t0) / 60, 2), process_peak=U_.mem_now())
        json.dump(info, open(os.path.join(outdir, name + '.json'), 'w', encoding='utf8', newline='\n'), indent=1)
    tt, nt = 0.0, 0   # time in training steps (crops, forward, backward) since the last check
    for it in range(1, iters + 1):
        ti = time.time()
        xs, ts, ws = [], [], []
        while len(xs) < BATCH:
            i = int(rng.integers(len(tr))) if np.all(w == w[0]) else int(rng.choice(len(tr), p=prob)); P = tr[i]; y, xx = draw_crop(rng, P); drawn[i] += 1
            a, b, c = build(P['S'], y, y + CROP, xx, xx + CROP)
            if rng.random() < 0.15: a[:, :, 6] = 128                             # sometimes no area prediction
            k = rng.integers(4); a, b, c = np.rot90(a, k), np.rot90(b, k), np.rot90(c, k)
            if rng.random() < 0.5: a, b, c = a[:, ::-1], b[:, ::-1], c[:, ::-1]
            a = a.astype(np.float32); a[:, :, :3] = np.clip(a[:, :, :3] * rng.uniform(0.85, 1.15) + rng.uniform(-15, 15), 0, 255)
            xs.append(a); ts.append(b); ws.append(c)
        for g_ in opt.param_groups: g_['lr'] = 1e-3 * 0.5 * (1 + np.cos(np.pi * it / iters))
        net.train(); out = net(norm(np.stack(xs)).to(dev)); tn = np.stack(ts)
        yt = torch.from_numpy(np.where(tn == 255, 0, tn).astype(np.int64)).to(dev); ok = torch.from_numpy((tn != 255).astype(np.float32)).to(dev)
        wt = torch.from_numpy(np.ascontiguousarray(np.stack(ws))).to(dev) * ok
        ce = (F.cross_entropy(out, yt, reduction='none') * wt).sum() / wt.sum().clamp(min=1.0)
        pl = F.softmax(out, 1)[:, 1] * ok; tl = yt.float() * ok
        dice = 1 - (2 * (pl * tl).sum() + 1) / (pl.sum() + tl.sum() + 1)
        loss = ce + dice
        opt.zero_grad(); loss.backward(); opt.step(); tt += time.time() - ti; nt += 1
        if it % val_every == 0 or it == iters:
            h = dict(iter=it, loss=round(float(loss), 4), minutes=round((time.time() - t0) / 60, 2)); h['train_s_per_iter'] = round(tt / max(1, nt), 3); tv = time.time()
            if va:
                c = np.zeros(4, np.int64); sc = {}
                for V in va:
                    cc = line_counts(predict_full(net, dev, V['x']), V['t'], V['vm']); c += cc; sc[V['plate']] = prf(cc)
                h['val'] = sc; h['val_pooled'] = prf(c); f1 = h['val_pooled']['f1']
                if best is None or f1 > best[1]:
                    best = (it, f1); torch.save(U_.cpu_state(net), os.path.join(outdir, name + '.pt')); h['best'] = True
            h['val_s'] = round(time.time() - tv, 2); hist.append(h); print(json.dumps(h), flush=True); save_json(); tt, nt = 0.0, 0
    torch.save(U_.cpu_state(net), os.path.join(outdir, name + '_last.pt'))
    if not va: torch.save(U_.cpu_state(net), os.path.join(outdir, name + '.pt')); info['note'] = 'no validation pixels: NAME.pt is the last'
    save_json(); print('wrote', os.path.join(outdir, name + '.pt'), 'best', info['best'], flush=True)

def predict(name, plate):
    dev = device(); net = UNet(classes=2, in_ch=7); net.load_state_dict(torch.load(DATA + f'models/{name}.pt', map_location='cpu')); net.to(dev)
    x, t, _ = load(plate); p = predict_full(net, dev, x)
    cv2.imwrite(DATA + f'{plate}_lines_{name}.png', (p * 255).astype(np.uint8)); print(plate, json.dumps(score(p, t)))

VALUED = ('--iters', '--data', '--seed', '--weights', '--out', '--val-every', '--area')
FLAGS = ('--no-guide', '--legacy-noguide')
if __name__ == '__main__':
    a, o = [], {}; k = 1
    while k < len(sys.argv):
        s = sys.argv[k]
        if s in VALUED:
            if k + 1 >= len(sys.argv): sys.exit(f'{s} needs a value')
            o.setdefault(s, []).append(sys.argv[k + 1]); k += 2
        elif s in FLAGS: o[s] = [True]; k += 1
        elif s.startswith('--'): sys.exit(f'unknown option {s} (known: {", ".join(VALUED + FLAGS)})')
        else: a.append(s); k += 1
    it = int(o['--iters'][-1]) if '--iters' in o else 3000
    if not a or a[0] not in ('train', 'predict'): sys.exit(__doc__)
    if '--data' in o:
        if a[0] != 'train': sys.exit('--data is for train')
        if LEGACY_NOGUIDE or '--area' in o: sys.exit('--legacy-noguide and --area are not for --data (the 7th input is DIR/N/area_in.png)')
        train_data(a[1], o['--data'][-1], a[2:], it, int(o['--seed'][-1]) if '--seed' in o else None, U_.parse_weights(o.get('--weights', [])),
                   os.path.abspath(o['--out'][-1]) if '--out' in o else DATA + 'models', int(o['--val-every'][-1]) if '--val-every' in o else U_.VAL_EVERY)
    else:
        for s in ('--seed', '--weights', '--out', '--val-every'):
            if s in o: sys.exit(f'{s} is for --data (the unet_data plates train as before)')
        os.makedirs(DATA + 'models', exist_ok=True)
        train(a[1], a[2:], it) if a[0] == 'train' else predict(a[1], a[2])
