"""Check sheets for targeted crops: for every target word, its scope (box + scope_pad) plus 4 px, scan beside truth
(text red, don't care yellow, other ink grey; word boxes magenta, target boxes pink), zoom Z, COLS pairs per row,
ROWS rows per sheet. python -B chk_targets.py OUTPREFIX Z COLS ROWS CROP [CROP ...] -> OUTPREFIX_N.jpg"""
import os, sys, json
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import INV, window
from build import colour

pre, Z, COLS, ROWS = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
crops = json.load(open(os.path.join(INV, 'truth', 'crops.json'), encoding='utf8'))
panels = []
for cid in sys.argv[5:]:
    c = crops[cid]; X0, Y0, X1, Y1 = c['win']; M = cv2.imread(os.path.join(INV, 'truth', f'{cid}_mask.png'), 0)
    W = json.load(open(os.path.join(INV, 'truth', f'{cid}_words.json'), encoding='utf8'))['words']
    im_all = window(c['plate'], X0, Y0, X1, Y1)[0]
    for w in W:
        if not w['target']: continue
        a = w['aabb']; pad = c.get('scope_pad', 25) + 4
        x0, y0, x1, y1 = max(X0, a[0] - pad), max(Y0, a[1] - pad), min(X1, a[2] + pad), min(Y1, a[3] + pad)
        im = im_all[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0]; m = M[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0]
        A = cv2.resize(im, None, fx=Z, fy=Z, interpolation=cv2.INTER_NEAREST); B = cv2.resize(colour(im, m), None, fx=Z, fy=Z, interpolation=cv2.INTER_NEAREST)
        for q in W:
            P = (np.array(q['poly']) - [x0, y0]) * Z
            cv2.polylines(B, [np.round(P).astype(np.int32)], True, (255, 0, 170) if q['target'] else (160, 0, 160), 1)
        t = np.full((A.shape[0] + 16, 2 * A.shape[1] + 4, 3), 255, np.uint8); t[16:, :A.shape[1]] = A; t[16:, A.shape[1] + 4:] = B
        cv2.putText(t, f"{w['id']} {w['ink_px']}/{w['text_px_final']} [{a[0]},{a[1]}]", (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 160), 1)
        panels.append(t)
per = COLS * ROWS
for s in range(0, len(panels), per):
    ps = panels[s:s + per]; rows = []
    for i in range(0, len(ps), COLS):
        r = ps[i:i + COLS]; h = max(p.shape[0] for p in r)
        rows.append(np.hstack([cv2.copyMakeBorder(p, 0, h - p.shape[0], 0, 10, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for p in r]))
    w_ = max(r.shape[1] for r in rows)
    cv2.imwrite(f'{pre}_{s // per + 1}.jpg', np.vstack([cv2.copyMakeBorder(r, 0, 8, 0, w_ - r.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r in rows]), [cv2.IMWRITE_JPEG_QUALITY, 90])
print(len(panels), 'panels')
