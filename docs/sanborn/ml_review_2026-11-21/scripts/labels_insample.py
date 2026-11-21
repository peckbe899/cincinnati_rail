import numpy as np, cv2
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
for N in ['82A', '80', '43', '45', '44']:
    lab = cv2.imread(U + f'{N}_label.png', 0); p = cv2.imread(U + f'{N}_pred_area_ng1.png', 0)
    m = lab != 255; pr = p[m] > 127; gt = lab[m] == 1
    iou = lambda a, b: float((a & b).sum() / max(1, (a | b).sum()))
    conf = np.abs(p[m].astype(np.float32) / 255 - 0.5).mean() * 2
    print(N, 'area_ng1 accuracy', round(float((pr == gt).mean()), 4), 'iou_street', round(iou(~pr, ~gt), 4), 'mean confidence', round(float(conf), 3))
