"""Read-only: crops of plate 44 around the merged predictions: scan, Ben's closed blocks (green), the guided pipeline's
block (red), ground the label calls block (blue tint). Written to this scratch folder only."""
import json, os
import numpy as np, cv2
from pq44 import gt_instances, pred_from_outlines, D, S
OUT = os.path.dirname(os.path.abspath(__file__)) + '/'
gt, ng, shape = gt_instances(); h, w = shape
pr, npr = pred_from_outlines(D + 'picks22_guided/22-44/outlines.json', shape)
img = cv2.resize(cv2.imread(D + 'cufp/22-44.jpg'), (w, h), interpolation=cv2.INTER_AREA)
lab = cv2.imread(D + 'unet_data/44_label.png', 0)
pn = cv2.resize(cv2.imread(D + 'unet_data/44_pred_area_ng1.png', 0), (w, h))
ga = np.bincount(gt.ravel(), minlength=ng + 1)
for j in (19, 34, 22, 46):
    m = pr == j; ys, xs = np.where(m)
    y0, y1, x0, x1 = max(0, ys.min() - 40), min(h, ys.max() + 40), max(0, xs.min() - 40), min(w, xs.max() + 40)
    v = img[y0:y1, x0:x1].copy().astype(np.float32)
    L = lab[y0:y1, x0:x1]
    v[L == 1] = v[L == 1] * 0.75 + np.array([255, 120, 0]) * 0.25        # label: block (blue tint)
    v = v.astype(np.uint8)
    for k in range(1, ng + 1):
        mk = (gt[y0:y1, x0:x1] == k).astype(np.uint8)
        if mk.any(): cs, _ = cv2.findContours(mk, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE); cv2.drawContours(v, cs, -1, (0, 170, 0), 3)
    cs, _ = cv2.findContours(m[y0:y1, x0:x1].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE); cv2.drawContours(v, cs, -1, (0, 0, 230), 2)
    s2 = (pn[y0:y1, x0:x1] <= 127).astype(np.uint8)
    cs, _ = cv2.findContours(s2, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE); cv2.drawContours(v, cs, -1, (200, 0, 200), 1)
    f = min(1.0, 1400 / max(v.shape[:2])); v = cv2.resize(v, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    cv2.imwrite(OUT + f'merge_pred{j}.jpg', v, [cv2.IMWRITE_JPEG_QUALITY, 85]); print('wrote', j, (y0, y1, x0, x1), v.shape)
