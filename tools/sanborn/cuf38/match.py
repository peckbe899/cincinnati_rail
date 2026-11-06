try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# png (Ben's raw scan of plate 38) -> tif (Ben's georeferenced copy) pixel mapping by SIFT matches; the tif is only a starting reference
import cv2, numpy as np, rasterio, json
from PIL import Image; Image.MAX_IMAGE_PIXELS = None
SP = _ws.DATA
S = 4
png = np.array(Image.open(SP + 'cuf/22-38.jpg').convert('L'))[::S, ::S]
r = rasterio.open(_ws.ext('/mnt/user-data/uploads/38_south_clifton.tif')); t = r.read(out_shape=(4, r.height // S, r.width // S))
tg = cv2.cvtColor(np.moveaxis(t[:3], 0, -1), cv2.COLOR_RGB2GRAY); tg[t[3] == 0] = 255
sift = cv2.SIFT_create(40000)
k1, d1 = sift.detectAndCompute(png, None); k2, d2 = sift.detectAndCompute(tg, None)
m = cv2.BFMatcher().knnMatch(d1, d2, k=2); good = [a for a, b in m if a.distance < 0.75 * b.distance]
P = np.float32([k1[a.queryIdx].pt for a in good]) * S; Q = np.float32([k2[a.trainIdx].pt for a in good]) * S * np.array([r.width / (r.width // S * S), r.height / (r.height // S * S)])
H, inl = cv2.findHomography(P, Q, cv2.RANSAC, 30.0); inl = inl.ravel().astype(bool)
print('matches', len(good), 'homography inliers', inl.sum())
P, Q = P[inl], Q[inl]
def poly(P, deg):
    x, y = P[:, 0] / 10000, P[:, 1] / 10000
    cols = [x ** i * y ** j for i in range(deg + 1) for j in range(deg + 1 - i)]
    return np.stack(cols, 1)
for deg in (1, 2, 3):
    X = poly(P, deg); cx, *_ = np.linalg.lstsq(X, Q[:, 0], rcond=None); cy, *_ = np.linalg.lstsq(X, Q[:, 1], rcond=None)
    res = np.hypot(X @ cx - Q[:, 0], X @ cy - Q[:, 1]); print('deg', deg, 'rms px', round(float(np.sqrt((res ** 2).mean())), 1), 'p95', round(float(np.percentile(res, 95)), 1))
# keep deg 3 with outlier trim
deg = 3
for it in range(3):
    X = poly(P, deg); cx, *_ = np.linalg.lstsq(X, Q[:, 0], rcond=None); cy, *_ = np.linalg.lstsq(X, Q[:, 1], rcond=None)
    res = np.hypot(X @ cx - Q[:, 0], X @ cy - Q[:, 1]); k = res < max(3 * np.median(res), 4); P, Q = P[k], Q[k]
print('final', len(P), 'rms px', round(float(np.sqrt((res[k] ** 2).mean())), 2))
json.dump(dict(deg=deg, cx=cx.tolist(), cy=cy.tolist(), tif_transform=list(r.transform)[:6], pts=len(P)), open(SP + 'cuf38/png2tif.json', 'w'))
