import cv2, numpy as np, json
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
d = json.load(open(SP+'picks22_guided/22-44/rail_ben.json',encoding='utf8'))
from collections import Counter
print(Counter(t['kind'] for t in d['tracks']), d.get('complete'), d.get('note','')[:200])
lab = cv2.imread(U+'44_label.png',0); h,w = lab.shape; p = cv2.imread(U+'44_pred_area_ng1.png',0)>127
R = np.zeros((h,w),np.uint8)
for t in d['tracks']:
    if t['kind'] == 'streetcar': continue
    cv2.polylines(R,[(np.array(t['pts'])/2).round().astype(np.int32)],False,1,1)
m = lab!=255; gt = lab==1; err = m & (p!=gt)
sm = json.load(open(SP+'streetmap/22-44.json',encoding='utf8'))
B = np.zeros((h,w),np.uint8)
for b in sm['blocks']: cv2.fillPoly(B,[(np.array(b['ring'])/2).round().astype(np.int32)],1)
dr = cv2.distanceTransform((R==0).astype(np.uint8),cv2.DIST_L2,3)
for rad in (10,20,30):
    z = (dr<=rad) & (B==0)          # within rad half-px of a railroad track, outside Ben's closed blocks
    print(f'rail buffer {rad}px outside Ben blocks: px {int(z.sum())}, label block {gt[z].mean():.3f} street {(lab[z]==0).mean():.3f} ignore {(lab[z]==255).mean():.3f}; area_ng1 calls block {p[z].mean():.3f}; share of all 44 errors here {err[z].sum()/err.sum():.3f}')
z = (dr<=20)&(B==0)&m
acc_all = 1-err.sum()/m.sum(); acc_wo = 1-(err&~z).sum()/(m&~z).sum()
print('accuracy on 44', round(float(acc_all),4), 'excluding rail buffer 20px', round(float(acc_wo),4))
