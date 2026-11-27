"""Scan | finder3 codes | truth (| optional new codes) for dev crops, zoomed.
    python -B .../scripts/view_crop.py OUT.png ZOOM DB16 DB10 ... [--new DIR]
codes colours: 1 grey, 2 magenta, 3 orange-blue, 4 yellow, 5 green. truth: 1 blue, 2 red, 3 orange, 0 white."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np, cv2
import bfcommon as C

a = sys.argv[1:]; new = None
if '--new' in a: i = a.index('--new'); new = a[i + 1]; a = a[:i] + a[i + 2:]
out, z, ids = a[0], int(a[1]), a[2:]
crops = C.dev_crops(); CC = {0: (255, 255, 255), 1: (150, 150, 150), 2: (220, 0, 220), 3: (255, 120, 0), 4: (0, 200, 230), 5: (0, 160, 0)}
TC = {0: (255, 255, 255), 1: (200, 80, 0), 2: (0, 0, 230), 3: (0, 160, 255)}
rows = []; cache = {}
def colorize(m, pal):
    o = np.zeros(m.shape + (3,), np.uint8)
    for v, c in pal.items(): o[m == v] = c
    return o
for tid in ids:
    c = crops[tid]; N = c['plate']; x0, y0, x1, y1 = c['win']
    if N not in cache: cache.clear(); cache[N] = (cv2.imread(f'cufp/22-{N}.jpg'), cv2.imread(C.f3_path(N), 0), cv2.imread(os.path.join(new, f'{N}_text.png'), 0) if new else None)
    im, f3, nw = cache[N]
    T = cv2.imread(os.path.join(C.DEVB, 'truth', f'{tid}_mask.png'), 0)
    p = [im[y0:y1, x0:x1], colorize(f3[y0:y1, x0:x1], CC), colorize(T, TC)]
    if nw is not None: p.append(colorize(nw[y0:y1, x0:x1], CC))
    r = np.concatenate([cv2.copyMakeBorder(q, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(0, 0, 0)) for q in p], 1)
    r = cv2.resize(r, None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
    cv2.putText(r, f'{tid} {N} {c.get("readings")}', (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    rows.append(r)
Wm = max(r.shape[1] for r in rows)
S = np.concatenate([cv2.copyMakeBorder(r, 0, 4, 0, Wm - r.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r in rows], 0)
cv2.imwrite(out, S); print(S.shape)
