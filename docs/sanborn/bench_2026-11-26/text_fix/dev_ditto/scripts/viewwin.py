"""Render drawn windows (choose/windows.json) for the ditto search, scan only (dev_ditto, 26 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/dev_ditto/scripts/viewwin.py PLATE RANK [RANK ...] [--scale 2.5] [--pad 0]

Writes pics/search/w_<PLATE>_<RANK>.png: the window at --scale with a 20 px grid (labelled every 100 px, minor lines
numbered mod 100), a thin red frame at the window edge when --pad > 0."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from zoom import zoom, DD

a = sys.argv; p = a[1]; ranks = [int(v) for v in a[2:] if not v.startswith('--') and v.isdigit()]
sc = float(a[a.index('--scale') + 1]) if '--scale' in a else 2.5
pad = int(a[a.index('--pad') + 1]) if '--pad' in a else 0
W = json.load(open(os.path.join(DD, 'choose', 'windows.json')))[p]['windows']
out = os.path.join(DD, 'pics', 'search'); os.makedirs(out, exist_ok=True)
for r in ranks:
    x0, y0, x1, y1 = W[r - 1]['win']
    G = zoom(p, x0 - pad, y0 - pad, x1 + pad, y1 + pad, sc, 20, False)
    if '--small' in a:   # a looking aid: a thin cyan ring round EVERY small separate ink piece (4-80 px), whatever its shape
        from common import window
        _, _, ink, (wx0, wy0, _, _) = window(p, x0 - pad, y0 - pad, x1 + pad, y1 + pad)
        n, lb, st, cen = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
        for i in range(1, n):
            if 4 <= st[i, 4] <= 80 and max(st[i, 2], st[i, 3]) <= 16:
                cx, cy = cen[i]; cv2.circle(G, (34 + int(cx * sc), 34 + int(cy * sc)), int(7 * sc), (230, 200, 0), 1)
    if pad:
        P = 34; X0 = P + int(pad * sc); Y0 = P + int(pad * sc); cv2.rectangle(G, (X0, Y0), (X0 + int(400 * sc), Y0 + int(300 * sc)), (0, 0, 255), 1)
    cv2.putText(G, f'{p} #{r}', (G.shape[1] - 90, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 120, 0), 1)
    f = os.path.join(out, f'w_{p}_{r:02d}.png'); cv2.imwrite(f, G); print(f, W[r - 1]['win'], G.shape)
