"""Several zooms of one truth crop on one sheet (scan left, truth right, 10 px grid), for checking by eye.

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/truth-fix/scripts/multizoom.py T1 NAME x0,y0,x1,y1 [x0,y0,x1,y1 ...] [--scale 4] [--cols 3]
Writes pics/mz_T#_NAME.png. Cells are numbered from 0 in the order given."""
import os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import look

tid, name = sys.argv[1], sys.argv[2]; sc = float(look.opt('--scale', d='4')); cols = int(look.opt('--cols', d='3'))
boxes = [[int(v) for v in a.split(',')] for a in sys.argv[3:] if a.count(',') == 3]
if '--fine' not in sys.argv: sys.argv += ['--fine', '10']
cells = []
for i, (x0, y0, x1, y1) in enumerate(boxes):
    k = min(sc, 245 / max(1, x1 - x0), 300 / max(1, y1 - y0))
    P = look.panel(tid, x0, y0, x1, y1, k, True)
    C = np.full((P.shape[0] + 14, P.shape[1], 3), 255, np.uint8); C[14:] = P
    cv2.putText(C, f'#{i} {x0},{y0}-{x1},{y1} x{k:.1f}', (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1)
    cells.append(C)
CW = max(c.shape[1] for c in cells); CH = max(c.shape[0] for c in cells)
rows = (len(cells) + cols - 1) // cols
G = np.full((rows * (CH + 4), cols * (CW + 4), 3), 200, np.uint8)
for i, C in enumerate(cells):
    r, c = divmod(i, cols); G[r * (CH + 4):r * (CH + 4) + C.shape[0], c * (CW + 4):c * (CW + 4) + C.shape[1]] = C
f = os.path.join(look.PICS, f'mz_{tid}_{name}.png'); cv2.imwrite(f, G); print(f, G.shape)
