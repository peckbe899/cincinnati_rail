"""rail_lost_spots.py (handoff, 26 Nov 2026): where Ben's tracks lose rail ink to the text mask. For a run sorted with Ben's
rail on (44_map_ben), every sample of his tracks (every 5 px) that had ink of its bin within 10 px (railroad) / 30 px
(streetcar) before the mask and has none after; the samples are grouped (within 60 px) and each group is cut out of the
scan with the mask and both sortings beside it, for looking at by eye.
    cd data/sanborn; python -B .../rail_lost_spots.py RUN N OUTPREFIX"""
import json, os, sys
import numpy as np, cv2
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
run, N, outp = sys.argv[1:4]; HO = 'bench_2026-11-25/text_v1/handoff/'; R = HO + 'runs/bins/'
bb = cv2.imread(R + f'{run}_before.png', 0); ba = cv2.imread(R + f'{run}_after.png', 0); tc = cv2.imread(HO + f'masks/{N}_text.png', 0); im = cv2.imread(f'cufp/22-{N}.jpg')
H, W = bb.shape; B = json.load(open(f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8'))['tracks']; res = {}
for kind, code, tol in (('railroad', 4, 10), ('streetcar', 5, 30)):
    S = []
    for t in B:
        if t['kind'] != kind: continue
        p = np.array(t['pts'], float)
        for q0, q1 in zip(p[:-1], p[1:]): S.append(q0[None] + np.linspace(0, 1, max(2, int(np.hypot(*(q1 - q0)) / 5) + 1))[:, None] * (q1 - q0)[None])
    if not S: continue
    q = np.vstack(S).round().astype(int); q = q[(q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H)]
    db = cv2.distanceTransform((bb != code).astype(np.uint8), cv2.DIST_L2, 5); da = cv2.distanceTransform((ba != code).astype(np.uint8), cv2.DIST_L2, 5)
    lost = q[(db[q[:, 1], q[:, 0]] <= tol) & (da[q[:, 1], q[:, 0]] > tol)]
    groups = []
    if len(lost):
        pr = np.array(sorted(cKDTree(lost).query_pairs(60)), int).reshape(-1, 2)
        from scipy.sparse import coo_matrix
        nc, lab = connected_components(coo_matrix((np.ones(len(pr)), (pr[:, 0], pr[:, 1])), shape=(len(lost), len(lost))), directed=False)
        for c in range(nc):
            g = lost[lab == c]; cx, cy = g.mean(0).round().astype(int); groups.append(dict(at=[int(cx), int(cy)], samples=int(len(g))))
            x0, y0 = max(0, cx - 90), max(0, cy - 90); x1, y1 = min(W, cx + 90), min(H, cy + 90)
            sc = im[y0:y1, x0:x1]; m = sc.copy(); col = {1: (0, 140, 0), 2: (255, 0, 255), 3: (255, 120, 0), 4: (0, 200, 200), 5: (0, 0, 230)}
            for v, cc in col.items(): m[tc[y0:y1, x0:x1] == v] = cc
            def binpic(b):
                c2 = (sc * 0.5 + 127).astype(np.uint8); s = b[y0:y1, x0:x1]; c2[s == 4] = (0, 0, 230); c2[s == 5] = (0, 150, 255); c2[s == 8] = (255, 0, 255); return c2
            pics = [sc, m, binpic(bb), binpic(ba)]
            for pp in pics[1:]:
                for t in B:
                    if t['kind'] == kind: cv2.polylines(pp, [np.round(np.array(t['pts']) - [x0, y0]).astype(np.int32)], False, (0, 0, 0), 1)
            z = np.hstack([cv2.resize(p_, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST) for p_ in pics])
            cv2.imwrite(f'{outp}_{kind}_{c}.png', z)
    res[kind] = dict(ben_samples=int(len(q)), lost_samples=int(len(lost)), groups=groups)
    print(kind, 'Ben samples', len(q), 'lost to the mask', len(lost), 'groups', groups)
json.dump(res, open(f'{outp}.json', 'w'), indent=1)
