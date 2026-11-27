"""List the ink pieces of a region with their truth labels (sealed cross-check helper; scan and truth only).
    python -B comps.py CROP x0 y0 x1 y1 [minpx]
Prints each 8-connected ink piece inside the region: box, area, and how many of its pixels the truth calls 0/1/2/3."""
import os, sys, json
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import FINAL, window
tid = sys.argv[1]; x0, y0, x1, y1 = [int(v) for v in sys.argv[2:6]]; mn = int(sys.argv[6]) if len(sys.argv) > 6 else 3
c = json.load(open(os.path.join(FINAL, 'crops.json'), encoding='utf8'))[tid]; X0, Y0, X1, Y1 = c['win']
M = cv2.imread(os.path.join(FINAL, f'{tid}_mask.png'), 0)
_, _, ink, (wx0, wy0, _, _) = window(c['plate'], x0, y0, x1, y1)
T = np.full(ink.shape, 9, np.uint8)
ax0, ay0, ax1, ay1 = max(wx0, X0), max(wy0, Y0), min(x1, X1), min(y1, Y1)
T[ay0 - wy0:ay1 - wy0, ax0 - wx0:ax1 - wx0] = M[ay0 - Y0:ay1 - Y0, ax0 - X0:ax1 - X0]
n, lb, st, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
for i in sorted(range(1, n), key=lambda i: (st[i][0], st[i][1])):
    x, y, w, h, a = st[i]
    if a < mn: continue
    L = T[lb == i]
    print(f'[{x + wx0},{y + wy0},{x + w + wx0},{y + h + wy0}] px {a}  labels ' + ' '.join(f'{v}:{int((L == v).sum())}' for v in (0, 1, 2, 3, 9) if (L == v).any()))
