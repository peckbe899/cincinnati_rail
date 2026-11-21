import cv2, numpy as np, json
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
for N in ['82A','80','43','45','44']:
    lab = cv2.imread(U+f'{N}_label.png',0); p = cv2.imread(U+f'{N}_pred_area_ng1.png',0) > 127
    n, cc, st, _ = cv2.connectedComponentsWithStats((lab==1).astype(np.uint8), connectivity=4)
    s = st[1:]; s = s[s[:,4] > 2000]; bw = np.median(np.minimum(s[:,2], s[:,3])); bl = np.median(np.maximum(s[:,2], s[:,3]))
    m = lab != 255; gt = lab == 1; err = (m & (p != gt)).astype(np.uint8)
    e = cv2.morphologyEx((lab==1).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3,3),np.uint8)) | cv2.morphologyEx((lab==0).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3,3),np.uint8))
    de = cv2.distanceTransform((e==0).astype(np.uint8), cv2.DIST_L2, 3)
    n2, cc2, st2, _ = cv2.connectedComponentsWithStats(err, connectivity=8); big = np.isin(cc2, 1 + np.where(st2[1:,4] >= 2000)[0])
    print(N, f'blocks>2000px: {len(s)}, median bbox short {bw:.0f} long {bl:.0f} | errs >=20 px from label edge {float((de[err>0]>=20).mean()):.3f}; in patches >=2000 px {float(big[err>0].mean()):.3f}')
# 44: same excluding rail band
lab = cv2.imread(U+'44_label.png',0); h,w = lab.shape; p = cv2.imread(U+'44_pred_area_ng1.png',0) > 127
R = np.zeros((h,w),np.uint8)
for t in json.load(open(SP+'picks22_guided/22-44/rail_ben.json',encoding='utf8'))['tracks']:
    if t['kind']=='railroad': cv2.polylines(R,[(np.array(t['pts'],float)/2).round().astype(np.int32)],False,1,1)
sm = json.load(open(SP+'streetmap/22-44.json',encoding='utf8')); B = np.zeros((h,w),np.uint8)
for b in sm['blocks']: cv2.fillPoly(B,[(np.array(b['ring'])/2).round().astype(np.int32)],1)
band = (cv2.distanceTransform((R==0).astype(np.uint8),cv2.DIST_L2,3) <= 20) & (B==0)
m = lab != 255; gt = lab==1; err = (m & (p != gt)).astype(np.uint8)
n2, cc2, st2, _ = cv2.connectedComponentsWithStats(err, connectivity=8); big = np.isin(cc2, 1 + np.where(st2[1:,4] >= 2000)[0])
e2 = err.astype(bool) & ~band
print('44 excl rail band: errs in patches>=2000', round(float(big[e2].mean()),3), '; errs inside Ben closed blocks', int(err[B>0].sum()), 'of', int(err.sum()))
