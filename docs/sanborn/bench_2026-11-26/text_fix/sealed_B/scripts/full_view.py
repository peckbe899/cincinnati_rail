"""Labelling aid for the full crop: 1.5x tiles (500 x 340 px of the crop) of the scan with the glyph-sized ink
clusters that no typed word covers boxed in blue and numbered, typed words in magenta (with annotation line), and a
full-plate px grid every 50 px. Ink less straight runs of 61 px (the builder's peel); pieces up to 90 px; clusters
join pieces closer than 7 px. Scan and my own words only. python -B full_view.py CROP [--tiles RC,RC]
Writes work/<CROP>_lab_RC.jpg and prints the clusters per tile."""
import os, sys, json
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import INV, window, line_mask

cid = sys.argv[1]; only = sys.argv[sys.argv.index('--tiles') + 1].split(',') if '--tiles' in sys.argv else None
c = json.load(open(os.path.join(INV, 'truth', 'crops.json'), encoding='utf8'))[cid]; X0, Y0, X1, Y1 = c['win']
wp = os.path.join(INV, 'truth', f'{cid}_words.json')
W = json.load(open(wp, encoding='utf8'))['words'] if os.path.exists(wp) else []
im, _, ink, (wx0, wy0, _, _) = window(c['plate'], X0 - 40, Y0 - 40, X1 + 40, Y1 + 40)
ln = line_mask(ink, 61, nang=72)
cand = ink & ~(cv2.dilate(ln.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
cov = np.zeros(ink.shape, np.uint8)
for w in W: cv2.fillPoly(cov, [np.round(np.array(w['poly']) - [wx0, wy0]).astype(np.int32)], 1)
n, lb, st, _ = cv2.connectedComponentsWithStats(cand.astype(np.uint8), connectivity=8)
covered = np.bincount(lb.ravel(), cov.ravel(), minlength=n) / np.maximum(1, st[:, 4])
keep = [i for i in range(1, n) if covered[i] < 0.5 and st[i, 4] >= 8 and max(st[i, 2], st[i, 3]) <= 90]
m = np.isin(lb, keep).astype(np.uint8)
ng, glb, gst, _ = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((7, 7), np.uint8)), connectivity=8)
cl = []
for j in range(1, ng):
    x, y, w_, h, _ = gst[j]; mm = (glb[y:y + h, x:x + w_] == j) & (m[y:y + h, x:x + w_] > 0); ys, xs = np.nonzero(mm)
    if len(xs) < 10: continue
    b = (xs.min() + x + wx0, ys.min() + y + wy0, xs.max() + x + wx0, ys.max() + y + wy0, len(xs))
    if b[2] < X0 or b[0] > X1 or b[3] < Y0 or b[1] > Y1: continue
    cl.append(b)
cl.sort(key=lambda b: (b[1] // 40, b[0]))
tw, th, sc = 500, 340, 1.5
for r, ty in enumerate(range(0, Y1 - Y0, th)):
    for cc, tx in enumerate(range(0, X1 - X0, tw)):
        if only and f'{r}{cc}' not in only: continue
        ox, oy = X0 + tx - 15, Y0 + ty - 15
        a = im[oy - wy0:oy - wy0 + th + 30, ox - wx0:ox - wx0 + tw + 30]
        A = cv2.resize(a, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
        P = lambda x, y: (int(round((x - ox) * sc)), int(round((y - oy) * sc)))
        for g in range((ox // 50 + 1) * 50, ox + tw + 30, 50):
            X = P(g, 0)[0]; A[:, X] = (A[:, X] * 0.75 + np.array([255, 160, 0]) * 0.25).astype(np.uint8); cv2.putText(A, str(g), (X + 2, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (200, 0, 0), 1)
        for g in range((oy // 50 + 1) * 50, oy + th + 30, 50):
            Y = P(0, g)[1]; A[Y] = (A[Y] * 0.75 + np.array([255, 160, 0]) * 0.25).astype(np.uint8); cv2.putText(A, str(g), (2, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (200, 0, 0), 1)
        for w in W:
            q = np.array([P(*v) for v in w['poly']], np.int32)
            if q[:, 0].max() < 0 or q[:, 1].max() < 0 or q[:, 0].min() > A.shape[1] or q[:, 1].min() > A.shape[0]: continue
            cv2.polylines(A, [q], True, (200, 0, 200), 1)
        lines = []
        for i, b in enumerate(cl):
            if b[2] < ox or b[0] > ox + tw + 30 or b[3] < oy or b[1] > oy + th + 30: continue
            cv2.rectangle(A, P(b[0] - 1, b[1] - 1), P(b[2] + 1, b[3] + 1), (255, 80, 0), 1)
            cv2.putText(A, str(i), (P(b[0], b[1])[0], P(b[0], b[1])[1] - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (230, 0, 0), 1)
            lines.append(f'{i}:{b[0]},{b[1]}-{b[2]},{b[3]}')
        cv2.imwrite(os.path.join(INV, 'work', f'{cid}_lab_{r}{cc}.jpg'), A, [cv2.IMWRITE_JPEG_QUALITY, 90])
        print(f'tile {r}{cc} [{ox},{oy}]:', ' '.join(lines))
