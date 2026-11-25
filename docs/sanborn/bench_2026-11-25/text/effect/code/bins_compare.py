"""bins_compare.py (text/effect, 25 Nov 2026): plate 44's ink bins with text taken first, against the sorting made with
Ben's street map (unet_data/44_bins.png, copy inputs/44_bins_ref.png = R). Writes scores/bins_compare.json and, for
the eye check, masks/trans_<RUN>_<from>to<to>.png of the main transitions.
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/bins_compare.py
Runs (all with Ben's rail, as R): 44_mapben_tSref (Ben's map, R's own text bin taken first), 44_mapben_tI2 (Ben's map,
the idealised mask I2 taken first), 44_nets44ben_base (no map: the outline step's own lines and blocks, grid 0 of the
baseline maps) and 44_nets44ben_tI2 (the same with I2 first). R2 = 44_mapben_tI2 is used as a second reference for the
no-map runs (R with I2's text taken out)."""
import json, os
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); RU = os.path.join(ROOT, 'runs')
NAMES = {0: 'none', 1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text', 9: 'not sorted'}
R = cv2.imread(os.path.join(ROOT, 'inputs', '44_bins_ref.png'), 0); R2 = cv2.imread(os.path.join(RU, '44_mapben_tI2.png'), 0)
out = {}
for run in ('44_mapben_tSref', '44_mapben_tI2', '44_nets44ben_base', '44_nets44ben_tI2'):
    X = cv2.imread(os.path.join(RU, run + '.png'), 0); ink = R > 0
    T = np.bincount(R[ink].astype(np.int64) * 10 + X[ink], minlength=100).reshape(10, 10)
    o = dict(all_ink_same_bin=round(float(np.trace(T[1:, 1:]) / T[1:, 1:].sum()), 4), bins={})
    for k in (1, 2, 3, 6, 7, 8, 9):
        o['bins'][NAMES[k]] = dict(R_px=int(T[k].sum()), X_px=int(T[:, k].sum()), kept=int(T[k, k]), agreement=round(float(T[k, k] / max(1, T[k].sum())), 4), precision_vs_R=round(float(T[k, k] / max(1, T[:, k].sum())), 4),
                                   to={NAMES[j]: int(T[k, j]) for j in range(10) if j != k and T[k, j] >= 1000}, from_={NAMES[j]: int(T[j, k]) for j in range(10) if j != k and T[j, k] >= 1000})
    if run.startswith('44_nets44'):
        T2 = np.bincount(R2[ink].astype(np.int64) * 10 + X[ink], minlength=100).reshape(10, 10)
        o['vs_R2'] = dict(all_ink_same_bin=round(float(np.trace(T2[1:, 1:]) / T2[1:, 1:].sum()), 4), **{NAMES[k]: round(float(T2[k, k] / max(1, T2[k].sum())), 4) for k in (1, 2, 3, 6, 7, 8)})
    else:
        for a, b in ((2, 8), (6, 8), (7, 8), (3, 8), (1, 8), (8, 2), (8, 3)):
            m = (R == a) & (X == b)
            if m.sum() >= 1000: cv2.imwrite(os.path.join(ROOT, 'masks', f'trans_{run}_{a}to{b}.png'), m.astype(np.uint8) * 255)
    out[run] = o; print(run, json.dumps(o), flush=True)
json.dump(out, open(os.path.join(ROOT, 'scores', 'bins_compare.json'), 'w'), indent=1)
