"""Labelling aid for ditto marks: for each rough point (typed by eye from the 2x window views), list the small ink
pieces (8-connected ink, all ink, no line peel) within R px and their union box, so the ditto box can be typed.
Scan only. python -B ditto_pieces.py PLATE R "x,y" "x,y" ...   (prints one line per point)"""
import os, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import window

p = sys.argv[1]; R = int(sys.argv[2])
for s in sys.argv[3:]:
    x, y = map(int, s.split(','))
    _, _, ink, (x0, y0, _, _) = window(p, x - R - 30, y - R - 30, x + R + 30, y + R + 30)
    n, lb, st, cen = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
    near = []
    for i in range(1, n):
        bx, by, w, h, a = st[i]
        gx0, gy0, gx1, gy1 = bx + x0, by + y0, bx + x0 + w - 1, by + y0 + h - 1
        dx = max(gx0 - x, 0, x - gx1); dy = max(gy0 - y, 0, y - gy1)
        if max(dx, dy) <= R: near.append((gx0, gy0, gx1, gy1, int(a), max(w, h)))
    small = [q for q in near if q[5] <= 16]
    big = [q for q in near if q[5] > 16]
    if small:
        u = (min(q[0] for q in small), min(q[1] for q in small), max(q[2] for q in small), max(q[3] for q in small))
        print(f'{s}: small {len(small)} union x {u[0]}-{u[2]} y {u[1]}-{u[3]} ink {sum(q[4] for q in small)} | pieces ' + ' '.join(f'[{q[0]},{q[1]},{q[2]},{q[3]}:{q[4]}]' for q in small) + (f' | big {len(big)}' if big else ''))
    else:
        print(f'{s}: no small piece; big ' + ' '.join(f'[{q[0]},{q[1]},{q[2]},{q[3]}:{q[4]}]' for q in big))
