import sys, numpy as np, cv2, json, os
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; OUT = sys.argv[1]
pl = sys.argv[2:]
crops = []
for n in pl:
    full = cv2.imread(D + f'cufp/22-{n}.jpg'); H, W = full.shape[:2]
    c = full[int(0.06 * H):int(0.20 * H), int(0.55 * W):int(0.92 * W)]
    c = cv2.resize(c, None, fx=0.28, fy=0.28, interpolation=cv2.INTER_AREA)
    cv2.putText(c, n, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
    crops.append(c)
w = max(c.shape[1] for c in crops)
crops = [cv2.copyMakeBorder(c, 0, 6, 0, w - c.shape[1], cv2.BORDER_CONSTANT, value=(0, 0, 0)) for c in crops]
for k in range(0, len(crops), 6):
    cv2.imwrite(OUT + f'/scale_{k // 6}.jpg', np.vstack(crops[k:k + 6]), [cv2.IMWRITE_JPEG_QUALITY, 85])
