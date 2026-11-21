"""Where do verified edges (N_edge.png, half size) sit relative to the area label? And half/full alignment check."""
import json, os, sys
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
OUT = os.path.dirname(os.path.abspath(__file__)) + '/'
for N in sys.argv[1:]:
    lab = cv2.imread(U + f'{N}_label.png', 0); h, w = lab.shape; e = cv2.imread(U + f'{N}_edge.png', 0) > 0
    alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
    k = np.ones((7, 7), np.uint8)
    n0 = cv2.dilate((lab == 0).astype(np.uint8), k) > 0; n1 = cv2.dilate((lab == 1).astype(np.uint8), k) > 0
    nedge = cv2.dilate((~alpha).astype(np.uint8), np.ones((21, 21), np.uint8)) > 0
    only0 = e & n0 & ~n1; only1 = e & n1 & ~n0
    print(N, 'edge px', int(e.sum()), 'only street near', int(only0.sum()), 'of which near paper edge (10 half px)', int((only0 & nedge).sum()), 'only block near', int(only1.sum()), 'of which near paper edge', int((only1 & nedge).sum()))
    # alignment: mean grey of the half-size image at edge px shifted by (dx, dy)
    img = cv2.imread(U + f'{N}_img.jpg', 0).astype(np.float32); ys, xs = np.nonzero(e & alpha)
    sel = (ys > 3) & (ys < h - 4) & (xs > 3) & (xs < w - 4); ys, xs = ys[sel], xs[sel]
    g = {(dx, dy): round(float(img[ys + dy, xs + dx].mean()), 1) for dx in range(-2, 3) for dy in range(-2, 3)}
    best = min(g, key=g.get); print('  half-size grey at edge px, shift (dx,dy)->mean; darkest at', best, 'value', g[best], 'at (0,0)', g[(0, 0)])
    if N == sys.argv[1]:
        im = cv2.imread(U + f'{N}_img.jpg'); vis = (im * 0.5 + 110).astype(np.uint8)
        vis[lab == 0] = (vis[lab == 0] * 0.6 + np.array([200, 120, 0]) * 0.4).astype(np.uint8)
        vis[(lab == 255) & alpha] = (vis[(lab == 255) & alpha] * 0.6 + 40).astype(np.uint8)
        d = lambda m: cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        vis[d(e)] = (0, 160, 0); vis[d(only0)] = (0, 0, 255); vis[d(only1)] = (255, 0, 255)
        cv2.imwrite(OUT + f'edgeside{N}.jpg', cv2.resize(vis, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
