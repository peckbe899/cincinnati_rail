"""Read-only: on the street ground between blocks that the guided pipeline merged on plate 44, what do the training
label (44_label.png) and the guide (44_guide.png, today's blocks) say? Also: line-network recall along Ben's printed lines."""
import json
import numpy as np, cv2
from pq44 import gt_instances, pred_from_outlines, D, S
gt, ng, shape = gt_instances(); h, w = shape
pr, npr = pred_from_outlines(D + 'picks22_guided/22-44/outlines.json', shape)
lab = cv2.imread(D + 'unet_data/44_label.png', 0); gd = cv2.imread(D + 'unet_data/44_guide.png')
print('label shape', lab.shape, 'guide shape', gd.shape, 'gt shape', shape)
lab = cv2.resize(lab, (w, h), interpolation=cv2.INTER_NEAREST); gb = cv2.resize(gd[:, :, 0], (w, h), interpolation=cv2.INTER_NEAREST)
print('guide block channel values', np.unique(gb)[:10])
ga = np.bincount(gt.ravel(), minlength=ng + 1)
tot = dict(street=0, block=0, ignore=0, guide_block=0, n=0)
for j in range(1, npr + 1):
    m = pr == j; ids, cnt = np.unique(gt[m], return_counts=True)
    cov = [int(i) for i, c in zip(ids, cnt) if i > 0 and c > 0.2 * ga[i]]
    if len(cov) < 2: continue
    bt = m & (gt == 0); L = lab[bt]
    r = dict(pred=j, gt=cov, px=int(bt.sum()), label_street=round(float((L == 0).mean()), 3), label_block=round(float((L == 1).mean()), 3),
             label_ignore=round(float((L == 255).mean()), 3), guide_says_block=round(float((gb[bt] > 127).mean()), 3))
    print(json.dumps(r))
    for k, v in (('street', (L == 0).sum()), ('block', (L == 1).sum()), ('ignore', (L == 255).sum()), ('guide_block', (gb[bt] > 127).sum()), ('n', bt.sum())): tot[k] += int(v)
print('all merged-street ground:', {k: round(v / tot['n'], 3) for k, v in tot.items() if k != 'n'}, 'px(half)', tot['n'])
# the same on all street ground of Ben's map (inside the paper, between his blocks) for reference
al = cv2.resize(np.load(D + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (w, h)) > 0.5
st = (gt == 0) & al & (lab != 255)
print('reference, all of Ben street ground that the label scores: label street share', round(float((lab[st] == 0).mean()), 3), 'guide block share', round(float((gb[st] > 127).mean()), 3))
st2 = (gt == 0) & al
print('reference, all of Ben street ground: label street', round(float((lab[st2] == 0).mean()), 3), 'label block', round(float((lab[st2] == 1).mean()), 3), 'ignore', round(float((lab[st2] == 255).mean()), 3))
bk = (gt > 0)
print('reference, all of Ben block ground: label block', round(float((lab[bk] == 1).mean()), 3), 'label street', round(float((lab[bk] == 0).mean()), 3), 'ignore', round(float((lab[bk] == 255).mean()), 3))
