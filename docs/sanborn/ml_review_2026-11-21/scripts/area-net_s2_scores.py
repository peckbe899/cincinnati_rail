import cv2, numpy as np
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
def sc(p, lab, t=0.5):
    m = lab != 255; pr = p[m] > t; gt = lab[m] == 1
    iou = lambda a, b: float((a & b).sum() / max(1, (a | b).sum()))
    return round(float((pr == gt).mean()),4), round(iou(pr,gt),4), round(iou(~pr,~gt),4), round(float(1-pr.mean()),3)
for N in ['82A','80','43','45','44']:
    lab = cv2.imread(U+f'{N}_label.png',0)
    alpha = cv2.resize(np.load(SP+f'cufp/{N}/png_alpha_s4.npy').astype(np.float32),(lab.shape[1],lab.shape[0]))>0.5
    print(N, 'labelled off paper px', int(((lab!=255)&~alpha).sum()))
    for model in ['area_ng1','edge_v1']:
        p = cv2.imread(U+f'{N}_pred_{model}.png',0)
        if p is None: continue
        p = p.astype(np.float32)/255
        a = sc(p, lab); print(f'  {model:9s} acc {a[0]} iou_block {a[1]} iou_street {a[2]} pred street share {a[3]} (label street share {float((lab[lab!=255]==0).mean()):.3f})')
        if N == '44':
            for t in [0.3,0.4,0.5,0.6,0.7,0.8]:
                print('     thr', t, sc(p, lab, t))
