"""Close zoom of a built crop: scan beside truth colours (text red, don't care yellow, other ink grey, outside the
scope tinted blue), full-plate px ticks every 10 px. python -B cz.py OUT.png "CROP|X0|Y0|X1|Y1|ZOOM" ..."""
import os, sys, json
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import INV, window
from build import colour

crops = json.load(open(os.path.join(INV, 'truth', 'crops.json'), encoding='utf8'))
panels = []
for s in sys.argv[2:]:
    f = s.split('|'); cid = f[0]; x0, y0, x1, y1 = map(int, f[1:5]); z = int(f[5])
    c = crops[cid]; X0, Y0, X1, Y1 = c['win']; M = cv2.imread(os.path.join(INV, 'truth', f'{cid}_mask.png'), 0)
    x0, y0, x1, y1 = max(x0, X0), max(y0, Y0), min(x1, X1), min(y1, Y1)
    im = window(c['plate'], x0, y0, x1, y1)[0]; m = M[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0]
    col = colour(im, m)
    if c.get('scope'):
        S = np.zeros(M.shape, bool)
        for r in c['scope']: S[max(0, r[1] - Y0):max(0, r[3] - Y0), max(0, r[0] - X0):max(0, r[2] - X0)] = True
        S = S[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0]; col[~S] = (col[~S] * 0.5 + np.array([255, 200, 160]) * 0.5).astype(np.uint8)
    A = cv2.resize(im, None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST); Bc = cv2.resize(col, None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
    for g in range((x0 // 10 + 1) * 10, x1, 10):
        X = (g - x0) * z; A[:, X] = (A[:, X] * 0.6 + np.array([255, 150, 0]) * 0.4).astype(np.uint8); Bc[:, X] = (Bc[:, X] * 0.7 + np.array([255, 150, 0]) * 0.3).astype(np.uint8)
    for g in range((y0 // 10 + 1) * 10, y1, 10):
        Y = (g - y0) * z; A[Y] = (A[Y] * 0.6 + np.array([255, 150, 0]) * 0.4).astype(np.uint8); Bc[Y] = (Bc[Y] * 0.7 + np.array([255, 150, 0]) * 0.3).astype(np.uint8)
    t = np.full((A.shape[0] + 18, 2 * A.shape[1] + 8, 3), 255, np.uint8); t[18:, :A.shape[1]] = A; t[18:, A.shape[1] + 8:] = Bc
    cv2.putText(t, f'{cid} [{x0},{y0},{x1},{y1}] x{z} (grid 10 px)', (2, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 160), 1)
    panels.append(t)
W = max(p.shape[1] for p in panels)
cv2.imwrite(sys.argv[1], np.vstack([cv2.copyMakeBorder(p, 0, 6, 0, W - p.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for p in panels]))
