"""numbers_check.py (diag/verify, 25 Nov 2026): Ben's point that numbers near the streets confound the networks, split
by network. 'Near-street numbers' = text px (bin 8 of unet_data/44_bins.png) within 40 px of one of Ben's lines (the
errors agent's layer errors/layers.npz 'nst'). For each line map on 44 (6 grids): its mean P(line) on those px and the
share of them with P > 0.5; and for each run's editor lines: the false length (more than 5 px from Ben's lines) that has
a near-street number px in its 7 x 7 window. Runs: baseline, pair, a__ (area_ng1 + new line net), b__ (new area net +
lines_ng1). Read-only; writes diag/verify/numbers_check.json.
    python -B numbers_check.py
"""
import json
import numpy as np, cv2
from scipy.spatial import cKDTree
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
D = SP + 'bench_2026-11-25/diag/'
L = np.load(D + 'errors/layers.npz'); nst = L['nst'] > 0; H, W = nst.shape
ben = np.load(D + 'errors/runs/ben.npz')['P']; tree = cKDTree(ben)
ys, xs = np.nonzero(nst)
SETS = {'baseline': (SP + 'bench44_maps/grid{g}/', D + 'swap/runs_baseline44/base__grid{g}/')}
for s in ('V1S1', 'V1S2', 'V2S1', 'V2S2'):
    SETS[f'pair {s}'] = (SP + f'train_v2_runs/eval/{s}/maps44/grid{{g}}/', SP + f'train_v2_runs/eval/{s}/runs44/v2__grid{{g}}/')
    SETS[f'a__ area_ng1 + lines {s}'] = (D + f'swap/eval/a__ng1+L_{s}/maps44/grid{{g}}/', D + f'swap/eval/a__ng1+L_{s}/runs44/v2__grid{{g}}/')
    SETS[f'b__ area {s} + lines_ng1'] = (D + f'swap/eval/b__A_{s}+ng1/maps44/grid{{g}}/', D + f'swap/eval/b__A_{s}+ng1/runs44/v2__grid{{g}}/')


def samples(lines):
    pts = []
    for e in lines:
        a, b = np.array(e['a'], float), np.array(e['b'], float); n = max(1, int(np.ceil(np.hypot(*(b - a)))))
        t = (np.arange(n) + 0.5) / n; pts.append(a[None] + t[:, None] * (b - a)[None])
    return np.concatenate(pts) if pts else np.zeros((0, 2))


nst_win = cv2.dilate(nst.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
R = {}
for name, (mp, rp) in SETS.items():
    rows = []
    for g in range(6):
        lm = cv2.imread(mp.format(g=g) + '44_lines.png', 0)
        assert lm.shape == (H, W), lm.shape
        v = lm[ys, xs].astype(np.float32) / 255
        sh = [e for e in json.load(open(rp.format(g=g) + '44_shown.json', encoding='utf8')) if e.get('state') != 'sheet']
        P = samples(sh); d, _ = tree.query(P, k=1, workers=-1); f = d > 5
        xi = np.clip(np.round(P[f, 0]).astype(int), 0, W - 1); yi = np.clip(np.round(P[f, 1]).astype(int), 0, H - 1)
        on = nst_win[yi, xi]
        rows.append(dict(meanP=float(v.mean()), share_gt05=float((v > 0.5).mean()), false=int(f.sum()), false_on_nst=int(on.sum())))
    m = dict(meanP_on_near_street_numbers=round(np.mean([r['meanP'] for r in rows]), 4), share_P_gt_05=round(np.mean([r['share_gt05'] for r in rows]), 4),
             false_len=round(np.mean([r['false'] for r in rows])), false_len_on_near_street_numbers=round(np.mean([r['false_on_nst'] for r in rows])))
    m['share_of_false'] = round(m['false_len_on_near_street_numbers'] / max(1, m['false_len']), 4)
    R[name] = m; print(name.ljust(32), m, flush=True)
json.dump(R, open(D + 'verify/numbers_check.json', 'w'), indent=1)
