"""Build the canon 1912 ground (map 2) from the Historic_Topo layers.

canon 1912 = I4 1912 ground (Ohio, with its south extension laid over it)
             -> Kentucky 1912 ground where it has values (Kentucky land in the riverworks window)
             -> 1912 riverworks: mode 1 force the target, mode 2 fill only (never cut)
real 1912  = the same without the riverworks step.

Usage: python make_ground_1912.py <Historic_Topo folder> <out folder>
All rasters: EPSG:26916, 2 m, int16 decimetres NAVD88, nodata -32768, on the LiDAR 2 m lattice.
"""
import sys, os, numpy as np, rasterio
from rasterio.windows import from_bounds

ND = -32768

def build(src):
    p = lambda *a: os.path.join(src, *a)
    with rasterio.open(p('1912_Ground_I4', 'I4_1912_cover.tif')) as c:
        prof = c.profile; tr = c.transform; H, W = c.height, c.width; cover = c.read(1)
    g = np.full((H, W), ND, np.int16)
    for name in ('I4_1912_ground_dm.tif', 'I4_1912_ground_south_ext_dm.tif'):   # extension laid over the base
        with rasterio.open(p('1912_Ground_I4', name)) as r:
            w = from_bounds(*r.bounds, transform=tr).round_offsets().round_lengths()
            a = r.read(1); sl = (slice(w.row_off, w.row_off + w.height), slice(w.col_off, w.col_off + w.width))
            g[sl] = np.where(a != ND, a, g[sl])
    with rasterio.open(p('KY_1912_Ground', 'ky1912_ground_dm.tif')) as r:
        w = from_bounds(*r.bounds, transform=tr).round_offsets().round_lengths()
        ky = r.read(1); win = (slice(w.row_off, w.row_off + w.height), slice(w.col_off, w.col_off + w.width))
    real = g.copy()
    real[win] = np.where(ky != ND, ky, real[win])
    canon = real.copy()
    with rasterio.open(p('Canon_Riverworks', 'map2_riverworks_target_dm.tif')) as r: tgt = r.read(1)
    with rasterio.open(p('Canon_Riverworks', 'map2_riverworks_mode.tif')) as r: mode = r.read(1)
    sub = canon[win]
    sub = np.where(mode == 1, tgt, sub)
    fill = (mode == 2) & (tgt != ND) & (sub != ND)
    sub = np.where(fill, np.maximum(sub, tgt), sub)
    canon[win] = sub
    return dict(profile=prof, transform=tr, cover=cover, real=real, canon=canon, win=win, ky=ky, mode=mode, tgt=tgt)

def write(path, arr, prof):
    pr = dict(prof); pr.update(dtype='int16', nodata=ND, compress='deflate', predictor=2, zlevel=9,
                               tiled=True, blockxsize=512, blockysize=512, count=1)
    with rasterio.open(path, 'w', **pr) as d: d.write(arr, 1)

if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    b = build(src)
    write(os.path.join(out, 'canon_1912_ground_dm.tif'), b['canon'], b['profile'])
    write(os.path.join(out, 'real_1912_ground_dm.tif'), b['real'], b['profile'])
