"""What Ben's deletions are made of, on plates 5 and 1A (read-only: picks22_guided/22-N/edges_ben.json, unet_data/N_bins.png).
A deleted line = verdict 'wrong'. Street lines = his kept lines (verdict 'ok', moved/added included). Each deleted line is
sampled each 1 px and classified as census.py does: the most common bin in a 7 x 7 window (bins are the rule-based guess
of ink_bins.py, not ground truth), any text (bin 8) in the window, near-street text (bin-8 px within 40 px of a kept
line), and the distance to the nearest kept line. Also the same for the kept lines, for reference.
    python -B deletions.py  -> deletions.json
"""
import json
import numpy as np, cv2
from scipy.spatial import cKDTree
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
HERE = SP + 'bench_2026-11-25/diag/errors/'
NAMES = {0: 'no ink', 1: 'block line', 2: 'lot line', 3: 'building', 4: 'railroad', 5: 'streetcar', 6: 'pipe', 7: 'sewer', 8: 'text/numbers', 9: 'not sorted'}


def sample(lines):
    P, ix = [], []
    for k, l in enumerate(lines):
        a = np.array(l['a'], float); b = np.array(l['b'], float); L = np.hypot(*(b - a))
        if L < 1: continue
        m = int(np.ceil(L)); t = (np.arange(m) + 0.5) / m; P.append(a + np.outer(t, b - a)); ix.append(np.full(m, k))
    return (np.vstack(P), np.concatenate(ix)) if P else (np.zeros((0, 2)), np.zeros(0, int))


def win(A, P, r=3):
    x = np.clip(np.round(P[:, 0]).astype(int), r, A.shape[1] - 1 - r); y = np.clip(np.round(P[:, 1]).astype(int), r, A.shape[0] - 1 - r)
    return np.stack([A[y + dy, x + dx] for dy in range(-r, r + 1) for dx in range(-r, r + 1)], 1)


out = {}
for n in ('5', '1A'):
    d = json.load(open(SP + f'picks22_guided/22-{n}/edges_ben.json', encoding='utf8'))['lines']
    bins = cv2.imread(SP + f'unet_data/{n}_bins.png', cv2.IMREAD_UNCHANGED)
    kept = [l for l in d if l.get('verdict') == 'ok']; wrong = [l for l in d if l.get('verdict') == 'wrong']
    Pk, _ = sample(kept); tree = cKDTree(Pk)
    ys, xs = np.nonzero(bins == 8); dt, _ = tree.query(np.c_[xs, ys].astype(np.float32), k=1, distance_upper_bound=41, workers=-1)
    nst = np.zeros(bins.shape, np.uint8); s = dt <= 40; nst[ys[s], xs[s]] = 1
    res = {}
    for name, lines in (('deleted', wrong), ('deleted_not_sheet', [l for l in wrong if l.get('src') != 'sheet']), ('kept', kept)):
        P, ix = sample(lines)
        wb = win(bins, P); cnt = np.stack([(wb == k).sum(1) for k in range(1, 10)], 1); dom = np.where(cnt.max(1) > 0, cnt.argmax(1) + 1, 0)
        text = cnt[:, 7] > 0; ns = win(nst, P).max(1) > 0
        dk, _ = tree.query(P, k=1, workers=-1) if name != 'kept' else (np.zeros(len(P)), None)
        r = dict(lines=len(lines), length=int(len(P)), ink={NAMES[k]: round(float((dom == k).mean()), 4) for k in range(10)},
                 any_text_in_window=round(float(text.mean()), 4), near_street_text_in_window=round(float(ns.mean()), 4),
                 src={k: sum(1 for l in lines if l.get('src') == k) for k in ('read', 'ben', 'sheet')})
        if name != 'kept':
            band = (dk > 5) & (dk <= 40)
            r['dist_to_kept'] = {f'{a}-{b}': round(float(((dk >= a) & (dk < b)).mean()), 4) for a, b in ((0, 5), (5, 20), (20, 40), (40, 80), (80, 1e9))}
            r['in_5_40_band'] = int(band.sum()); r['band_share_near_street_text'] = round(float(ns[band].mean()), 4) if band.any() else None
            # per line: share of its length with text in the window; lines mostly on text
            per = np.bincount(ix, text.astype(float), minlength=len(lines)) / np.maximum(np.bincount(ix, minlength=len(lines)), 1)
            r['lines_half_or_more_on_text'] = int((per >= 0.5).sum())
            perr = np.bincount(ix, np.isin(dom, (4, 5)).astype(float), minlength=len(lines)) / np.maximum(np.bincount(ix, minlength=len(lines)), 1)
            r['lines_half_or_more_on_rail_bins'] = int((perr >= 0.5).sum())
        res[name] = r
    # reference: share of the 5-40 px band beside kept lines with near-street text in the window (every 4th px of the plate)
    gy, gx = np.mgrid[0:bins.shape[0]:4, 0:bins.shape[1]:4]; G = np.c_[gx.ravel(), gy.ravel()].astype(np.float32)
    dg, _ = tree.query(G, k=1, distance_upper_bound=41, workers=-1); band = (dg > 5) & (dg <= 40)
    res['reference_band_share_near_street_text'] = round(float((win(nst, G[band]).max(1) > 0).mean()), 4)
    out[n] = res
    print(n, json.dumps(res, indent=1))
json.dump(dict(note=__doc__, plates=out), open(HERE + 'deletions.json', 'w'), indent=1)
