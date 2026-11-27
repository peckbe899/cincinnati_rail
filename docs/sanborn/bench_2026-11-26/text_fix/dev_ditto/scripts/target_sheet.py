"""All target words on contact sheets at 6x, scan left and truth right, for the final look (dev_ditto, 26 Nov 2026).

    cd data/sanborn; python -B bench_2026-11-26/text_fix/dev_ditto/scripts/target_sheet.py TRUTHDIR [--pad 10] [--per 48]

Truth colours: text red, not text blue, don't care orange, paper pale. Writes TRUTHDIR/check/targets_NN.png."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import plate_img

a = sys.argv; TD = os.path.abspath(a[1]); pad = int(a[a.index('--pad') + 1]) if '--pad' in a else 10
per = int(a[a.index('--per') + 1]) if '--per' in a else 48; k = int(a[a.index('--k') + 1]) if '--k' in a else 6
C = json.load(open(os.path.join(TD, 'crops.json'))); cells = []
ONLY = set(a[a.index('--only') + 1].split(',')) if '--only' in a else None
NAME = a[a.index('--name') + 1] if '--name' in a else 'targets'
for cid in sorted(C):
    f = os.path.join(TD, f'{cid}_words.json')
    if not os.path.exists(f) or (ONLY and cid not in ONLY): continue
    c = C[cid]; X0, Y0, X1, Y1 = c['win']; M = cv2.imread(os.path.join(TD, f'{cid}_mask.png'), 0); im = plate_img(c['plate'])
    for w in json.load(open(f))['words']:
        if not w['target']: continue
        a0, b0, a1, b1 = w['aabb']; x0, y0, x1, y1 = max(X0, a0 - pad), max(Y0, b0 - pad), min(X1, a1 + pad + 1), min(Y1, b1 + pad + 1)
        S = im[y0:y1, x0:x1].copy(); T = (S.astype(np.float32) * 0.3 + 255 * 0.7).astype(np.uint8); m = M[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0]
        T[m == 1] = (200, 120, 40); T[m == 2] = (0, 0, 230); T[m == 3] = (0, 170, 255)
        S = cv2.resize(S, None, fx=k, fy=k, interpolation=cv2.INTER_NEAREST); T = cv2.resize(T, None, fx=k, fy=k, interpolation=cv2.INTER_NEAREST)
        q = (np.array(w['poly']) - [x0, y0]) * k; cv2.polylines(T, [np.round(q).astype(np.int32)], True, (0, 150, 0), 1)
        cell = np.hstack([S, np.full((S.shape[0], 2, 3), 255, np.uint8), T])
        cell = cv2.copyMakeBorder(cell, 13, 1, 1, 1, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        cv2.putText(cell, f"{w['id']} {w.get('style', '')} {w['text_px']}px{' U' if 'unsure' in w['flags'] else ''}", (2, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 0, 0), 1)
        cells.append(cell)
CW = max(x.shape[1] for x in cells); CHh = max(x.shape[0] for x in cells); cols = max(1, 1500 // (CW + 3))
for s in range(0, len(cells), per):
    part = cells[s:s + per]; rows = (len(part) + cols - 1) // cols
    G = np.full((rows * (CHh + 3), cols * (CW + 3), 3), 170, np.uint8)
    for i, x in enumerate(part):
        r, cc = divmod(i, cols); G[r * (CHh + 3):r * (CHh + 3) + x.shape[0], cc * (CW + 3):cc * (CW + 3) + x.shape[1]] = x
    fn = os.path.join(TD, 'check', f'{NAME}_{s // per + 1:02d}.png'); cv2.imwrite(fn, G); print(fn, G.shape)
