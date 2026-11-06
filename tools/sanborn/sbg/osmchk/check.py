"""Check the Sanborn-built basin streets against OSM.
A: every street piece sampled every 4 m (8 m kept off each end): distance to the OSM street of the same name;
   where none within 25 m, the nearest parallel OSM road of any name within 8 m.
B: every named OSM road inside the basin layer's area sampled the same way: is there a basin street within 8 m, parallel?"""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import json, sys, collections, pickle, numpy as np
sys.path.insert(0, (_ws.CODE + 'sbg'))
from names import key, base
from shapely.geometry import LineString, Point, shape
from shapely.ops import unary_union
from shapely.strtree import STRtree
SP = _ws.DATA
L = json.load(open(SP + 'sbg/fit/basin_sanborn.json'))['features']
ST = [f for f in L if f['properties']['layer'] == 'street']
deck = [shape(f['geometry']) for f in json.load(open(SP + 'deckpage/deck.json'))['features'] if f['properties'].get('layer') == 'deck'][0].buffer(0)
ROADS = {'residential', 'secondary', 'primary', 'tertiary', 'unclassified', 'service', 'pedestrian', 'living_street', 'secondary_link', 'primary_link', 'tertiary_link', 'trunk', 'construction', 'footway'}
O = []
for f in json.load(open(SP + 'basin/osm_basin.geojson'))['features']:
    p = f['properties']; h = p.get('highway')
    if h not in ROADS: continue
    if h == 'footway' and not p.get('name'): continue
    O.append(dict(name=p.get('name') or '', k=key(p.get('name') or ''), hw=h, g=LineString(f['geometry']['coordinates'])))
OT = STRtree([o['g'] for o in O])
byk = collections.defaultdict(list); byb = collections.defaultdict(list)
for i, o in enumerate(O):
    if o['k']: byk[o['k']].append(i); byb[base(o['k'])].append(i)
def unit(g, d):
    a = g.interpolate(max(0, d - 4)); b = g.interpolate(min(g.length, d + 4)); v = np.array([b.x - a.x, b.y - a.y]); return v / (np.hypot(*v) + 1e-9)
def osm_dir(g, p):
    return unit(g, g.project(p))
def samples(g, step=4.0, trim=8.0):
    if g.length <= 2 * trim + 1: ds = [g.length / 2]
    else: ds = np.arange(trim, g.length - trim + 0.01, step)
    return [(d, g.interpolate(d)) for d in ds]
# ---------------- A
SAMP = []
for si, f in enumerate(ST):
    g = shape(f['geometry']); p = f['properties']; k = key(p['name']) if p['name'] else ''
    cand = byk.get(k) or byb.get(base(k), []) if k else []
    cg = [O[i]['g'] for i in cand]
    for d, pt in samples(g):
        u = unit(g, d); rec = dict(si=si, x=pt.x, y=pt.y, name=p['name'], kind=p['kind'])
        best = None
        for i, h in zip(cand, cg):
            dd = h.distance(pt)
            if dd < 25 and (best is None or dd < best[0]): best = (dd, i)
        if best:
            o = O[best[1]]; q = o['g'].interpolate(o['g'].project(pt)); nrm = np.array([-u[1], u[0]])
            rec.update(st='same', d=best[0], sd=float((np.array([pt.x - q.x, pt.y - q.y])) @ nrm), osm=o['name'])
        else:
            bb = None
            for j in OT.query(pt.buffer(8)):
                o = O[int(j)]; dd = o['g'].distance(pt)
                if dd > 8: continue
                ang = np.degrees(np.arccos(min(1, abs(u @ osm_dir(o['g'], pt)))))
                if ang > 20: continue
                if bb is None or dd < bb[0]: bb = (dd, int(j))
            if bb: rec.update(st='other', d=bb[0], osm=O[bb[1]]['name'], hw=O[bb[1]]['hw'])
            else: rec.update(st='none')
        SAMP.append(rec)
# ---------------- B
area = unary_union([shape(f['geometry']).buffer(40) for f in L if f['properties']['layer'] in ('street', 'block')]).difference(deck.buffer(10))
BT = STRtree([shape(f['geometry']) for f in ST]); BG = [shape(f['geometry']) for f in ST]
OSMS = []
for i, o in enumerate(O):
    if not o['name'] or o['hw'] == 'footway': continue
    g = o['g'].intersection(area)
    for part in getattr(g, 'geoms', [g]):
        if part.geom_type != 'LineString' or part.length < 4: continue
        for d, pt in samples(part, 4.0, 4.0):
            u = unit(part, d); best = None
            for j in BT.query(pt.buffer(8)):
                h = BG[int(j)]; dd = h.distance(pt)
                if dd > 8: continue
                ang = np.degrees(np.arccos(min(1, abs(u @ osm_dir(h, pt)))))
                if ang > 20: continue
                if best is None or dd < best[0]: best = (dd, int(j))
            OSMS.append(dict(oi=i, name=o['name'], hw=o['hw'], x=pt.x, y=pt.y, hit=best is not None, bname=ST[best[1]]['properties']['name'] if best else None, d=best[0] if best else None))
pickle.dump(dict(SAMP=SAMP, OSMS=OSMS), open(SP + 'sbg/osmchk/samples.pkl', 'wb'))
print('A samples', len(SAMP), collections.Counter(s['st'] for s in SAMP)); print('B samples', len(OSMS), sum(s['hit'] for s in OSMS))
