"""Features of every hole contour (odd depth in RETR_TREE, area >= MIN_AREA) of a plate's block mask, to find what tells
a street hole (an alley or street enclosed by block ground) from a pocket of unsure ground in open land.

    python hole_features.py RUN_DIR N [AREA_PNG]     -> RUN_DIR/N_hole_features.json, printed table

RUN_DIR holds N_blockmask.png (half size, from outlines_nest.py). Per hole (full-size px): area, perimeter, mean width
(2 area / perimeter), the width the hole keeps under erosion (largest inscribed radius x 2), minAreaRect aspect, mean
P(block) inside, share of the hole the area network is sure is street (P < 0.1), parent block area, and where it is.
"""
import json, os, sys
import numpy as np
import cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
run, N = sys.argv[1].rstrip('/') + '/', sys.argv[2]
area_png = sys.argv[3] if len(sys.argv) > 3 else SP + f'unet_data/{N}_pred_area_ng1.png'
bm = (cv2.imread(run + f'{N}_blockmask.png', 0) > 127).astype(np.uint8)          # half size
pa = cv2.imread(area_png, 0); pa = cv2.resize(pa, (bm.shape[1], bm.shape[0]), interpolation=cv2.INTER_LINEAR) if pa.shape != bm.shape else pa
cs, hier = cv2.findContours(bm, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
rows = []
if hier is not None:
    hier = hier[0]
    dep = []
    for i in range(len(cs)):
        j, d = i, 0
        while hier[j][3] >= 0: j = hier[j][3]; d += 1
        dep.append(d)
    for i, c in enumerate(cs):
        if dep[i] % 2 == 0: continue
        A = cv2.contourArea(c) * 4
        if A < 6000: continue
        m = np.zeros(bm.shape, np.uint8); cv2.drawContours(m, [c], -1, 1, -1)
        kids = [k for k in range(len(cs)) if hier[k][3] == i]
        for k in kids: cv2.drawContours(m, [cs[k]], -1, 0, -1)                 # nested blocks are not the hole's ground
        inside = m > 0
        dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
        P = cv2.arcLength(c, True) * 2; (cx, cy), (rw, rh), _ = cv2.minAreaRect(c)
        par = hier[i][3]
        rows.append(dict(contour=i, depth=dep[i], area=round(A), perimeter=round(P), mean_width=round(2 * A / P, 1), inscribed_width=round(float(dt.max()) * 2 * 2, 1),
                         rect_aspect=round(max(rw, rh) / max(1, min(rw, rh)), 2), p_block_mean=round(float(pa[inside].mean()) / 255, 3),
                         sure_street=round(float((pa[inside] < 26).mean()), 3), parent_area=round(cv2.contourArea(cs[par]) * 4), centre=[round(cx * 2), round(cy * 2)], nested_blocks=len(kids)))
json.dump(rows, open(run + f'{N}_hole_features.json', 'w'), indent=1)
for r in rows: print(r)
