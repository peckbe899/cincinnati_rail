"""Zoom on chosen changed words of a blockfix run (fix_block_a): scan | finder3 | blockfix (changed px outlined red), 3x.
    cd data/sanborn; python -B .../code/zoomch.py N BASE_DIR NEW_DIR OUT.png I1,I2,... (indices into N_text.json changes)"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from viz import paint, COL
N, bd, nd, outp, ids = sys.argv[1:6]; z = 3
ch = json.load(open(os.path.join(nd, f'{N}_text.json')))['changes']
b = cv2.imread(os.path.join(bd, f'{N}_text.png'), 0); n = cv2.imread(os.path.join(nd, f'{N}_text.png'), 0); im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = b.shape; rows = []
for i in [int(v) for v in ids.split(',')]:
    x0, y0, x1, y1 = ch[i]['fbox']; g = 20; X0, Y0, X1, Y1 = max(0, x0 - g), max(0, y0 - g), min(W, x1 + g), min(H, y1 + g)
    s = im[Y0:Y1, X0:X1]; d = (b[Y0:Y1, X0:X1] != n[Y0:Y1, X0:X1]).astype(np.uint8); pn = paint(s, n[Y0:Y1, X0:X1], COL)
    pn[(cv2.dilate(d, np.ones((3, 3), np.uint8)) > 0) & (d == 0)] = (0, 0, 255)
    r = cv2.resize(np.concatenate([s, paint(s, b[Y0:Y1, X0:X1], COL), pn], 1), None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
    r = np.pad(r, ((16, 4), (0, 0), (0, 0)), constant_values=255); cv2.putText(r, f'#{i} {x0},{y0}', (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1); rows.append(r)
Wm = max(r.shape[1] for r in rows); cv2.imwrite(outp, np.concatenate([np.pad(r, ((0, 0), (0, Wm - r.shape[1]), (0, 0)), constant_values=255) for r in rows], 0))
