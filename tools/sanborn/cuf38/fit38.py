try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Plate 38 (1922, Clifton) georeference from Ben's raw scan: picked crossings (sbg/picks22/s22-38_*.json) matched to the same crossings in
# OpenStreetMap; Ben's GeoTIFF only seeds the match (png -> tif pixels by SIFT, cuf38/png2tif.json). Streets moved or widened since 1922
# drop out as outliers. Models compared by leave-one-out error: affine, quadratic, affine + smoothing thin-plate spline.
# Writes cuf38/matches38.json, cuf38/fit38_report.json, cuf38/fwd38.pkl (px -> world) and cuf38/model38.npz (world -> px grid, 2 m).
import json, sys, pickle, collections, glob, numpy as np
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'sbg'); sys.path.insert(0, _ws.CODE + 'cuf')
from names import key, base
from shapely.geometry import shape, Point
from shapely.ops import unary_union, nearest_points
from scipy.interpolate import RBFInterpolator, griddata
from pyproj import Transformer
W3857 = Transformer.from_crs(3857, 26916, always_xy=True)
G = json.load(open(SP + 'cuf38/png2tif.json'))
def poly(x, y, deg):
    x = np.asarray(x, float) / 10000; y = np.asarray(y, float) / 10000
    return np.stack([x ** i * y ** j for i in range(deg + 1) for j in range(deg + 1 - i)], -1)
def seed(x, y):                      # png px -> world through Ben's GeoTIFF
    X = poly(x, y, G['deg']); tx = X @ np.array(G['cx']); ty = X @ np.array(G['cy']); a = G['tif_transform']
    return W3857.transform(a[0] * (tx + 0.5) + a[1] * (ty + 0.5) + a[2], a[3] * (tx + 0.5) + a[4] * (ty + 0.5) + a[5])
# ---- picks
P = []
for fn in sorted(glob.glob(SP + 'sbg/picks22/s22-38_*.json')):
    for p in json.load(open(fn))['intersections']: P.append(dict(p, part=fn[-6]))
M = []
for p in P:
    if '?' in p['a'] + p['b']: continue
    k = tuple(sorted((key(p['a']), key(p['b']))))
    q = next((m for m in M if m['k'] == k and np.hypot(m['x'] - p['x'], m['y'] - p['y']) < 60), None)
    if q: q['xs'].append(p['x']); q['ys'].append(p['y']); q['x'] = float(np.mean(q['xs'])); q['y'] = float(np.mean(q['ys']))
    else: M.append(dict(k=k, a=p['a'], b=p['b'], x=float(p['x']), y=float(p['y']), xs=[p['x']], ys=[p['y']]))
spread = [float(np.hypot(np.ptp(m['xs']), np.ptp(m['ys']))) for m in M if len(m['xs']) > 1]
print('picks', len(P), 'crossings', len(M), 'read twice', len(spread), 'median spread px', round(float(np.median(spread)), 1) if spread else '-')
# ---- OSM
OL = collections.defaultdict(list)
for fn in ('lph/osm_north.geojson', 'basin/osm_basin.geojson', 'lph/osm_east.geojson'):
    for f in json.load(open(SP + fn))['features']:
        nm = f['properties'].get('name')
        if nm and f['geometry']['type'] == 'LineString':
            g = shape(f['geometry']); OL[key(nm)].append(g); OL['B:' + base(key(nm))].append(g)
U = {k: unary_union(v) for k, v in OL.items()}
def lines(k): return U.get(k) or U.get('B:' + base(k))
for m in M:
    E, N = seed(m['x'], m['y']); m['seed'] = (float(E), float(N)); m['osm'] = None
    la, lb = lines(m['k'][0]), lines(m['k'][1])
    if la is None or lb is None: m['why'] = 'not in OSM: ' + ', '.join(n for n, l in zip(m['k'], (la, lb)) if l is None); continue
    x = la.intersection(lb); pts = [g for g in getattr(x, 'geoms', [x]) if g.geom_type == 'Point'] if not x.is_empty else []
    if not pts:
        a, b = nearest_points(la, lb)
        if a.distance(b) < 3: pts = [Point((a.x + b.x) / 2, (a.y + b.y) / 2)]
    pts = [g for g in pts if g.distance(Point(E, N)) < 45]
    if not pts: m['why'] = 'no OSM crossing within 45 m of the seed'; continue
    g = min(pts, key=lambda g: g.distance(Point(E, N))); m['osm'] = (g.x, g.y)
K = [m for m in M if m['osm']]
print('matched to OSM', len(K))
X = np.array([[m['x'], m['y']] for m in K]); O = np.array([m['osm'] for m in K]); S = np.array([m['seed'] for m in K])
print('seed (Ben GeoTIFF) vs OSM: rms', round(float(np.sqrt(np.mean(np.sum((S - O) ** 2, 1)))), 1), 'median', round(float(np.median(np.hypot(*(S - O).T))), 1))
# ---- models
def fit_poly(Xs, Os, deg):
    A = poly(Xs[:, 0], Xs[:, 1], deg); ce, *_ = np.linalg.lstsq(A, Os[:, 0], rcond=None); cn, *_ = np.linalg.lstsq(A, Os[:, 1], rcond=None)
    return lambda q: np.stack([poly(q[:, 0], q[:, 1], deg) @ ce, poly(q[:, 0], q[:, 1], deg) @ cn], 1)
def fit_tps(Xs, Os, sm):
    base_ = fit_poly(Xs, Os, 1); R = Os - base_(Xs)
    rb = RBFInterpolator(Xs / 1000, R, kernel='thin_plate_spline', smoothing=sm, degree=1)
    return lambda q: base_(q) + rb(q / 1000)
MODELS = {'affine': lambda Xs, Os: fit_poly(Xs, Os, 1), 'quadratic': lambda Xs, Os: fit_poly(Xs, Os, 2)}
for sm in (0.3, 1, 3, 10, 30, 100): MODELS[f'tps{sm}'] = (lambda s: lambda Xs, Os: fit_tps(Xs, Os, s))(sm)
def loo(name, keep):
    e = np.zeros(len(K)); idx = np.where(keep)[0]
    for i in idx:
        j = keep.copy(); j[i] = False; f = MODELS[name](X[j], O[j]); e[i] = np.hypot(*(f(X[i:i + 1])[0] - O[i]))
    return e
# streets realigned since 1922 (their crossings disagree with their neighbours on both plates): left out by name
MOVED = ('Dixmyth', 'Glenmary', 'Lafayette')       # Dixmyth: both plates 35-41 m off today's; Glenmary: all five crossings off; Lafayette: its two crossings disagree with each other and with the 1912 survey corner          # realigned since 1922: both plates put Dixmyth/Whitfield 35-41 m from today's
keep = np.array([not any(w in m['a'] + m['b'] for w in MOVED) for m in K]); dropped = [(m['a'] + ' / ' + m['b'], 'moved street') for m in K if any(w in m['a'] + m['b'] for w in MOVED)]
for it in range(25):                       # drop a control the smooth field cannot reach (a moved street); edge distortion shared by neighbours stays
    f_ = MODELS['tps1'](X[keep], O[keep]); r_ = np.hypot(*(f_(X) - O).T); w = int(np.argmax(np.where(keep, r_, -1)))
    if r_[w] > 6.0: keep[w] = False; dropped.append((K[w]['a'] + ' / ' + K[w]['b'], round(float(r_[w]), 1)))
    else: break
print('dropped as moved/widened:', dropped)
rep = {}
for name in MODELS:
    e = loo(name, keep)[keep]; rep[name] = (float(np.sqrt(np.mean(e ** 2))), float(e.max()))
    print(f'{name:10s} leave-one-out rms {rep[name][0]:5.2f} max {rep[name][1]:5.2f}')
best = min(rep, key=lambda k: rep[k][0]); f = MODELS[best](X[keep], O[keep])
res = np.hypot(*(f(X) - O).T)
print('chosen', best, 'fit rms', round(float(np.sqrt(np.mean(res[keep] ** 2))), 2))
for m, r, k_ in zip(K, res, keep): m['res'] = float(r); m['used'] = bool(k_)
json.dump(M, open(SP + 'cuf38/matches38.json', 'w'), indent=1)
json.dump(dict(model=best, controls=int(keep.sum()), matched=len(K), crossings=len(M), dropped=dropped, loo=rep,
               seed_rms=float(np.sqrt(np.mean(np.sum((S - O) ** 2, 1))))), open(SP + 'cuf38/fit38_report.json', 'w'), indent=1)
pickle.dump(dict(model=best, X=X[keep], O=O[keep]), open(SP + 'cuf38/fwd38.pkl', 'wb'))
# ---- inverse grid world -> png px (forward on a 16 px grid, then linear interpolation on a 2 m world grid)
gx, gy = np.meshgrid(np.arange(0, 10748 + 16, 16.0), np.arange(0, 6719 + 16, 16.0)); Q = np.c_[gx.ravel(), gy.ravel()]
Wd = f(Q); E0, N0 = np.floor(Wd.min(0) / 2) * 2 - 10; E1, N1 = np.ceil(Wd.max(0) / 2) * 2 + 10; step = 2.0
ge, gn = np.meshgrid(np.arange(E0, E1, step), np.arange(N1, N0, -step))
px = griddata(Wd, Q[:, 0], (ge, gn), method='linear'); py = griddata(Wd, Q[:, 1], (ge, gn), method='linear')
px = np.where(np.isnan(px), -1e6, px).astype(np.float32); py = np.where(np.isnan(py), -1e6, py).astype(np.float32)
np.savez_compressed(SP + 'cuf38/model38.npz', E0=E0, N1=N1, step=step, px=px, py=py)
print('inverse grid', px.shape, 'world box', [E0, N0, E1, N1])
