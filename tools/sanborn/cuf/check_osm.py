try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben's georeference of plate 22-35N against today's streets: every picked crossing of two named streets, matched to the same crossing in
# OpenStreetMap (nearest within 60 m of Ben's position), with the offset Ben's -> today
import json, sys, collections, numpy as np
sys.path.insert(0, (_ws.CODE + 'cuf')); sys.path.insert(0, (_ws.CODE + 'sbg'))
import common as C
from names import key, base
from shapely.geometry import shape, Point, MultiPoint
from shapely.ops import unary_union
SP = C.SP
P = []
for part in 'wme':
    for p in json.load(open(SP + f'sbg/picks22/s22-35N_{part}.json'))['intersections']: P.append(dict(p, part=part))
# merge the strips' duplicate readings (same pair within 60 px)
M = []
for p in P:
    k = tuple(sorted((key(p['a']), key(p['b']))))
    if '?' in p['a'] + p['b']: continue
    q = next((m for m in M if m['k'] == k and np.hypot(m['x'] - p['x'], m['y'] - p['y']) < 60), None)
    if q: q['xs'].append(p['x']); q['ys'].append(p['y']); q['x'] = float(np.mean(q['xs'])); q['y'] = float(np.mean(q['ys']))
    else: M.append(dict(k=k, a=p['a'], b=p['b'], x=p['x'], y=p['y'], xs=[p['x']], ys=[p['y']]))
OL = collections.defaultdict(list)
for fn in ('lph/osm_north.geojson', 'basin/osm_basin.geojson', 'lph/osm_east.geojson'):
    for f in json.load(open(SP + fn))['features']:
        nm = f['properties'].get('name')
        if nm and f['geometry']['type'] == 'LineString':
            g = shape(f['geometry']); OL[key(nm)].append(g); OL['B:' + base(key(nm))].append(g)
U = {k: unary_union(v) for k, v in OL.items()}
def lines(k): return U.get(k) or U.get('B:' + base(k))
out = []
for m in M:
    E, N = C.px2ben(m['x'], m['y']); m['ben'] = (float(E), float(N))
    la, lb = lines(m['k'][0]), lines(m['k'][1]); m['osm'] = None
    if la is None or lb is None: m['why'] = 'not in OSM: ' + ', '.join(n for n, l in zip(m['k'], (la, lb)) if l is None); continue
    x = la.intersection(lb)
    pts = [g for g in getattr(x, 'geoms', [x]) if g.geom_type == 'Point'] if not x.is_empty else []
    if not pts:   # T-junctions often stop a metre short in OSM: nearest approach
        from shapely.ops import nearest_points
        a, b = nearest_points(la, lb)
        if a.distance(b) < 3: pts = [Point((a.x + b.x) / 2, (a.y + b.y) / 2)]
    pts = [g for g in pts if g.distance(Point(E, N)) < 60]
    if not pts: m['why'] = 'no OSM crossing within 60 m'; continue
    g = min(pts, key=lambda g: g.distance(Point(E, N))); m['osm'] = (g.x, g.y); m['d'] = (g.x - E, g.y - N)
json.dump(M, open(SP + 'cuf/matches.json', 'w'), indent=1)
ok = [m for m in M if m['osm']]
print('crossings', len(M), 'matched to OSM', len(ok))
for m in sorted(ok, key=lambda m: -np.hypot(*m['d'])): print(f"{np.hypot(*m['d']):6.1f} m  dE {m['d'][0]:6.1f} dN {m['d'][1]:6.1f}  {m['a']} / {m['b']}  px ({m['x']:.0f},{m['y']:.0f})")
for m in M:
    if not m['osm']: print('  --', m['a'], '/', m['b'], ':', m.get('why'))
