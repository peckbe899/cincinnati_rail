"""Integrator: render a region of a plate folder's area label over the scan with a full-px grid, to place a hand mask.
    python -B region.py PLATE_DIR X0 Y0 X1 Y1 OUT.jpg [STEP]      (full-size px)"""
import sys, json, os
import numpy as np, cv2
d, x0, y0, x1, y1, out = sys.argv[1], *map(int, sys.argv[2:6]), sys.argv[6]; step = int(sys.argv[7]) if len(sys.argv) > 7 else 200
img = cv2.imread(os.path.join(d, 'img.jpg')); lab = cv2.imread(os.path.join(d, 'label.png'), 0)
a, b, c, e = y0 // 2, y1 // 2, x0 // 2, x1 // 2
I = img[a:b, c:e].astype(np.float32); L = lab[a:b, c:e]
for v, col in ((1, (60, 200, 60)), (0, (230, 120, 30))):
    m = L == v; I[m] = 0.55 * I[m] + 0.45 * np.array(col, np.float32)
I = I.clip(0, 255).astype(np.uint8)
for X in range((x0 // step + 1) * step, x1, step):
    cv2.line(I, ((X - x0) // 2, 0), ((X - x0) // 2, I.shape[0]), (0, 0, 255), 1); cv2.putText(I, str(X), ((X - x0) // 2 + 2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
for Y in range((y0 // step + 1) * step, y1, step):
    cv2.line(I, (0, (Y - y0) // 2), (I.shape[1], (Y - y0) // 2), (0, 0, 255), 1); cv2.putText(I, str(Y), (2, (Y - y0) // 2 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
cv2.imwrite(out, I, [cv2.IMWRITE_JPEG_QUALITY, 88])
