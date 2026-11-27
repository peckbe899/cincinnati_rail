"""List ink pieces (8-connected, L < 140 on the paper) meeting a rectangle: box (full-plate px, inclusive) and px.
python -B pieces.py PLATE x0 y0 x1 y1 [--min 2] [--max 100000]   (dev_ditto, 26 Nov 2026; scan only)"""
import sys, os
sys.dont_write_bytecode = True
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import window
a = sys.argv; p = a[1]; x0, y0, x1, y1 = [int(v) for v in a[2:6]]
mn = int(a[a.index('--min') + 1]) if '--min' in a else 2; mx = int(a[a.index('--max') + 1]) if '--max' in a else 100000
_, _, ink, (wx0, wy0, _, _) = window(p, x0 - 150, y0 - 150, x1 + 150, y1 + 150)
n, lb, st, cen = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
sub = lb[y0 - wy0:y1 - wy0 + 1, x0 - wx0:x1 - wx0 + 1]
for k in sorted(set(np.unique(sub)) - {0}, key=lambda k: (st[k, 1], st[k, 0])):
    bx, by, bw, bh, A = st[k]
    if mn <= A <= mx: print(f'{bx + wx0},{by + wy0}-{bx + bw - 1 + wx0},{by + bh - 1 + wy0} px {A}{"  BIG" if max(bw, bh) >= 46 else ""}')
