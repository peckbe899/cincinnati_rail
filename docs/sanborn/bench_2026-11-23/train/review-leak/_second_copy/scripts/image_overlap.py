"""review-leak: does any training plate's scan show ground that is also on 44 or 90? SIFT on the scans at 1/4 size, ratio
test, then a RANSAC similarity (scale free, so a 100-ft and a 200-ft sheet of the same ground also match). Inliers of a
real shared area run into the dozens or hundreds; unrelated sheets give a handful (repeated print symbols). Positive
controls: 43 and 45 against 44 (they share a boundary strip with it, measured from the placements). Reads only.
cd data/sanborn; python -B bench_2026-11-23/train/review-leak/scripts/image_overlap.py"""
import json, time
import numpy as np, cv2
OUT = 'bench_2026-11-23/train/review-leak/'
TEST = ['44', '90']
TRAIN = json.load(open('train_v2/manifest.json', encoding='utf8'))['plates']
sift = cv2.SIFT_create(nfeatures=40000)
F = {}


def feats(N):
    if N in F: return F[N]
    im = cv2.imread(f'cufp/22-{N}.jpg', cv2.IMREAD_REDUCED_GRAYSCALE_4)
    al = np.load(f'cufp/{N}/png_alpha_s4.npy').astype(np.float32)
    m = (cv2.resize(al, (im.shape[1], im.shape[0])) > 0.5).astype(np.uint8) * 255
    k, d = sift.detectAndCompute(im, m); F[N] = (np.float32([p.pt for p in k]), d, im.shape); return F[N]


bf = cv2.BFMatcher(cv2.NORM_L2)
res = []
for t in TEST:
    for N in list(TRAIN):
        t0 = time.time(); ka, da, sa = feats(t); kb, db, sb = feats(N)
        mm = bf.knnMatch(db, da, k=2); good = [m for m, n in (x for x in mm if len(x) == 2) if m.distance < 0.75 * n.distance]
        inl, sc = 0, None
        if len(good) >= 6:
            A = kb[[m.queryIdx for m in good]]; B = ka[[m.trainIdx for m in good]]
            M, mask = cv2.estimateAffinePartial2D(A, B, method=cv2.RANSAC, ransacReprojThreshold=4.0, maxIters=20000, confidence=0.999)
            if M is not None: inl = int(mask.sum()); sc = round(float(np.hypot(M[0, 0], M[0, 1])), 3)
        r = dict(test=t, train=N, source=TRAIN[N]['source'], kp_test=len(ka), kp_train=len(kb), ratio_matches=len(good), ransac_inliers=inl, scale=sc, s=round(time.time() - t0, 1))
        res.append(r); print(json.dumps(r), flush=True)
json.dump(res, open(OUT + 'image_overlap.json', 'w'), indent=1)
