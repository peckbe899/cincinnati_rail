"""Read-only: for each merge in plate 44's outlines (one predicted block covering >= 2 of Ben's blocks), how wide is the
street between the merged blocks, and how much of that street ground did the area network / line network see?"""
import json
import numpy as np, cv2
from pq44 import gt_instances, pred_from_outlines, D, S
gt, ng, shape = gt_instances()
pr, npr = pred_from_outlines(D + 'picks22_guided/22-44/outlines.json', shape)
sm = json.load(open(D + 'streetmap/22-44.json', encoding='utf8'))
pa = cv2.resize(cv2.imread(D + 'unet_data/44_pred_edge_v1.png', 0), (shape[1], shape[0]))
pn = cv2.resize(cv2.imread(D + 'unet_data/44_pred_area_ng1.png', 0), (shape[1], shape[0]))
pl = cv2.imread(D + 'unet_data/44_lines_lines_v2.png', 0); pl = cv2.resize(pl, (shape[1], shape[0]), interpolation=cv2.INTER_AREA)
ga = np.bincount(gt.ravel(), minlength=ng + 1)
res = []
for j in range(1, npr + 1):
    m = pr == j
    ids, cnt = np.unique(gt[m], return_counts=True)
    cov = [(int(i), int(c)) for i, c in zip(ids, cnt) if i > 0 and c > 0.2 * ga[i]]
    if len(cov) < 2: continue
    # street between them: ground inside the predicted block that is in no gt block
    between = m & (gt == 0)
    # width: the distance between each pair of covered gt blocks
    widths = []
    for a in range(len(cov)):
        da = cv2.distanceTransform((gt != cov[a][0]).astype(np.uint8), cv2.DIST_L2, 3)
        for b in range(a + 1, len(cov)):
            mb = gt == cov[b][0]; d = float(da[mb].min()) / S   # full-size px
            if d < 400: widths.append(round(d, 1))
    res.append(dict(pred=j, gt_blocks=[c[0] for c in cov], street_px_between=int(between.sum() / S / S),
                    min_gap_fullpx=sorted(widths)[:3],
                    edge_v1_says_street=round(float((pa[between] <= 127).mean()), 3) if between.any() else None,
                    area_ng1_says_street=round(float((pn[between] <= 127).mean()), 3) if between.any() else None,
                    lines_v2_mean=round(float(pl[between].mean()), 1) if between.any() else None))
for r in res: print(json.dumps(r))
gaps = [r['min_gap_fullpx'][0] for r in res if r['min_gap_fullpx']]
print('merged predictions', len(res), 'gt blocks involved', sum(len(r['gt_blocks']) for r in res))
print('narrowest gap between merged blocks (full px): ', sorted(gaps))
# for reference: the gaps between neighbouring gt blocks that were NOT merged
allw = []
for i in range(1, ng + 1):
    di = cv2.distanceTransform((gt != i).astype(np.uint8), cv2.DIST_L2, 3)
    for k in range(i + 1, ng + 1):
        d = float(di[gt == k].min()) / S
        if d < 400: allw.append(d)
print('all neighbouring gt block gaps < 400 px (full px), quartiles:', np.percentile(allw, [0, 25, 50, 75, 100]).round(1).tolist(), 'n', len(allw))
