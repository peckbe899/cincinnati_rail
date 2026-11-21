"""v-final: the rules' railroad and streetcar bins on 44 (ink_bins --no-ben: the rules alone) for three grounds, scored
against Ben's 28 tracks (picks22_guided/22-44/rail_ben.page_2026-11-21.json; rail_ben.json still has 26). My own scorer,
following score_rail.py's definitions: found = share of his track length with rule ink of that kind within 10 px
(railroad) or 30 px (streetcar); precision = share of the rule's px of that kind within 10 px (railroad) or 30 px
(streetcar) of his tracks of that kind; far = rule px more than 25 px from every track of his.
    python -B rail44.py -> v-final/rail44.json"""
import json
import numpy as np, cv2
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-final/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
T = json.load(open(SP + 'picks22_guided/22-44/rail_ben.page_2026-11-21.json'))['tracks']
res = dict(tracks=len(T), railroad_tracks=sum(t['kind'] == 'railroad' for t in T))
for tag in ('map', 'nets', 'none'):
    R = cv2.imread(V + f'rail44/{tag}_noben.png', cv2.IMREAD_UNCHANGED); H, W = R.shape; r = {}
    for k, kind, tol in ((4, 'railroad', 10), (5, 'streetcar', 30)):
        D = cv2.distanceTransform((R != k).astype(np.uint8), cv2.DIST_L2, 5); band = np.zeros((H, W), np.uint8); band25 = np.zeros((H, W), np.uint8); tot = fnd = 0.0
        for t in T:
            if t['kind'] != kind: continue
            p = np.array(t['pts'], float); cv2.polylines(band, [p.round().astype(np.int32)], False, 1, 2 * tol + 1); cv2.polylines(band25, [p.round().astype(np.int32)], False, 1, 51)
            for q0, q1 in zip(p[:-1], p[1:]):
                L = np.hypot(*(q1 - q0)); S = q0[None] + np.linspace(0, 1, max(2, int(L / 4) + 1))[:, None] * (q1 - q0)[None]; q = S.round().astype(int)
                q = q[(q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H)]; tot += L; fnd += L * float((D[q[:, 1], q[:, 0]] <= tol).mean())
        m = R == k; r[kind] = dict(found=round(fnd / tot, 4), precision=round(float(band[m].mean()), 4) if m.any() else None, px=int(m.sum()), far_px=int((m & (band25 == 0)).sum()))
    res[tag] = r
json.dump(res, open(V + 'rail44.json', 'w'), indent=1); print(json.dumps(res, indent=1))
