"""Kentucky ground for maps 1-2 over the riverworks window.
Base: I4 (cleaned LiDAR outside the 1912 survey). Post-1912 works zones (Z_all, Kentucky side) are rebuilt by a thin-plate
solve that keeps the surrounding ground and passes near 1914 USGS 20 ft contours (labelled on unchanged ground, carried
along each contour into the zone). Saves ky1912_ground.npy (window grid) and a check image."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, json, cv2, rasterio, sys
from scipy import ndimage as ndi
import scipy.sparse as sp, scipy.sparse.linalg as spla, pyamg
from skimage.morphology import skeletonize
from pyproj import Transformer
FT = 1200 / 3937
d = np.load('rw_setup.npz'); L = d['L']; x0 = float(d['x0']); y1 = float(d['y1']); H, W = L.shape
KY = np.load('rw_KY.npy'); Z = np.load('rw_Zall.npy') & KY
with rasterio.open('I4_1912_ground_dm.tif') as ds:
    a = ds.read(1, window=rasterio.windows.from_bounds(x0, y1 - 2 * H, x0 + 2 * W, y1, ds.transform), boundless=True, fill_value=-32768)
B = np.where(a[:H, :W] > -30000, a[:H, :W] / 10.0, np.nan).astype(np.float32)
B = np.where(np.isfinite(B), B, ndi.gaussian_filter(L, 2))
Zd = ndi.binary_dilation(Z, iterations=3)
# ---- 1914 contours: brown skeleton at native resolution, mapped onto the 2 m grid with segment ids
SH = [_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/USGS_Historical/OH_West Cincinnati_226552_1914_62500_geo.tif"),
      _ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/USGS_Historical/OH_East Cincinnati_224942_1914_62500_geo.tif")]
SPLIT = Transformer.from_crs('EPSG:4326', 'EPSG:26916', always_xy=True).transform(-84.50, 39.09)[0]
seg = np.zeros((H, W), np.int32); nseg = 0
for si, f in enumerate(SH):
    s = rasterio.open(f); U = Transformer.from_crs(s.crs, 'EPSG:26916', always_xy=True); V = Transformer.from_crs('EPSG:26916', s.crs, always_xy=True)
    xs, ys = V.transform([x0, x0 + 2 * W, x0, x0 + 2 * W], [y1, y1, y1 - 2 * H, y1 - 2 * H])
    r_a, c_a = s.index(min(xs), max(ys)); r_b, c_b = s.index(max(xs), min(ys))
    r0, c0 = max(0, min(r_a, r_b)), max(0, min(c_a, c_b)); r1, c1 = min(s.height, max(r_a, r_b)), min(s.width, max(c_a, c_b))
    w = rasterio.windows.Window(c0, r0, c1 - c0, r1 - r0)
    img = np.dstack([s.read(i, window=w) for i in (3, 2, 1)])
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32); Lc, ac, bc = lab[..., 0], lab[..., 1] - 128, lab[..., 2] - 128
    brown = (ac > 8) & (bc > 15) & (Lc > 60) & (Lc < 200) & (ac < 45)
    brown = cv2.morphologyEx(brown.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)).astype(bool)
    sk = skeletonize(brown)
    cl, nc = ndi.label(sk, structure=np.ones((3, 3)))
    yy, xx = np.nonzero(sk); tr = s.window_transform(w)
    X = tr.c + (xx + 0.5) * tr.a; Y = tr.f + (yy + 0.5) * tr.e
    E, N = U.transform(X, Y); E = np.asarray(E); N = np.asarray(N)
    keep = (E < SPLIT) if si == 0 else (E >= SPLIT)
    cc = ((E - x0) / 2).astype(int); rr = ((y1 - N) / 2).astype(int)
    ok = keep & (cc >= 0) & (cc < W) & (rr >= 0) & (rr < H)
    seg[rr[ok], cc[ok]] = cl[yy[ok], xx[ok]] + nseg; nseg += nc
    print('sheet', si, 'skeleton px', ok.sum(), 'segments', nc)
seg = ndi.grey_dilation(seg, size=(2, 2)) * KY
# ---- label segments on unchanged ground (outside zones by 20 m)
far = ~ndi.binary_dilation(Zd, iterations=10)
ids = seg.ravel(); zf = (B / FT).ravel(); out = far.ravel() & (ids > 0)
order = np.argsort(ids[out]); sid = ids[out][order]; zv = zf[out][order]
bnd = np.r_[0, np.nonzero(np.diff(sid))[0] + 1, len(sid)]
labels = {}
for a_, b_ in zip(bnd[:-1], bnd[1:]):
    if b_ - a_ < 8: continue
    q = np.round(zv[a_:b_] / 20) * 20; v, cnt = np.unique(q, return_counts=True)
    if cnt.max() / (b_ - a_) >= 0.5: labels[sid[a_]] = v[cnt.argmax()]
lab_arr = np.zeros(nseg + 1, np.float32) * np.nan
for k, v in labels.items(): lab_arr[k] = v * FT
cons = (seg > 0) & Zd & np.isfinite(lab_arr[seg])
print('labelled segments', len(labels), 'constraint px inside zones', cons.sum())
# ---- thin-plate rebuild: unknowns are the zone pixels only, solved at 4 m, known ground around them
def tp_fill(val, mask, cval, cmask, wc=0.3):
    h, w = val.shape; Ui = -np.ones((h, w), np.int64); ui = np.nonzero(mask.ravel())[0]; Ui.ravel()[ui] = np.arange(len(ui))
    D1 = ndi.binary_dilation(mask, iterations=1)
    pr, pc = np.nonzero(D1); rows = []; cu = []; vu = []; kk = []
    rhs_k = np.zeros(len(pr))
    for (dr, dc, coef) in ((0, 0, -4.0), (-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0)):
        r2 = np.clip(pr + dr, 0, h - 1); c2 = np.clip(pc + dc, 0, w - 1)
        u = Ui[r2, c2]; isu = u >= 0
        rows.append(np.nonzero(isu)[0]); cu.append(u[isu]); vu.append(np.full(isu.sum(), coef))
        rhs_k[~isu] += coef * val[r2[~isu], c2[~isu]]
    Au = sp.csr_matrix((np.concatenate(vu), (np.concatenate(rows), np.concatenate(cu))), shape=(len(pr), len(ui)))
    wv = np.where(cmask.ravel()[ui], wc, 0.0); cv_ = np.where(cmask.ravel()[ui], cval.ravel()[ui], 0.0)
    A = (Au.T @ Au + sp.diags(wv + 1e-9)).tocsr(); bvec = -Au.T @ rhs_k + wv * cv_
    ml = pyamg.smoothed_aggregation_solver(A, max_coarse=500)
    x0g = np.full(len(ui), np.nanmedian(val[~mask]))
    sol = ml.solve(bvec, x0=x0g, tol=1e-8, maxiter=400, accel='cg')
    out = val.copy(); out.ravel()[ui] = sol; return out
B4 = B[::2, ::2]; Z4 = Zd[::2, ::2]
cz4 = ndi.maximum_filter(cons.astype(np.uint8), 2)[::2, ::2].astype(bool) & Z4
cv4 = ndi.maximum_filter(np.where(cons, lab_arr[seg], -1e9), 2)[::2, ::2]
F4 = tp_fill(B4.astype(np.float64), Z4, cv4, cz4)
F2 = cv2.resize(F4.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)[:H, :W]
wz = np.clip(ndi.gaussian_filter(Zd.astype(np.float32), 2) * 1.5, 0, 1) * ndi.binary_dilation(Zd, iterations=4)
G = np.where(wz > 0, wz * F2 + (1 - wz) * B, B).astype(np.float32); nz = ndi.label(Zd)[1]
np.save('ky1912_ground.npy', np.where(KY, G, np.nan).astype(np.float32))
dz = (G - B)[Zd]
print('zones %d, rebuilt %.2f km2, change p5/p50/p95 %.1f/%.1f/%.1f m' % (nz, Zd.sum() * 4e-6, *np.percentile(dz, [5, 50, 95])))
