import cv2, numpy as np
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
for N in ['82A','80','43','45','44']:
    lab = cv2.imread(U+f'{N}_label.png',0); p = cv2.imread(U+f'{N}_pred_area_ng1.png',0)>127; e = cv2.imread(U+f'{N}_edge.png',0)>0
    blk = (lab==1).astype(np.uint8); n, cc, st, _ = cv2.connectedComponentsWithStats(blk, connectivity=4)
    big = st[1:][st[1:,4]>2000]; dims = np.sort(big[:,2:4],1)
    # street width: 2 x distance to nearest non-street, sampled on the street skeleton approx by local maxima
    s = (lab==0).astype(np.uint8); d = cv2.distanceTransform(s, cv2.DIST_L2, 5)
    mx = (d == cv2.dilate(d, np.ones((7,7),np.uint8))) & (d>2)
    w = 2*d[mx]
    b = cv2.morphologyEx(p.astype(np.uint8),cv2.MORPH_GRADIENT,np.ones((3,3),np.uint8))>0; nb = cv2.dilate(b.astype(np.uint8),np.ones((5,5),np.uint8))>0
    print(N, f'blocks>2000px: {len(big)}, short side median {np.median(dims[:,0]):.0f} long side median {np.median(dims[:,1]):.0f} px | street width (2*inscribed) median {np.median(w):.0f} p90 {np.percentile(w,90):.0f} px | green edge met by area_ng1 boundary {nb[e].mean():.3f}')
