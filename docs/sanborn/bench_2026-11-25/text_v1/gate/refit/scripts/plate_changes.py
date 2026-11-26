"""What finder3 changed against finder2 on a whole plate, for looking at by eye (no truth): a random sample of the
8-connected blobs whose text call differs, as tiles scan | finder2 | finder3 (magenta text, grey line, green other,
yellow shared). Title: '+' = became text, '-' = became other ink, and the pixels.
    cd data/sanborn; python -B .../plate_changes.py N OUT.jpg [--n 48] [--seed 0] [--min 20]"""
import os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
a = sys.argv[1:]; N, out = a[0], a[1]; n_ = int(a[a.index('--n') + 1]) if '--n' in a else 48; seed = int(a[a.index('--seed') + 1]) if '--seed' in a else 0
mn = int(a[a.index('--min') + 1]) if '--min' in a else 20
A = cv2.imread(f'bench_2026-11-25/text_v1/finder2/out/final/{N}_text.png', 0); B = cv2.imread(f'bench_2026-11-25/text_v1/classifier/out/finder3/{N}_text.png', 0)
ta, tb = np.isin(A, (2, 3)), np.isin(B, (2, 3)); d = (ta != tb).astype(np.uint8)
n, lb, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(d, np.ones((7, 7), np.uint8)), connectivity=8)
cnt = np.bincount(lb[d > 0], minlength=n); ids = np.nonzero(cnt >= mn)[0]; ids = ids[ids > 0]
rng = np.random.default_rng(seed); pick = rng.choice(ids, min(n_, len(ids)), replace=False) if len(ids) else []
im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = A.shape; COL = {1: (160, 160, 160), 2: (220, 0, 220), 3: (220, 0, 220), 4: (0, 200, 230), 5: (0, 150, 0)}
def paint(base, code):
    o = (base * 0.3 + 255 * 0.7).astype(np.uint8)
    for v, c in COL.items(): o[code == v] = c
    return o
tiles = []
for i in pick:
    cx, cy = st[i, 0] + st[i, 2] // 2, st[i, 1] + st[i, 3] // 2; s = max(35, st[i, 2] // 2 + 15, st[i, 3] // 2 + 15)
    X0, Y0, X1, Y1 = max(0, cx - s), max(0, cy - s), min(W, cx + s), min(H, cy + s); m = (lb[Y0:Y1, X0:X1] == i) & (d[Y0:Y1, X0:X1] > 0)
    sign = '+' if (tb[Y0:Y1, X0:X1] & m).sum() >= (ta[Y0:Y1, X0:X1] & m).sum() else '-'
    t_ = cv2.resize(np.concatenate([im[Y0:Y1, X0:X1], paint(im[Y0:Y1, X0:X1], A[Y0:Y1, X0:X1]), paint(im[Y0:Y1, X0:X1], B[Y0:Y1, X0:X1])], 1), (330, 110), interpolation=cv2.INTER_AREA)
    cv2.putText(t_, f'{cx},{cy} {sign}{int(m.sum())}', (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 0), 1); tiles.append(t_)
cols = 4; rows = max(1, (len(tiles) + cols - 1) // cols); sheet = np.full((rows * 112, cols * 332, 3), 255, np.uint8)
for j, t_ in enumerate(tiles): r, c_ = divmod(j, cols); sheet[r * 112:r * 112 + 110, c_ * 332:c_ * 332 + 330] = t_
cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
print(N, 'changed blobs', len(ids), '(>=', mn, 'px); became text px', int((tb & ~ta).sum()), '; became other px', int((ta & ~tb).sum()))
