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
"""
import json, os, sys, time
import numpy as np
import cv2
import torch, torch.nn.functional as F
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
import _ws  # noqa: E402
from unet import UNet, device  # noqa: E402
SP = _ws.DATA; DATA = SP + 'unet_data/'; CROP, BATCH, LINE, GAP, TOL, JIT, NEG_INK, POS = 448, 6, 3, 4, 3, 24, 4.0, 3.0
AREA = 'edge_v1'       # the area network whose street / block prediction is the seventh input (15 Nov 2026)

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
            a = x[y:y + CROP, xx:xx + CROP].copy(); dy, dx = rng.integers(-JIT, JIT + 1, 2)
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
            json.dump(dict(name=name, plates=plates, iters=iters, crop=CROP, batch=BATCH, line_px=LINE, tol_px=TOL, history=hist), open(DATA + f'models/{name}.json', 'w', encoding='utf8', newline='\n'), indent=1)

def predict(name, plate):
    dev = device(); net = UNet(classes=2, in_ch=7); net.load_state_dict(torch.load(DATA + f'models/{name}.pt', map_location='cpu')); net.to(dev)
    x, t, _ = load(plate); p = predict_full(net, dev, x)
    cv2.imwrite(DATA + f'{plate}_lines_{name}.png', (p * 255).astype(np.uint8)); print(plate, json.dumps(score(p, t)))

if __name__ == '__main__':
    a = sys.argv[1:]; it = 3000
    if '--iters' in a: k = a.index('--iters'); it = int(a[k + 1]); a = a[:k] + a[k + 2:]
    os.makedirs(DATA + 'models', exist_ok=True)
    train(a[1], a[2:], it) if a[0] == 'train' else predict(a[1], a[2])
