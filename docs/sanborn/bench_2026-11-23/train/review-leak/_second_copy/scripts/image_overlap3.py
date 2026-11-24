"""review-leak: shared ground between a training plate and 44 or 90, third try. image_overlap2.py's clusters were mostly
degenerate (many train points onto one test point, scale ~0). Here: mutual nearest neighbours that also pass the ratio
test, one match per test point, up to 4 RANSAC clusters, a cluster counted only when its scale is not degenerate (> 0.2)
and its inliers are spread (> 40 quarter px). Furniture out as in image_overlap2 (KEY box, off the map ground).
Positive controls (detection power): a strip of the test sheet itself (10% of its width, from its middle), and a
third of it at half scale with JPEG noise (a 200-ft sheet of 100-ft ground), each matched like a training plate.
Reads only. cd data/sanborn; python -B bench_2026-11-23/train/review-leak/scripts/image_overlap3.py"""
import json, os, time
import numpy as np, cv2
OUT = 'bench_2026-11-23/train/review-leak/'
KEY = json.load(open('bench_2026-11-21/census/rail_key.json', encoding='utf8'))
TRAIN = json.load(open('train_v2/manifest.json', encoding='utf8'))['plates']
sift = cv2.SIFT_create(nfeatures=40000); bf = cv2.BFMatcher(cv2.NORM_L2); F = {}


def mask_of(N, h, w):
    al = np.load(f'cufp/{N}/png_alpha_s4.npy').astype(np.float32); m = cv2.resize(al, (w, h)) > 0.5
    g = f'unet_data/{N}_mapground.png'
    if os.path.exists(g): m &= cv2.resize(cv2.imread(g, 0), (w, h), interpolation=cv2.INTER_NEAREST) > 0
    kb = (KEY.get(N) or {}).get('key_box')
    if kb: x0, y0, x1, y1 = [int(v / 4) for v in kb]; m[max(0, y0 - 10):y1 + 10, max(0, x0 - 10):x1 + 10] = False
    return m


def det(im, m):
    k, d = sift.detectAndCompute(im, m.astype(np.uint8) * 255); return np.float32([p.pt for p in k]), d


def feats(N):
    if N not in F:
        im = cv2.imread(f'cufp/22-{N}.jpg', cv2.IMREAD_REDUCED_GRAYSCALE_4); m = mask_of(N, *im.shape); F[N] = (im, m) + det(im, m)
    return F[N]


def match(kb, db, ka, da):
    f = bf.knnMatch(db, da, k=2); r = bf.match(da, db); back = {m.queryIdx: m.trainIdx for m in r}
    good = [m for m, n in (x for x in f if len(x) == 2) if m.distance < 0.8 * n.distance and back.get(m.trainIdx) == m.queryIdx]
    A = np.float32([kb[m.queryIdx] for m in good]).reshape(-1, 2); B = np.float32([ka[m.trainIdx] for m in good]).reshape(-1, 2)
    cl = []
    for _ in range(4):
        if len(A) < 8: break
        M, mask = cv2.estimateAffinePartial2D(A, B, method=cv2.RANSAC, ransacReprojThreshold=4.0, maxIters=20000, confidence=0.999)
        if M is None: break
        inl = mask.ravel() > 0
        if inl.sum() < 3: break
        s = float(np.hypot(M[0, 0], M[0, 1])); a = A[inl]; spread = float(np.hypot(*(a.max(0) - a.min(0))))
        cl.append(dict(inliers=int(inl.sum()), scale=round(s, 3), rot_deg=round(float(np.degrees(np.arctan2(M[1, 0], M[0, 0]))), 1), spread=round(spread, 1),
                       real=bool(s > 0.2 and spread > 40), train_center=[round(float(v)) for v in a.mean(0)], test_center=[round(float(v)) for v in B[inl].mean(0)]))
        A, B = A[~inl], B[~inl]
    best = max([c['inliers'] for c in cl if c['real']] or [0])
    return len(good), cl, best


res = []
for t in ('44', '90'):
    im, m, ka, da = feats(t); h, w = im.shape
    # positive controls
    s0 = w // 2 - w // 20; strip = im[:, s0:s0 + w // 10].copy(); kb, db = det(strip, m[:, s0:s0 + w // 10])
    n, cl, best = match(kb, db, ka, da); r = dict(test=t, train='CONTROL strip 10% width, same scale', mutual=n, best_real=best, clusters=cl); res.append(r); print(t, 'control strip', n, best, flush=True)
    third = im[h // 3:2 * h // 3, w // 3:2 * w // 3]; small = cv2.resize(third, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    ok, enc = cv2.imencode('.jpg', small, [cv2.IMWRITE_JPEG_QUALITY, 60]); small = cv2.imdecode(enc, 0)
    kb, db = det(small, np.ones(small.shape, bool)); n, cl, best = match(kb, db, ka, da)
    r = dict(test=t, train='CONTROL middle third at half scale, JPEG 60', mutual=n, best_real=best, clusters=cl); res.append(r); print(t, 'control half-scale', n, best, flush=True)
    for N in TRAIN:
        t0 = time.time(); _, _, kb, db = feats(N); n, cl, best = match(kb, db, ka, da)
        r = dict(test=t, train=N, source=TRAIN[N]['source'], mutual=n, best_real=best, clusters=cl, s=round(time.time() - t0, 1)); res.append(r)
        print(t, N.ljust(4), 'mutual', n, 'best real cluster', best, [(c['inliers'], c['scale'], c['spread'], c['real']) for c in cl], flush=True)
json.dump(res, open(OUT + 'image_overlap3.json', 'w'), indent=1)
