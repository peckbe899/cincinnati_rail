"""Tick spacing of the rows the railroad rule accepts: true rows (on Ben's railroad, plates 44 and 90) against the false
rows of plate 5 (Ben: no railroad there). Runs ink_bins.railroad from code/orig/ink_bins.py (byte copy of the repo's)
with the ground each plate is sorted with: 44 Ben's street map blocks, 5 and 90 the networks' block polygons
(outlines.json). Read-only on the repo; writes scores/tick_gaps.json. diag/rail5, 25 Nov 2026.
    cd data/sanborn; python -B bench_2026-11-25/diag/rail5/code/tick_gaps.py"""
import json, os, sys, importlib.util
sys.dont_write_bytecode = True
import numpy as np, cv2
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('ib_orig', os.path.join(ROOT, 'code', 'orig', 'ink_bins.py')); IB = importlib.util.module_from_spec(spec); spec.loader.exec_module(IB)
out = {}
for N in ('5', '44', '90'):
    im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
    paper = cv2.resize(np.load(f'cufp/{N}/png_alpha_s4.npy'), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    ink = (cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0] < IB.INK_L) & paper; del im
    closed = np.zeros((H, W), np.uint8)
    if N == '44':
        for bl in json.load(open('streetmap/22-44.json', encoding='utf8'))['blocks']: cv2.fillPoly(closed, [np.round(np.array(bl['ring'])).astype(np.int32)], 1)
    else:
        closed = IB.block_ground(json.load(open(os.path.join(ROOT, 'inputs', 'outlines.json') if N == '5' else f'picks22_guided/22-{N}/outlines.json', encoding='utf8')), H, W)
    rr, info = IB.railroad(ink, closed, paper); T = info['T']; E = np.array(info['E'], int).reshape(-1, 2)
    ben = [t for t in json.load(open(f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8'))['tracks'] if t['kind'] == 'railroad' and t.get('src') != 'rule']
    m = np.zeros((H, W), np.uint8)
    for t in ben: cv2.polylines(m, [np.round(np.array(t['pts'])).astype(np.int32)], False, 1, 1)
    d = cv2.distanceTransform((m == 0).astype(np.uint8), cv2.DIST_L2, 5)
    Ls = np.hypot(*(T[E[:, 0]] - T[E[:, 1]]).T); mid = ((T[E[:, 0]] + T[E[:, 1]]) / 2).round().astype(int)
    true = d[np.clip(mid[:, 1], 0, H - 1), np.clip(mid[:, 0], 0, W - 1)] <= 15
    nc, lab = connected_components(coo_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(len(T), len(T))), directed=False)
    rows = []
    for c in np.unique(lab[E[:, 0]]):
        k = lab[E[:, 0]] == c; p = np.unique(E[k])
        # the gap of a row: the median of its links' lengths, each tick's link to its nearest neighbour in the row
        nn = [];
        for i in p:
            js = [b if a == i else a for a, b in E[k] if i in (a, b)]; nn.append(min(np.hypot(*(T[js] - T[i]).T)))
        rows.append(dict(ticks=int(len(p)), gap_med=round(float(np.median(nn)), 1), gap_iqr=[round(float(v), 1) for v in np.percentile(nn, [25, 75])],
                         span=round(float(np.hypot(*(T[p].max(0) - T[p].min(0)))), 1), true=bool(true[k].mean() > 0.5), at=T[p].mean(0).round().tolist()))
    out[N] = dict(ben_railroad_tracks=len(ben), rows=rows, rail_px=int(rr.sum()))
    tr = [r for r in rows if r['true']]; fa = [r for r in rows if not r['true']]
    q = lambda R: (np.percentile([r['gap_med'] for r in R], [0, 10, 50, 90, 100]).round(1).tolist() if R else None)
    print(f'plate {N}: rows {len(rows)}, true {len(tr)} gap pct(0,10,50,90,100) {q(tr)} | false {len(fa)} gap {q(fa)} | ticks per false row {[r["ticks"] for r in fa]}', flush=True)
json.dump(out, open(os.path.join(ROOT, 'scores', 'tick_gaps.json'), 'w'), indent=1)
