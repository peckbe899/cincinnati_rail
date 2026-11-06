"""Riverworks for maps 2 and 3: Ohio Embankment (70 ft wall, quai bas, quai haut, landward slope), Lunken levees (83 ft)
plus a 1 m airfield lift, Mill Creek deck (sloped 70 ft -> 160 m, lateral slopes), lower Mill Creek culvert (map 2).
Each work returns a target z and a mode on its own crop: 1 = force (deck/quay surfaces), 2 = fill only (never cuts)."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, json, rasterio
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
from shapely.geometry import shape, Point, LineString
from shapely.ops import substring, unary_union
from rasterio.features import rasterize
from affine import Affine
from pyproj import Transformer
T = Transformer.from_crs('EPSG:4326', 'EPSG:26916', always_xy=True)
FT = 1200 / 3937; Z0 = 428.05                       # Cincinnati gauge zero, ft NAVD88 (NWS CCNO1)
g2m = lambda g: (Z0 + g) * FT
WALL, LUNK = g2m(70), g2m(83)                       # 151.81, 155.77 m
QBAS, QBW, QHW, SLOPE, ZTOP = 142.0, 12.0, 52.0, 0.035, 160.0
d = np.load('rw_setup.npz'); L = d['L']; S12 = d['S12']; C = d['C']; bnd = d['bnd']; wat = d['wat']; R = d['R']
x0 = float(d['x0']); y1 = float(d['y1']); W = int(d['W']); H = int(d['H']); tr = Affine(2, 0, x0, 0, -2, y1)
ST = {k: tuple(v) for k, v in json.load(open('rw_stations.json')).items()}
arc = shape(json.load(open('rw_wall_arc.geojson')))
B = _ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/OSM/")
wf = json.load(open(B + 'water.geojson'))['features']
def lines(name):
    return unary_union([LineString([T.transform(*p) for p in f['geometry']['coordinates']]) for f in wf
                        if f['geometry']['type'] == 'LineString' and f['properties'].get('name') == name])
LMRl, MCl = lines('Little Miami River'), lines('Mill Creek')
class Ctx:
    def __init__(self, bounds, pad):
        bx0, by0, bx1, by1 = bounds
        c0 = max(0, int((bx0 - pad - x0) / 2)); c1 = min(W, int((bx1 + pad - x0) / 2) + 1)
        r0 = max(0, int((y1 - (by1 + pad)) / 2)); r1 = min(H, int((y1 - (by0 - pad)) / 2) + 1)
        self.sl = (slice(r0, r1), slice(c0, c1)); self.H = r1 - r0; self.W = c1 - c0
        self.tr = Affine(2, 0, x0 + 2 * c0, 0, -2, y1 - 2 * r0); self.ox = x0 + 2 * c0; self.oy = y1 - 2 * r0
    def ras(self, geoms, at=True):
        return rasterize([(g, 1) for g in geoms], out_shape=(self.H, self.W), transform=self.tr, all_touched=at).astype(bool)
    def pt(self, i, j): return Point(self.ox + 2 * j + 1, self.oy - 2 * i - 1)
def edt(mask, ind=False):
    if ind:
        dd, ii = ndi.distance_transform_edt(~mask, return_indices=True); return (dd * 2).astype(np.float32), ii.astype(np.int32)
    return (ndi.distance_transform_edt(~mask) * 2).astype(np.float32)
def blank(c): return np.full((c.H, c.W), np.nan, np.float32), np.zeros((c.H, c.W), np.uint8)
# ---------------------------------------------------------------- Embankment
def embankment(arcgeom, base):
    c = Ctx(arcgeom.bounds, 700); b = base[c.sl]; Cc = C[c.sl]
    lmr = c.ras([LMRl.buffer(35)])
    Aa = c.ras([arcgeom]) & ~lmr
    dA = edt(Aa); dO = edt(bnd[c.sl] & ~ndi.binary_dilation(c.ras([arcgeom]), iterations=4))
    side = ~Cc & (dA < dO) & (dA < 600) & ~lmr
    recl = side & wat[c.sl] & (dA < 250)
    quai = side & (dA < QBW)
    flat = side & ((dA < QHW) | recl) & ~quai
    z, mode = blank(c)
    q = quai & (b < WALL); z[q] = QBAS; mode[q] = 1
    z[flat] = WALL; mode[flat] = 2
    df = edt(flat | quai)
    zs = WALL - SLOPE * df
    sl = side & ~flat & ~quai & (zs > b)
    z[sl] = zs[sl]; mode[sl] = 2
    return c, z, mode, recl.sum()
# ---------------------------------------------------------------- Lunken
def lunken(base):
    e, n = T.transform(-84.418, 39.102); c = Ctx((e - 2800, n - 2800, e + 2800, n + 2800), 0); b = base[c.sl]; Lc = L[c.sl]; Cc = C[c.sl]
    lmr = c.ras([LMRl.buffer(35)])
    rid = (Lc - ndi.grey_opening(Lc, size=(25, 25)) > 2.5) & (Lc > 148)
    lab, nn = ndi.label(rid); sz = np.bincount(lab.ravel()); sz[0] = 0
    ring = lab == np.argmax(sz)
    sk = skeletonize(ndi.binary_closing(ring, iterations=3))
    bf = LMRl.buffer(55); off = unary_union([p.exterior for p in getattr(bf, 'geoms', [bf])])
    eb = c.ras([off]) & ~ndi.binary_dilation(ring, iterations=60) & (Lc < LUNK - 0.5) & ~Cc
    dl = edt(sk | eb)
    zz = LUNK - np.maximum(0, dl - 3) / 3.0
    z, mode = blank(c)
    m = (zz > b) & (dl < 40) & ~Cc & ~lmr
    z[m] = zz[m]; mode[m] = 2
    gy, gx = np.gradient(ndi.gaussian_filter(Lc, 2), 2)
    low = (Lc > 142) & (Lc < 147.5) & (np.hypot(gx, gy) < 0.02) & ~Cc & ~lmr & ~ndi.binary_dilation(ring, iterations=10)
    lab2, _ = ndi.label(low); ra, ca = [int(v) for v in ((c.oy - T.transform(-84.418, 39.105)[1]) / 2, (T.transform(-84.418, 39.105)[0] - c.ox) / 2)]
    k2 = lab2[ra - 30:ra + 30, ca - 30:ca + 30]; k2 = np.bincount(k2[k2 > 0]).argmax() if (k2 > 0).any() else 0
    inside = (lab2 == k2) & (k2 > 0)
    z[inside] = np.fmax(z[inside], b[inside] + 1.0); mode[inside & (mode == 0)] = 2
    return c, z, mode, ring.sum(), inside.sum(), eb.sum()
# ---------------------------------------------------------------- Mill Creek deck
mouth = arc.interpolate(arc.project(Point(T.transform(-84.5472, 39.0975))))
axis = LineString([(mouth.x, mouth.y)] + [T.transform(*p) for p in
                  [(-84.5455, 39.1020), (-84.5420, 39.1100), (-84.5435, 39.1210), (-84.5420, 39.1300), (-84.5380, 39.1420)]])
S = axis.length
def deck(base):
    c = Ctx(axis.bounds, 900); b = base[c.sl]; Cc = C[c.sl]
    near = edt(c.ras([axis])) < 600
    corr0 = R[c.sl] & near
    ys, xs = np.nonzero(corr0); k = slice(None, None, 5)
    sv = np.array([axis.project(c.pt(i, j)) for i, j in zip(ys[k], xs[k])])
    keep = np.zeros_like(corr0); ok = (sv > 1) & (sv < S - 1); keep[ys[k][ok], xs[k][ok]] = True
    corr = ndi.binary_fill_holes(ndi.binary_closing(ndi.binary_dilation(keep, iterations=14), iterations=40)) & ~Cc
    corr |= ndi.binary_dilation(c.ras([MCl]), iterations=8) & ndi.binary_dilation(corr, iterations=60)
    corr = ndi.binary_fill_holes(ndi.binary_closing(corr, iterations=10)) & ~Cc
    ci, cj = np.nonzero(corr); stp = max(1, len(ci) // 60000)
    zs = np.array([WALL + (ZTOP - WALL) * min(1.0, max(0.0, axis.project(c.pt(i, j)) / S)) for i, j in zip(ci[::stp], cj[::stp])], np.float32)
    zc = np.full((c.H, c.W), np.nan, np.float32); zc[ci[::stp], cj[::stp]] = zs
    _, ii = edt(np.isfinite(zc), True); zc = zc[ii[0], ii[1]]
    z, mode = blank(c)
    z[corr] = zc[corr]; mode[corr] = 1
    dcorr, ic = edt(corr, True)
    zn = zc[ic[0], ic[1]] - SLOPE * dcorr
    sl = ~corr & ~Cc & (zn > b) & (dcorr < 400)
    z[sl] = zn[sl]; mode[sl] = 2
    return c, z, mode, corr
# ---------------------------------------------------------------- lower Mill Creek culvert (1903-08), map 2
def culvert(base):
    seg = MCl.intersection(Point(mouth.x, mouth.y).buffer(3200))
    c = Ctx(seg.bounds, 300); b = base[c.sl]
    nlim = T.transform(-84.54, 39.120)[1]; rlim = max(0, int((c.oy - nlim) / 2))
    ch = c.ras([seg.buffer(18)]); ch[:rlim] = False; ch &= ~C[c.sl]
    ringm = ~ndi.binary_dilation(ch, iterations=15) & ndi.binary_dilation(ch, iterations=40) & np.isfinite(b)
    _, ii = edt(ringm, True); flv = ndi.median_filter(np.where(ringm, b, np.nan), size=1)[ii[0], ii[1]]
    z, mode = blank(c)
    m = ch & (flv > b); z[m] = flv[m]; mode[m] = 2
    return c, z, mode
def combine(base, parts):
    out = base.copy(); zt = np.full((H, W), np.nan, np.float32); md = np.zeros((H, W), np.uint8)
    for c, z, m in parts:
        o, Z, M = out[c.sl], zt[c.sl], md[c.sl]
        f = m == 1; o[f] = z[f]; Z[f] = z[f]; M[f] = 1
        fi = (m == 2) & (M != 1); o[fi] = np.fmax(o[fi], z[fi]); Z[fi] = np.fmax(Z[fi], z[fi]); M[fi & (M == 0)] = 2
    return out, zt, md
# ---------------------------------------------------------------- build
base3 = L
ce, e3, m3e, nrec = embankment(arc, base3)
cl, l3, m3l, nring, nin, neb = lunken(base3)
cd, dk, m3d, corr = deck(base3)
G3, Z3, M3 = combine(base3, [(ce, e3, m3e), (cl, l3, m3l), (cd, dk, m3d)])
print('map 3: embankment %.2f km2 (reclaimed %.2f km2); Lunken %.2f km2 (ring px %d, east-bank px %d, airfield px %d); deck corridor %.2f km2, deck slopes %.2f km2'
      % ((m3e > 0).sum() * 4e-6, nrec * 4e-6, (m3l > 0).sum() * 4e-6, nring, neb, nin, corr.sum() * 4e-6, (m3d == 2).sum() * 4e-6))
base2 = np.where(np.isfinite(S12), S12, L).astype(np.float32)
pa = arc.project(mouth); pb = arc.project(Point(ST['Sawyer'])); arc2 = substring(arc, min(pa, pb), max(pa, pb))
c2e, e2, m2e, nrec2 = embankment(arc2, base2)
c2c, cu2, m2c = culvert(base2)
G2, Z2, M2 = combine(base2, [(c2e, e2, m2e), (c2c, cu2, m2c)])
print('map 2: embankment arc %.2f km, %.2f km2; culvert %.3f km2' % (arc2.length / 1e3, (m2e > 0).sum() * 4e-6, (m2c > 0).sum() * 4e-6))
cfull = np.zeros((H, W), bool); cfull[cd.sl] = corr
np.savez_compressed('rw_out.npz', G3=G3, M3=M3, G2=G2, M2=M2, corr=cfull)
json.dump({'wall_m': WALL, 'lunken_m': LUNK, 'quai_bas_m': QBAS, 'quai_bas_w': QBW, 'quai_haut_reach': QHW, 'slope': SLOPE,
           'deck_top_m': ZTOP, 'deck_axis_len_m': S, 'axis_utm': list(axis.coords), 'arc2_km': arc2.length / 1e3},
          open('rw_params.json', 'w'), indent=1)
def save(name, arr, dtype, nod):
    with rasterio.open(name, 'w', driver='GTiff', height=H, width=W, count=1, dtype=dtype, crs='EPSG:26916', transform=tr,
                       compress='deflate', predictor=2 if dtype == 'int16' else 1, tiled=True, nodata=nod) as ds: ds.write(arr, 1)
for k, Z, M, G, base in (('map3', Z3, M3, G3, base3), ('map2', Z2, M2, G2, base2)):
    save(f'{k}_riverworks_target_dm.tif', np.where(np.isfinite(Z), np.round(Z * 10), -32768).astype(np.int16), 'int16', -32768)
    save(f'{k}_riverworks_mode.tif', M, 'uint8', 0)
    save(f'{k}_riverworks_delta_dm.tif', np.where(M > 0, np.round((G - base) * 10), 0).astype(np.int16), 'int16', None)
print('saved')
