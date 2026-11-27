"""Labelling aid: list the ink pieces near a point (ink less straight runs of L px, the builder's own peel), with their
boxes, so typed word coordinates can be checked against the scan. Scan only.
python -B comps.py PLATE CX CY [R=110] [L=75] [MINH=20]"""
import os, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import window, line_mask

p = sys.argv[1]; cx, cy = int(sys.argv[2]), int(sys.argv[3])
R = int(sys.argv[4]) if len(sys.argv) > 4 else 110; L = int(sys.argv[5]) if len(sys.argv) > 5 else 75; MH = int(sys.argv[6]) if len(sys.argv) > 6 else 20
_, _, ink, (x0, y0, _, _) = window(p, cx - R - L, cy - R - L, cx + R + L, cy + R + L)
ln = line_mask(ink, L | 1, nang=72)
cand = ink & ~(cv2.dilate(ln.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
n, lb, st, cen = cv2.connectedComponentsWithStats(cand.astype(np.uint8), connectivity=8)
rows = []
for i in range(1, n):
    x, y, w, h, a = st[i]
    if max(w, h) < MH or a < 15: continue
    gx, gy = x + x0, y + y0
    if abs(gx + w / 2 - cx) > R or abs(gy + h / 2 - cy) > R: continue
    rows.append((gy, gx, w, h, a))
for gy, gx, w, h, a in sorted(rows):
    print(f'  box x {gx}-{gx + w - 1}  y {gy}-{gy + h - 1}  ({w}x{h}, {a} px)')
