import cv2, numpy as np, json
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
sm = json.load(open(SP+'streetmap/22-44.json',encoding='utf8'))
lab = cv2.imread(U+'44_label.png',0); h,w = lab.shape
alpha = cv2.resize(np.load(SP+'cufp/44/png_alpha_s4.npy').astype(np.float32),(w,h)) > 0.5
B = np.zeros((h,w),np.uint8)
for b in sm['blocks']: cv2.fillPoly(B,[(np.array(b['ring'])/2).round().astype(np.int32)],1)
# Ben line pixels sampled densely (not rasterised) -> list of points at half size
pts = []
for l in sm['lines']:
    if l['kind'] not in ('printed','drawn'): continue
    a = np.array(l['a'],float)/2; b = np.array(l['b'],float)/2; L = np.hypot(*(b-a)); n = max(2,int(L))
    pts.append(a + np.outer(np.linspace(0,1,n), b-a))
pts = np.vstack(pts); xi = np.clip(pts[:,0].round().astype(int),0,w-1); yi = np.clip(pts[:,1].round().astype(int),0,h-1)
Bin = cv2.erode(B, np.ones((7,7),np.uint8)) > 0
Lr = np.zeros((h,w),np.uint8)
for l in sm['lines']: cv2.line(Lr, tuple((np.array(l['a'])/2).round().astype(int)), tuple((np.array(l['b'])/2).round().astype(int)), 1, 1)
dl = cv2.distanceTransform((Lr==0).astype(np.uint8), cv2.DIST_L2, 5)
m = lab != 255; gt = lab == 1
for name in ['area_ng1','edge_v1']:
    p = cv2.imread(U+f'44_pred_{name}.png',0) > 127
    bnd = cv2.morphologyEx(p.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3,3),np.uint8)) > 0
    bnd &= alpha   # ignore boundary against off-paper
    db = cv2.distanceTransform((~bnd).astype(np.uint8), cv2.DIST_L2, 5)
    dd = db[yi,xi]
    print(name, 'acc on label', round(float((p[m]==gt[m]).mean()),4), '| Ben line pts within 1.5/3/6:', [round(float((dd<=t).mean()),3) for t in (1.5,3,6)],
          '| Ben interior called block', round(float(p[Bin].mean()),4), '| boundary px >10 from any Ben line inside his blocks', int((bnd & Bin & (dl>10)).sum()), '| total boundary px on paper', int(bnd.sum()))
