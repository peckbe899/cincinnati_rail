"""Map 3 ground over the whole LiDAR extent for the profile/travel-time repo: full smoothed base (m3_smooth_full.py)
+ canon interstates + riverworks + Kentucky works (window grid, pasted at its offset). Writes 2 x 2 GeoTIFF tiles and a VRT."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, json, rasterio, os
from affine import Affine
DM = json.load(open('dem2m.json')); H, W = DM['h'], DM['w']; X0, Y1 = DM['x0'], DM['y1']
D = np.load('dem2m.npy', mmap_mode='r'); B = np.load('m3/full_base_dm.npy', mmap_mode='r')
d = np.load('rw_setup.npz'); x0 = float(d['x0']); y1 = float(d['y1']); h, w = d['L'].shape
wr0 = int((Y1 - y1) / 2); wc0 = int((x0 - X0) / 2)
works = []
for t, m in (('map3_riverworks_target_dm.tif', 'map3_riverworks_mode.tif'), ('map3_ky_terraces_target_dm.tif', 'map3_ky_terraces_mode.tif')):
    with rasterio.open(t) as ds: tz = ds.read(1)
    with rasterio.open(m) as ds: tm = ds.read(1)
    works.append((tz, tm))
IS = rasterio.open('map3_canon_interstates_delta_dm.tif')
os.makedirs(_ws.ext('/mnt/user-data/outputs/M3full'), exist_ok=True)
names = []
for qi, (ra, rb) in enumerate(((0, H // 2), (H // 2, H))):
    for qj, (ca, cb) in enumerate(((0, W // 2), (W // 2, W))):
        G = np.asarray(B[ra:rb, ca:cb]).astype(np.int32)
        raw = np.asarray(D[ra:rb, ca:cb]).astype(np.int32)
        dl = IS.read(1, window=rasterio.windows.Window(ca, ra, cb - ca, rb - ra)).astype(np.int32)
        G = np.where((dl != 0) & (raw > -30000), raw + dl, G)
        # paste the window works where they overlap this tile
        r0, r1 = max(ra, wr0), min(rb, wr0 + h); c0, c1 = max(ca, wc0), min(cb, wc0 + w)
        if r1 > r0 and c1 > c0:
            sub = G[r0 - ra:r1 - ra, c0 - ca:c1 - ca]
            for tz, tm in works:
                z = tz[r0 - wr0:r1 - wr0, c0 - wc0:c1 - wc0].astype(np.int32); m = tm[r0 - wr0:r1 - wr0, c0 - wc0:c1 - wc0]
                sub[:] = np.where(m == 1, z, np.where(m == 2, np.maximum(sub, z), sub))
        G = np.where(raw < -30000, -32768, G).astype(np.int16)
        name = f'map3_profile_dem_dm_r{qi}c{qj}.tif'; names.append(name)
        prof = dict(driver='GTiff', height=rb - ra, width=cb - ca, count=1, dtype='int16', crs='EPSG:26916',
                    transform=Affine(2, 0, X0 + 2 * ca, 0, -2, Y1 - 2 * ra), nodata=-32768, compress='deflate', predictor=2,
                    tiled=True, blockxsize=512, blockysize=512, zlevel=9)
        with rasterio.open(_ws.ext('/mnt/user-data/outputs/M3full/') + name, 'w', **prof) as ds:
            ds.write(G, 1); ds.update_tags(units='decimetres NAVD88', scale='0.1')
        print(name, os.path.getsize(_ws.ext('/mnt/user-data/outputs/M3full/') + name) / 1e6, 'MB', flush=True)
json.dump(names, open('m3/full_tiles.json', 'w'))
