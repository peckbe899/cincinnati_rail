"""Zoom picture: scan beside one or more code masks, for a plate window (finder2, 25 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/finder2/scripts/zoom.py N X0 Y0 X1 Y1 OUT.png [--s 2] MASK [MASK ...]

Codes: 1 line grey, 2 text magenta, 3 text by context blue, 4 shared yellow (v1: lone stroke), 5 other green."""
import sys, os
sys.dont_write_bytecode = True
import numpy as np, cv2
COL = {1: (150, 150, 150), 2: (220, 0, 220), 3: (255, 120, 0), 4: (0, 200, 230), 5: (0, 160, 0)}

a = sys.argv[1:]; s = 2.0
if '--s' in a: i = a.index('--s'); s = float(a[i + 1]); a = a[:i] + a[i + 2:]
N, x0, y0, x1, y1, out = a[0], int(a[1]), int(a[2]), int(a[3]), int(a[4]), a[5]; masks = a[6:]
im = cv2.imread(f'cufp/22-{N}.jpg')[y0:y1, x0:x1]
panels = [im]
for m in masks:
    c = cv2.imread(m, 0); c = c[y0:y1, x0:x1] if c.shape[0] > (y1 - y0) else c
    o = (im * 0.3 + 255 * 0.7).astype(np.uint8)
    for v, col in COL.items(): o[c == v] = col
    panels.append(o)
p = np.concatenate([np.pad(q, ((0, 0), (0, 4), (0, 0)), constant_values=0) for q in panels], 1)
p = cv2.resize(p, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST if s >= 1 else cv2.INTER_AREA)
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True); cv2.imwrite(out, p)
