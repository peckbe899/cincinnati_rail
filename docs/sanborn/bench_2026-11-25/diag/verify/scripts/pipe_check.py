"""pipe_check.py (diag/verify, 25 Nov 2026): is the 'sides on water pipes and sewers' error (errors C3) made by the new
LINE nets or by the new AREA nets? For each run on plate 44's six grids: the editor's shown lines (44_shown.json minus
the sheet outline), sampled each 1 px; a sample is false when it lies more than 5 px from every sample of Ben's lines
(errors/runs/ben.npz; no direction test, which the errors agent found moves 'new false' by 2% or less). The ink under
a false sample is the most common non-zero bin of unet_data/44_bins.png in a 7 x 7 window (0 if none). Reports mean
false length, and the false length on pipe (bin 6) and sewer (bin 7) ink, for: the baseline, each pair, area_ng1 + the
pair's line net (a__), and the pair's area net + lines_ng1 (b__). Read-only; writes diag/verify/pipe_check.json.
    python -B pipe_check.py
"""
import json
import numpy as np, cv2
from scipy.spatial import cKDTree
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
D = SP + 'bench_2026-11-25/diag/'
ben = np.load(D + 'errors/runs/ben.npz')['P']; tree = cKDTree(ben)
bins = cv2.imread(SP + 'unet_data/44_bins.png', cv2.IMREAD_UNCHANGED); H, W = bins.shape
RUNS = {'baseline': D + 'swap/runs_baseline44/base__grid{g}/'}
for s in ('V1S1', 'V1S2', 'V2S1', 'V2S2'):
    RUNS[f'pair {s}'] = SP + f'train_v2_runs/eval/{s}/runs44/v2__grid{{g}}/'
    RUNS[f'a__ area_ng1 + lines {s}'] = D + f'swap/eval/a__ng1+L_{s}/runs44/v2__grid{{g}}/'
    RUNS[f'b__ area {s} + lines_ng1'] = D + f'swap/eval/b__A_{s}+ng1/runs44/v2__grid{{g}}/'


def samples(lines):
    pts = []
    for e in lines:
        a, b = np.array(e['a'], float), np.array(e['b'], float); n = max(1, int(np.ceil(np.hypot(*(b - a)))))
        t = (np.arange(n) + 0.5) / n; pts.append(a[None] + t[:, None] * (b - a)[None])
    return np.concatenate(pts) if pts else np.zeros((0, 2))


def ink(P):
    out = np.zeros(len(P), np.int16)
    xi = np.clip(np.round(P[:, 0]).astype(int), 3, W - 4); yi = np.clip(np.round(P[:, 1]).astype(int), 3, H - 4)
    win = np.stack([bins[yi + dy, xi + dx] for dy in range(-3, 4) for dx in range(-3, 4)], 1)
    for k in range(len(P)):
        v = win[k][win[k] > 0]
        if len(v): out[k] = np.bincount(v, minlength=10).argmax()
    return out


R = {}
for name, path in RUNS.items():
    rows = []
    for g in range(6):
        sh = [e for e in json.load(open(path.format(g=g) + '44_shown.json', encoding='utf8')) if e.get('state') != 'sheet']
        P = samples(sh); d, _ = tree.query(P, k=1, workers=-1); f = d > 5
        b = ink(P[f])
        rows.append(dict(shown=len(P), false=int(f.sum()), pipe=int((b == 6).sum()), sewer=int((b == 7).sum()), text=int((b == 8).sum()), lot=int((b == 2).sum()), noink=int((b == 0).sum())))
    m = {k: round(float(np.mean([r[k] for r in rows])), 0) for k in rows[0]}
    m['precision_nodir'] = round(1 - m['false'] / m['shown'], 4); m['pipe_sewer'] = m['pipe'] + m['sewer']
    R[name] = m
    print(name.ljust(32), m, flush=True)
json.dump(R, open(D + 'verify/pipe_check.json', 'w'), indent=1)
