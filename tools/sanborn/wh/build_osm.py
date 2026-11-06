"""Western Hills major streets from OpenStreetMap (Ben, 24-25 October 2026: only primary, secondary and tertiary, inside his line and out to the plan edges; the rest comes from the plates).
First version (all streets inside, 1914 dating outside) is wh/build_osm_v120.py, undone 25 October.
Inside Ben's boundary (wh/western_hills_area.kml): every public street (residential, unclassified, living street, tertiary,
secondary, primary, trunk; no motorways, links, service ways, footways). Outside it, out to the plan edges: primary,
secondary and tertiary only (the old pikes). Divided roads are centred between their carriageways (sbg/fit/osmfollow.py).
Nothing is drawn where the page already has streets or blocks; new streets that stop at that edge are carried onto the
existing street they meet. Widths: 50 ft placeholder (Ben: widths later). Set 'w1', ids SW#### (inside) and SZ#### (outside).
   python3 wh/build_osm.py [--install]
"""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, os, collections, numpy as np
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon, MultiLineString, box, shape
from shapely.ops import unary_union, linemerge, transform, substring
from shapely.strtree import STRtree
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'sbg/fit'); import osmfollow as OF
OSM = _ws.ext('/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/OSM/streets_all.geojson')
INSTALL = '--install' in sys.argv; SET = 'w1'; REM = SP + 'wh/removed.json'; FT = 0.3048
INNER = {'secondary', 'primary'}      # Ben, 25 October: only primary and secondary; everything else comes from the plates
OUTER = INNER
PLAN = box(699000, 4320800, 736900, 4347000)
W_DEF = 50 * FT
AREA = Polygon(json.load(open(SP + 'wh/area_utm.json')))
TR = Transformer.from_crs(4326, 26916, always_xy=True)
rep = collections.OrderedDict()

BJ = json.load(open(SP + 'deckpage/basin.json'))
if os.path.exists(REM):
    R0 = json.load(open(REM)); ids = {f['properties']['id'] for f in R0['features']}
    BJ['features'] = [f for f in BJ['features'] if f['properties'].get('set') != SET and f['properties'].get('id') not in ids] + R0['features']
BJ['features'] = [f for f in BJ['features'] if f['properties'].get('set') != SET]

# ---------------------------------------------------------------- what the page already covers
DK = json.load(open(SP + 'deckpage/deck.json'))
ex_streets, cover = [], []
FILLS = {'c29', 'c26A', 'c26B', 'c31', 'c33'}     # the Price Hill plates fill in around these streets, so they never take ground from them
for f in BJ['features'] + DK['features']:
    if f['properties'].get('set') in FILLS: continue
    L = f['properties'].get('layer'); g = shape(f['geometry'])
    if L == 'street' and g.geom_type == 'LineString':
        ex_streets.append(g); cover.append(g.buffer(f['properties'].get('width_m', 12) / 2 + 6, cap_style=2))
    elif L in ('block', 'deck') and g.geom_type in ('Polygon', 'MultiPolygon'):
        cover.append(g.buffer(3))
TAKEN = unary_union(cover).buffer(4).buffer(-4)
EXT = STRtree(ex_streets)
rep['taken_km2'] = round(TAKEN.area / 1e6, 2)

# ---------------------------------------------------------------- OSM ways
lo = TR.transform(699000, 4320800, direction='INVERSE'); hi = TR.transform(736900, 4347000, direction='INVERSE')
ways = []
for f in json.load(open(OSM))['features']:
    p = f['properties']; h = p.get('highway')
    if h not in INNER or f['geometry']['type'] != 'LineString': continue
    c = f['geometry']['coordinates']
    if all(not (lo[0] - .01 < x < hi[0] + .01 and lo[1] - .01 < y < hi[1] + .01) for x, y in c[::max(1, len(c) // 4)]): continue
    g = LineString([TR.transform(x, y) for x, y in c])
    if not g.intersects(PLAN): continue
    inside = g.intersects(AREA.buffer(30))
    if not inside and h not in OUTER: continue
    ways.append(dict(name=p.get('name') or '', h=h, g=g))
rep['osm_ways'] = len(ways)

# ---------------------------------------------------------------- divided roads: centre the carriageway pairs
byname = collections.defaultdict(list)
for w in ways:
    if w['name']: byname[w['name']].append(w)
def paired_share(ws):
    pts, dirs, own = [], [], []
    for k, w in enumerate(ws):
        g = w['g']
        for d in np.arange(0, g.length, 10.0):
            a = g.interpolate(max(0, d - 4)); b = g.interpolate(min(g.length, d + 4)); v = np.array([b.x - a.x, b.y - a.y]); v /= np.hypot(*v) + 1e-9
            pts.append(g.interpolate(d).coords[0]); dirs.append(v); own.append(k)
    if len(pts) < 6: return 0.0
    from scipy.spatial import cKDTree
    P = np.array(pts); D = np.array(dirs); T = cKDTree(P); n = 0
    for i, p in enumerate(P):
        nr = np.array([-D[i][1], D[i][0]])
        for j in T.query_ball_point(p, 45):
            if own[j] == own[i]: continue
            v = P[j] - p
            if 6 <= abs(v @ nr) and abs(v @ D[i]) < 6 and abs(D[i] @ D[j]) > 0.94: n += 1; break
    return n / len(P)
divided = {}
for nm, ws in byname.items():
    if len(ws) < 2: continue
    sh = paired_share(ws)
    if sh > 0.3: divided[nm] = round(sh, 2)
rep['divided_roads'] = divided
cent = []
for nm in divided:
    ws = byname[nm]
    for g, n_, _, _ in OF.centreline([(nm, w['g']) for w in ws]):
        cent.append(dict(name=nm, h=max((w['h'] for w in ws), key=lambda h: ['road', 'living_street', 'unclassified', 'residential', 'tertiary', 'secondary', 'primary', 'trunk'].index(h)), g=g))
ways = [w for w in ways if w['name'] not in divided] + cent

# ---------------------------------------------------------------- clip: inside the boundary (plus 30 m for the boundary roads), outside only the pikes;
# never over what the page already has
AREA30 = AREA.buffer(30)
pieces = []
for w in ways:
    g = w['g'].difference(TAKEN)
    if g.is_empty: continue
    if w['h'] in OUTER: keep = g.intersection(PLAN)
    else: keep = g.intersection(AREA30)
    for q in (keep.geoms if hasattr(keep, 'geoms') else [keep]):
        if q.geom_type == 'LineString' and q.length > 2: pieces.append(dict(name=w['name'], h=w['h'], g=q, inner=w['h'] not in OUTER or q.intersects(AREA)))
# local streets reaching past the boundary road: cut back to the last junction inside
tree = STRtree([p['g'] for p in pieces])
for p in pieces:
    if p['h'] in OUTER: continue
    near = [pieces[i] for i in tree.query(p['g'].buffer(1))]
    g = p['g']
    if g.within(AREA): continue
    others = unary_union([q['g'] for q in near if q is not p])
    J = []
    if not others.is_empty:
        X = others.intersection(g)
        for pt in (X.geoms if hasattr(X, 'geoms') else [X]):
            if pt.geom_type == 'Point' and AREA.buffer(1).contains(pt): J.append(g.project(pt))
    s0 = 0.0 if AREA.buffer(1).contains(Point(g.coords[0])) else (min(J) if J else None)
    s1 = g.length if AREA.buffer(1).contains(Point(g.coords[-1])) else (max(J) if J else None)
    if s0 is None or s1 is None or s1 - s0 < 2: p['g'] = None; continue
    p['g'] = substring(g, s0, s1)
pieces = [p for p in pieces if p['g'] is not None and p['g'].length > 2]

# ---------------------------------------------------------------- one line per street run
groups = collections.defaultdict(list)
for p in pieces: groups[(p['name'], p['h'] in OUTER and not p['inner'])].append(p)
lines = []
for (nm, outer), ps in groups.items():
    u = unary_union([p['g'] for p in ps]); m = linemerge(u) if u.geom_type == 'MultiLineString' else u
    hs = collections.Counter(p['h'] for p in ps).most_common(1)[0][0]
    for q in (m.geoms if hasattr(m, 'geoms') else [m]):
        if q.length >= 8: lines.append(dict(name=nm, h=hs, g=q.simplify(0.5), outer=outer and not q.intersects(AREA)))

# ---------------------------------------------------------------- carriageway scraps: a short piece lying along a longer one of the same name goes
from shapely.strtree import STRtree as _T
_t = _T([L['g'] for L in lines]); drop = set()
for i, L in enumerate(lines):
    if L['g'].length > 400: continue
    for j in _t.query(L['g'].buffer(25)):
        M = lines[j]
        if j == i or j in drop or M['name'] != L['name'] or M['g'].length <= L['g'].length: continue
        if L['g'].intersection(M['g'].buffer(25)).length > 0.8 * L['g'].length: drop.add(i); break
rep['carriageway_scraps_dropped'] = len(drop)
lines = [L for i, L in enumerate(lines) if i not in drop]

# ---------------------------------------------------------------- ends cut at the page's edge: carried onto the existing street they meet
carried = 0
for L in lines:
    c = list(L['g'].coords)
    for e in (0, -1):
        q = Point(c[e])
        if TAKEN.boundary.distance(q) > 3: continue
        cand = [ex_streets[i] for i in EXT.query(q.buffer(30))]
        if not cand: continue
        s = min(cand, key=lambda s: s.distance(q))
        if s.distance(q) > 30: continue
        t = s.interpolate(s.project(q)).coords[0]
        if e == 0: c = [t] + c
        else: c = c + [t]
        carried += 1
    L['g'] = LineString(c)
rep['carried_onto_page_streets'] = carried

# ---------------------------------------------------------------- Ben's rail-driven moves (wh/street_shifts.json): Spring Grove Avenue west at Ivorydale (26 October 2026)
SHF = SP + 'wh/street_shifts.json'
if os.path.exists(SHF):
    sh = json.load(open(SHF)); sh = sh if isinstance(sh, list) else [sh]
    for L in lines:
        for m in sh:
            c = list(L['g'].coords)
            if L['name'] == m['name'] and Point(c[0]).distance(Point(m['start'])) < 3 and Point(c[-1]).distance(Point(m['end'])) < 3:
                L['g'] = LineString(m['coords']); rep.setdefault('shifted', []).append(m['name'])
# ---------------------------------------------------------------- features
out = []; ni = no = 0
for L in sorted(lines, key=lambda L: (L['outer'], L['name'], L['g'].bounds[0])):
    if L['outer']: no += 1; fid = f'SZ{no:04d}'
    else: ni += 1; fid = f'SW{ni:04d}'
    out.append(dict(type='Feature', properties=dict(layer='street', id=fid, name=L['name'], kind='we_street', width_m=round(W_DEF, 2), width_ft=50,
        width_src='default', side='', src='OSM (Western Hills, 2026-10-24)' if not L['outer'] else 'OSM (main roads outside the Western Hills line, 2026-10-24)',
        geom_src='OSM ' + L['h'], osm_class=L['h'], set=SET),
        geometry=dict(type='LineString', coordinates=[[round(x, 1), round(y, 1)] for x, y in L['g'].coords])))
rep['inside'] = dict(streets=ni, km=round(sum(LineString(f['geometry']['coordinates']).length for f in out if f['properties']['id'].startswith('SW')) / 1000, 1))
rep['outside'] = dict(streets=no, km=round(sum(LineString(f['geometry']['coordinates']).length for f in out if f['properties']['id'].startswith('SZ')) / 1000, 1))
rep['by_class_km'] = {h: round(sum(LineString(f['geometry']['coordinates']).length for f in out if f['properties']['osm_class'] == h) / 1000, 1) for h in sorted({f['properties']['osm_class'] for f in out})}
json.dump(dict(type='FeatureCollection', features=out), open(SP + 'wh/w1_streets.geojson', 'w'))
for k, v in rep.items(): print(k, v)
if INSTALL:
    json.dump(dict(type='FeatureCollection', features=[]), open(REM, 'w'))
    BJ['features'] = BJ['features'] + out
    json.dump(BJ, open(SP + 'deckpage/basin.json', 'w'), separators=(',', ':')); print('installed', len(out))
