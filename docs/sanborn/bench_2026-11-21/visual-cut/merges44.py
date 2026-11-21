"""Plate 44 (the only ground truth): the batch's outline step (out44/, outlines_copy.py on the batch's two maps) against
Ben's 55 blocks. PQ from the review's scorer (pq44_copy.py = research-maps_pq44.py, unchanged), then every outline
polygon that covers 2 or more of Ben's blocks (each >= 20 % covered), with what separates them: the narrowest gap
between the two blocks' rings (alley if < 45 px, i.e. about 30 ft at 1.46 px/ft; street otherwise). Also the false
editor lines (under 20 % on Ben's lines, audit/44_audit.json) by the ink bin under them (44_bins.png, which on 44 is
sorted with Ben's street map: lot line, building outline, pipe, sewer, text, rail). Reads only; writes audit/44_merges.json.
"""
import json, os
import numpy as np, cv2
from shapely.geometry import Polygon
import pq44_copy as Q
HERE = os.path.dirname(os.path.abspath(__file__)); D = Q.D
gt, ng, shape = Q.gt_instances()
pr, npr = Q.pred_from_outlines(os.path.join(HERE, 'out44', '44_outlines_poly.json'), shape)
r = Q.pq(gt, ng, pr, npr, 'batch outline step on 44 (area_ng1 + lines_ng1)'); print(json.dumps(r))
bm = cv2.resize(cv2.imread(os.path.join(HERE, 'out44', '44_blockmask.png'), 0), (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
pr2, npr2 = Q.pred_from_mask(bm); print(json.dumps(Q.pq(gt, ng, pr2, npr2, 'block mask before straightening')))
sm = json.load(open(D + 'streetmap/22-44.json', encoding='utf8')); rings = [Polygon(b['ring']).buffer(0) for b in sm['blocks']]
m = (gt > 0) | (pr > 0); joint = np.bincount(gt[m].astype(np.int64) * (npr + 1) + pr[m], minlength=(ng + 1) * (npr + 1)).reshape(ng + 1, npr + 1); ga = joint.sum(1)
merges = []
for j in range(1, npr + 1):
    cov = [i for i in range(1, ng + 1) if joint[i, j] > 0.2 * ga[i]]
    if len(cov) < 2: continue
    gaps = []
    for x in range(len(cov)):
        for y in range(x + 1, len(cov)):
            d = rings[cov[x] - 1].distance(rings[cov[y] - 1])
            if d < 150: gaps.append(round(d, 1))
    merges.append(dict(poly=j - 1, ben_blocks=cov, gaps=sorted(gaps)))
alley = sum(1 for mm in merges for g in mm['gaps'] if g < 45); street = sum(1 for mm in merges for g in mm['gaps'] if g >= 45)
print('polygons covering >= 2 of Ben blocks:', len(merges), '| neighbour pairs joined across an alley (<45 px):', alley, 'across a street:', street)
for mm in merges: print(mm)
# false editor lines by ink bin
A = json.load(open(os.path.join(HERE, 'audit', '44_audit.json'))); bins = cv2.imread(D + 'unet_data/44_bins.png', cv2.IMREAD_UNCHANGED)
NAMES = {0: 'no ink', 1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text and numbers', 9: 'not sorted'}
H, W = bins.shape; tally = {}
for l in A['lines']:
    if l['on_ben'] >= 0.2: continue
    a, b = np.array(l['a']), np.array(l['b']); t = np.linspace(0.1, 0.9, max(5, int(l['L'] / 4))); q = a + np.outer(t, b - a)
    d = (b - a) / l['L']; nrm = np.array([-d[1], d[0]]); v = []
    for qq in q:
        best = 0
        for o in (0, -1, 1, -2, 2, -3, 3):
            x, y = (qq + nrm * o).round().astype(int)
            if 0 <= x < W and 0 <= y < H and bins[y, x]: best = int(bins[y, x]); break
        v.append(best)
    k = NAMES[np.bincount(v, minlength=10).argmax()]
    e = tally.setdefault(k, [0, 0.0]); e[0] += 1; e[1] += l['L']
print('false editor lines (< 20 % on Ben lines) by majority ink bin:', {k: (v[0], round(v[1])) for k, v in sorted(tally.items(), key=lambda kv: -kv[1][1])})
json.dump(dict(pq=r, merges=merges, false_by_bin={k: [v[0], round(v[1])] for k, v in tally.items()}), open(os.path.join(HERE, 'audit', '44_merges.json'), 'w'), indent=1)
