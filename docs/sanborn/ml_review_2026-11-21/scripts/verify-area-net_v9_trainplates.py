import cv2, numpy as np
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
for N in ['82A','80','43','45','44']:
    lab = cv2.imread(U+f'{N}_label.png',0); p = cv2.imread(U+f'{N}_pred_area_ng1.png',0).astype(np.float32)/255
    e = cv2.imread(U+f'{N}_edge.png',0); tgt = (cv2.dilate(e, np.ones((3,3),np.uint8)) > 0).astype(np.uint8); tgt[(lab==255)&(tgt==0)] = 255
    m = lab != 255; pr = p[m] > 0.5; gt = lab[m] == 1
    iou = lambda a,b: float((a&b).sum()/max(1,(a|b).sum()))
    b = cv2.morphologyEx((p>0.5).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3,3),np.uint8)) > 0
    nb = cv2.dilate(b.astype(np.uint8), np.ones((5,5),np.uint8)) > 0
    print(N, 'acc %.4f iou_street %.3f green_met %.3f' % ((pr==gt).mean(), iou(~pr,~gt), nb[tgt==1].mean()))
