"""Riverworks setup: window grids, canon river raster, Ohio-bank wall arc (Sedamsville to Belterra),
LMR channel, Mill Creek line, rail corridor. Saves rw_setup.npz + a check image."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, json, pickle, cv2, rasterio
from scipy import ndimage as ndi
from shapely.geometry import Point, LineString, mapping
from shapely.ops import substring
from rasterio.features import rasterize
from affine import Affine
from pyproj import Transformer
from pilot_common import hs
T = Transformer.from_crs('EPSG:4326', 'EPSG:26916', always_xy=True)
DM = json.load(open('dem2m.json')); DEM = np.load('dem2m.npy', mmap_mode='r')
B = _ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/OSM/")
ST = {'Sedamsville': (-84.56725, 39.08847), 'Belterra': (-84.41477, 39.05490), 'Sawyer': (-84.49506, 39.10431),
      'Penn': (-84.49970, 39.10245), 'CampWashN': (-84.5380, 39.1420)}
ST = {k: T.transform(*v) for k, v in ST.items()}
# window (2 m), snapped to the DEM grid
x0 = DM['x0'] + 2 * int((T.transform(-84.585, 39.10)[0] - DM['x0']) / 2)
x1 = DM['x0'] + 2 * int((T.transform(-84.400, 39.10)[0] - DM['x0']) / 2)
y1 = DM['y1'] - 2 * int((DM['y1'] - T.transform(-84.50, 39.150)[1]) / 2)
y0 = DM['y1'] - 2 * int((DM['y1'] - T.transform(-84.50, 39.040)[1]) / 2)
W = int((x1 - x0) / 2); H = int((y1 - y0) / 2)
tr = Affine(2, 0, x0, 0, -2, y1)
r0 = int((DM['y1'] - y1) / 2); c0 = int((x0 - DM['x0']) / 2)
L = np.asarray(DEM[r0:r0 + H, c0:c0 + W]).astype(np.float32) / 10
# I4 1912 ground over the window (nan outside the mosaic)
with rasterio.open('I4_1912_ground_dm.tif') as ds:
    a = ds.read(1, window=rasterio.windows.from_bounds(x0, y0, x1, y1, ds.transform), boundless=True, fill_value=-32768)
S12 = np.where(a > -30000, a / 10.0, np.nan).astype(np.float32)[:H, :W]
cov = rasterio.open('I4_1912_cover.tif')
cv_ = cov.read(1, window=rasterio.windows.from_bounds(x0, y0, x1, y1, cov.transform), boundless=True, fill_value=0)[:H, :W].astype(bool)
O, Lk = pickle.load(open('canon_river.pkl', 'rb'))
C = rasterize([(O, 1)], out_shape=(H, W), transform=tr).astype(bool)
# Ohio-bank arc of the canon outline between Sedamsville and Belterra, the side passing Penn
ring = LineString(O.exterior.coords)
pa, pb = ring.project(Point(ST['Sedamsville'])), ring.project(Point(ST['Belterra']))
lo_, hi_ = min(pa, pb), max(pa, pb)
arcA = substring(ring, lo_, hi_)
arcB = LineString(list(substring(ring, hi_, ring.length).coords) + list(substring(ring, 0, lo_).coords)[1:])
arc = arcA if arcA.distance(Point(ST['Penn'])) < arcB.distance(Point(ST['Penn'])) else arcB
print('wall arc length %.2f km' % (arc.length / 1e3))
def mask_of(geom, w=1):
    return rasterize([(geom, 1)], out_shape=(H, W), transform=tr, all_touched=True).astype(bool)
A = mask_of(arc)
# all canon boundary pixels, and which belong to the arc
bnd = C & ~ndi.binary_erosion(C)
# real water: flat and near the local canon water level
B50 = 50; lev = np.full((H // B50 + 1, W // B50 + 1), np.nan)
for i in range(0, H, B50):
    for j in range(0, W, B50):
        v = L[i:i + B50, j:j + B50][C[i:i + B50, j:j + B50]]
        if v.size > 400: lev[i // B50, j // B50] = np.percentile(v, 20)
m = np.isfinite(lev); idx = ndi.distance_transform_edt(~m, return_distances=False, return_indices=True); lev = lev[tuple(idx)]
LV = cv2.resize(ndi.gaussian_filter(lev, 1.5).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
gy, gx = np.gradient(ndi.gaussian_filter(L, 1), 2)
wat = (np.hypot(gx, gy) < 0.01) & (np.abs(L - LV) < 0.5)
lab, n = ndi.label(wat); sz = np.bincount(lab.ravel()); sz[0] = 0
wat = np.isin(lab, np.nonzero(sz > 3000)[0])
# LMR: real water outside the canon river, north of the Ohio near Lunken, reaching > 600 m from the canon bank
dC = ndi.distance_transform_edt(~C) * 2
out = wat & ~C
lab, n = ndi.label(out)
far = np.zeros(n + 1); np.maximum.at(far, lab.ravel(), dC.ravel())
lmr_e, lmr_n = T.transform(-84.432, 39.085)
cand = [k for k in range(1, n + 1) if far[k] > 600]
lmr = np.zeros((H, W), bool)
for k in cand:
    ys, xs = np.nonzero(lab == k)
    e = x0 + xs.mean() * 2; nn = y1 - ys.mean() * 2
    if np.hypot(e - lmr_e, nn - lmr_n) < 3000: lmr |= lab == k
print('LMR water px', lmr.sum())
# Mill Creek line (OSM)
wf = json.load(open(B + 'water.geojson'))['features']
mc = [LineString([T.transform(*p) for p in f['geometry']['coordinates']]) for f in wf
      if f['geometry']['type'] == 'LineString' and f['properties'].get('name') == 'Mill Creek']
MC = mask_of(__import__('shapely.ops', fromlist=['unary_union']).unary_union(mc)) if mc else np.zeros((H, W), bool)
# rail corridor in the Mill Creek valley: OSM active rail within the valley floor, south of Camp Washington N
rf = json.load(open(B + 'rail.geojson'))['features']
rl = [LineString([T.transform(*p) for p in f['geometry']['coordinates']]) for f in rf
      if f['properties'].get('railway') == 'rail' and len(f['geometry']['coordinates']) > 1]
R = rasterize([(g.buffer(12), 1) for g in rl], out_shape=(H, W), transform=tr).astype(bool)
np.savez_compressed('rw_setup.npz', L=L, S12=S12, cov=cv_, C=C, A=A, bnd=bnd, wat=wat, lmr=lmr, MC=MC, R=R, LV=LV,
                    x0=x0, y1=y1, W=W, H=H)
json.dump({k: list(v) for k, v in ST.items()}, open('rw_stations.json', 'w'))
json.dump(mapping(arc), open('rw_wall_arc.geojson', 'w'))
im = cv2.cvtColor(hs(L, 6, 2), cv2.COLOR_GRAY2BGR)
im[C] = (im[C] * 0.5 + np.array([120, 60, 0]) * 0.5).astype(np.uint8)
im[ndi.binary_dilation(A, iterations=3)] = (0, 0, 255); im[lmr] = (255, 0, 255); im[ndi.binary_dilation(MC, iterations=2)] = (255, 200, 0)
im[R & ~C] = (im[R & ~C] * 0.4 + np.array([0, 180, 0]) * 0.6).astype(np.uint8)
cv2.imwrite('rw_setup.jpg', cv2.resize(im, (W // 4, H // 4), interpolation=cv2.INTER_AREA))
print('window', W, H)
