"""review-leak: where on the two sheets are the RANSAC inliers of image_overlap.py (sheet furniture such as lettering, or
the map ground)? Draws both sheets side by side with the inliers, and reports the transform. Reads only.
cd data/sanborn; python -B bench_2026-11-23/train/review-leak/scripts/image_overlap_where.py 90:89 90:79 ..."""
import json, os, sys
import numpy as np, cv2
OUT = 'bench_2026-11-23/train/review-leak/overlap_pics/'; os.makedirs(OUT, exist_ok=True)
sift = cv2.SIFT_create(nfeatures=40000); bf = cv2.BFMatcher(cv2.NORM_L2)


def feats(N):
    im = cv2.imread(f'cufp/22-{N}.jpg', cv2.IMREAD_REDUCED_GRAYSCALE_4)
    al = np.load(f'cufp/{N}/png_alpha_s4.npy').astype(np.float32)
    m = (cv2.resize(al, (im.shape[1], im.shape[0])) > 0.5).astype(np.uint8) * 255
    k, d = sift.detectAndCompute(im, m); return im, np.float32([p.pt for p in k]), d


def mapground(N, shape):
    f = f'unet_data/{N}_mapground.png'
    if not os.path.exists(f): return None
    g = cv2.imread(f, 0); return cv2.resize(g, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST) > 0


res = {}
for pair in sys.argv[1:]:
    t, N = pair.split(':'); ia, ka, da = feats(t); ib, kb, db = feats(N)
    mm = bf.knnMatch(db, da, k=2); good = [m for m, n in (x for x in mm if len(x) == 2) if m.distance < 0.75 * n.distance]
    A = kb[[m.queryIdx for m in good]]; B = ka[[m.trainIdx for m in good]]
    M, mask = cv2.estimateAffinePartial2D(A, B, method=cv2.RANSAC, ransacReprojThreshold=4.0, maxIters=20000, confidence=0.999)
    inl = mask.ravel() > 0; a_in, b_in = A[inl], B[inl]
    ga, gb = mapground(t, ia.shape), mapground(N, ib.shape)
    def on(g, p): return None if g is None else round(float(np.mean([g[int(min(y, g.shape[0] - 1)), int(min(x, g.shape[1] - 1))] for x, y in p])), 3)
    r = dict(test=t, train=N, inliers=int(inl.sum()), M=np.round(M, 3).tolist(), scale=round(float(np.hypot(M[0, 0], M[0, 1])), 3),
             train_bbox_quarter_px=[float(a_in[:, 0].min()), float(a_in[:, 1].min()), float(a_in[:, 0].max()), float(a_in[:, 1].max())], train_size_quarter=list(ib.shape[::-1]),
             test_bbox_quarter_px=[float(b_in[:, 0].min()), float(b_in[:, 1].min()), float(b_in[:, 0].max()), float(b_in[:, 1].max())], test_size_quarter=list(ia.shape[::-1]),
             share_inliers_on_train_mapground=on(gb, a_in), share_inliers_on_test_mapground=on(ga, b_in))
    res[pair] = r; print(json.dumps(r), flush=True)
    s = 0.25; ca = cv2.cvtColor(cv2.resize(ia, None, fx=s, fy=s), cv2.COLOR_GRAY2BGR); cb = cv2.cvtColor(cv2.resize(ib, None, fx=s, fy=s), cv2.COLOR_GRAY2BGR)
    for (x, y) in a_in: cv2.circle(cb, (int(x * s), int(y * s)), 4, (0, 0, 255), -1)
    for (x, y) in b_in: cv2.circle(ca, (int(x * s), int(y * s)), 4, (0, 0, 255), -1)
    h = max(ca.shape[0], cb.shape[0]); pad = lambda c: cv2.copyMakeBorder(c, 0, h - c.shape[0], 0, 10, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    pic = np.hstack([pad(cb), pad(ca)]); cv2.putText(pic, f'train {N} (left)  test {t} (right)  inliers {int(inl.sum())}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
    cv2.imwrite(OUT + f'{t}_vs_{N}.jpg', pic, [cv2.IMWRITE_JPEG_QUALITY, 80])
json.dump(res, open(OUT + 'where.json', 'w'), indent=1)
