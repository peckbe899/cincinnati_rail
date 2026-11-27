"""Dev (fix_block_a): run blockfix on a whole plate with debug and draw the words refused for one reason (scan | codes).
    cd data/sanborn; python -B .../code/rejsheet.py N BASE_DIR WHY OUT.png [--set k=v]"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import blockfix
from viz import paint, COL
a = sys.argv; N, bd, why, outp = a[1:5]
opts = {}
for i, v in enumerate(a):
    if v == '--set': k, val = a[i + 1].split('=', 1); opts[k] = json.loads(val)
codes = cv2.imread(os.path.join(bd, f'{N}_text.png'), 0); im = cv2.imread(f'cufp/22-{N}.jpg')
dbg = {}; out, info = blockfix.apply(N, codes, None, blockfix.scale_of(N), debug=dbg, return_info=True, **opts)
tiles = []; H, W = codes.shape
for w in dbg['words']:
    if w['why'] != why: continue
    x0, y0, x1, y1 = w['fbox']; g = 20; X0, Y0, X1, Y1 = max(0, x0 - g), max(0, y0 - g), min(W, x1 + g), min(H, y1 + g)
    s = im[Y0:Y1, X0:X1]; r = np.concatenate([s, paint(s, codes[Y0:Y1, X0:X1], COL)], 1)
    r = np.pad(cv2.resize(r, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_NEAREST), ((14, 4), (0, 6), (0, 0)), constant_values=255)
    cv2.putText(r, f"{x0},{y0} H{w['H']} W{w['W']} a{w['anchor']} sw{w['sw']} d{w['dens']}", (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 0, 0), 1)
    tiles.append(r)
rows = []; cur = []; cw = 0
for t in tiles:
    if cw + t.shape[1] > 2200 and cur: rows.append(cur); cur = []; cw = 0
    cur.append(t); cw += t.shape[1]
if cur: rows.append(cur)
R = [np.concatenate([np.pad(t, ((0, max(x.shape[0] for x in r) - t.shape[0]), (0, 0), (0, 0)), constant_values=255) for t in r], 1) for r in rows]
Wm = max(r.shape[1] for r in R)
cv2.imwrite(outp, np.concatenate([np.pad(r, ((0, 0), (0, Wm - r.shape[1]), (0, 0)), constant_values=255) for r in R], 0))
print(len(tiles), info['why'])
