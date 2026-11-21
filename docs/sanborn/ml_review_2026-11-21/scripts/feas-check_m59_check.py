"""Read-only checks for M5 and M9/M10.
M5: after M1+M2 (min map + instance markers, run H), what separates the blocks that are still merged: street width in
    Ben's map, and what the TRAINING LABEL (44_label.png) and both area maps say on that ground. A skeleton-recall loss on
    the label's street class can only help where the label says street.
M9/M10: SQ 0.84-0.90 -> how far off are the matched outlines? Boundary distance pred->gt and gt->pred, in FULL px."""
import json
import numpy as np, cv2
from shapely.geometry import Polygon
import ws44 as W
from pq44 import pq, pred_from_outlines, D
from m1_check import ws_inst, per_instance, half

sm = json.load(open(D + 'streetmap/22-44.json', encoding='utf8')); polys = [Polygon(b['ring']).buffer(0) for b in sm['blocks']]
gt, ng = W.gt, W.ng; h, w = W.shape
lab = cv2.resize(cv2.imread(D + 'unet_data/44_label.png', 0), (w, h), interpolation=cv2.INTER_NEAREST)
e1h = cv2.resize(cv2.imread(D + 'unet_data/44_pred_edge_v1.png', 0), (w, h)); ngh = cv2.resize(cv2.imread(D + 'unet_data/44_pred_area_ng1.png', 0), (w, h))

def merged_pairs(pr, npr):
    m = (gt > 0) | (pr > 0)
    joint = np.bincount(gt[m].astype(np.int64) * (npr + 1) + pr[m], minlength=(ng + 1) * (npr + 1)).reshape(ng + 1, npr + 1); ga, pa = joint.sum(1), joint.sum(0)
    out = []
    for i in range(1, ng + 1):
        j = int(np.argmax(joint[i, 1:])) + 1; inter = joint[i, j]
        if inter / (ga[i] + pa[j] - inter) > 0.5: continue
        cov = [int(k) for k in np.where(joint[1:, j] > 0.2 * ga[1:])[0] + 1]
        out.append((i, j, cov))
    return out

e1, ng1 = W.area('edge_v1'), W.area('area_ng1'); mn = np.minimum(e1, ng1)
ws = ws_inst(mn, W.pl); inst, k = per_instance(ws); pr = half(inst)
print(json.dumps({x: y for x, y in pq(gt, ng, pr, k, 'H').items() if x in ('tp', 'fp', 'fn', 'PQ')}))
seen = set()
for i, j, cov in merged_pairs(pr, k):
    if j in seen: continue
    seen.add(j); between = (pr == j) & (gt == 0)
    widths = [round(polys[a - 1].distance(polys[b - 1]), 1) for a in cov for b in cov if a < b]
    L = lab[between]
    print(json.dumps(dict(pred=j, gt_blocks=cov, ben_gap_full_px=widths, ground_half_px=int(between.sum()),
                          label_street=round(float((L == 0).mean()), 3), label_block=round(float((L == 1).mean()), 3), label_ignore=round(float((L == 255).mean()), 3),
                          edge_v1_street=round(float((e1h[between] <= 127).mean()), 3), area_ng1_street=round(float((ngh[between] <= 127).mean()), 3))))

# M9/M10: boundary offsets of matched outlines (outlines.json, the real guided output), in full px
pro, npo = pred_from_outlines(D + 'picks22_guided/22-44/outlines.json', (h, w))
m = (gt > 0) | (pro > 0)
joint = np.bincount(gt[m].astype(np.int64) * (npo + 1) + pro[m], minlength=(ng + 1) * (npo + 1)).reshape(ng + 1, npo + 1); ga, pa = joint.sum(1), joint.sum(0)
d_all, per = [], []
for i in range(1, ng + 1):
    j = int(np.argmax(joint[i, 1:])) + 1; inter = joint[i, j]; iou = inter / (ga[i] + pa[j] - inter)
    if iou <= 0.5: continue
    g = (gt == i).astype(np.uint8); p = (pro == j).astype(np.uint8)
    gb = cv2.morphologyEx(g, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0; pb = cv2.morphologyEx(p, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    dg = cv2.distanceTransform((~gb).astype(np.uint8), cv2.DIST_L2, 3); dp = cv2.distanceTransform((~pb).astype(np.uint8), cv2.DIST_L2, 3)
    d = np.r_[dg[pb], dp[gb]] * 2.0                      # half size -> full px
    d_all.append(d); per.append((round(float(iou), 3), round(float(np.median(d)), 1), round(float(np.percentile(d, 90)), 1), int(ga[i])))
d_all = np.concatenate(d_all)
print('matched', len(per), 'boundary distance full px: median', round(float(np.median(d_all)), 1), 'p75', round(float(np.percentile(d_all, 75)), 1), 'p90', round(float(np.percentile(d_all, 90)), 1),
      'share <= 6 px', round(float((d_all <= 6).mean()), 3), 'share > 20 px', round(float((d_all > 20).mean()), 3))
per.sort(); print('lowest-IoU matched blocks (iou, median d, p90 d, gt half px):', per[:8])
print('median block area half px', int(np.median([p[3] for p in per])))
