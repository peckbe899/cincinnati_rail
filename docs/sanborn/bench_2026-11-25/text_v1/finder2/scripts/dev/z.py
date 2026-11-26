"""dev zoom (finder2): scan | mask codes | truth-error view, for a plate window.
    cd data/sanborn; python -B <this> N X0 Y0 X1 Y1 OUT.png [--s 2] MASK [MASK ...]
MASK is a plate-sized PNG, or Tn:PATH for a crop-sized PNG of truth crop Tn (its window from truth/crops.json).
Panels per mask: codes (1 grey, 2 magenta, 3 blue, 4 yellow, 5 green); and, when the window lies in a truth crop, an error
panel (text found magenta, missed red, false text green, don't care pale yellow)."""
import sys, os, json
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); TRUTH = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'truth'))
COL = {1: (150, 150, 150), 2: (220, 0, 220), 3: (255, 120, 0), 4: (0, 200, 230), 5: (0, 160, 0)}
crops = json.load(open(os.path.join(TRUTH, 'crops.json')))
a = sys.argv[1:]; s = 2.0
if '--s' in a: i = a.index('--s'); s = float(a[i + 1]); a = a[:i] + a[i + 2:]
N, x0, y0, x1, y1, out = a[0], int(a[1]), int(a[2]), int(a[3]), int(a[4]), a[5]
im = cv2.imread(f'cufp/22-{N}.jpg')[y0:y1, x0:x1]; panels = [im]
tr = None
for tid, c in crops.items():
    X0, Y0, X1, Y1 = c['win']
    if c['plate'] == N and x0 >= X0 and y0 >= Y0 and x1 <= X1 and y1 <= Y1:
        tr = cv2.imread(os.path.join(TRUTH, f'{tid}_mask.png'), 0)[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0]
for m in a[6:]:
    if ':' in m and m.split(':')[0] in crops:
        tid, path = m.split(':', 1); X0, Y0 = crops[tid]['win'][:2]; c = cv2.imread(path, 0)[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0]
    else: c = cv2.imread(m, 0)[y0:y1, x0:x1]
    o = (im * 0.3 + 255 * 0.7).astype(np.uint8)
    for v, col in COL.items(): o[c == v] = col
    panels.append(o)
    if tr is not None:
        t = np.isin(c, (2, 3)); e = (im * 0.3 + 255 * 0.7).astype(np.uint8)
        e[tr == 1] = (170, 170, 170); e[tr == 3] = (160, 235, 235); e[(tr == 2) & t] = (220, 0, 220); e[(tr == 2) & ~t] = (0, 0, 255); e[(tr == 1) & t] = (0, 170, 0)
        panels.append(e)
p = np.concatenate([np.pad(q, ((0, 0), (0, 4), (0, 0)), constant_values=0) for q in panels], 1)
p = cv2.resize(p, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST if s >= 1 else cv2.INTER_AREA)
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True); cv2.imwrite(out, p)
