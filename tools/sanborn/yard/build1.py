try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Part 1: limit, references, under-deck structures. Writes yard/part1.json (shapely-ready GeoJSON).
import json, sys, math
sys.path.insert(0, (_ws.CODE + 'yard'))
from lv import *
from shapely.geometry import shape, mapping, LineString, Polygon, Point, box, MultiPolygon
from shapely.ops import unary_union, substring
D = json.load(open(S + 'deckpage/deck.json')); C = json.load(open(S + 'deckpage/context.json'))
ST = json.load(open(S + 'deckpage/structures.json')); TK = json.load(open(S + 'deckpage/tracks.json'))
deck = [shape(f['geometry']) for f in D['features'] if f['properties'].get('layer') == 'deck'][0]
deck = deck.buffer(3.0, join_style=2).buffer(-3.0, join_style=2)   # closes the outline's thin ring round the roundabout (the disc is decked)
st = {f['properties']['name']: shape(f['geometry']) for f in ST['features'] if f['geometry']['type'] != 'Point'}
out = []
def add(layer, g, **p):
    if g.is_empty: return
    p['layer'] = layer; out.append({'type': 'Feature', 'properties': p, 'geometry': mapping(g)})

# ---- limit: the deck, west of the CUT structures, east of New street W (its line carried south to the river)
nw = [shape(f['geometry']) for f in D['features'] if f['properties'].get('name') == 'New street W'][0]
(a, b) = nw.coords[0], nw.coords[-1]
if a[1] > b[1]: a, b = b, a
k = (b[0] - a[0]) / (b[1] - a[1])
nwx = lambda n: a[0] + k * (n - a[1]) if n <= b[1] else None
cut_east = [st['CUT platform deck'], st['CUT approach viaduct (south)'], st['Intercity pair: viaduct'], st['Intercity pair: trough']]
nav = st['North arch viaduct']; nav_main = max(nav.geoms, key=lambda g: g.bounds[2]); cut_east.append(nav_main)
CE = unary_union(cut_east)
rows = []; step = 2.0
n = deck.bounds[1]
while n <= deck.bounds[3]:
    L = LineString([(711000, n), (714000, n)]); I = deck.intersection(L)
    segs = [g for g in getattr(I, 'geoms', [I]) if not g.is_empty and g.length > 0]
    ce = CE.intersection(L); iv = sorted((g.bounds[0], g.bounds[2]) for g in getattr(ce, 'geoms', [ce]) if not g.is_empty and g.length > 0)
    xe = None   # the eastmost group of structure intervals (gaps under 60 m merged): the APEx body, not the strands west of it
    for x0_, x1_ in iv:
        if xe is None or x0_ - last > 60: xe = x0_
        last = x1_
    xw = nwx(n)
    for g in segs:
        x0, x1 = g.bounds[0], g.bounds[2]
        if xw is not None: x0 = max(x0, xw)
        if xe is not None: x1 = min(x1, xe)
        if x1 - x0 > 1: rows.append(box(x0, n - step / 2, x1, n + step / 2))
    n += step
limit = unary_union(rows).buffer(3, join_style=2).buffer(-3, join_style=2).simplify(1.0)
limit = limit.intersection(deck)
limit = max(getattr(limit, 'geoms', [limit]), key=lambda g: g.area)   # the main body only (drops the slivers of the western lobes)
# today's yard north of the deck (Ben: the northern yard footprint is fair game): OSM yard tracks, footprint as measured for today's yard
_o = json.load(open(S + 'yard/osm_rail_deck.json'))
_q = unary_union([shape(f['geometry']).buffer(3) for f in _o['features'] if f['properties'].get('service') == 'yard']).buffer(12).buffer(-12)
_north = unary_union([g for g in getattr(_q.difference(deck), 'geoms', [_q.difference(deck)]) if g.area > 500 and g.bounds[1] > 4335000])
_north = _north.buffer(40, join_style=2).buffer(-40, join_style=2)   # the yard's area, gaps between its track groups included
limit = unary_union([limit, _north]).buffer(2, join_style=2).buffer(-2, join_style=2).difference(CE.buffer(2))
limit = max(getattr(limit, 'geoms', [limit]), key=lambda g: g.area)
_nb = box(711000, 4335000, 714000, 4337000)
limit = unary_union([limit, limit.intersection(_nb).convex_hull.difference(CE.buffer(2))])   # the gap between the arms of today's northern yard is inside its extent
limit = max(getattr(limit, 'geoms', [limit]), key=lambda g: g.area)
limit = Polygon(limit.exterior, [r for r in limit.interiors if Polygon(r).area > 5000])
# ---- Mill Creek (Ben, 27 October): under Exposition Boulevard, a curved culvert from the roundabout to Millvale Boulevard, under Millvale Boulevard to Albone.
# The yard stays east (and south) of it. The deck and flattened land run north to Albone.
import math as _m
_B = json.load(open(S + 'deckpage/basin.json'))
_mv = {f['properties']['id']: LineString(f['geometry']['coordinates']) for f in _B['features'] if f['properties'].get('id') in ('SMV0036', 'SMV0034', 'SMV0033', 'SMV0037', 'SMV0038')}
_blvd = [shape(f['geometry']) for f in D['features'] if f['properties'].get('layer') == 'boulevard'][0]
_rb = [shape(f['geometry']) for f in D['features'] if f['properties'].get('layer') == 'roundabout'][0]
_rbc = (_rb.centroid.x, _rb.centroid.y)
# connector: Ben's sketch (27 October), smoothed: from the north end of Exposition Boulevard, tangent to its line, a curve left onto
# about -11 deg, a curve left along the hill onto about -26 deg, a curve right into Millvale Boulevard's line at Hopple. Underground: the Palace sits over it.
from ygen import fil as _fil
def _line_pt(p, brg, d): return (p[0] + d * _m.sin(_m.radians(brg)), p[1] + d * _m.cos(_m.radians(brg)))
def _isect(p, b1, q, b2):
    d1 = (_m.sin(_m.radians(b1)), _m.cos(_m.radians(b1))); d2 = (_m.sin(_m.radians(b2)), _m.cos(_m.radians(b2)))
    den = d1[0] * d2[1] - d1[1] * d2[0]; t = ((q[0] - p[0]) * d2[1] - (q[1] - p[1]) * d2[0]) / den
    return (p[0] + d1[0] * t, p[1] + d1[1] * t)
_AX = 3.64
_P0 = (712279.0 + _m.tan(_m.radians(_AX)) * (4333525.0 - 4330887.0), 4333525.0)
_p = _mv['SMV0036'].coords[-1]; _q = (711951.0, 4335070.0)
_b3 = _m.degrees(_m.atan2(_q[0] - _p[0], _q[1] - _p[1]))          # Millvale Boulevard's heading at Hopple (northward)
_b1, _b2 = -10.8, -26.0
_A = (712360.0, 4333968.0); _Bp = (712181.0, 4334548.0)            # on the sketch's centre line
_PI1 = _isect(_P0, _AX, _A, _b1); _PI2 = _isect(_A, _b1, _Bp, _b2); _PI3 = _isect(_Bp, _b2, _p, _b3)
_RADII = [900.0, 800.0, 500.0]
_V = [_line_pt(_P0, _AX + 180, 260.0), _PI1, _PI2, _PI3, _q]
_pts = _fil(_V[:3], _RADII[0])[:-1] + _fil(_V[1:4], _RADII[1])[1:-1] + _fil(_V[2:], _RADII[2])[1:]
_conn = LineString(_pts)
_R = _RADII
CONN_R = _R; CONN = _conn
W_CULV = 45.72    # drawing value: the culvert strip as wide as Millvale Boulevard over it
W_CONN = 30.0     # drawing value: the link culvert
_CONNSTRIP = unary_union([_conn.interpolate(k * _conn.length / 120).buffer((70.0 + (W_CULV - 70.0) * k / 120) / 2) for k in range(121)])
_creek = unary_union([_blvd, _CONNSTRIP] + [g.buffer(W_CULV / 2 if k in ('SMV0036', 'SMV0034', 'SMV0033') else 11.5, cap_style=2) for k, g in _mv.items()])
# west / north side of the creek: polygon from the creek line out to far corners
_line = [(712279 - 0.0636 * 900, 4329987)] + [(712279.0, 4330887.0)] + list(_conn.coords) + list(_mv['SMV0036'].coords)[::-1] + list(_mv['SMV0034'].coords)[::-1] + [(712130.0, 4336356.0)] + list(_mv['SMV0033'].coords)[::-1] + [(713300.0, 4337330.0)]
_west = Polygon(_line + [(713300.0, 4338500.0), (710000.0, 4338500.0), (710000.0, 4329987.0)])
_west = _west.buffer(0) if not _west.is_valid else _west
# candidate: the deck and the flattened land north of it, west of the APEx viaduct (eastmost structure group per row), not on the creek or west of it
_north_zone = box(711500, 4334800, 713300, 4337300)
_cand = unary_union([deck, _north_zone])
_rows = []; _n = 4330600.0
while _n <= 4337300:
    _L = LineString([(710000, _n), (714500, _n)]); _ce = CE.intersection(_L)
    _iv = sorted((g.bounds[0], g.bounds[2]) for g in getattr(_ce, 'geoms', [_ce]) if not g.is_empty and g.length > 0)
    _xe = None
    for _a, _b in _iv:
        if _xe is None or _a - _last > 25: _xe = _a
        _last = _b
    if _xe is None: _xe = 714500
    _rows.append(box(710000, _n - 1.0, _xe, _n + 1.0)); _n += 2.0
_westCE = unary_union(_rows)
_emb = unary_union([g for nm, g in st.items() if nm in ('North trunk fill (Northside / Spring Grove to ground)', 'Ludlow underbridge')])
limit = _cand.intersection(_westCE).difference(_west).difference(_creek.buffer(1)).difference(_emb.buffer(2))
limit = limit.buffer(3, join_style=2).buffer(-3, join_style=2)
limit = max(getattr(limit, 'geoms', [limit]), key=lambda g: g.area)
limit = Polygon(limit.exterior, [r for r in limit.interiors if Polygon(r).area > 5000])
print('connector', [round(v) for v in _R], round(_conn.length), 'PIs', [tuple(round(c) for c in v) for v in (_PI1, _PI2, _PI3)])
add('yard_limit', limit, name='Yard limit', note='The deck and the flattened land north of it to Albone, east and south of Mill Creek (under Exposition Boulevard, the curved culvert from the roundabout to Millvale Boulevard, and Millvale Boulevard), west of the CUT structures and the APEx viaduct. The CUT platform deck and its throats are embanked (Ben, 26 October), so nothing runs under them.')

# ---- references: today's Queensgate (OSM yard tracks), historic yards (1904 and 1922 Sanborn, traced by eye)
osm = json.load(open(S + 'yard/osm_rail_deck.json'))
yl = [shape(f['geometry']) for f in osm['features'] if f['properties'].get('service') == 'yard']
qg = unary_union([g.buffer(3) for g in yl]).buffer(12).buffer(-12)
qg = unary_union([g for g in getattr(qg, 'geoms', [qg]) if g.area > 2000])
add('yard_today', qg, name='Queensgate yard today (OSM yard tracks)', area_m2=round(qg.area))
H = {
 'Riverfront yard (1922 Sanborn)': [(712335, 4330930), (712345, 4331000), (712450, 4331035), (712700, 4331045), (712900, 4331050), (712905, 4330885), (712700, 4330880), (712520, 4330905), (712420, 4330925)],
 'Mill Creek yard (1922 Sanborn)': [(712345, 4331560), (712335, 4332200), (712400, 4332200), (712430, 4332000), (712520, 4331880), (712470, 4331800), (712440, 4331560)],
 'McLean Avenue yard (1922 Sanborn)': [(712780, 4331580), (712780, 4332200), (712900, 4332200), (712900, 4331580)],
 'Brighton yard (1904 Sanborn)': [(712470, 4333340), (712480, 4333630), (712560, 4333630), (712640, 4333500), (712680, 4333350)],
}
for nme, c in H.items():
    g = Polygon(c); add('yard_hist', g, name=nme, area_m2=round(g.area))
print('historic total', round(sum(Polygon(c).area for c in H.values())), 'today', round(qg.area), 'limit', round(limit.area))

# ---- under-deck structures (boxes), each with its rail level and the yard floor there
def cls(z, n):
    if z is None: return 'unset'
    y = yard_z(n)
    if z <= y - 7.0: return 'under'
    if z >= y + 8.0: return 'over'
    return 'in'
add('ud_box', _blvd, name='Mill Creek culvert (under Exposition Boulevard)', kind='creek', cls='in', note='the yard stays east of it')
add('ud_box', _CONNSTRIP, name='Mill Creek culvert (Exposition Boulevard to Millvale Boulevard)', kind='creek', cls='in', note='Ben\u2019s sketch of 27 October, smoothed: curves of %d, %d and %d m, tangent to both boulevards; the Palace stands over it; 70 m wide at the boulevard narrowing to 45.7 m at Millvale (drawing values)' % (CONN_R[0], CONN_R[1], CONN_R[2]))
add('ud_box', unary_union([g.buffer(W_CULV / 2, cap_style=2) for k, g in _mv.items() if k in ('SMV0036', 'SMV0034', 'SMV0033')]), name='Mill Creek culvert (under Millvale Boulevard)', kind='creek', cls='in', note='to Albone; the yard stays east and south of it')
# RER A (Deck page levels, 10z.4): 135.9 under CUT, 1.8% up to Evans 147.5 under W Liberty, 148.4 at the deck edge
ra = [r for r in C['rer'] if r['id'] == 'R-A-712835-4331872'][0]; raL = LineString(ra['c'])
sE = raL.project(Point(712309.3, 4332365.2)); sD = raL.project(Point(712341.5, 4332787.8))
Z_EVANS = 139.0   # Ben, 27 October: RER A lowered at least 7 m under the yard floor from Evans to Union Terminal (was 147.5 m at Evans)
def za(s): return 135.9 + (Z_EVANS - 135.9) * s / sE if s <= sE else Z_EVANS + (148.4 - Z_EVANS) * (s - sE) / (sD - sE) if s <= sD else 148.4 + 0.033 * (s - sD)
def seg_classes(Lg, zf, half, name, kind, note=''):
    s = 0; cur = None; s0 = 0; tot = Lg.length
    while s <= tot + 1e-6:
        p = Lg.interpolate(s); c = cls(zf(s), p.y)
        if c != cur:
            if cur is not None: emit(Lg, s0, s, cur, zf, half, name, kind, note)
            cur, s0 = c, s
        s += 5
    emit(Lg, s0, tot, cur, zf, half, name, kind, note)
def emit(Lg, s0, s1, c, zf, half, name, kind, note):
    if s1 - s0 < 1: return
    g = substring(Lg, s0, s1); z0, z1 = zf(s0), zf(s1)
    p0, p1 = Lg.interpolate(s0), Lg.interpolate(s1)
    poly = g.buffer(half, cap_style=2, join_style=2).intersection(deck)
    add('ud_box', poly, name=name, kind=kind, cls=c, rail=[round(z0, 1) if z0 is not None else None, round(z1, 1) if z1 is not None else None],
        yard=[round(yard_z(p0.y), 1), round(yard_z(p1.y), 1)], note=note)
    add('ud_line', g, name=name, kind=kind, cls=c)
half_rer = 2.25 + 4.2
seg_classes(raL, za, half_rer, 'RER A', 'rer', 'lowered (Ben, 27 October): Evans 139.0 m, 135.9 m at the Union Terminal box, 2.2% up to the deck edge (148.4 m); was 147.5 m at Evans on the Deck page')
# B/D: Straight box 151.64 (Deck page), Western 138.4 and Union Terminal 135.7 (Rail Profiles station levels), straight grades between platform ends
bd = [r for r in C['rer'] if r['id'] == 'R-BD-712316-4334957'][0]; bdL = LineString(bd['c'])
sS = bdL.project(Point(712727.6, 4334135.5)); sW = bdL.project(Point(712686.6, 4333281.7)); sU = bdL.length  # the piece ends at the UT box
hp = 102.1
def zbd(s):
    if s <= sS - hp: return None   # north of Straight: ramp and viaduct, Deck page structure states
    if s <= sS + hp: return 151.64
    if s <= sW - hp: return 151.64 + (138.4 - 151.64) * (s - sS - hp) / (sW - hp - sS - hp)
    if s <= sW + hp: return 138.4
    return 138.4 + (135.7 - 138.4) * (s - sW - hp) / max(1, sU - sW - hp)
sub = substring(bdL, sS - hp, sU)
seg_classes(sub, lambda s: zbd(s + sS - hp), half_rer, 'RER B/D', 'rer', 'Straight 151.64 m (Deck page); Western 138.4 m, Union Terminal 135.7 m (Rail Profiles station levels); straight grades between')
# B/D north of Straight: the ramp is at yard level, the viaduct is over the deck
for r in C['rer_struct']:
    if r['line'] == 'B/D' and r['state'] == 'ramp':
        g = LineString(r['c']); add('ud_box', g.buffer(half_rer, cap_style=2, join_style=2).intersection(deck), name='RER B/D ramp (3.3% up from the Straight box)', kind='rer', cls='in', rail=[151.6, 165.2], note='Deck page structure state; clears freight only near its top')
        add('ud_line', g, name='RER B/D ramp', kind='rer', cls='in')
# RER E (Rail Profiles station levels: Mill Creek 137.11, Union Terminal 142.0; straight grade between) and the intercity pair's climb from the lower level to the CS bridge (144.0 m at the foot, 2.81% up, 10r.6)
re_ = [r for r in C['rer'] if r['id'] == 'R-E-716800-4335721'][0]; reL = LineString(re_['c']).intersection(deck.buffer(50))
if reL.geom_type == 'MultiLineString': reL = max(reL.geoms, key=lambda g: g.length)
sM = reL.project(Point(712264.4, 4330963.5)) if False else None
pE0, pE1 = Point(reL.coords[0]), Point(reL.coords[-1])
def zre(s):   # Union Terminal end at the north-east, Mill Creek at the south-west
    t = s / reL.length; n0 = reL.coords[0][1]; n1 = reL.coords[-1][1]
    zN, zS = 142.0, 137.11
    return zN + (zS - zN) * t if n0 > n1 else zS + (zN - zS) * t
seg_classes(reL, zre, half_rer, 'RER E', 'rer', 'Mill Creek 137.11 m and Union Terminal 142.0 m (Rail Profiles station levels), straight grade between')
for f in TK['features']:
    p = f['properties']
    if p.get('layer') == 'lower' and p['name'].startswith('Intercity pair (west track)'):
        icL = LineString(f['geometry']['coordinates'])
        if icL.coords[0][1] < icL.coords[-1][1]: icL = LineString(list(icL.coords)[::-1])   # from the foot (north) south
        seg_classes(icL, lambda s: 144.0 + 0.0281 * s, 4.0 + 4.2, 'Intercity pair to the CS bridge', 'lower', 'from the lower level (144.0 m) up 2.81% to the CS bridge (10r.6); both tracks')
# station boxes: platforms + track + 4.2 m (the structures rule), Metro and RER, with station levels where set
STL = {}
for rid in DB:
    for nm, z in (DB[rid].get('st') or {}).items(): STL.setdefault((DB[rid].get('line', ''), nm), z)
def st_level(sys_, line, name):
    if sys_ == 'metro':
        d = DB.get(line.replace(' ', '_'))
        return (d.get('st') or {}).get(name) if d else None
    for rid, d in DB.items():
        if rid.startswith('RER_') and name in (d.get('st') or {}): return d['st'][name]
    return None
for p in C['plats']:
    g = Polygon(p['c'])
    if not g.intersects(deck): continue
    z = st_level(p['sys'], p['line'], p.get('st'))
    if p['st'] == 'Straight': z = 151.64
    if p['st'] == 'Evans' and p['sys'] == 'rer': z = Z_EVANS
    bx = g.buffer((1.45 if p['sys'] == 'metro' else 1.75) + 4.2, join_style=2)
    n_ = g.centroid.y
    add('ud_box', bx, name=f"{p['st']} ({'Metro ' + p['line'] if p['sys'] == 'metro' else 'RER ' + p['line']}) station box", kind='station', sys=p['sys'], cls=cls(z, n_), rail=[z, z], yard=[round(yard_z(n_), 1)] * 2)
# CUT lower level (-2, 144 m) and the lower pairs under the deck: inside the CUT footprint (east of the limit), drawn for reference
for f in TK['features']:
    p = f['properties']
    if p.get('layer') == 'lower' and p.get('state') in ('under', 'ramp', 'climb') and shape(f['geometry']).intersects(deck):
        add('ud_line', shape(f['geometry']), name=p['name'], kind='lower', cls='in')
# Metro running tunnels, levels not set on the Rail Profiles page for most: drawn, not classed
for m in C['metro']:
    g = LineString(m['c']).intersection(deck)
    if not g.is_empty: add('ud_line', g, name=m['name'], kind='metro', cls='unset', era=m.get('era'))
json.dump({'type': 'FeatureCollection', 'features': out}, open(S + 'yard/part1.json', 'w'))
import collections
print(collections.Counter((f['properties']['layer'], f['properties'].get('cls')) for f in out))
