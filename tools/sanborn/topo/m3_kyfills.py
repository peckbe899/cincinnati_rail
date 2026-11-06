"""Real riverfront fills on the Kentucky side since the 1950s (e.g. Dayton's raised riverfront): LiDAR above the
1955 contours by more than 3 m on labelled contour pixels within 400 m of the Kentucky bank, grown into zones.
Saves m3/kyfill_zones4.npy on the 4 m DEM grid (input to m3_rebuild.py)."""
import numpy as np, json, sys
from scipy import ndimage as ndi
sys.path.insert(0, '.')
from m3_contours import contour_seg
FT = 1200 / 3937
d = np.load('rw_setup.npz'); x0 = float(d['x0']); y1 = float(d['y1']); H, W = d['L'].shape
DM = json.load(open('dem2m.json')); D = np.load('dem2m.npy', mmap_mode='r')
KY = np.load('rw_KY.npy'); C = d['C']; CL = np.load('rw_CL.npy')
r0 = int((DM['y1'] - y1) / 4); c0 = int((x0 - DM['x0']) / 4); h, w = H // 2, W // 2
ky4 = KY[::2, ::2][:h, :w]; wt4 = (C | CL)[::2, ::2][:h, :w]
band = ky4 & ~wt4 & (ndi.distance_transform_edt(~wt4) * 4 < 400)
L4 = np.asarray(D[r0 * 2:(r0 + h) * 2:2, c0 * 2:(c0 + w) * 2:2]).astype(np.float64) / 10
seg, ns = contour_seg(r0, c0, h, w)
# label each contour by the mode of nearest-10 ft LiDAR on its pixels OUTSIDE the band (unchanged upland)
ids = seg.ravel(); zf = (L4 / FT).ravel(); o = (~band).ravel() & ky4.ravel() & (ids > 0)
order = np.argsort(ids[o]); sid = ids[o][order]; zv = zf[o][order]
bnd = np.r_[0, np.nonzero(np.diff(sid))[0] + 1, len(sid)]; labv = np.full(ns + 1, np.nan)
for a_, b_ in zip(bnd[:-1], bnd[1:]):
    if b_ - a_ < 8: continue
    q = np.round(zv[a_:b_] / 10) * 10; v, cnt = np.unique(q, return_counts=True)
    if cnt.max() / (b_ - a_) >= 0.5: labv[sid[a_]] = v[cnt.argmax()] * FT
inb = band & (seg > 0) & np.isfinite(labv[seg])
res = np.where(inb, L4 - labv[seg], 0)
hit = inb & (res > 3.0)
print('labelled contour px in band', inb.sum(), 'above by >3 m', hit.sum())
# grow: low-slope raised ground connected to the hits, inside the band
gy, gx = np.gradient(ndi.gaussian_filter(L4, 1), 4)
grow = ndi.binary_dilation(hit, iterations=6) & band
lab, n = ndi.label(grow); sz = np.bincount(lab.ravel()); sz[0] = 0
keep = np.isin(lab, np.nonzero(sz * 16 > 5000)[0])
keep = ndi.binary_closing(keep, iterations=3) & band
print('fill zones: %d, %.3f km2' % (ndi.label(keep)[1], keep.sum() * 16e-6))
Zx = np.zeros((DM['h'] // 2, DM['w'] // 2), bool); Zx[r0:r0 + h, c0:c0 + w] = keep
np.save('m3/kyfill_zones4.npy', Zx)
lab2, n2 = ndi.label(keep)
for k in range(1, n2 + 1):
    m = lab2 == k; ys, xs = np.nonzero(m)
    e = x0 + (xs.mean() * 2 + 1) * 2; nn = y1 - (ys.mean() * 2 + 1) * 2
    from pyproj import Transformer
    lo, la = Transformer.from_crs('EPSG:26916', 'EPSG:4326', always_xy=True).transform(e, nn)
    print(k, '%.3f km2' % (m.sum() * 16e-6), 'at %.4f, %.4f' % (lo, la), 'median LiDAR above 1955: %.1f m' % np.median(res[m & hit]) if (m & hit).any() else '')
