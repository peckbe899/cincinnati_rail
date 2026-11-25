"""Glyph clustering prototype (no download, CPU, OpenCV + numpy only).
Takes the single-character-sized pieces of today's text bin (ink_bins bin 8) on one plate, normalises each
to 32x32, reduces to 48 numbers by PCA and groups them with k-means (cv2.kmeans, k clusters, fixed seed).
Writes:
  out/glyphs_<plate>.npz       the glyph images, boxes and cluster ids
  pics/clusters_<plate>_<i>.png contact sheets: one row per cluster, 22 random members, scan pixels
Usage: python -B glyph_cluster.py 44 80
Nothing is trained on labels here; the clusters are unsupervised."""
import os, sys, cv2, numpy as np
R = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D'
B = os.path.join(R, 'data/sanborn/bench_2026-11-25/text/research')
plate, K = sys.argv[1], int(sys.argv[2])
code = cv2.imread(os.path.join(R, f'data/sanborn/unet_data/{plate}_bins.png'), cv2.IMREAD_UNCHANGED)
scan = cv2.imread(os.path.join(R, f'data/sanborn/cufp/22-{plate}.jpg'), cv2.IMREAD_GRAYSCALE)
t = (code == 8).astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(t, connectivity=8)
S = 32


def norm(mask):
    h, w = mask.shape
    s = 26.0 / max(h, w)
    m = cv2.resize(mask.astype(np.float32), (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)
    out = np.zeros((S, S), np.float32)
    y, x = (S - m.shape[0]) // 2, (S - m.shape[1]) // 2
    out[y:y + m.shape[0], x:x + m.shape[1]] = m
    return cv2.GaussianBlur(out, (3, 3), 0.8)


ids, feats, boxes = [], [], []
for i in range(1, n):
    x, y, w, h, a = st[i]
    if not (16 <= h <= 48 and 4 <= w <= h + 4 and a >= 30):
        continue
    m = (lab[y:y + h, x:x + w] == i)
    ids.append(i); boxes.append((x, y, w, h)); feats.append(norm(m))
G = np.array(feats)
X = G.reshape(len(G), -1)
asp = np.array([b[2] / b[3] for b in boxes], np.float32)
mu = X.mean(0)
U, Sv, Vt = np.linalg.svd(X[np.random.default_rng(0).choice(len(X), min(4000, len(X)), replace=False)] - mu, full_matrices=False)
P = (X - mu) @ Vt[:48].T
P = np.hstack([P, 3 * asp[:, None]]).astype(np.float32)
cv2.setRNGSeed(0)
_, lbl, _ = cv2.kmeans(P, K, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.01), 4, cv2.KMEANS_PP_CENTERS)
lbl = lbl.ravel()
print(plate, 'glyph candidates', len(G), 'clusters', K)
np.savez_compressed(os.path.join(B, f'out/glyphs_{plate}.npz'), G=G.astype(np.float16), boxes=np.array(boxes), comp=np.array(ids), cluster=lbl)
# contact sheets, 20 clusters per sheet, ordered by size
order = np.argsort(-np.bincount(lbl, minlength=K))
rng = np.random.default_rng(1)
cell = 44
per = 20
for s0 in range(0, K, per):
    rows = []
    for c in order[s0:s0 + per]:
        mem = np.where(lbl == c)[0]
        pick = rng.choice(mem, min(22, len(mem)), replace=False)
        row = np.full((cell, 70 + 22 * cell), 255, np.uint8)
        cv2.putText(row, f'{c}', (2, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 0, 1)
        cv2.putText(row, f'n{len(mem)}', (2, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.45, 0, 1)
        for j, g in enumerate(pick):
            x, y, w, h = boxes[g]
            c0 = scan[max(0, y - 3):y + h + 3, max(0, x - 3):x + w + 3]
            sc = min((cell - 4) / c0.shape[0], (cell - 4) / c0.shape[1], 1.0)
            c0 = cv2.resize(c0, (max(1, int(c0.shape[1] * sc)), max(1, int(c0.shape[0] * sc))))
            X0 = 70 + j * cell
            row[2:2 + c0.shape[0], X0:X0 + c0.shape[1]] = c0
        rows.append(row)
        rows.append(np.full((2, row.shape[1]), 160, np.uint8))
    cv2.imwrite(os.path.join(B, f'pics/clusters_{plate}_{s0 // per}.png'), np.vstack(rows))
