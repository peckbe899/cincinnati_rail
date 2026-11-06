try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# 2026-10-22 (Ben: 1922 and 1904 disagree in Northside / Camp Washington, Colerain especially): the vol. 1 halves there (22-16L/R,
# 34L/R, 35L, 37L/R) had been placed with one affine each (lph/tf22_cw.json, 10u.4). Same fit as cufp/fit.py, seeded from that affine,
# on the crossings already picked (sbg/picks22/s22-<half>.json). Outputs in cuf_cw/<half>/.
#   python3 cuf_cw/fit.py 37R
# --- cufp/fit.py header follows ---
# Step 3 for a 1922 plate N (generalised from cuf38/fit38.py, 2026-10-21): picked crossings (sbg/picks22/s22-N_*.json) matched to the
# same crossings in OpenStreetMap; Ben's GeoTIFF only seeds the match (cufp/N/png2tif.json). Without a GeoTIFF (plate 70: over the 400 MB
# transfer limit) the seed is a RANSAC affine on crossings whose name pair is unique on the plate and in OSM.
# Streets moved or widened since 1922 drop out (named in MOVED, then the tps1 > 6 m test). Models compared by leave-one-out error.
# Writes cufp/N/matches.json, report.json, fwd.pkl (px -> world), model.npz (world -> px grid, 2 m).
#   python3 cufp/fit.py N
import json, sys, os, pickle, collections, glob, numpy as np
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'sbg'); sys.path.insert(0, _ws.CODE + 'cuf')
from names import key, base
from shapely.geometry import shape, Point
from shapely.ops import unary_union, nearest_points
from scipy.interpolate import RBFInterpolator, griddata
from pyproj import Transformer
N = sys.argv[1]; D = SP + f'cuf_cw/{N}/'; os.makedirs(D, exist_ok=True)
CFG = json.load(open(SP + 'cuf_cw/config.json')).get(N, json.load(open(SP + 'cuf_cw/config.json')).get('all', {}))
MOVED = tuple(CFG.get('moved', []))              # streets realigned since 1922, left out by name
FORCE_OUT = set(tuple(sorted(p)) for p in CFG.get('force_out', []))
W3857 = Transformer.from_crs(3857, 26916, always_xy=True)
W0, H0 = json.load(open(D + 'size.json')) if os.path.exists(D + 'size.json') else (None, None)
def poly(x, y, deg):
    x = np.asarray(x, float) / 10000; y = np.asarray(y, float) / 10000
    return np.stack([x ** i * y ** j for i in range(deg + 1) for j in range(deg + 1 - i)], -1)
G = json.load(open(D + 'png2tif.json')) if os.path.exists(D + 'png2tif.json') else None
# ---- picks
P = []
for fn in [SP + f'sbg/picks22/s22-{N}.json'] + sorted(glob.glob(SP + f'sbg/picks22/s22-{N}_*.json')):    # the first read and the second read's strips (2026-10-22)
    for p in json.load(open(fn))['intersections']: P.append(dict(p, part=os.path.basename(fn)[-6] if '_' in os.path.basename(fn) else '-'))
M = []
for p in P:
    if '?' in p['a'] + p['b'] or key(p['a']) == key(p['b']): continue
    k = tuple(sorted((key(p['a']), key(p['b']))))
    q = next((m for m in M if m['k'] == k and np.hypot(m['x'] - p['x'], m['y'] - p['y']) < 60), None)
    if q: q['xs'].append(p['x']); q['ys'].append(p['y']); q['x'] = float(np.mean(q['xs'])); q['y'] = float(np.mean(q['ys']))
    else: M.append(dict(k=k, a=p['a'], b=p['b'], x=float(p['x']), y=float(p['y']), xs=[p['x']], ys=[p['y']]))
spread = [float(np.hypot(np.ptp(m['xs']), np.ptp(m['ys']))) for m in M if len(m['xs']) > 1]
print('plate', N, 'picks', len(P), 'crossings', len(M), 'read twice', len(spread), 'median spread px', round(float(np.median(spread)), 1) if spread else '-')
# ---- OSM
OL = collections.defaultdict(list)
for fn in ('lph/osm_north.geojson', 'basin/osm_basin.geojson', 'lph/osm_east.geojson'):
    for f in json.load(open(SP + fn))['features']:
        nm = f['properties'].get('name')
        if nm and f['geometry']['type'] == 'LineString':
            g = shape(f['geometry']); OL[key(nm)].append(g); OL['B:' + base(key(nm))].append(g)
U = {k: unary_union(v) for k, v in OL.items()}
ALIAS = {key(a_): key(b_) for a_, b_ in {'Victory Boulevard': 'Victory Parkway', 'Clough Avenue': 'Crane Avenue'}.items()}      # renamed since 1922 (same street)
def lines(k): k = ALIAS.get(k, k); return U.get(k) or U.get('B:' + base(k))
def osm_x(k):
    la, lb = lines(k[0]), lines(k[1])
    if la is None or lb is None: return None, 'not in OSM: ' + ', '.join(n for n, l in zip(k, (la, lb)) if l is None)
    x = la.intersection(lb); pts = [g for g in getattr(x, 'geoms', [x]) if g.geom_type == 'Point'] if not x.is_empty else []
    if not pts:
        a, b = nearest_points(la, lb)
        if a.distance(b) < 3: pts = [Point((a.x + b.x) / 2, (a.y + b.y) / 2)]
    return pts, None
sys.path.insert(0, _ws.CODE + 'lph'); import mosn; TF22 = json.load(open(SP + 'lph/tf22_cw.json'))
if True:
    def seed(x, y): E, Nn = mosn.ap(TF22[N], np.array([x], float), np.array([y], float)); return float(E[0]), float(Nn[0])
elif G:
    def seed(x, y):
        X = poly(x, y, G['deg']); tx = X @ np.array(G['cx']); ty = X @ np.array(G['cy']); a = G['tif_transform']
        return W3857.transform(a[0] * (tx + 0.5) + a[1] * (ty + 0.5) + a[2], a[3] * (tx + 0.5) + a[4] * (ty + 0.5) + a[5])
else:                                            # name seed: unique name pairs, RANSAC affine
    cnt = collections.Counter(m['k'] for m in M); cand = []
    for m in M:
        if cnt[m['k']] != 1: continue
        pts, why = osm_x(m['k'])
        if pts and len(pts) == 1: cand.append((m['x'], m['y'], pts[0].x, pts[0].y))
    C_ = np.array(cand); rng = np.random.default_rng(0); best = None
    for it in range(4000):
        s = rng.choice(len(C_), 3, replace=False); A = np.c_[C_[s, :2], np.ones(3)]
        try: T = np.linalg.solve(A, C_[s, 2:])
        except np.linalg.LinAlgError: continue
        r = np.hypot(*(np.c_[C_[:, :2], np.ones(len(C_))] @ T - C_[:, 2:]).T); n = int((r < 25).sum())
        if best is None or n > best[0]: best = (n, T)
    A = np.c_[C_[:, :2], np.ones(len(C_))]; inl = np.hypot(*(A @ best[1] - C_[:, 2:]).T) < 25
    T, *_ = np.linalg.lstsq(A[inl], C_[inl, 2:], rcond=None)
    print('name seed: unique pairs', len(C_), 'inliers', int(inl.sum()), 'rms', round(float(np.sqrt(np.mean(np.sum((A[inl] @ T - C_[inl, 2:]) ** 2, 1)))), 1))
    def seed(x, y): return tuple(np.array([x, y, 1.0]) @ T)
RAD = 45
for PASS in (1, 2):              # pass 2: seed again from the pass-1 fit (the GeoTIFF can be 20-40 m off at plate edges) and match within 30 m
    if PASS == 2:
        f1 = f; seed = lambda x, y: tuple(f1(np.array([[x, y]], float))[0]); RAD = 30; print('--- pass 2 (re-seeded from pass 1)')
    for m in M:
        E, Nn = seed(m['x'], m['y']); m['seed'] = (float(E), float(Nn)); m['osm'] = None
        pts, why = osm_x(m['k'])
        if pts is None: m['why'] = why; continue
        pts = [g for g in pts if g.distance(Point(E, Nn)) < RAD]
        if not pts: m['why'] = f'no OSM crossing within {RAD} m of the seed'; continue
        g = min(pts, key=lambda g: g.distance(Point(E, Nn))); m['osm'] = (g.x, g.y); m.pop('why', None)
    K = [m for m in M if m['osm']]
    print('matched to OSM', len(K))
    X = np.array([[m['x'], m['y']] for m in K]); O = np.array([m['osm'] for m in K]); S = np.array([m['seed'] for m in K])
    print('seed vs OSM: rms', round(float(np.sqrt(np.mean(np.sum((S - O) ** 2, 1)))), 1), 'median', round(float(np.median(np.hypot(*(S - O).T))), 1))
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
        e = np.zeros(len(K))
        for i in np.where(keep)[0]:
            j = keep.copy(); j[i] = False; f = MODELS[name](X[j], O[j]); e[i] = np.hypot(*(f(X[i:i + 1])[0] - O[i]))
        return e
    # Colerain through Northside (north of the Elmore interchange) has moved or been widened since 1922: today's centre line sits 6-12 m
    # off both the 1904 and the 1922 sheets at Powers, Burgoyne, Hoffner and Blue Rock, while the side streets fit within 1-2 m
    NOFF = lambda m: 'Colerain' in m['a'] + m['b'] and m['seed'][1] > 4336600
    isout = lambda m: any(w in m['a'] + m['b'] for w in MOVED) or m['k'] in FORCE_OUT or NOFF(m)
    keep = np.array([not isout(m) for m in K]); dropped = [(m['a'] + ' / ' + m['b'], 'moved street') for m in K if isout(m)]
    # first a robust affine pass (a bad seed match far off would bend the spline), then the tps1 test
    for it in range(60):
        f_ = MODELS['affine'](X[keep], O[keep]); r_ = np.hypot(*(f_(X) - O).T); w = int(np.argmax(np.where(keep, r_, -1)))
        if r_[w] > 25.0: keep[w] = False; dropped.append((K[w]['a'] + ' / ' + K[w]['b'], round(float(r_[w]), 1), 'affine'))
        else: break
    for it in range(60):
        f_ = MODELS['tps1'](X[keep], O[keep]); r_ = np.hypot(*(f_(X) - O).T); w = int(np.argmax(np.where(keep, r_, -1)))
        if r_[w] > 6.0: keep[w] = False; dropped.append((K[w]['a'] + ' / ' + K[w]['b'], round(float(r_[w]), 1)))
        else: break
    print('dropped:', dropped)
    rep = {}
    for name in MODELS:
        e = loo(name, keep)[keep]; rep[name] = (float(np.sqrt(np.mean(e ** 2))), float(e.max()))
        print(f'{name:10s} leave-one-out rms {rep[name][0]:5.2f} max {rep[name][1]:5.2f}')
    best = min(rep, key=lambda k: rep[k][0]); f = MODELS[best](X[keep], O[keep])
    res = np.hypot(*(f(X) - O).T)
    print('chosen', best, 'controls', int(keep.sum()), 'fit rms', round(float(np.sqrt(np.mean(res[keep] ** 2))), 2))
for m, r, k_ in zip(K, res, keep): m['res'] = float(r); m['used'] = bool(k_)
json.dump(M, open(D + 'matches.json', 'w'), indent=1)
json.dump(dict(model=best, controls=int(keep.sum()), matched=len(K), crossings=len(M), dropped=dropped, loo=rep, moved=list(MOVED),
               seed='affine of 10u.4', seed_rms=float(np.sqrt(np.mean(np.sum((S - O) ** 2, 1))))), open(D + 'report.json', 'w'), indent=1)
pickle.dump(dict(model=best, X=X[keep], O=O[keep]), open(D + 'fwd.pkl', 'wb'))
# ---- inverse grid world -> png px
from PIL import Image; Image.MAX_IMAGE_PIXELS = None
from sb import find; import cv2; _im = cv2.imread(find('22-' + N), cv2.IMREAD_GRAYSCALE); H0, W0 = _im.shape; del _im
gx, gy = np.meshgrid(np.arange(0, W0 + 16, 16.0), np.arange(0, H0 + 16, 16.0)); Q = np.c_[gx.ravel(), gy.ravel()]
Wd = f(Q); E0, N0 = np.floor(Wd.min(0) / 2) * 2 - 10; E1, N1 = np.ceil(Wd.max(0) / 2) * 2 + 10; step = 2.0
ge, gn = np.meshgrid(np.arange(E0, E1, step), np.arange(N1, N0, -step))
px = griddata(Wd, Q[:, 0], (ge, gn), method='linear'); py = griddata(Wd, Q[:, 1], (ge, gn), method='linear')
px = np.where(np.isnan(px), -1e6, px).astype(np.float32); py = np.where(np.isnan(py), -1e6, py).astype(np.float32)
np.savez_compressed(D + 'model.npz', E0=E0, N1=N1, step=step, px=px, py=py)
print('inverse grid', px.shape, 'world box', [E0, N0, E1, N1])
