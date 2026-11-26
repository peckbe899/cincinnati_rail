"""What the second opinion changed on the truth crops (DEV ONLY, T1-T7): every blob of pixels whose text call differs
between finder2 and a finder3 mask, as tiles: scan | finder2 | finder3, with the truth shown as a coloured outline
(green = truth text, red = truth non-text). Sorted by the pixels gained (+) or lost (-) in F1 terms.
    cd data/sanborn; python -B .../change_sheet.py NEW_PATTERN({crop} or {plate}) OUT.jpg [CROPS]"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
TR = os.path.join('bench_2026-11-25', 'text_v1', 'truth'); F2 = os.path.join('bench_2026-11-25', 'text_v1', 'finder2', 'out', 'final', '{plate}_text.png')
newp, out = sys.argv[1], sys.argv[2]; crops_ = (sys.argv[3] if len(sys.argv) > 3 else 'T1,T2,T3,T4,T6,T7').split(',')
crops = json.load(open(os.path.join(TR, 'crops.json'))); tiles = []; ims = {}
COL = {1: (160, 160, 160), 2: (220, 0, 220), 3: (220, 0, 220), 4: (0, 200, 230), 5: (0, 150, 0)}
def paint(base, code):
    o = (base * 0.3 + 255 * 0.7).astype(np.uint8)
    for v, c in COL.items(): o[code == v] = c
    return o
for t in crops_:
    c = crops[t]; x0, y0, x1, y1 = c['win']; N = c['plate']
    if N not in ims: ims[N] = cv2.imread(f'cufp/22-{N}.jpg')
    im = ims[N][y0:y1, x0:x1]; tr = cv2.imread(os.path.join(TR, f'{t}_mask.png'), 0)
    a = cv2.imread(F2.replace('{plate}', N), 0)[y0:y1, x0:x1]; b = cv2.imread(newp.replace('{crop}', t).replace('{plate}', N), 0)
    if b.shape != a.shape: b = b[y0:y1, x0:x1]
    ta, tb = np.isin(a, (2, 3)), np.isin(b, (2, 3)); d = (ta != tb).astype(np.uint8)
    n, lb, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(d, np.ones((7, 7), np.uint8)), connectivity=8)
    for i in range(1, n):
        m = (lb == i) & (d > 0); gain = int(((tb & ~ta & m) & (tr == 2)).sum() - ((tb & ~ta & m) & (tr == 1)).sum() + ((ta & ~tb & m) & (tr == 1)).sum() - ((ta & ~tb & m) & (tr == 2)).sum())
        if not m.sum(): continue
        cx, cy = st[i, 0] + st[i, 2] // 2, st[i, 1] + st[i, 3] // 2; s = max(35, st[i, 2] // 2 + 15, st[i, 3] // 2 + 15)
        X0, Y0, X1, Y1 = max(0, cx - s), max(0, cy - s), min(im.shape[1], cx + s), min(im.shape[0], cy + s)
        pa, pb = paint(im[Y0:Y1, X0:X1], a[Y0:Y1, X0:X1]), paint(im[Y0:Y1, X0:X1], b[Y0:Y1, X0:X1])
        for p_ in (pa, pb):
            for v, col in ((2, (0, 170, 0)), (1, (0, 0, 255))):
                e = ((tr[Y0:Y1, X0:X1] == v) & m[Y0:Y1, X0:X1]).astype(np.uint8); ed = cv2.dilate(e, np.ones((3, 3), np.uint8)) - e; p_[ed > 0] = col
        tile = cv2.resize(np.concatenate([im[Y0:Y1, X0:X1], pa, pb], 1), (330, 110), interpolation=cv2.INTER_AREA)
        cv2.putText(tile, f'{t} {x0 + cx},{y0 + cy} {gain:+d}', (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 0), 1); tiles.append((gain, tile))
tiles.sort(key=lambda q: q[0]); print(len(tiles), 'changed blobs; net', sum(g for g, _ in tiles), '; worst', [g for g, _ in tiles[:8]], 'best', [g for g, _ in tiles[-8:]])
sel = tiles[:60] + tiles[-30:] if len(tiles) > 90 else tiles
cols = 4; rows = (len(sel) + cols - 1) // cols; sheet = np.full((rows * 112, cols * 332, 3), 255, np.uint8)
for j, (_, t_) in enumerate(sel): r, c_ = divmod(j, cols); sheet[r * 112:r * 112 + 110, c_ * 332:c_ * 332 + 330] = t_
cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
