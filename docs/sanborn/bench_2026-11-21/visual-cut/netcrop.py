"""What the two networks said in a window (visual-cut, 21 Nov 2026): to tell which step lost an alley or a side.
Reads only; writes views/net_N_X0_Y0.jpg.

    python netcrop.py N X0 Y0 W H [SCALE]

Three panels side by side (or stacked if the window is wide): the scan with the editor lines; the area network's
P(block) (N_pred_area_ng1.png, half size, upsampled: white = block, black = street) with the street seed the outline
step uses in red (P <= 0.5 eroded by SEED_S = 8 px, outlines.py:38) and the block seed in green (P > 0.5 eroded by
SEED_B = 14 px, outlines.py:39); the line network's P(line) (N_lines_lines_ng1.png, full size) with the outline
step's block mask boundary in blue.
"""
import os, sys
import numpy as np, cv2
from vlib import load, draw, HERE
n = sys.argv[1]; x0, y0, w, h = map(int, sys.argv[2:6]); D = load(n); W, H = D['W'], D['H']
s = float(sys.argv[6]) if len(sys.argv) > 6 else min(1.0, 900 / max(w, h))
x1, y1 = min(W, x0 + w), min(H, y0 + h)
a = draw(D, x0, y0, w, h, s, labels=True)
pa = cv2.resize(D['pa'], (W, H), interpolation=cv2.INTER_LINEAR)[y0:y1, x0:x1]; al = D['alpha'][y0:y1, x0:x1]
el = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
# seeds must be computed with context: pad the window by 40 px
X0, Y0, X1, Y1 = max(0, x0 - 40), max(0, y0 - 40), min(W, x1 + 40), min(H, y1 + 40)
PA = cv2.resize(D['pa'], (W, H), interpolation=cv2.INTER_LINEAR)[Y0:Y1, X0:X1]; AL = D['alpha'][Y0:Y1, X0:X1]
ss = cv2.erode(((PA <= 127) & AL).astype(np.uint8), el(8))[y0 - Y0:y0 - Y0 + (y1 - y0), x0 - X0:x0 - X0 + (x1 - x0)] > 0
bs = cv2.erode(((PA > 127) & AL).astype(np.uint8), el(14))[y0 - Y0:y0 - Y0 + (y1 - y0), x0 - X0:x0 - X0 + (x1 - x0)] > 0
b = np.dstack([pa, pa, pa]).astype(np.float32)
b[ss] = b[ss] * 0.4 + np.array([0, 0, 255]) * 0.6; b[bs] = b[bs] * 0.6 + np.array([0, 200, 0]) * 0.4
b = cv2.resize(b.clip(0, 255).astype(np.uint8), (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA)
pl = D['pl'][y0:y1, x0:x1]; c = cv2.cvtColor(255 - pl, cv2.COLOR_GRAY2BGR)
bm = (cv2.resize(D['bm'], (W, H), interpolation=cv2.INTER_NEAREST)[y0:y1, x0:x1] > 127).astype(np.uint8)
edge = cv2.morphologyEx(bm, cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8)) > 0; c[edge] = (255, 120, 0)
c = cv2.resize(c, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA)
for im, t in ((a, 'scan + editor lines'), (b, 'area net P(block); red street seed, green block seed'), (c, 'line net P(line) dark; blue = block mask edge')):
    cv2.putText(im, t, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4); cv2.putText(im, t, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
out = np.vstack([a, b, c]) if a.shape[1] > 1.3 * a.shape[0] else np.hstack([a, b, c])
f = os.path.join(HERE, 'views', f'net_{n}_{x0}_{y0}.jpg'); cv2.imwrite(f, out, [cv2.IMWRITE_JPEG_QUALITY, 85]); print(f, out.shape)
