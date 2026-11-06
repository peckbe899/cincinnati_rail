"""Map 3 base: rebuild the real-only works zones (Z_real, zones v2) to the ground before them, from the 1950-55 USGS
1:24,000 sheets (10 ft contours). Per zone component: thin-plate solve over the zone at 4 m with the surrounding LiDAR
fixed, pulled toward 1950s contours labelled on unchanged ground. Writes map3_realonly_delta_dm.tif (2 m, full DEM grid,
0 outside the zones) and m3/ check data."""
import numpy as np, json, cv2, rasterio, sys
from scipy import ndimage as ndi
import scipy.sparse as sp, pyamg
from affine import Affine
sys.path.insert(0, '.')
from m3_contours import contour_seg
FT = 1200 / 3937
DM = json.load(open('dem2m.json')); D = np.load('dem2m.npy', mmap_mode='r')
Zr = np.load('Z_real.npy')
extra = np.load(sys.argv[1]) if len(sys.argv) > 1 else None      # optional extra zones on the 4 m grid
if extra is not None: Zr = Zr | extra
lab, n = ndi.label(Zr, structure=np.ones((3, 3))); objs = ndi.find_objects(lab)
def tp_fill(val, mask, cval, cmask, wc=0.3):
    h, w = val.shape; Ui = -np.ones((h, w), np.int64); ui = np.nonzero(mask.ravel())[0]; Ui.ravel()[ui] = np.arange(len(ui))
    pr, pc = np.nonzero(ndi.binary_dilation(mask, iterations=1)); rows = []; cu = []; vu = []; rhs = np.zeros(len(pr))
    for dr, dc, coef in ((0, 0, -4.0), (-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0)):
        r2 = np.clip(pr + dr, 0, h - 1); c2 = np.clip(pc + dc, 0, w - 1); u = Ui[r2, c2]; isu = u >= 0
        rows.append(np.nonzero(isu)[0]); cu.append(u[isu]); vu.append(np.full(isu.sum(), coef)); rhs[~isu] += coef * val[r2[~isu], c2[~isu]]
    Au = sp.csr_matrix((np.concatenate(vu), (np.concatenate(rows), np.concatenate(cu))), shape=(len(pr), len(ui)))
    wv = np.where(cmask.ravel()[ui], wc, 0.0); cv_ = np.where(cmask.ravel()[ui], cval.ravel()[ui], 0.0)
    A = (Au.T @ Au + sp.diags(wv + 1e-9)).tocsr(); b = -Au.T @ rhs + wv * cv_
    ml = pyamg.smoothed_aggregation_solver(A, max_coarse=500)
    sol = ml.solve(b, x0=np.full(len(ui), np.median(val[~mask])), tol=1e-8, maxiter=400, accel='cg')
    out = val.copy(); out.ravel()[ui] = sol; return out
H4, W4 = Zr.shape; DEL = np.zeros((H4, W4), np.float32); D2 = np.zeros((DM['h'], DM['w']), np.int16); rep = []
M = 150
for k, s in enumerate(objs, 1):
    r0 = max(0, s[0].start - M); r1 = min(H4, s[0].stop + M); c0 = max(0, s[1].start - M); c1 = min(W4, s[1].stop + M)
    h, w = r1 - r0, c1 - c0
    L4 = np.asarray(D[r0 * 2:r1 * 2:2, c0 * 2:c1 * 2:2]).astype(np.float64) / 10
    nod = L4 < -1000; L4[nod] = np.median(L4[~nod])
    zk = lab[r0:r1, c0:c1] == k; Zd = ndi.binary_dilation(zk, iterations=2) & ~nod
    seg, ns = contour_seg(r0, c0, h, w)
    far = ~ndi.binary_dilation(Zr[r0:r1, c0:c1], iterations=5) & ~nod
    ids = seg.ravel(); zf = (L4 / FT).ravel(); o = far.ravel() & (ids > 0)
    order = np.argsort(ids[o]); sid = ids[o][order]; zv = zf[o][order]
    bnd = np.r_[0, np.nonzero(np.diff(sid))[0] + 1, len(sid)]; labv = np.full(ns + 1, np.nan)
    for a_, b_ in zip(bnd[:-1], bnd[1:]):
        if b_ - a_ < 8: continue
        q = np.round(zv[a_:b_] / 10) * 10; v, cnt = np.unique(q, return_counts=True)
        if cnt.max() / (b_ - a_) >= 0.5: labv[sid[a_]] = v[cnt.argmax()] * FT
    cons = (seg > 0) & Zd & np.isfinite(labv[seg]) & (ndi.distance_transform_edt(Zd) > 2)
    F0 = tp_fill(L4, Zd, np.zeros_like(L4), np.zeros_like(Zd))          # edges only
    # keep a contour's constraints only if it has 6+ px in the zone and agrees with itself (residual spread < 2 m)
    if cons.any():
        sg = seg[cons]; res = labv[sg] - F0[cons]
        o2 = np.argsort(sg); sg2 = sg[o2]; rs2 = res[o2]; b2 = np.r_[0, np.nonzero(np.diff(sg2))[0] + 1, len(sg2)]
        good = set()
        for a_, b_ in zip(b2[:-1], b2[1:]):
            if b_ - a_ >= 6 and np.std(rs2[a_:b_]) < 2.0 and abs(np.median(rs2[a_:b_])) < 15: good.add(sg2[a_])
        cons &= np.isin(seg, list(good)) if good else False
    F = tp_fill(L4, Zd, np.where(cons, labv[seg], 0), cons, wc=0.1) if cons.any() else F0
    F = np.where(Zd, ndi.gaussian_filter(F, 1.5), F)
    wz = np.clip(ndi.gaussian_filter(Zd.astype(np.float32), 1) * 1.5, 0, 1) * ndi.binary_dilation(Zd, iterations=2)
    dl = (wz * (F - L4)).astype(np.float32)
    DEL[r0:r1, c0:c1] = np.where(np.abs(dl) > np.abs(DEL[r0:r1, c0:c1]), dl, DEL[r0:r1, c0:c1])
    # 2 m: the rebuilt surface replaces the 2 m LiDAR inside the zone (so lane and pad detail goes too), feathered
    L2 = np.asarray(D[r0 * 2:r1 * 2, c0 * 2:c1 * 2]).astype(np.float32) / 10
    F2 = cv2.resize(F.astype(np.float32), (2 * w, 2 * h), interpolation=cv2.INTER_LINEAR)
    w2 = cv2.resize(wz.astype(np.float32), (2 * w, 2 * h), interpolation=cv2.INTER_LINEAR)
    d2 = np.where(L2 < -1000, 0, w2 * (F2 - L2)); d2 = np.round(d2 * 10).astype(np.int16)
    cur = D2[r0 * 2:r1 * 2, c0 * 2:c1 * 2]; D2[r0 * 2:r1 * 2, c0 * 2:c1 * 2] = np.where(np.abs(d2) > np.abs(cur), d2, cur)
    d_ = dl[Zd]; rep.append(dict(comp=k, km2=round(zk.sum() * 16e-6, 3), labelled_segments=int(np.isfinite(labv).sum()),
                                  constraint_px=int(cons.sum()), p5=round(float(np.percentile(d_, 5)), 1),
                                  p50=round(float(np.percentile(d_, 50)), 1), p95=round(float(np.percentile(d_, 95)), 1)))
    print(rep[-1], flush=True)
np.save('m3/realonly_delta4.npy', DEL)
json.dump(rep, open('m3/realonly_report.json', 'w'), indent=1)
# 2 m GeoTIFF, full DEM grid (zeros compress to almost nothing)
prof = dict(driver='GTiff', height=DM['h'], width=DM['w'], count=1, dtype='int16', crs='EPSG:26916',
            transform=Affine(2, 0, DM['x0'], 0, -2, DM['y1']), compress='deflate', predictor=2, tiled=True, nodata=None)
with rasterio.open('map3_realonly_delta_dm.tif', 'w', **prof) as ds: ds.write(D2, 1)
print('done; changed km2 (|d|>0.3 m): %.2f' % ((np.abs(DEL) > 0.3).sum() * 16e-6))
