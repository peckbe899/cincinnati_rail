import cv2, numpy as np, json
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
for N in ['44','43']:
    lab = cv2.imread(U+f'{N}_label.png',0); p = cv2.imread(U+f'{N}_pred_area_ng1.png',0)>127
    m = lab!=255; gt = lab==1
    err = m & (p!=gt)
    # distance from each pixel to the nearest pixel of the other class (label boundary)
    db = np.minimum(cv2.distanceTransform((lab!=1).astype(np.uint8),cv2.DIST_L2,3), cv2.distanceTransform((lab!=0).astype(np.uint8),cv2.DIST_L2,3))
    # db is distance to nearest pixel NOT of own class (incl ignore) -> use distance to opposite class instead
    d_to_block = cv2.distanceTransform((lab!=1).astype(np.uint8),cv2.DIST_L2,3)
    d_to_street = cv2.distanceTransform((lab!=0).astype(np.uint8),cv2.DIST_L2,3)
    dopp = np.where(gt, cv2.distanceTransform((lab!=0).astype(np.uint8)*0+ (lab!=0).astype(np.uint8),cv2.DIST_L2,3), 0)
    # proper: for block pixel distance to nearest street pixel; for street pixel distance to nearest block pixel
    ds = cv2.distanceTransform((lab!=0).astype(np.uint8),cv2.DIST_L2,3)  # dist to nearest street px
    dbk = cv2.distanceTransform((lab!=1).astype(np.uint8),cv2.DIST_L2,3) # dist to nearest block px
    dd = np.where(gt, ds, dbk)
    tot = err.sum(); print(N, 'errors', int(tot), 'share of labelled', round(float(tot/m.sum()),4))
    for a,b in [(0,3),(3,8),(8,20),(20,50),(50,1e9)]:
        sel = m & (dd>=a) & (dd<b)
        print(f'   dist to other class {a}-{b}: share of labelled {sel.sum()/m.sum():.3f}, error rate {err[sel].mean():.4f}, share of all errors {err[sel].sum()/tot:.3f}')
    n, cc, st, _ = cv2.connectedComponentsWithStats(err.astype(np.uint8), connectivity=8)
    a = st[1:,4]; a.sort()
    cum = np.cumsum(a[::-1])
    print('   error blobs', n-1, 'largest', a[-5:].tolist(), 'blobs >= 2000 px hold', round(float(a[a>=2000].sum()/tot),3), 'of error px; >= 20000 px hold', round(float(a[a>=20000].sum()/tot),3))
    # errors by type
    print('   street called block', round(float((err & ~gt).sum()/tot),3), 'block called street', round(float((err & gt).sum()/tot),3))
