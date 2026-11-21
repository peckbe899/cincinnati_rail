import cv2, numpy as np, json, os
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
for N in ['82A','80','43','45','44']:
    f = U+f'{N}_rail_rule.json'
    if not os.path.exists(f): print(N,'no rule'); continue
    d = json.load(open(f,encoding='utf8'))
    lab = cv2.imread(U+f'{N}_label.png',0); h,w = lab.shape; p = cv2.imread(U+f'{N}_pred_area_ng1.png',0)>127
    g = cv2.imread(U+f'{N}_guide.png')[:,:,0]>127
    R = np.zeros((h,w),np.uint8); kinds={}
    for t in d['tracks']:
        kinds[t['kind']] = kinds.get(t['kind'],0)+1
        if t['kind'] != 'railroad': continue
        cv2.polylines(R,[(np.array(t['pts'],float)/2).round().astype(np.int32)],False,1,1)
    dr = cv2.distanceTransform((R==0).astype(np.uint8),cv2.DIST_L2,3); z=(dr<=10)&(lab!=255)
    m = lab!=255; gt=lab==1; err = m&(p!=gt)
    bf = SP+f'picks22_guided/22-{N}/rail_ben.json'
    print(N, kinds, 'ben rail' if os.path.exists(bf) else '', f'band px {int(z.sum())} ({z.sum()/m.sum():.3f} of labelled); label block {(lab[z]==1).mean():.3f}; parcels {g[z].mean():.3f}; ng1 block {p[z].mean():.3f}; acc overall {1-err.sum()/m.sum():.4f}, in band {1-err[z].sum()/z.sum():.3f}; share of errs in band {err[z].sum()/err.sum():.3f}; band share of label block px {(gt&z).sum()/gt.sum():.3f}')
