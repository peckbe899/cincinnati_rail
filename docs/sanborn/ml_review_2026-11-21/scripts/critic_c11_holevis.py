import sys, numpy as np, cv2
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = D + 'unet_data/'; OUT = sys.argv[1]
for n in sys.argv[2:]:
    b = (cv2.imread(U + f'{n}_blockmask.png', 0) > 0).astype(np.uint8); H2, W2 = b.shape
    full = cv2.imread(D + f'cufp/22-{n}.jpg', cv2.IMREAD_REDUCED_COLOR_2); full = cv2.resize(full, (W2, H2))
    v = (full * 0.6 + 100).astype(np.uint8)
    cs, hier = cv2.findContours(b, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    for c, h in zip(cs, hier[0]):
        if h[3] < 0: cv2.drawContours(v, [c], -1, (0, 160, 0), 5)            # exported (outer) boundary: green
        elif cv2.contourArea(c) * 4 >= 6000: cv2.drawContours(v, [c], -1, (0, 0, 255), 5)   # hole: dropped by RETR_EXTERNAL: red
    s = 1600 / W2; cv2.imwrite(OUT + f'/holes_{n}.jpg', cv2.resize(v, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 82])
