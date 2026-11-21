"""outline-quality, 21 Nov 2026: what separates the Ben blocks that the batch outline step merges on plate 44?

For every pair of Ben blocks that end up inside one batch outline (runs/batch of bench44), take the ground between them
(pixels off his blocks whose distance to block i plus distance to block k is at most the gap width + 8 px) and:
  - the share of that gap ground the area map calls street (P(block) < 0.5), and its mean P(block);
  - the share of Ben's sides facing the gap (his block boundary within gap+8 px of the other block) that have line-map
    support (P(line) > 0.5 / > 0.25 within 5 px), i.e. whether the line network drew the dividing line.
Read-only; writes merge_cues.json here.
    python merge_cues.py
"""
import json, os, sys
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
sys.dont_write_bytecode = True; sys.path.insert(0, HERE); import bench44_copy as B  # noqa: E402

T = B.load_truth(); gt = T['gt']; ng = T['ng']; h2, w2 = gt.shape
polys = json.load(open(HERE + '../bench44/runs/batch/outlines.json'))
pr = B.raster([np.array([s['a'] for s in p], float) for p in polys]); npr = len(polys)
pa = cv2.resize(cv2.imread(B.U + '44_pred_area_ng1.png', 0), (w2, h2), interpolation=cv2.INTER_AREA)
pl = cv2.imread(B.U + '44_lines_lines_ng1.png', 0)
plh = cv2.resize(cv2.dilate(pl, np.ones((11, 11), np.uint8)), (w2, h2), interpolation=cv2.INTER_NEAREST)   # max within 5 px full size
m = (gt > 0) | (pr > 0)
joint = np.bincount(gt[m].astype(np.int64) * (npr + 1) + pr[m], minlength=(ng + 1) * (npr + 1)).reshape(ng + 1, npr + 1)
ga = joint.sum(1)
dts = {}
def dt(i):
    if i not in dts: dts[i] = cv2.distanceTransform((gt != i).astype(np.uint8), cv2.DIST_L2, 5)
    return dts[i]
out = []
for j in range(1, npr + 1):
    held = [i for i in range(1, ng + 1) if joint[i, j] >= 0.5 * ga[i]]
    if len(held) < 2: continue
    for x in range(len(held)):
        for y in range(x + 1, len(held)):
            i, k = held[x], held[y]; di, dk = dt(i), dt(k)
            gap = float((di[gt == k]).min())                      # half px
            if gap > 80: continue                                  # not neighbours
            g = (gt == 0) & (di + dk <= gap + 4) & (pr == j)
            if g.sum() < 20: continue
            side = ((gt == i) & (dk <= gap + 4)) | ((gt == k) & (di <= gap + 4))
            side &= cv2.dilate(((gt == i) | (gt == k)).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~cv2.erode(((gt == i) | (gt == k)).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
            mid = g & (np.abs(di - dk) <= 1.5)
            out.append(dict(poly=j - 1, ben=[i, k], gap_full_px=round(gap * 2, 1), gap_px=int(g.sum() * 4),
                            street_share=round(float((pa[g] < 128).mean()), 3), mean_P=round(float(pa[g].mean() / 255), 3),
                            mid_street_share=round(float((pa[mid] < 128).mean()), 3) if mid.any() else None, mid_min_P=round(float(pa[mid].min() / 255), 3) if mid.any() else None,
                            side_line_05=round(float((plh[side] > 127).mean()), 3), side_line_025=round(float((plh[side] > 64).mean()), 3), side_px=int(side.sum())))
            print(json.dumps(out[-1]), flush=True)
json.dump(out, open(HERE + 'merge_cues.json', 'w'), indent=1)
arr = lambda k: np.array([o[k] for o in out if o[k] is not None])
print('pairs', len(out), 'median street_share', np.median(arr('street_share')), 'median side_line_05', np.median(arr('side_line_05')), 'median side_line_025', np.median(arr('side_line_025')))
