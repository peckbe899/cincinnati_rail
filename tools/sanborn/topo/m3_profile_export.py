"""Export the map 3 ground (2026 canon) over the riverworks window as one raster for the travel-time / profile repo.
Ground = smoothed base (LiDAR + real-only rebuild, imprint removed) + canon interstates + riverworks + Kentucky works."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, json, rasterio
from affine import Affine
d = np.load('rw_setup.npz'); L = d['L']; x0 = float(d['x0']); y1 = float(d['y1']); H, W = L.shape
DM = json.load(open('dem2m.json')); r0 = int((DM['y1'] - y1) / 2); c0 = int((x0 - DM['x0']) / 2)
win = rasterio.windows.Window(c0, r0, W, H)
G = np.load('m3/map3_smooth_base.npy')
with rasterio.open('map3_canon_interstates_delta_dm.tif') as ds: dl = ds.read(1, window=win).astype(np.float32) / 10
G = np.where(dl != 0, L + dl, G)
for t, m in (('map3_riverworks_target_dm.tif', 'map3_riverworks_mode.tif'), ('map3_ky_terraces_target_dm.tif', 'map3_ky_terraces_mode.tif')):
    with rasterio.open(t) as ds: tz = ds.read(1).astype(np.float32) / 10
    with rasterio.open(m) as ds: tm = ds.read(1)
    G = np.where(tm == 1, tz, G); f = tm == 2; G[f] = np.fmax(G[f], tz[f])
assert np.isfinite(G).all() and G.min() > 100 and G.max() < 400
out = _ws.ext('/mnt/user-data/outputs/M3/map3_profile_dem_dm.tif')
prof = dict(driver='GTiff', height=H, width=W, count=1, dtype='int16', crs='EPSG:26916', transform=Affine(2, 0, x0, 0, -2, y1),
            nodata=-32768, compress='deflate', predictor=2, tiled=True, blockxsize=512, blockysize=512, zlevel=9)
with rasterio.open(out, 'w', **prof) as ds:
    ds.write(np.round(G * 10).astype(np.int16), 1)
    ds.update_tags(units='decimetres NAVD88', scale='0.1', content='Map 3 (alternate 2026) ground: LiDAR, real-only works rebuilt from 1950s USGS sheets, building/street imprint removed, canon interstates, Embankment, Mill Creek deck, Lunken levees, Kentucky terraces')
# border check against the real LiDAR (what the lines read outside)
with rasterio.open('map3_realonly_delta_dm.tif') as ds: ro = ds.read(1, window=win).astype(np.float32) / 10
e = np.zeros((H, W), bool); e[:1] = e[-1:] = True; e[:, :1] = e[:, -1:] = True
dz = (G - L)[e]; dz2 = (G - (np.where(dl != 0, L + dl, L + ro)))[e]
print('border vs raw LiDAR: share within 0.1 m %.1f%%, max |d| %.1f m' % (100 * np.mean(np.abs(dz) <= 0.1), np.abs(dz).max()))
print('border vs LiDAR + real-only rebuild + canon interstates: share within 0.1 m %.1f%%, max |d| %.1f m' % (100 * np.mean(np.abs(dz2) <= 0.1), np.abs(dz2).max()))
lon_lat = __import__('pyproj').Transformer.from_crs('EPSG:26916', 'EPSG:4326', always_xy=True)
print('bounds UTM', x0, y1 - 2 * H, x0 + 2 * W, y1, ' lon/lat', [round(v, 4) for v in lon_lat.transform(x0, y1 - 2 * H)], [round(v, 4) for v in lon_lat.transform(x0 + 2 * W, y1)])
