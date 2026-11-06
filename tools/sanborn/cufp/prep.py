try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Step 1 for a 1922 plate N (generalised from cuf38/match.py, 2026-10-21):
#   PNG (Ben's raw scan, the image we fit)  -> cufp/22-N.jpg (full size, for the readers), cufp/N/png_s8.jpg, cufp/N/png_alpha_s4.npy
#   GeoTIFF (Ben's georeferenced copy, only a reference) -> cufp/N/png2tif.json (png px -> tif px, deg-3 polynomial from SIFT),
#   cufp/N/tif_s8.jpg. After this the GeoTIFF is not needed (it can be deleted to save disk).
# usage: python3 cufp/prep.py N "<New Sanborn>/GeoTIFF/<name>.tif" (the old /mnt/user-data/uploads/... form still works: configs/sanborn_paths.json)
import sys, os, json, cv2, numpy as np, rasterio
from PIL import Image; Image.MAX_IMAGE_PIXELS = None
SP = _ws.DATA
N = sys.argv[1]; TIF = _ws.ext(sys.argv[2]) if len(sys.argv) > 2 else None   # no GeoTIFF: png products only; the seed then comes from street names (fit.py)
D = SP + f'cufp/{N}/'; os.makedirs(D, exist_ok=True)
PNG = _ws.ext(os.environ.get('PNG') or f'/mnt/user-data/uploads/PNG/{N}.png')
im = np.array(Image.open(PNG).convert('RGBA')); H0, W0 = im.shape[:2]
a = im[:, :, 3]; rgb = im[:, :, :3].copy(); rgb[a == 0] = 255
if not os.path.exists(SP + f'cufp/22-{N}.jpg'):
    cv2.imwrite(SP + f'cufp/22-{N}.jpg', rgb[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 88])
cv2.imwrite(D + 'png_s8.jpg', rgb[::8, ::8, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 85])
np.save(D + 'png_alpha_s4.npy', (a[::4, ::4] > 0).astype(np.uint8))
if TIF is None: sys.exit(0)
S = 4
png = cv2.cvtColor(rgb[::S, ::S], cv2.COLOR_RGB2GRAY); del im, rgb
r = rasterio.open(TIF); t = r.read(out_shape=(r.count, r.height // S, r.width // S))
tg = cv2.cvtColor(np.ascontiguousarray(np.moveaxis(t[:3], 0, -1)), cv2.COLOR_RGB2GRAY)
if r.count > 3: tg[t[3] == 0] = 255
else: tg[(t[0] == 0) & (t[1] == 0) & (t[2] == 0)] = 255
cv2.imwrite(D + 'tif_s8.jpg', tg[::2, ::2])
sift = cv2.SIFT_create(40000)
k1, d1 = sift.detectAndCompute(png, None); k2, d2 = sift.detectAndCompute(tg, None)
m = cv2.BFMatcher().knnMatch(d1, d2, k=2); good = [p for p, q in m if p.distance < 0.75 * q.distance]
P = np.float32([k1[g.queryIdx].pt for g in good]) * S
Q = np.float32([k2[g.trainIdx].pt for g in good]) * S * np.array([r.width / (r.width // S * S), r.height / (r.height // S * S)])
Hm, inl = cv2.findHomography(P, Q, cv2.RANSAC, 30.0); inl = inl.ravel().astype(bool)
print(N, 'png', W0, H0, 'tif', r.width, r.height, r.crs, 'matches', len(good), 'homography inliers', int(inl.sum()))
P, Q = P[inl], Q[inl]
def poly(P, deg):
    x, y = P[:, 0] / 10000, P[:, 1] / 10000
    return np.stack([x ** i * y ** j for i in range(deg + 1) for j in range(deg + 1 - i)], 1)
deg = 3
for it in range(3):
    X = poly(P, deg); cx, *_ = np.linalg.lstsq(X, Q[:, 0], rcond=None); cy, *_ = np.linalg.lstsq(X, Q[:, 1], rcond=None)
    res = np.hypot(X @ cx - Q[:, 0], X @ cy - Q[:, 1]); k = res < max(3 * np.median(res), 4); P, Q = P[k], Q[k]
print('seed final', len(P), 'rms px', round(float(np.sqrt((res[k] ** 2).mean())), 2))
json.dump(dict(deg=deg, cx=cx.tolist(), cy=cy.tolist(), tif_transform=list(r.transform)[:6], tif_crs=str(r.crs), pts=int(len(P)),
               png_size=[W0, H0]), open(D + 'png2tif.json', 'w'))
