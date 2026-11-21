import sys, numpy as np, cv2
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = D + 'unet_data/'; OUT = sys.argv[1]
for n in sys.argv[2:]:
    full = cv2.imread(D + f'cufp/22-{n}.jpg'); H, W = full.shape[:2]; s = 1400 / max(H, W)
    sm = cv2.resize(full, (int(W * s), int(H * s)), interpolation=cv2.INTER_AREA)
    p = cv2.resize(cv2.imread(U + f'{n}_pred_area_ng1.png', 0), (sm.shape[1], sm.shape[0]))
    ov = sm.copy(); ov[p > 127] = (0.55 * ov[p > 127] + 0.45 * np.array([60, 60, 255])).astype(np.uint8)
    cv2.imwrite(OUT + f'/thumb_{n}.jpg', np.hstack([sm, ov]) if W >= H else np.hstack([sm, ov]), [cv2.IMWRITE_JPEG_QUALITY, 80])
