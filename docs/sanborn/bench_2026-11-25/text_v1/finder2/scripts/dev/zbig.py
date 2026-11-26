"""dev (finder2): picture of the big-letter core pieces and why each was refused, for a plate window.
    cd data/sanborn; python -B <this> N X0 Y0 X1 Y1 OUT.png [--s 1] [--set k=v]
Colours: letter magenta; streetcar bar orange; dot cyan; carries a long line red; box blue; lone bar yellow; size dark
green. Long-line ink light grey; other ink dark grey."""
import sys, os, ast
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..', '..', 'code')))
import finder2 as F
a = sys.argv[1:]; s = 1.0
while '--set' in a: i = a.index('--set'); k, v = a[i + 1].split('=', 1); F.P[k] = ast.literal_eval(v); a = a[:i] + a[i + 2:]
if '--s' in a: i = a.index('--s'); s = float(a[i + 1]); a = a[:i] + a[i + 2:]
N, x0, y0, x1, y1, out = a[0], int(a[1]), int(a[2]), int(a[3]), int(a[4]), a[5]
M = 300; F.DEBUG = {}
code, rec, _ = F.run(N, (max(0, x0 - M), max(0, y0 - M), x1 + M, y1 + M), out=None, verbose=False)
ox, oy = x0 - max(0, x0 - M), y0 - max(0, y0 - M); sl = (slice(oy, oy + y1 - y0), slice(ox, ox + x1 - x0))
im = cv2.imread(f'cufp/22-{N}.jpg')[y0:y1, x0:x1]; why = F.DEBUG['big_why'][sl]; LL = F.DEBUG['LL'][sl]; code = code[sl]
o = (im * 0.3 + 255 * 0.7).astype(np.uint8); o[code > 0] = (90, 90, 90); o[LL > 0] = (200, 200, 200)
for v, col in {1: (220, 0, 220), 2: (0, 140, 255), 3: (230, 230, 0), 4: (0, 0, 230), 5: (230, 0, 0), 6: (0, 220, 230), 7: (0, 60, 160), 8: (60, 0, 160), 9: (160, 160, 0), 10: (0, 90, 255), 20: (0, 110, 0)}.items(): o[why == v] = col
p = np.concatenate([im, np.zeros((y1 - y0, 4, 3), np.uint8), o], 1)
p = cv2.resize(p, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST if s >= 1 else cv2.INTER_AREA); cv2.imwrite(out, p); print(rec['big'])
