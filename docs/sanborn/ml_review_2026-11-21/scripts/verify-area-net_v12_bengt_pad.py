import numpy as np, cv2
exec(open('v3_bengt.py').read().split("m = lab != 255; gt = lab == 1")[0])
for name, Q in (('stored', cv2.imread(U+'44_pred_area_ng1.png',0) > 127), ('pad192', np.load('44_ng1_pad192.npy') > 0.5)):
    bnd = (cv2.morphologyEx(Q.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3,3),np.uint8)) > 0) & alpha
    db = cv2.distanceTransform((~bnd).astype(np.uint8), cv2.DIST_L2, 5); dd = db[yi,xi]
    print(name, [round(float((dd<=t).mean()),3) for t in (1.5,3,6)], 'interior block', round(float(Q[Bin].mean()),4), 'spurious', int((bnd & Bin & (dl>10)).sum()))
