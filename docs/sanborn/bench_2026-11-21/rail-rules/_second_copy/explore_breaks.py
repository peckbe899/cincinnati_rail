"""Exploration (rail-rules, 21 Nov 2026): where do the rules' tracks end inside one of Ben's tracks on plate 44?
For every rule track end lying within 10 px of a Ben track of the same kind and more than 100 px from his track's ends,
print the nearest other rule end of that kind (distance, and how straight the two run on), and cut a crop.
Read-only on the repo; writes only into bench_2026-11-21/rail-rules/explore/.
    cd data/sanborn
    python bench_2026-11-21/rail-rules/explore_breaks.py RULE.json [TAG]"""
import sys, json, os
import numpy as np, cv2
from scipy.spatial import cKDTree
OUT = 'bench_2026-11-21/rail-rules/explore'; os.makedirs(OUT, exist_ok=True)
rp = sys.argv[1]; tag = sys.argv[2] if len(sys.argv) > 2 else 'x'
TJ = json.load(open('picks22_guided/22-44/rail_ben.page_2026-11-21.json', encoding='utf8'))
R = json.load(open(rp, encoding='utf8'))['tracks']
im = cv2.imread('cufp/22-44.jpg')


def dense(p, step=2.0):
    p = np.asarray(p, float); S = [p[:1]]
    for a, b in zip(p[:-1], p[1:]):
        n = max(2, int(np.hypot(*(b - a)) / step) + 1); S.append(a[None] + np.linspace(0, 1, n)[1:, None] * (b - a)[None])
    return np.vstack(S)


rows = []
for kind in ('railroad', 'streetcar'):
    ben = [dense(t['pts']) for t in TJ['tracks'] if t['kind'] == kind]
    rule = [np.asarray(t['pts'], float) for t in R if t['kind'] == kind]
    if not rule: continue
    ends = []   # (point, out-direction, track index)
    for i, p in enumerate(rule):
        for q, r in ((p[0], p[min(1, len(p) - 1)]), (p[-1], p[max(-2, -len(p))])):
            d = q - r; ends.append((q, d / max(1e-6, np.hypot(*d)), i))
    E = np.array([e[0] for e in ends]); TE = cKDTree(E)
    for bi, S in enumerate(ben):
        cum = np.r_[0, np.cumsum(np.hypot(*np.diff(S, axis=0).T))]; T = cKDTree(S)
        for k, (q, o, i) in enumerate(ends):
            d, j = T.query(q)
            if d > 10 or cum[j] < 100 or cum[j] > cum[-1] - 100: continue
            dd, jj = TE.query(q, k=6); best = None
            for d2, j2 in zip(dd, jj):
                if j2 >= len(ends) or ends[j2][2] == i: continue
                v = E[j2] - q; L = np.hypot(*v); c_face = float(-(o @ ends[j2][1])); c_on = float(v @ o / L) if L > 1e-6 else 1.0
                best = dict(dist=round(float(L), 1), face=round(c_face, 3), on=round(c_on, 3), other=int(ends[j2][2])); break
            rows.append(dict(kind=kind, ben=bi, at=[round(float(v)) for v in q], rule=int(i), rule_len=round(float(np.hypot(*np.diff(rule[i], axis=0).T).sum())), along=round(float(cum[j])), nearest_end=best))
for r in rows: print(r)
json.dump(rows, open(f'{OUT}/breaks_{tag}.json', 'w'), indent=1)
# crops, 300 px around each break, with rule tracks drawn
tiles = []
for r in rows:
    x, y = r['at']; x0, y0 = max(0, x - 150), max(0, y - 150); c = im[y0:y0 + 300, x0:x0 + 300].copy()
    c = cv2.copyMakeBorder(c, 0, 300 - c.shape[0], 0, 300 - c.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255))
    for t in R:
        col = (0, 0, 230) if t['kind'] == 'railroad' else (0, 150, 255)
        cv2.polylines(c, [np.round(np.asarray(t['pts']) - [x0, y0]).astype(np.int32)], False, col, 1)
    for t in TJ['tracks']:
        cv2.polylines(c, [np.round(np.asarray(t['pts']) - [x0, y0]).astype(np.int32)], False, (200, 0, 200), 1, cv2.LINE_AA)
    cv2.circle(c, (x - x0, y - y0), 6, (0, 200, 0), 2)
    cv2.putText(c, f"{r['kind'][:2]} b{r['ben']} {r['nearest_end']['dist'] if r['nearest_end'] else '-'}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    tiles.append(c)
if tiles:
    n = 6; rws = [np.hstack(tiles[i:i + n] + [np.full((300, 300, 3), 255, np.uint8)] * (n - len(tiles[i:i + n]))) for i in range(0, len(tiles), n)]
    cv2.imwrite(f'{OUT}/breaks_{tag}.jpg', np.vstack(rws), [cv2.IMWRITE_JPEG_QUALITY, 88])
