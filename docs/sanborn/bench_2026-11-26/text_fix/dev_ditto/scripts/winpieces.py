"""A drawn window with every small ink piece (px in [--min, --max], box side <= 14) boxed and numbered, scan only.
python -B winpieces.py PLATE RANK [--scale 3] [--min 3] [--max 60]  -> pics/search/wp_PLATE_RANK.png and .txt (dev_ditto)"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from zoom import zoom, DD
from common import window
a = sys.argv; p = a[1]; r = int(a[2])
sc = float(a[a.index('--scale') + 1]) if '--scale' in a else 3
mn = int(a[a.index('--min') + 1]) if '--min' in a else 3; mx = int(a[a.index('--max') + 1]) if '--max' in a else 60
x0, y0, x1, y1 = json.load(open(os.path.join(DD, 'choose', 'windows.json')))[p]['windows'][r - 1]['win']
G = zoom(p, x0, y0, x1, y1, sc, 20, False)
_, _, ink, (wx0, wy0, _, _) = window(p, x0, y0, x1, y1)
n, lb, st, cen = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
out = []
for k in range(1, n):
    bx, by, bw, bh, A = st[k]
    if not (mn <= A <= mx) or max(bw, bh) > 14: continue
    j = len(out); out.append(f'{j} {bx + wx0},{by + wy0}-{bx + bw - 1 + wx0},{by + bh - 1 + wy0} px {A}')
    P = 34; cv2.rectangle(G, (P + int(bx * sc) - 1, P + int(by * sc) - 1), (P + int((bx + bw) * sc), P + int((by + bh) * sc)), (230, 190, 0), 1)
    cv2.putText(G, str(j), (P + int((bx + bw) * sc) + 1, P + int(by * sc) + 7), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 90, 0), 1)
f = os.path.join(DD, 'pics', 'search', f'wp_{p}_{r:02d}'); cv2.imwrite(f + '.png', G); open(f + '.txt', 'w').write('\n'.join(out) + '\n'); print(f + '.png', len(out), 'pieces')
