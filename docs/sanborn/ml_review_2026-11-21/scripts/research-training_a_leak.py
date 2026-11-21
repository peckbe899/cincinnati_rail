# read-only: compare area-network answers on its training plates vs the held-out plate 44
import cv2, numpy as np, json
U = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
res = {}
for model in ('area_ng1', 'edge_v1'):
    for p in ('82A', '80', '43', '45', '44'):
        lab = cv2.imread(U + f'{p}_label.png', 0); pr = cv2.imread(U + f'{p}_pred_{model}.png', 0)
        if pr is None or lab is None: continue
        m = lab != 255; gt = lab[m] == 1; pb = pr[m].astype(np.float32) / 255; ph = pb > 0.5
        iou_s = float(((~ph) & (~gt)).sum() / max(1, ((~ph) | (~gt)).sum()))
        # confidence: share of labelled pixels with p in (0.1, 0.9); mean binary entropy
        unsure = float(((pb > 0.1) & (pb < 0.9)).mean())
        e = -(pb * np.log(pb + 1e-6) + (1 - pb) * np.log(1 - pb + 1e-6)); 
        # calibration: accuracy among confident pixels
        conf = (pb < 0.05) | (pb > 0.95)
        res[f'{model} {p}'] = dict(acc=round(float((ph == gt).mean()), 4), iou_street=round(iou_s, 4), unsure_share=round(unsure, 4), mean_entropy=round(float(e.mean()), 4),
                                   confident_share=round(float(conf.mean()), 4), acc_confident=round(float((ph[conf] == gt[conf]).mean()), 4), acc_unconfident=round(float((ph[~conf] == gt[~conf]).mean()), 4))
for k, v in res.items(): print(k, json.dumps(v))
