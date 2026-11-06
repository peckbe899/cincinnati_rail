try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Northside / Camp Washington: where the 1922 halves (affine, lph/tf22_cw.json) and the 1904 frames (as drawn on the page) sit against
# today's OSM crossings of the same two streets. Writes cuf_cw/diag.json.
import json, sys, glob, pickle, os, collections, numpy as np
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'sbg'); sys.path.insert(0, _ws.CODE + 'cuf'); sys.path.insert(0, _ws.CODE + 'lph')
import mosn, tps
sys.path.insert(0, _ws.CODE + 'cufp'); import fwdlib
from names import key, base
from shapely.geometry import shape, Point, box
from shapely.ops import unary_union, nearest_points
from matplotlib.path import Path
BOX = box(710900, 4334200, 713700, 4338200)
OL = collections.defaultdict(list)
for fn in ('lph/osm_north.geojson', 'basin/osm_basin.geojson', 'lph/osm_east.geojson'):
    for f in json.load(open(SP + fn))['features']:
        nm = f['properties'].get('name')
        if nm and f['geometry']['type'] == 'LineString':
            g = shape(f['geometry'])
            if g.intersects(BOX.buffer(500)): OL[key(nm)].append(g); OL['B:' + base(key(nm))].append(g)
U = {k: unary_union(v) for k, v in OL.items()}
def lines(k): return U.get(k) or U.get('B:' + base(k))
XC = {}
def osm_pts(k):
    if k in XC: return XC[k]
    la, lb = lines(k[0]), lines(k[1]); pts = []
    if la is not None and lb is not None:
        x = la.intersection(lb); pts = [g for g in getattr(x, 'geoms', [x]) if g.geom_type == 'Point'] if not x.is_empty else []
        if not pts:
            a, b = nearest_points(la, lb)
            if a.distance(b) < 3: pts = [Point((a.x + b.x) / 2, (a.y + b.y) / 2)]
    XC[k] = pts; return pts
def match(a, b, E, N, rad=45):
    k = tuple(sorted((key(a), key(b)))); pts = [g for g in osm_pts(k) if g.distance(Point(E, N)) < rad]
    if not pts: return None
    g = min(pts, key=lambda g: g.distance(Point(E, N))); return (g.x, g.y)
out = dict(p22=[], f04=[])
# ---- 1922 halves
TF22 = json.load(open(SP + 'lph/tf22_cw.json'))
for k in ('16L', '16R', '31R', '33L', '34L', '34R', '35L', '37L', '37R'):
    fns = [SP + f'sbg/picks22/s22-{k}.json'] + sorted(glob.glob(SP + f'sbg/picks22/s22-{k}_*.json'))
    for p in [q for fn in fns if os.path.exists(fn) for q in json.load(open(fn))['intersections']]:
        if '?' in p['a'] + p['b'] or key(p['a']) == key(p['b']): continue
        if os.path.exists(SP + f'cuf_cw/{k}/fwd.pkl'): E, N = fwdlib.world(k, p['x'], p['y'])
        else: E, N = mosn.ap(TF22[k], np.array([p['x']], float), np.array([p['y']], float)); E, N = float(E[0]), float(N[0])
        if not BOX.contains(Point(E, N)): continue
        o = match(p['a'], p['b'], E, N); out['p22'].append(dict(src='22-' + k, a=p['a'], b=p['b'], x=p['x'], y=p['y'], E=E, N=N, osm=o))
# ---- 1904 frames as drawn now
TF = {}
for fn in ('lph/tf_all.json', 'lph/tf_ext.json', 'lph/tf_ext2.json', 'lph/tf_ext3.json'): TF.update(json.load(open(SP + fn)))
MOD = pickle.load(open(SP + 'lph/tps.pkl', 'rb'))
PX = {}
for fn in ('lph/panels_ext.json', 'lph/panels_ext2.json', 'lph/panels_ext3.json'): PX.update(json.load(open(SP + fn)))
for fr in TF:
    sh = ''.join(ch for ch in fr if ch.isdigit()); fn = SP + f'sbg/picks/s{sh}.json'
    if not os.path.exists(fn): continue
    sibs = [q for q in PX if ''.join(ch for ch in q if ch.isdigit()) == sh and q != fr]
    for p in json.load(open(fn))['intersections']:
        if '?' in p['a'] + p['b'] or key(p['a']) == key(p['b']): continue
        if fr in PX and not Path(np.array(PX[fr])).contains_point((p['x'], p['y'])): continue
        if any(Path(np.array(PX[s])).contains_point((p['x'], p['y'])) for s in sibs): continue
        E, N = mosn.ap(TF[fr], np.array([p['x']], float), np.array([p['y']], float))
        if fr in MOD: dE, dN = tps.disp(fr, E, N, MOD); E, N = E + dE, N + dN
        E, N = float(E[0]), float(N[0])
        if not BOX.contains(Point(E, N)): continue
        o = match(p['a'], p['b'], E, N); out['f04'].append(dict(src=fr, a=p['a'], b=p['b'], x=p['x'], y=p['y'], E=E, N=N, osm=o))
json.dump(out, open(SP + 'cuf_cw/diag.json', 'w'), indent=1)
for g in ('p22', 'f04'):
    R = out[g]; by = collections.defaultdict(list)
    for r in R: by[r['src']].append(r)
    print('==', g)
    for s, L in sorted(by.items()):
        h = [r for r in L if r['osm']]; d = np.array([np.hypot(r['E'] - r['osm'][0], r['N'] - r['osm'][1]) for r in h]) if h else np.array([])
        v = np.array([[r['osm'][0] - r['E'], r['osm'][1] - r['N']] for r in h]).mean(0) if h else (0, 0)
        print(f"{s:6s} crossings {len(L):3d} on OSM {len(h):3d}" + (f"  median {np.median(d):5.1f} m  p90 {np.percentile(d, 90):5.1f}  mean shift ({v[0]:+.1f}, {v[1]:+.1f})" if h else ''))
print('== Colerain crossings')
for r in out['p22'] + out['f04']:
    if 'Colerain' in r['a'] + r['b'] and r['osm']:
        print(f"{r['src']:6s} {r['a']} / {r['b']}: {np.hypot(r['E'] - r['osm'][0], r['N'] - r['osm'][1]):5.1f} m  ({r['osm'][0] - r['E']:+.1f}, {r['osm'][1] - r['N']:+.1f})")
