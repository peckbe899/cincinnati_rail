"""sample_bin8.py (text/effect, 25 Nov 2026): 48 random pixels of a text mask (seeded; a pixel-weighted sample, so big
pieces are drawn more often, as their share of the mask), each shown as a 2x crop of 96 x 96 px with the connected piece
it belongs to tinted magenta and a red cross on the pixel. For classifying by eye (text / line piece / other).
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/sample_bin8.py N MASK.png OUT.png [SEED]"""
import sys, numpy as np, cv2
N, mf, out = sys.argv[1:4]; seed = int(sys.argv[4]) if len(sys.argv) > 4 else 1
im = cv2.imread(f'cufp/22-{N}.jpg'); M = cv2.imread(mf, 0) > 0; H, W = M.shape
ys, xs = np.nonzero(M); rng = np.random.default_rng(seed); pick = rng.choice(len(ys), 48, replace=False)
n, lab = cv2.connectedComponents(M.astype(np.uint8), connectivity=8); tiles = []
for k, i in enumerate(pick):
    y, x = int(ys[i]), int(xs[i]); x0, y0 = min(max(0, x - 48), W - 96), min(max(0, y - 48), H - 96)
    raw = im[y0:y0 + 96, x0:x0 + 96].copy(); comp = lab[y0:y0 + 96, x0:x0 + 96] == lab[y, x]
    t = raw.copy(); t[comp] = (0.3 * t[comp] + 0.7 * np.array([255, 0, 255])).astype(np.uint8)
    cv2.drawMarker(t, (x - x0, y - y0), (0, 0, 255), cv2.MARKER_CROSS, 9, 1)
    t = np.hstack([cv2.resize(raw, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST), np.full((192, 3, 3), 255, np.uint8), cv2.resize(t, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)])
    cv2.putText(t, str(k), (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2); tiles.append(np.pad(t, ((3, 3), (3, 3), (0, 0)), constant_values=255))
rows = [np.hstack(tiles[r * 4:(r + 1) * 4]) for r in range(12)]
cv2.imwrite(out, np.vstack(rows[:6])); cv2.imwrite(out[:-4] + '_b.png', np.vstack(rows[6:]))
print('picked', [(int(xs[i]), int(ys[i])) for i in pick])
