"""shift_test.py (diag/swap, 25 Nov 2026): is a map shifted against Ben's map? For shifts of the map by (dx, dy) half px
(area) or full px (lines), the score on 44's decided ground: area accuracy, line F1 at 3 px (as pixel_maps44.py).
Also 1A (validation region and the whole taught ground) against train_v2/1A/label.png. System python. Prints json.
    python -B shift_test.py area|lines|area1A NAME=PNG [NAME=PNG ...] [--r 4]
"""
import sys, json, glob
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
D = SP + 'bench_2026-11-25/diag/swap/'
W, H = 10768, 7219; S = 0.5; h2, w2 = int(H * S), int(W * S)
args = [a for a in sys.argv[1:] if not a.startswith('--')]; R = int(sys.argv[sys.argv.index('--r') + 1]) if '--r' in sys.argv else 4
kind = args[0]; maps = dict(a.split('=', 1) for a in args[1:] if '=' in a and not a.startswith('--'))
def shift(m, dx, dy):
    M = np.float32([[1, 0, dx], [0, 1, dy]]); return cv2.warpAffine(m, M, (m.shape[1], m.shape[0]), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE)
out = {}
if kind == 'area':
    sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8')); gt = np.zeros((h2, w2), np.uint8)
    for b in sm['blocks']: cv2.fillPoly(gt, [(np.array(b['ring']) * S).round().astype(np.int32)], 1)
    dec = cv2.imread(glob.glob(D + 'runs_baseline44/cache/decided_half_*_260.png')[0], 0) > 0; blk = gt > 0
    for n, f in maps.items():
        p = cv2.imread(f, 0); g = {}
        for dy in range(-R, R + 1):
            for dx in range(-R, R + 1):
                g[(dx, dy)] = float((((shift(p, dx, dy) > 127) == blk)[dec]).mean())
        b = max(g, key=g.get); out[n] = dict(at0=round(g[(0, 0)], 4), best_shift_dxdy=b, best=round(g[b], 4))
        print(n, out[n], flush=True)
elif kind == 'area1A':
    l = cv2.imread(SP + 'train_v2/1A/label.png', 0); vm = cv2.imread(SP + 'train_v2/1A/valmask.png', 0) > 0; t = l != 255
    for n, f in maps.items():
        p = cv2.imread(f, 0); r = {}
        for nm, sel in (('val', t & vm), ('all_taught', t)):
            g = {(dx, dy): float((((shift(p, dx, dy) > 127) == (l == 1))[sel]).mean()) for dy in range(-R, R + 1) for dx in range(-R, R + 1)}
            b = max(g, key=g.get); r[nm] = dict(at0=round(g[(0, 0)], 4), best_shift_dxdy=b, best=round(g[b], 4))
        out[n] = r; print(n, r, flush=True)
else:
    sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8')); L = np.zeros((H, W), np.uint8)
    for l in sm['lines']: cv2.line(L, tuple(int(round(v)) for v in l['a']), tuple(int(round(v)) for v in l['b']), 1, 1)
    K = np.ones((7, 7), np.uint8); near = cv2.dilate(L, K) > 0
    a4 = np.load(SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32); alpha = cv2.resize(a4, (W, H)) > 0.5
    for n, f in maps.items():
        p = cv2.imread(f, 0); g = {}
        for dy in range(-R, R + 1, 2):
            for dx in range(-R, R + 1, 2):
                pr = (shift(p, dx, dy) > 127) & alpha; np_ = cv2.dilate(pr.astype(np.uint8), K) > 0
                P = (pr & near).sum() / max(1, pr.sum()); Rr = (L.astype(bool) & np_).sum() / max(1, L.sum()); g[(dx, dy)] = float(2 * P * Rr / max(1e-9, P + Rr))
        b = max(g, key=g.get); out[n] = dict(at0=round(g[(0, 0)], 4), best_shift_dxdy=b, best=round(g[b], 4)); print(n, out[n], flush=True)
