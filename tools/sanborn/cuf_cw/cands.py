try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# OSM crossings inside each half's mapped area between streets whose names the half shows (from its picks, bends, ends), not yet
# matched as a control: candidates for a second read.
import json, sys, collections, itertools, pickle, numpy as np
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'sbg'); sys.path.insert(0, _ws.CODE + 'lph'); sys.path.insert(0, _ws.CODE + 'cuf')
from names import key, base
import mosn
from shapely.geometry import shape, Point, Polygon
from shapely.ops import unary_union
from plates import POLY22
POLY22 = dict(POLY22); POLY22.update({'22-34R': POLY22['22-34R'], '22-35L': [(90, 90), (6200, 90), (6200, 7700), (90, 7700)], '22-16L': [(0, 0), (6000, 0), (6000, 7790), (0, 7790)]})
TF22 = json.load(open(SP + 'lph/tf22_cw.json'))
OSM = collections.defaultdict(list)
for fn in ('lph/osm_north.geojson', 'basin/osm_basin.geojson', 'lph/osm_east.geojson'):
    for f in json.load(open(SP + fn))['features']:
        nm = f['properties'].get('name')
        if nm and f['geometry']['type'] == 'LineString' and f['properties'].get('highway') not in ('motorway', 'motorway_link', 'service', 'footway', 'pedestrian'): OSM[nm].append(shape(f['geometry']))
OU = {n: unary_union(v) for n, v in OSM.items()}
out = {}
for k in sys.argv[1:]:
    J = json.load(open(SP + f'sbg/picks22/s22-{k}.json')); M = json.load(open(SP + f'cuf_cw/{k}/matches.json'))
    shown = set()
    for p in J['intersections']: shown |= {base(key(p['a'])), base(key(p['b']))}
    for q in J.get('ends', []) + J.get('bends', []):
        for f_ in ('street', 'name', 'a'):
            if q.get(f_): shown.add(base(key(q[f_])))
    used = {tuple(sorted((base(m['k'][0]), base(m['k'][1])))) for m in M if m.get('osm')}
    pts = np.array(POLY22.get('22-' + k, [(0, 0), (6000, 0), (6000, 7790), (0, 7790)]), float)
    E, N = mosn.ap(TF22[k], pts[:, 0], pts[:, 1]); FP = Polygon(np.c_[E, N]).buffer(-20)
    names = [n for n in OU if base(key(n)) in shown and OU[n].intersects(FP)]
    C = []
    for a, b in itertools.combinations(names, 2):
        kk = tuple(sorted((base(key(a)), base(key(b)))))
        if kk[0] == kk[1] or kk in used: continue
        x = OU[a].intersection(OU[b])
        for g in getattr(x, 'geoms', [x]):
            if g.geom_type == 'Point' and FP.contains(g):
                # where on the half: invert the affine
                px, py = mosn.inv(TF22[k], np.array([g.x]), np.array([g.y])); C.append(dict(a=a, b=b, E=round(g.x, 1), N=round(g.y, 1), px=int(px[0]), py=int(py[0])))
    out[k] = C; print(k, 'shown names', len(shown), 'controls', len(used), 'candidates', len(C)); [print('   ', c['a'], '/', c['b'], c['px'], c['py']) for c in C]
json.dump(out, open(SP + 'cuf_cw/cands.json', 'w'), indent=1)
