"""review-leak: do any training plates share ground with 44 (or 90) on the placed plates' world grids (cufp/N/model.npz)?
Reads only. cd data/sanborn; python -B bench_2026-11-23/train/review-leak/scripts/footprints.py"""
import json, os
import numpy as np, cv2
OUT = 'bench_2026-11-23/train/review-leak/'
PL = ['44', '43', '45', '80', '82A', '66', '68', '76']


def fp(N):
    z = np.load(f'cufp/{N}/model.npz'); px, py = z['px'], z['py']; E0, N1, st = float(z['E0']), float(z['N1']), float(z['step'])
    im = cv2.imread(f'cufp/22-{N}.jpg', cv2.IMREAD_REDUCED_GRAYSCALE_8); H, W = im.shape[0] * 8, im.shape[1] * 8
    al = np.load(f'cufp/{N}/png_alpha_s4.npy').astype(np.float32); ah, aw = al.shape
    ok = (px > -1e5) & (py > -1e5) & (px >= 0) & (py >= 0) & (px < W) & (py < H)
    ax = np.clip((px / W * aw).astype(int), 0, aw - 1); ay = np.clip((py / H * ah).astype(int), 0, ah - 1)
    ok &= al[ay, ax] > 0.5
    ii, jj = np.nonzero(ok)
    cells = set(zip(np.floor((E0 + jj * st) / 4).astype(int).tolist(), np.floor((N1 - ii * st) / 4).astype(int).tolist())); st = 4.0
    return cells, st


res = {}; F = {}
for N in PL:
    if os.path.exists(f'cufp/{N}/model.npz'): F[N] = fp(N)
for N in PL:
    if N == '44' or N not in F: continue
    c, st = F[N]; c44, s44 = F['44']
    inter = len(c & c44)
    res[N] = dict(cells=len(c), cells_44=len(c44), shared_cells=inter, shared_m2=inter * st * st, share_of_44=round(inter / max(1, len(c44)), 5), share_of_N=round(inter / max(1, len(c)), 5))
    print(N, json.dumps(res[N]))
json.dump(res, open(OUT + 'footprints.json', 'w'), indent=1)
