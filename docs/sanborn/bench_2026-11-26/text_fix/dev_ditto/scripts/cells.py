"""Contact sheet of scan-only zooms round given points, for deciding ditto or not (dev_ditto, 26 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/dev_ditto/scripts/cells.py NAME PLATE:x:y[:half] [PLATE:x:y ...] [--scale 6] [--cols 4] [--half 30]

Each cell is the scan round (x, y) +- half px at --scale, with a 10 px grid (full-plate px, every 50 labelled) and the
cell number. Writes pics/cells_<NAME>.png. Scan only: never a finder output or bins."""
import os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from zoom import zoom, DD

a = sys.argv; name = a[1]
sc = float(a[a.index('--scale') + 1]) if '--scale' in a else 6
cols = int(a[a.index('--cols') + 1]) if '--cols' in a else 4
hd = int(a[a.index('--half') + 1]) if '--half' in a else 30
pts = [q for q in a[2:] if q.count(':') >= 2 and not q.startswith('--')]
cells = []
for i, q in enumerate(pts):
    f = q.split(':'); p = f[0]; x, y = int(float(f[1])), int(float(f[2])); h = int(f[3]) if len(f) > 3 else hd
    G = zoom(p, x - h, y - h, x + h, y + h, sc, 10, False)
    C = np.full((G.shape[0] + 16, G.shape[1], 3), 255, np.uint8); C[16:] = G
    cv2.putText(C, f'#{i} {p} {x},{y}', (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
    cells.append(C)
CW = max(c.shape[1] for c in cells); CH = max(c.shape[0] for c in cells); rows = (len(cells) + cols - 1) // cols
S = np.full((rows * (CH + 4), min(cols, len(cells)) * (CW + 4), 3), 180, np.uint8)
for i, C in enumerate(cells):
    r, c = divmod(i, cols); S[r * (CH + 4):r * (CH + 4) + C.shape[0], c * (CW + 4):c * (CW + 4) + C.shape[1]] = C
f = os.path.join(DD, 'pics', f'cells_{name}.png'); cv2.imwrite(f, S); print(f, S.shape)
