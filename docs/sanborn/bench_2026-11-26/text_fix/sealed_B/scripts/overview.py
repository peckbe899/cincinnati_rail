"""Quarter-size overview of a sealed plate (scan only, paper outside the sheet greyed), split into 2x2 tiles with a
full-plate px grid every 500 px. python -B overview.py PLATE [--scale 0.25] -> sealed_B/pics/ov_PLATE_RC.jpg"""
import os, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import plate_img, paper, INV

p = sys.argv[1]; sc = float(sys.argv[sys.argv.index('--scale') + 1]) if '--scale' in sys.argv else 0.25
im = plate_img(p); H, W = im.shape[:2]
s = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
pp = cv2.resize(paper(p).astype(np.uint8), (s.shape[1], s.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
s[~pp] = (s[~pp] * 0.4 + 120).astype(np.uint8)
for gx in range(500, W, 500):
    X = int(gx * sc); s[:, X] = (s[:, X] * 0.6 + np.array([0, 0, 200]) * 0.4).astype(np.uint8)
for gy in range(500, H, 500):
    Y = int(gy * sc); s[Y, :] = (s[Y, :] * 0.6 + np.array([0, 0, 200]) * 0.4).astype(np.uint8)
h2, w2 = s.shape[0] // 2, s.shape[1] // 2
for r in range(2):
    for c in range(2):
        t = s[r * h2:(r + 1) * h2 + 20, c * w2:(c + 1) * w2 + 20].copy()
        for gx in range(500, W, 500):
            X = int(gx * sc) - c * w2
            if 0 <= X < t.shape[1]: cv2.putText(t, str(gx), (X + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 200), 1)
        for gy in range(500, H, 500):
            Y = int(gy * sc) - r * h2
            if 0 <= Y < t.shape[0]: cv2.putText(t, str(gy), (2, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 200), 1)
        cv2.imwrite(os.path.join(INV, 'pics', f'ov_{p}_{r}{c}.jpg'), t, [cv2.IMWRITE_JPEG_QUALITY, 90])
print(p, W, H, s.shape)
