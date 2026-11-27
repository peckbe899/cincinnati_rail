"""Pointer for the ditto search (sealed builder A, 26 Nov 2026): small ink pieces that come in pairs, like the two
ticks of a ditto mark. Scan and paper mask only. Used only to point the eye at spots the 2x look may have missed;
every ditto is decided by eye on 5-6x zooms.
    python -B .../tick_pairs.py PLATE x0 y0 x1 y1      prints candidate centres
A piece: 8-connected ink (L < 140 on the paper), 5-90 px, at most 16 px across, not touching any piece over 400 px.
A pair: two such pieces whose centres are 3-14 px apart."""
import sys, os
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import window
N = sys.argv[1]; x0, y0, x1, y1 = [int(v) for v in sys.argv[2:6]]
_, _, ink, (wx0, wy0, _, _) = window(N, x0, y0, x1, y1)
n, lb, st, ce = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
small = [i for i in range(1, n) if 5 <= st[i, 4] <= 90 and max(st[i, 2], st[i, 3]) <= 16]
big = np.isin(lb, [i for i in range(1, n) if st[i, 4] > 400])
bigd = cv2.dilate(big.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
small = [i for i in small if not bigd[lb == i].any()]
C = np.array([ce[i] for i in small]) if small else np.zeros((0, 2))
out = []; used = set()
for a in range(len(small)):
    for b in range(a + 1, len(small)):
        d = np.hypot(*(C[a] - C[b]))
        if 3 <= d <= 14:
            c = (C[a] + C[b]) / 2 + [wx0, wy0]; out.append((int(c[0]), int(c[1])))
seen = []
for c in out:
    if all(abs(c[0] - s[0]) > 8 or abs(c[1] - s[1]) > 8 for s in seen): seen.append(c)
print(N, len(seen), ' '.join(f'{x},{y}' for x, y in seen))
