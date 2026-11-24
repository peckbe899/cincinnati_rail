"""review-leak: image_overlap.py again with the sheet furniture taken out (the printed KEY box from the 21 Nov census, and
on the PDF sheets everything off the map ground, N_mapground.png), and up to 3 RANSAC clusters per pair (the strongest
one removed before the next), so a small shared strip is not hidden behind a bigger furniture match. Reads only.
cd data/sanborn; python -B bench_2026-11-23/train/review-leak/scripts/image_overlap2.py"""
import json, os, time
import numpy as np, cv2
OUT = 'bench_2026-11-23/train/review-leak/'
KEY = json.load(open('bench_2026-11-21/census/rail_key.json', encoding='utf8'))
TRAIN = json.load(open('train_v2/manifest.json', encoding='utf8'))['plates']
SC = json.load(open('scale_table.json', encoding='utf8'))
sift = cv2.SIFT_create(nfeatures=40000); bf = cv2.BFMatcher(cv2.NORM_L2); F = {}


def feats(N):
    if N in F: return F[N]
    im = cv2.imread(f'cufp/22-{N}.jpg', cv2.IMREAD_REDUCED_GRAYSCALE_4); h, w = im.shape
    al = np.load(f'cufp/{N}/png_alpha_s4.npy').astype(np.float32); m = cv2.resize(al, (w, h)) > 0.5
    g = f'unet_data/{N}_mapground.png'
    if os.path.exists(g): m &= cv2.resize(cv2.imread(g, 0), (w, h), interpolation=cv2.INTER_NEAREST) > 0
    kb = (KEY.get(N) or {}).get('key_box')
    if kb: x0, y0, x1, y1 = [int(v / 4) for v in kb]; m[max(0, y0 - 10):y1 + 10, max(0, x0 - 10):x1 + 10] = False
    k, d = sift.detectAndCompute(im, m.astype(np.uint8) * 255); F[N] = (np.float32([p.pt for p in k]), d, m.mean()); return F[N]


res = []
for t in ('44', '90'):
    for N in TRAIN:
        t0 = time.time(); ka, da, _ = feats(t); kb, db, _ = feats(N)
        mm = bf.knnMatch(db, da, k=2); good = [m for m, n in (x for x in mm if len(x) == 2) if m.distance < 0.75 * n.distance]
        A = kb[[m.queryIdx for m in good]] if good else np.zeros((0, 2), np.float32); B = ka[[m.trainIdx for m in good]] if good else np.zeros((0, 2), np.float32)
        expect = (SC.get(N, {}).get('ft_per_inch') or 0) / max(1, SC.get(t, {}).get('ft_per_inch') or 1)   # a shared ground would match at this scale (train px -> test px)
        cl = []
        for _ in range(3):
            if len(A) < 8: break
            M, mask = cv2.estimateAffinePartial2D(A, B, method=cv2.RANSAC, ransacReprojThreshold=4.0, maxIters=20000, confidence=0.999)
            if M is None: break
            inl = mask.ravel() > 0; s = float(np.hypot(M[0, 0], M[0, 1])); a = A[inl]
            spread = float(np.hypot(*(a.max(0) - a.min(0)))) if inl.sum() else 0.0
            cl.append(dict(inliers=int(inl.sum()), scale=round(s, 3), rot_deg=round(float(np.degrees(np.arctan2(M[1, 0], M[0, 0]))), 1), spread_train_quarter_px=round(spread, 1),
                           train_center=[round(float(v), 1) for v in a.mean(0)] if inl.sum() else None, plausible_scale=bool(abs(s - expect) < 0.08 * max(expect, 0.1))))
            A, B = A[~inl], B[~inl]
        r = dict(test=t, train=N, ratio_matches=len(good), expected_scale=round(expect, 3), clusters=cl, s=round(time.time() - t0, 1)); res.append(r)
        print(t, N.ljust(4), 'ratio', len(good), 'clusters', [(c['inliers'], c['scale'], c['rot_deg'], c['spread_train_quarter_px'], c['plausible_scale']) for c in cl], flush=True)
json.dump(res, open(OUT + 'image_overlap2.json', 'w'), indent=1)
