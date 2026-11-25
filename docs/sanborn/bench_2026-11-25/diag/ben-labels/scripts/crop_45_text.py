"""Picture: plate 45's text bin (unet_data/45_bins.png, made without block lines) against its line-net positives
(train_v2/45/lines.png). Text blue, positives green, positives touching text red.  python -B .../crop_45_text.py"""
import sys, os
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa
full = scan('45'); bins = cv2.imread(SP + 'unet_data/45_bins.png', 0); t = cv2.imread(SP + 'train_v2/45/lines.png', 0)
tdil = cv2.dilate((bins == 8).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
v = full.copy(); v[bins == 8] = (255, 120, 0); v[(t == 1) & ~tdil] = (0, 170, 0); v[(t == 1) & tdil] = (0, 0, 255)
ys, xs = np.nonzero((t == 1) & tdil); i = len(ys) // 3; cy, cx = ys[i], xs[i]
cv2.imwrite(os.path.join(DIAG, 'text_vs_pos_45.jpg'), v[max(0, cy - 450):cy + 450, max(0, cx - 700):cx + 700], [cv2.IMWRITE_JPEG_QUALITY, 88])
print(cy, cx)
