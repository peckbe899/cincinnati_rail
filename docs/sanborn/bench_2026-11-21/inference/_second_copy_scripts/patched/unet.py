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
"""
import json, os, sys, time
import numpy as np
import cv2
import torch, torch.nn as nn, torch.nn.functional as F
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
import _ws  # noqa: E402
DATA = _ws.DATA + 'unet_data/'; CROP, BATCH = 384, 8
NOGUIDE = '--no-guide' in sys.argv   # 21 Nov 2026: a network for plates that were never placed; the guide channels are blank in training and in use

def device():
    try:
        import torch_directml as d
        k = max(range(d.device_count()), key=lambda i: ('RX' in d.device_name(i)) + ('NVIDIA' in d.device_name(i)))
        print('device', d.device_name(k), flush=True); return d.device(k)
    except Exception:
        return torch.device('cuda' if torch.cuda.is_available() else 'cpu')

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
    e = cv2.imread(DATA + f'{plate}_edge.png', 0)
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

# Test-time augmentation (21 Nov 2026, bench_2026-11-21/inference): each tile is also run turned and flipped, the
# answers are turned back and averaged. Training already uses all 8 quarter turns and flips (train(), lines 125-126), so
# every transform is one the network was taught. (k quarter turns, then a left-right flip); (3, True) is the transpose.
TTA = {1: ((0, False),), 2: ((0, False), (0, True)), 4: ((0, False), (0, True), (2, True), (3, True)),
       8: ((0, False), (0, True), (1, False), (1, True), (2, False), (2, True), (3, False), (3, True))}
def turn(t, k, f):
    t = torch.rot90(t, k, (-2, -1)) if k else t
    return torch.flip(t, (-1,)) if f else t
def unturn(t, k, f):
    t = torch.flip(t, (-1,)) if f else t
    return torch.rot90(t, -k, (-2, -1)) if k else t

def predict_full(net, dev, img, tile=768, pad=64, tta=1):
    """P(block) for a whole image, by overlapping tiles (the outer pad of each tile is thrown away). tta = 4 or 8: each
    tile is averaged over that many turns and flips (TTA); tta = 1 is the single pass, exactly as before."""
    h, w = img.shape[:2]; out = np.zeros((h, w), np.float32); edge = np.zeros((h, w), np.float32); step = tile - 2 * pad
    im = cv2.copyMakeBorder(img, pad, pad + tile, pad, pad + tile, cv2.BORDER_REFLECT)
    net.eval(); ts = TTA[tta]
    with torch.no_grad():
        for y in range(0, h, step):
            for x in range(0, w, step):
                t = norm(im[None, y:y + tile, x:x + tile])
                o = net(torch.cat([turn(t, k, f) for k, f in ts]).to(dev))
                pb, pe = F.softmax(o[:, :2], 1)[:, 1].cpu(), torch.sigmoid(o[:, 2]).cpu()
                p = (sum(unturn(pb[i], k, f) for i, (k, f) in enumerate(ts)) / len(ts)).numpy()[pad:pad + step, pad:pad + step]
                out[y:y + step, x:x + step] = p[:min(step, h - y), :min(step, w - x)]
                q = (sum(unturn(pe[i], k, f) for i, (k, f) in enumerate(ts)) / len(ts)).numpy()[pad:pad + step, pad:pad + step]
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
    json.dump(dict(name=name, plates=plates, iters=iters, crop=CROP, batch=BATCH, history=hist), open(DATA + f'models/{name}.json', 'w', encoding='utf8', newline='\n'), indent=1)

def predict(name, plate):
    dev = device(); net = UNet(); net.load_state_dict(torch.load(DATA + f'models/{name}.pt', map_location='cpu')); net.to(dev)
    img, _ = load(plate); p = predict_full(net, dev, img)
    cv2.imwrite(DATA + f'{plate}_pred_{name}.png', (p * 255).astype(np.uint8)); cv2.imwrite(DATA + f'{plate}_edgepred_{name}.png', (predict_full.edge * 255).astype(np.uint8))
    print('wrote', f'{plate}_pred_{name}.png', p.shape)

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    it = int(sys.argv[sys.argv.index('--iters') + 1]) if '--iters' in sys.argv else 3000
    a = [x for x in a if x != str(it) or '--iters' not in sys.argv]
    train(a[1], a[2:], it) if a[0] == 'train' else predict(a[1], a[2])
