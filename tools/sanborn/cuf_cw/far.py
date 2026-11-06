try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, collections, numpy as np
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'sbg'); sys.path.insert(0, _ws.CODE + 'lph')
from names import key, base
import mosn
from shapely.geometry import shape, Point, box
from shapely.ops import unary_union, nearest_points
OL = collections.defaultdict(list); BOX = box(710500, 4333500, 714200, 4338600)
for fn in ('lph/osm_north.geojson', 'basin/osm_basin.geojson', 'lph/osm_east.geojson'):
    for f in json.load(open(SP + fn))['features']:
        nm = f['properties'].get('name')
        if nm and f['geometry']['type'] == 'LineString':
            g = shape(f['geometry'])
            if g.intersects(BOX): OL[key(nm)].append(g); OL['B:' + base(key(nm))].append(g)
U = {k: unary_union(v) for k, v in OL.items()}
def lines(k): return U.get(k) or U.get('B:' + base(k))
TF22 = json.load(open(SP + 'lph/tf22_cw.json'))
for k in sys.argv[1:]:
    M = json.load(open(SP + f'cuf_cw/{k}/matches.json'))
    for m in M:
        if not m.get('why', '').startswith('no OSM'): continue
        E, N = mosn.ap(TF22[k], np.array([m['x']], float), np.array([m['y']], float)); P = Point(float(E[0]), float(N[0]))
        la, lb = lines(m['k'][0]), lines(m['k'][1])
        if la is None or lb is None: print(k, m['a'], '/', m['b'], ': not in OSM box'); continue
        x = la.intersection(lb); pts = [g for g in getattr(x, 'geoms', [x]) if g.geom_type == 'Point'] if not x.is_empty else []
        a, b = nearest_points(la, lb)
        d = min([g.distance(P) for g in pts]) if pts else None
        print(k, m['a'], '/', m['b'], ': nearest OSM crossing', None if d is None else round(d), 'm', '' if pts else f'(lines never meet; closest {a.distance(b):.0f} m apart, {P.distance(a):.0f} m from seed)')
