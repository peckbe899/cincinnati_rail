"""dev (finder2): contact sheet of Ben's line ink (within 1 px of his lines) that a mask calls text, grouped in 8-connected
blobs, biggest first; optionally only what a second (older) mask did not call text. CHECK pictures only.
    cd data/sanborn; python -B <this> N NEW_PATTERN NEWCODES OUT.jpg [OLD_PATTERN OLDCODES] [--top 60]"""
import os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
SP = os.getcwd(); sys.path.insert(0, os.path.join(SP, 'bench_2026-11-25', 'text', 'finder', 'scripts'))
import benlines
a = sys.argv[1:]; top = 60; tol = 1
if '--tol' in a: i = a.index('--tol'); tol = int(a[i + 1]); a = a[:i] + a[i + 2:]
if '--top' in a: i = a.index('--top'); top = int(a[i + 1]); a = a[:i] + a[i + 2:]
N, newp, newc, out = a[0], a[1], [int(v) for v in a[2].split(',')], a[3]
code = cv2.imread(newp.replace('{plate}', N), 0); H, W = code.shape; t = np.isin(code, newc)
if len(a) > 4: old = cv2.imread(a[4].replace('{plate}', N), 0); t &= ~np.isin(old, [int(v) for v in a[5].split(',')])
m, _ = benlines.raster(N, W, H); d = cv2.distanceTransform((m == 0).astype(np.uint8), cv2.DIST_L2, 5)
hit = (t & (code > 0) & (d <= tol)).astype(np.uint8)
n, lb, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(hit, np.ones((15, 15), np.uint8)), connectivity=8)
cnt = np.bincount(lb[hit > 0], minlength=n); order = np.argsort(-cnt)[:top]; order = order[cnt[order] > 0]
im = cv2.imread(f'cufp/22-{N}.jpg'); tiles = []
for i in order:
    cx, cy = st[i, 0] + st[i, 2] // 2, st[i, 1] + st[i, 3] // 2; s = 60
    X0, Y0, X1, Y1 = max(0, cx - s), max(0, cy - s), min(W, cx + s), min(H, cy + s)
    a_ = im[Y0:Y1, X0:X1]; o = (a_ * 0.35 + 255 * 0.65).astype(np.uint8); c = code[Y0:Y1, X0:X1]
    o[c == 1] = (150, 150, 150); o[np.isin(c, newc)] = (220, 0, 220); o[c == 4] = (0, 200, 230); o[(m[Y0:Y1, X0:X1] > 0) & ~(hit[Y0:Y1, X0:X1] > 0)] = (255, 160, 0); o[hit[Y0:Y1, X0:X1] > 0] = (0, 0, 255)
    t_ = cv2.resize(np.concatenate([a_, o], 1), (360, 180)); cv2.putText(t_, f'{cx},{cy} {cnt[i]}', (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1); tiles.append(t_)
cols = 4; rows = max(1, (len(tiles) + cols - 1) // cols); sheet = np.full((rows * 182, cols * 362, 3), 255, np.uint8)
for i, t_ in enumerate(tiles): r, c = divmod(i, cols); sheet[r * 182:r * 182 + 180, c * 362:c * 362 + 360] = t_
cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 90]); print(N, 'hit px', int(hit.sum()), 'blobs', int((cnt > 0).sum()), 'top', [int(v) for v in cnt[order][:20]])
