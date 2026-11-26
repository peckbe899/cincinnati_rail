"""dev (finder2): A/B picture for a plate window: scan | finder2 with settings A | with settings B (codes coloured: line
grey, text magenta/blue, shared yellow, other green). Settings are 'k=v;k=v' (python literals), '-' for none.
    cd data/sanborn; python -B <this> N X0 Y0 X1 Y1 OUT.png A B [--s 2]"""
import sys, os, ast
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..', '..', 'code')))
import finder2 as F
a = sys.argv[1:]; s = 2.0
if '--s' in a: i = a.index('--s'); s = float(a[i + 1]); a = a[:i] + a[i + 2:]
N, x0, y0, x1, y1, out, A, B = a[0], int(a[1]), int(a[2]), int(a[3]), int(a[4]), a[5], a[6], a[7]
M = 300; base = dict(F.P); im = cv2.imread(f'cufp/22-{N}.jpg')[y0:y1, x0:x1]; panels = [im]
COL = {1: (150, 150, 150), 2: (220, 0, 220), 3: (255, 120, 0), 4: (0, 200, 230), 5: (0, 160, 0)}
for st in (A, B):
    F.P.clear(); F.P.update(base)
    if st != '-':
        for kv in st.split(';'): k, v = kv.split('=', 1); F.P[k.strip()] = ast.literal_eval(v)
    X0, Y0 = max(0, x0 - M), max(0, y0 - M)
    code, rec, _ = F.run(N, (X0, Y0, x1 + M, y1 + M), out=None, verbose=False); c = code[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0]
    o = (im * 0.3 + 255 * 0.7).astype(np.uint8)
    for v, col in COL.items(): o[c == v] = col
    panels.append(o); print(st, 'text px', int(np.isin(c, (2, 3)).sum()), 'line px', int((c == 1).sum()))
p = np.concatenate([np.pad(q, ((0, 0), (0, 4), (0, 0)), constant_values=0) for q in panels], 1)
cv2.imwrite(out, cv2.resize(p, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST if s >= 1 else cv2.INTER_AREA))
