import cv2, numpy as np, glob, os
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
STEP = 640; res = []
for f in sorted(glob.glob(U+'*_pred_area_ng1.png')):
    N = os.path.basename(f).split('_')[0]
    p = cv2.imread(f,0)
    if p is None: continue
    b = p > 127; h,w = b.shape
    try: al = cv2.resize(np.load(SP+f'cufp/{N}/png_alpha_s4.npy').astype(np.float32),(w,h)) > 0.5
    except Exception: al = np.ones_like(b)
    fx = (b[:,1:] != b[:,:-1]) & al[:,1:] & al[:,:-1]   # fx[:,c] = change between col c and c+1
    fy = (b[1:] != b[:-1]) & al[1:] & al[:-1]
    mx = al[:,1:] & al[:,:-1]; my = al[1:] & al[:-1]
    sc = np.array([c-1 for c in range(STEP, w, STEP)],int); sr = np.array([r-1 for r in range(STEP, h, STEP)],int)
    # control: columns offset by 320 from seams (mid-tile)
    cc = np.array([c-1 for c in range(STEP//2, w, STEP)],int); cr = np.array([r-1 for r in range(STEP//2, h, STEP)],int)
    def rate(F, M, idx, ax):
        if ax == 1: return F[:,idx].sum()/max(1,M[:,idx].sum())
        return F[idx].sum()/max(1,M[idx].sum())
    r = (rate(fx,mx,sc,1), rate(fx,mx,cc,1), rate(fy,my,sr,0), rate(fy,my,cr,0), fx.sum()/mx.sum())
    res.append(r)
print('plates', len(res))
r = np.array(res).mean(0)
print('col flips: seam %.4f  mid-tile %.4f  all %.4f | row flips: seam %.4f mid-tile %.4f' % (r[0], r[1], r[4], r[2], r[3]))
# share of predicted boundary pixels that lie on seam lines (+-1 px) on plate 44
p = cv2.imread(U+'44_pred_area_ng1.png',0) > 127; h,w = p.shape
bnd = cv2.morphologyEx(p.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3,3),np.uint8)) > 0
seam = np.zeros((h,w),bool)
for c in range(STEP, w, STEP): seam[:, c-2:c+2] = True
for rr in range(STEP, h, STEP): seam[rr-2:rr+2, :] = True
print('44: boundary px on +-2 of a seam', int((bnd&seam).sum()), 'share', round(float((bnd&seam).sum()/bnd.sum()),4), 'seam band share of plate', round(float(seam.mean()),4))
