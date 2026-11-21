import cv2, numpy as np, json
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
for N in ['82A','80','43','45','44']:
    d = json.load(open(U+f'{N}_rail_rule.json',encoding='utf8'))
    lab = cv2.imread(U+f'{N}_label.png',0); h,w = lab.shape; p = cv2.imread(U+f'{N}_pred_area_ng1.png',0)>127
    R = np.zeros((h,w),np.uint8); L=0
    for t in d['tracks']:
        if t['kind'] != 'railroad': continue
        q = np.array(t['pts'])/2; L += np.hypot(*np.diff(q,axis=0).T).sum()
        cv2.polylines(R,[q.round().astype(np.int32)],False,1,1)
    dr = cv2.distanceTransform((R==0).astype(np.uint8),cv2.DIST_L2,3); z=(dr<=10)&(lab!=255)
    print(N, f'rule railroad length {L:.0f} half-px; labelled px within 10 px of a track {int(z.sum())}: label block {(lab[z]==1).mean():.3f}; area_ng1 block {p[z].mean():.3f}; share of labelled block px on plate {((lab==1)&z).sum()/(lab==1).sum():.3f}')
