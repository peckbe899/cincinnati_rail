"""Measure each ditto mark's ink box from a rough centre (sealed builder A, 26 Nov 2026). Scan and paper mask only.
For each centre in truth/annot/ditto_list.json: the ink pieces (8-connected, L < 140 on the paper) with at most 150 px and
at most 20 px across whose centre lies within 11 px of the rough centre are the mark; prints their union box, centre,
ink px and the number of pieces. Pieces joined to a line are not found (the mark is then typed by hand)."""
import os, sys, json
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import window
D = json.load(open(os.path.join(HERE, '..', 'truth', 'annot', 'ditto_list.json')))
out = {}
for w, (N, pts) in D.items():
    for k, (x, y) in enumerate(pts):
        _, _, ink, (x0, y0, _, _) = window(N, x - 30, y - 30, x + 31, y + 31)
        n, lb, st, ce = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
        sel = [i for i in range(1, n) if st[i, 4] <= 150 and max(st[i, 2], st[i, 3]) <= 20 and np.hypot(ce[i][0] + x0 - x, ce[i][1] + y0 - y) <= 11]
        if not sel: print(w, k, N, x, y, 'NOTHING'); out[f'{w}-{k}'] = None; continue
        bx0 = min(st[i, 0] for i in sel) + x0; by0 = min(st[i, 1] for i in sel) + y0
        bx1 = max(st[i, 0] + st[i, 2] for i in sel) + x0; by1 = max(st[i, 1] + st[i, 3] for i in sel) + y0
        px = int(sum(st[i, 4] for i in sel))
        out[f'{w}-{k}'] = [int(bx0), int(by0), int(bx1), int(by1), px, len(sel)]
        print(w, k, N, x, y, '->', bx0, by0, bx1, by1, 'c', (bx0 + bx1) // 2, (by0 + by1) // 2, 'px', px, 'pieces', len(sel))
json.dump(out, open(os.path.join(HERE, '..', 'truth', 'annot', 'ditto_boxes_measured.json'), 'w'), indent=0)
