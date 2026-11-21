import cv2, numpy as np, glob, os
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
STEP = 640
tot = []
for f in sorted(glob.glob(U+'*_pred_area_ng1.png')):
    N = os.path.basename(f).split('_')[0]
    p = cv2.imread(f,0).astype(np.float32)/255; h,w = p.shape
    try: alpha = cv2.resize(np.load(SP+f'cufp/{N}/png_alpha_s4.npy').astype(np.float32),(w,h))>0.5
    except Exception: alpha = np.ones_like(p,bool)
    dy = np.abs(p[1:]-p[:-1]); mky = alpha[1:]&alpha[:-1]       # dy[i] = |p[i+1]-p[i]|
    dx = np.abs(p[:,1:]-p[:,:-1]); mkx = alpha[:,1:]&alpha[:,:-1]
    # binary flips
    by = ((p[1:]>0.5)!=(p[:-1]>0.5)); bx = ((p[:,1:]>0.5)!=(p[:,:-1]>0.5))
    seam_r = [y-1 for y in range(STEP,h,STEP)]; seam_c=[x-1 for x in range(STEP,w,STEP)]
    non_r = [r for r in range(h-1) if all(abs(r-s)>3 for s in seam_r)]; non_c=[c for c in range(w-1) if all(abs(c-s)>3 for s in seam_c)]
    def m(d, mk, idx, axis):
        if axis==0: return float(d[idx][mk[idx]].mean())
        return float(d[:,idx][mk[:,idx]].mean())
    r = (m(dy,mky,seam_r,0), m(dy,mky,non_r,0), m(dx,mkx,seam_c,1), m(dx,mkx,non_c,1), m(by.astype(np.float32),mky,seam_r,0), m(by.astype(np.float32),mky,non_r,0), m(bx.astype(np.float32),mkx,seam_c,1), m(bx.astype(np.float32),mkx,non_c,1))
    tot.append(r)
    print(f'{N:4s} {h}x{w} |dP| seam rows {r[0]:.4f} other rows {r[1]:.4f} (x{r[0]/r[1]:.1f}) | seam cols {r[2]:.4f} other {r[3]:.4f} (x{r[2]/r[3]:.1f}) | 0.5-flips seam rows {r[4]:.4f} other {r[5]:.4f} | cols {r[6]:.4f} other {r[7]:.4f}')
t = np.array(tot).mean(0); print('MEAN', np.round(t,4), 'ratios', round(t[0]/t[1],2), round(t[2]/t[3],2), round(t[4]/t[5],2), round(t[6]/t[7],2))
