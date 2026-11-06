"""Relief renders of map 2 (alternate 1912) and map 3 (alternate 2026) over the riverworks window.
Map 3 = LiDAR, real-only works (zones v2) rebuilt from the 1950-55 sheets, canon interstates, riverworks, Kentucky terraces.
Map 2 = I4 1912 ground (LiDAR outside the survey), Kentucky works removed (ky1912.py), + 1912 riverworks."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, json, cv2, rasterio
from scipy import ndimage as ndi
DM = json.load(open('dem2m.json'))
d = np.load('rw_setup.npz'); o = np.load('rw_out.npz')
x0 = float(d['x0']); y1 = float(d['y1']); W = int(d['W']); H = int(d['H'])
L = d['L']; C = d['C']; wat = d['wat']; LV = d['LV']
r0 = int((DM['y1'] - y1) / 2); c0 = int((x0 - DM['x0']) / 2)
def pushpull(val, mask):
    v = np.where(mask, 0, val).astype(np.float64); w = (~mask).astype(np.float64); levels = []
    while min(v.shape) > 4 and (w == 0).any():
        levels.append((v, w))
        h2, w2 = (v.shape[0] + 1) // 2, (v.shape[1] + 1) // 2
        pv = np.zeros((h2 * 2, w2 * 2)); pw = np.zeros_like(pv); pv[:v.shape[0], :v.shape[1]] = v * w; pw[:w.shape[0], :w.shape[1]] = w
        sv = pv.reshape(h2, 2, w2, 2).sum((1, 3)); sw = pw.reshape(h2, 2, w2, 2).sum((1, 3))
        v = np.where(sw > 0, sv / np.maximum(sw, 1e-9), 0); w = np.minimum(sw, 1)
    for pv, pw in reversed(levels):
        up = cv2.resize(v.astype(np.float32), (pv.shape[1], pv.shape[0]), interpolation=cv2.INTER_LINEAR)
        v = pw * pv + (1 - pw) * up
    return np.where(mask, v, val).astype(np.float32)
# ---- map 3 composite
with rasterio.open('map3_realonly_delta_dm.tif') as ds:   # real-only works rebuilt from the 1950s sheets (m3_rebuild.py)
    G = L + ds.read(1, window=rasterio.windows.Window(c0, r0, W, H)).astype(np.float32) / 10
import os
if os.path.exists('m3/map3_smooth_base.npy'): G = np.load('m3/map3_smooth_base.npy')   # building/street imprint removed (m3_smooth.py)
with rasterio.open('map3_canon_interstates_delta_dm.tif') as ds:
    dl = ds.read(1, window=rasterio.windows.Window(c0, r0, W, H)).astype(np.float32) / 10
G = np.where(dl != 0, L + dl, G)
with rasterio.open('map3_riverworks_target_dm.tif') as ds: tz = ds.read(1).astype(np.float32) / 10
with rasterio.open('map3_riverworks_mode.tif') as ds: tm = ds.read(1)
G = np.where(tm == 1, tz, G); f = tm == 2; G[f] = np.fmax(G[f], tz[f])
G3_pre = G.copy()
with rasterio.open('map3_ky_terraces_target_dm.tif') as ds: kz = ds.read(1).astype(np.float32) / 10
with rasterio.open('map3_ky_terraces_mode.tif') as ds: km = ds.read(1)
G = np.where(km == 1, kz, G); f = km == 2; G[f] = np.fmax(G[f], kz[f])  # Kentucky terraces and levees
G3 = G
G2 = o['G2'].copy()
_K = np.load('ky1912_ground.npy'); _k = np.isfinite(_K) & (o['M2'] == 0)
G2[_k] = _K[_k]  # Kentucky 1912 ground (post-1912 works removed)
# ---- render
STOPS = [(135, (196, 214, 170)), (150, (170, 199, 140)), (165, (205, 210, 150)), (185, (222, 206, 150)),
         (210, (205, 175, 128)), (240, (180, 145, 110)), (270, (160, 130, 110)), (290, (235, 230, 225))]
def tint(z):
    zs = [s[0] for s in STOPS]; out = np.zeros(z.shape + (3,), np.float32)
    for k in range(3): out[..., k] = np.interp(z, zs, [s[1][k] for s in STOPS])
    return out
def shade(z, res):
    acc = np.zeros_like(z, np.float32)
    for az, wgt in ((315, 0.5), (270, 0.2), (0, 0.2), (225, 0.1)):
        gy, gx = np.gradient(z * 2.0, res); sl = np.arctan(np.hypot(gx, gy)); asp = np.arctan2(-gx, gy)
        a = np.radians(az); b = np.radians(45)
        acc += wgt * np.clip(np.sin(b) * np.cos(sl) + np.cos(b) * np.sin(sl) * np.cos(a - asp), 0, 1)
    return acc
import pickle
from shapely.geometry import shape as _shape
from shapely.ops import transform as _tf
from pyproj import Transformer as _Tr
from rasterio.features import rasterize as _ras
from affine import Affine as _Af
_T = _Tr.from_crs('EPSG:4326', 'EPSG:26916', always_xy=True).transform
_O, _Lk = pickle.load(open('canon_river.pkl', 'rb'))
_wf = json.load(open(_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/OSM/water.geojson")))['features']
_ohio, _other = [], []
for f in _wf:
    if f['geometry']['type'] in ('Polygon', 'MultiPolygon') and f['properties'].get('water') == 'river':
        g = _tf(_T, _shape(f['geometry'])); (_ohio if g.intersection(_O).area > 0.5 * g.area else _other).append(g)
_tr = _Af(2, 0, x0, 0, -2, y1)
_r = lambda gs: _ras([(g, 1) for g in gs], out_shape=(H, W), transform=_tr).astype(bool) if gs else np.zeros((H, W), bool)
CANON, OHIO_REAL, OTHER = _r([_O, _Lk]), _r(_ohio), _r(_other)
WATER3 = (CANON | OTHER) & ~(((o['M3'] > 0) | (km > 0)) & (G3 > 140))
WATER2 = (CANON | OHIO_REAL | OTHER) & ~((o['M2'] > 0) & (G2 > 140))
# canon riverbed (bathy/b1-b12: Corps surveys, Embankment deepening, Metro crossing sites)
from scipy.ndimage import map_coordinates as _mc
_B = np.load('../bathy/work/bed_canon4_r.npy')
_yy, _xx = np.mgrid[0:H, 0:W]
_bi = (4350000 - (y1 - (_yy + 0.5) * 2)) / 4 - 0.5; _bj = ((x0 + (_xx + 0.5) * 2) - 695000) / 4 - 0.5
BED3 = _mc(np.nan_to_num(_B, nan=-999), [_bi, _bj], order=1, mode='nearest').astype(np.float32); BED3[BED3 < 100] = np.nan
del _yy, _xx, _bi, _bj
POOL = (428.05 + 30.0) * 0.3048   # river level for the map: Cincinnati gauge (USGS 03255000, zero 428.05 ft NAVD88) at 30 ft
DEEP = [(0, (176, 214, 232)), (3, (128, 182, 216)), (7, (78, 140, 194)), (12, (44, 98, 160)), (20, (22, 56, 112))]
def render(G, name, title, water, bed=None):
    s = 2; wtr = water[::s, ::s]
    hasb = None
    if bed is not None:
        bb = bed[::s, ::s]; hasb = wtr & np.isfinite(bb)
        Z = G[::s, ::s].copy(); Z[hasb] = bb[hasb]
    else:
        Z = G[::s, ::s]
    res = 2.0 * s; sh = shade(Z, res)
    rgb = tint(Z) * (0.35 + 0.75 * sh)[..., None]
    rgb[wtr] = (150, 185, 215)
    if hasb is not None:
        dep = np.clip(POOL - Z, 0, 25); ds = [p[0] for p in DEEP]
        col = np.stack([np.interp(dep, ds, [p[1][k] for p in DEEP]) for k in range(3)], -1)
        col = col * (0.72 + 0.4 * sh)[..., None]
        rgb[hasb] = col[hasb]
    edge = wtr & ~ndi.binary_erosion(wtr); rgb[edge] = (95, 130, 170)
    bgr = np.clip(rgb[..., ::-1], 0, 255).astype(np.uint8)
    cv2.rectangle(bgr, (0, 0), (len(title) * 19 + 30, 52), (255, 255, 255), -1)
    cv2.putText(bgr, title, (14, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (40, 40, 40), 2, cv2.LINE_AA)
    cv2.imwrite(name, bgr, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return bgr.shape
print(render(G3, 'map3_relief.jpg', 'Map 3 - alternate 2026', WATER3, BED3))
print(render(G2, 'map2_relief.jpg', 'Map 2 - alternate 1912', WATER2))
# map3_window_ground.npy is the pre-terrace base used by ky_terr.py; saved without the terraces
np.save('map3_window_ground.npy', np.where(km > 0, G3_pre, G3).astype(np.float32))
# map 3 ground with the riverbed under the canon water (for delivery)
G3B = np.where(WATER3 & np.isfinite(BED3), BED3, G3).astype(np.float32); np.save('m3/map3_window_ground_bed.npy', G3B)
