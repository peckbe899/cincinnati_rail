"""Georeferenced GeoTIFFs (EPSG:26916, 0.15 m, JPEG + internal mask) for every frame of lph/tf_all.json, warped as the page
tiles (Lower Price Hill frames bent onto the 1922 plates by lph/tps.pkl; panel frames keep their own panel)."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import os, sys, json, numpy as np, cv2, rasterio
from rasterio.transform import from_origin
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'lph')
import tiles_n as T
from matplotlib.path import Path
OUT = _ws.ext('/mnt/user-data/outputs/Georef_1904/')
RES, CG = 0.15, 8
def vol(s): return 'v1' if s < 100 else ('v3' if s < 400 else ('v5' if s < 600 else 'v6'))
for f in sorted(T.TF, key=lambda f: (T.mosn.sheet_of(f), f)):
    s = T.mosn.sheet_of(f); suf = f[len(str(s)):]
    p = OUT + f'Sanborn_1904_{vol(s)}_sheet{s:03d}{suf}_EPSG26916.tif'
    if os.path.exists(p): continue
    fp = T.footprint(f)
    if len(fp) < 3: continue
    e0, n0 = fp.min(0) - 25; e1, n1 = fp.max(0) + 25
    W, H = int((e1 - e0) / RES), int((n1 - n0) / RES)
    nx, ny = W // CG + 2, H // CG + 2
    jj, ii = np.meshgrid(np.arange(nx) * CG, np.arange(ny) * CG)
    xc, yc = T.WARP(f, e0 + (jj + 0.5) * RES, n1 - (ii + 0.5) * RES)
    mx = cv2.resize(xc.astype(np.float32), (nx * CG, ny * CG), interpolation=cv2.INTER_LINEAR)[:H, :W]
    my = cv2.resize(yc.astype(np.float32), (nx * CG, ny * CG), interpolation=cv2.INTER_LINEAR)[:H, :W]
    im = T.IMG.get(s); m, d = T.pmask(s)
    xi = np.clip((mx / 8).astype(np.int32), 0, m.shape[1] - 1); yi = np.clip((my / 8).astype(np.int32), 0, m.shape[0] - 1)
    ok = (mx >= 0) & (my >= 0) & (mx < im.shape[1] - 1) & (my < im.shape[0] - 1) & m[yi, xi]
    if f in T.KEEP or f in T.DROP:
        q = np.c_[mx[::4, ::4].ravel(), my[::4, ::4].ravel()]; sel = np.ones(len(q), bool)
        for poly in T.KEEP.get(f, []): sel &= Path(np.array(poly.exterior.coords)).contains_points(q)
        for poly in T.DROP.get(f, []): sel &= ~Path(np.array(poly.exterior.coords)).contains_points(q)
        sel = sel.reshape(mx[::4, ::4].shape)
        ok &= cv2.resize(sel.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST).astype(bool)
    rgb = cv2.remap(im, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)[:, :, ::-1]
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(p, 'w', driver='GTiff', width=W, height=H, count=3, dtype='uint8', crs='EPSG:26916', transform=from_origin(e0, n1, RES, RES),
                           compress='JPEG', photometric='YCBCR', jpeg_quality=82, tiled=True, blockxsize=512, blockysize=512) as dd:
            for k in range(3): dd.write(rgb[..., k], k + 1)
            dd.write_mask(ok)
    print(f, W, H, round(os.path.getsize(p) / 1e6, 2), flush=True)
print('done', flush=True)
