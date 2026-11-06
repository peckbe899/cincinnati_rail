"""Sketch only: proposed streets for the west side of the valley, W 6th to Ralston, east of State Ave and Beekman St."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, math, numpy as np
from shapely.geometry import LineString, Point, shape
from shapely.ops import unary_union, linemerge
SP = _ws.DATA
D = json.load(open(SP + 'deckpage/deck.json')); F = D['features']
O = json.load(open(SP + 'lph/osm_north.geojson'))['features']
picks = json.load(open(SP + 'lph/wb_picks.json'))
bl = [f for f in F if f['properties']['layer'] == 'boulevard'][0]['geometry']['coordinates'][0]
U = np.array(bl[3]) - np.array(bl[0]); U /= np.linalg.norm(U); Wd = np.array([U[1], -U[0]])   # north on the axis; east on its square
def unit(b): r = math.radians(b); return np.array([math.sin(r), math.cos(r)])
osm = lambda nm: unary_union([shape(f['geometry']) for f in O if f['properties'].get('name') == nm and shape(f['geometry']).geom_type == 'LineString'])
STATE, BEEK = osm('State Avenue'), osm('Beekman Street')
WEST = unary_union([STATE, BEEK])
PK = {(a, b): (e, n) for s, a, b, e, n, side, d in picks}
def pk(a, b): return np.array(PK.get((a, b)) or PK[(b, a)], float)
st = {}
for f in F:
    p = f['properties']
    if p['layer'] == 'street': st.setdefault(p['name'], []).append((p, LineString(f['geometry']['coordinates'])))
EDGE_W = LineString([tuple(np.array(bl[0]) - U * 200), tuple(np.array(bl[3]) + U * 200)])
def ray_to(p, d, target, maxl=2000):
    g = LineString([tuple(p), tuple(np.array(p) + d * maxl)]).intersection(target)
    if g.is_empty: return None
    g = min(getattr(g, 'geoms', [g]), key=lambda q: q.distance(Point(p)))
    return np.array(g.coords[0]) if g.geom_type != 'Point' else np.array([g.x, g.y])
P = []   # (zone, name, line, kind)  kind: new / reconnect / 1904 / option
# ---- zone A: the Exposition grounds, Hopkins to State/Harrison: basin streets carried across the boulevard to State on the grid
for nm in ('Kenner', 'Courtland', 'Flint', 'Wade', 'Wilstach', 'Sherman', 'Poplar', 'Findlay', 'York', 'Exeter', 'Dayton', 'Bank', 'Dolph', 'McRoberts'):
    for p, l in st.get(nm, []):
        if p.get('side') != 'E': continue
        c = list(l.coords); w = np.array(min(c, key=lambda q: q[0]))
        if abs(w[0] - (bl[0][0] + (w[1] - bl[0][1]) * U[0] / U[1]) - 70) > 15: continue    # piece that ends at the boulevard's east edge
        e = ray_to(w, -Wd, WEST)
        if e is not None: P.append(('A', nm, LineString([tuple(w), tuple(e)]), 'new'))
# N-S: Depot, Summer, Berlin, Evans carried north on the axis bearing to State; a new street midway between Evans and the boulevard
for nm, p0 in (('Depot', (711720.0, 4331777.0)), ('Summer', (711879.5, 4331898.0)), ('Berlin', (711952.0, 4331909.0)), ('Evans', (712022.0, 4331818.0))):
    e = ray_to(p0, U, WEST)
    if e is not None: P.append(('A', nm + ' (north)', LineString([p0, tuple(e)]), 'new'))
hop = [l for p, l in st['Hopkins']][0]; ev = np.array([712022.0, 4331818.0]); bw = ray_to(ev, Wd, EDGE_W)
mid = (ev + bw) / 2; mid = np.array(LineString([tuple(mid - U * 100), tuple(mid + U * 100)]).intersection(hop).coords[0])
e = ray_to(mid, U, WEST); P.append(('A', 'new N-S (Hopkins to State)', LineString([tuple(mid), tuple(e)]), 'new'))
w8 = [l for p, l in st['W 8th (viaduct line)']][0]; s8 = ray_to(mid, -U, w8)
P.append(('A', 'new N-S (W 8th to Hopkins)', LineString([tuple(s8), tuple(mid)]), 'option'))
# ---- zone 2: Queen City to Hopple on the deck grid (Ben: fill it like zone 1)
deck = max(getattr(_dk := [shape(f['geometry']) for f in F if f['properties']['layer'] == 'deck'][0], 'geoms', [_dk]), key=lambda g: g.area)
from shapely.geometry import Polygon, box
pal = [shape(f['geometry']) for f in F if f['properties']['layer'] == 'block' and f['properties']['type'] == 'park' and shape(f['geometry']).bounds[1] > 4333600][0]
civic = unary_union([pal] + [shape(f['geometry']).buffer(4) for f in F if f['properties']['layer'] in ('roundabout', 'palace', 'forecourt')])
BK04 = [('Beekman Street', 'Queen City Avenue'), ('Beekman Street', 'Tremont Street'), ('Beekman Street', 'Waverly Avenue'), ('Beekman Street', 'Knox Street'),
        ('Beekman Street', 'Fairmount Avenue'), ('Western Avenue', 'Cummings Street'), ('Western Avenue', 'Vinton Street'), ('Western Avenue', 'Dempsey Street'),
        ('Baltimore Avenue', 'Western Avenue'), ('Carll Street', 'Western Avenue'), ('Holliday Street', 'Western Avenue'), ('Denham Street', 'Western Avenue'),
        ('Pulte Street', 'Western Avenue'), ('South Hopple Street', 'Western Avenue'), ('Hopple Street', 'Western Avenue')]
bc = [tuple(pk(*k)) for k in BK04]; bk = LineString(bc)          # Beekman as the 1904 sheets have it (Western Avenue north of Fairmount)
BEEK = unary_union([BEEK.difference(box(711800, 4333600, 712500, 4334925)), bk])
P.append(('2', 'Beekman Street (1904 Beekman / Western Avenue)', bk, '1904'))
W2 = Polygon(bc + [(712950, bc[-1][1]), (712950, bc[0][1])]).buffer(0).intersection(box(711800, 4333645, 712950, 4334915))
rest = W2.difference(deck)
strip = unary_union([g for g in getattr(rest, 'geoms', [rest]) if g.distance(bk) < 3])
R2 = unary_union([W2.intersection(deck), strip]).difference(civic).buffer(0)
def clip_add(zone, nm, line, kind='new', minl=40):
    g = line.intersection(R2)
    for q in getattr(g, 'geoms', [g]):
        if q.geom_type == 'LineString' and q.length > minl: P.append((zone, nm, q, kind))
TW, TA = math.degrees(math.atan2(*Wd)) % 360, math.degrees(math.atan2(*U)) % 360
def ew(y500, nm):   # E-W grid line through y at x = 712500
    p0 = np.array([712500.0, y500]); return LineString([tuple(p0 - Wd * 1200), tuple(p0 + Wd * 600)])
# north of the Palace grounds: Camp Washington's grid (Ben, 2026-10-13). Its E-W streets (1904 and 1922 plates 16L, 34R) run
# about 93.0 deg (Alfred 92.98, Straight 93.04, Marshall 93.13, Township 92.79); its N-S streets follow Garrard Avenue (3.36 deg).
TE, TN = 93.0, 3.36
uE, uN = unit(TE), unit(TN)
def ewl(p0): p0 = np.array(p0, float); return LineString([tuple(p0 - uE * 1000), tuple(p0 + uE * 1000)])
def nsl(p0): p0 = np.array(p0, float); return LineString([tuple(p0 - uN * 1300), tuple(p0 + uN * 1)])
north_of = lambda y: (lambda g: g)
CW = [('Alfred (Camp Washington line)', (712772.0, 4333981.0), 'reconnect'), ('Straight (Camp Washington line)', (712804.0, 4334170.0), 'reconnect'),
      ('Marshall (Camp Washington line)', (712752.0, 4334368.0), 'reconnect'), ('Township (carried west)', (712495.0, 4334672.0), 'reconnect')]
R2full = unary_union([W2.intersection(deck), strip]).buffer(0)
for nm, p0, k in CW:
    g = ewl(p0).intersection(R2full if nm.startswith('Alfred') else R2)
    for q in getattr(g, 'geoms', [g]):
        if q.geom_type == 'LineString' and q.length > 40: P.append(('2', nm, q, k))
# new E-W lines between them, laid from the 1904 cross streets on Beekman where one falls in the gap
for nm, p0 in (('new E-W (Alfred-Straight)', (712500.0, 4334091.0)), ('Dempsey (carried east)', tuple(pk('Western Avenue', 'Dempsey Street'))),
               ('Baltimore (carried east)', tuple(pk('Baltimore Avenue', 'Western Avenue'))), ('Carll (carried east)', tuple(pk('Carll Street', 'Western Avenue'))),
               ('South Hopple (carried east)', tuple(pk('South Hopple Street', 'Western Avenue')))):
    clip_add('2', nm, ewl(p0))
# Willow Lane (1922, to Rawson) carried west to Pulte Street on Beekman (5 m off the grid line)
clip_add('2', 'Willow Lane-Pulte', LineString([(712534.0, 4334708.0), (712497.0, 4334712.0), tuple(pk('Pulte Street', 'Western Avenue'))]), kind='reconnect')
# N-S: Rawson, Meeker and Johnson carried south over the deck; two more west of Johnson, 100 m apart
for nm, p0 in (('Meeker (carried south)', (712559.0, 4334769.0)), ('Rawson (carried south)', (712495.0, 4334672.0)), ('Johnson (carried south)', (712389.0, 4334874.0))):
    clip_add('2', nm, nsl(p0))
J = np.array([712389.0, 4334874.0]); wE = np.array([uN[1], -uN[0]])
for off in (100, 200, 300):
    g = nsl(J - wE * off).intersection(R2)
    for q in getattr(g, 'geoms', [g]):
        if q.geom_type == 'LineString' and q.length > 40 and min(c[1] for c in q.coords) > 4333990: P.append(('2', f'new N-S (Johnson - {off} m)', q, 'new'))
PE = nsl(J)
P.append(('2', 'Queen City (roundabout to Beekman)', LineString([(712350.0, 4333652.0), tuple(pk('Beekman Street', 'Queen City Avenue'))]), 'new'))
P.append(('2', 'Alfred to Fairmount', LineString([(712329.0, 4334012.0), tuple(pk('Beekman Street', 'Fairmount Avenue'))]), 'reconnect'))
for nm in ('Tremont Street', 'Waverly Avenue', 'Knox Street'):
    b0 = pk('Beekman Street', nm); e = ray_to(b0, Wd, PE)
    if e is not None: P.append(('2', nm.split()[0] + ' (east)', LineString([tuple(b0), tuple(e)]), 'new'))
# Cummings Street (1904) along Beekman, with the 1904 cross streets that reached it
cm = [pk('Western Avenue', 'Cummings Street'), pk('Cummings Street', 'Vinton Street'), pk('Dempsey Street', 'Cummings Street'), pk('Carll Street', 'Cummings Street'), pk('Denham Street', 'Cummings Street')]
P.append(('2', 'Cummings Street (1904)', LineString([tuple(q) for q in cm]), '1904'))
for a_, c_ in (('Vinton Street', ('Cummings Street', 'Vinton Street')), ('Denham Street', ('Denham Street', 'Cummings Street'))):
    P.append(('2', a_.split()[0] + ' (1904, to Cummings)', LineString([tuple(pk('Western Avenue', a_)), tuple(pk(*c_))]), '1904'))
BASIN = json.load(open(SP + 'deckpage/basin.json'))['features']
def bend(nm, near):
    best = None
    for f in BASIN:
        if f['properties'].get('name') != nm or f['properties']['layer'] != 'street': continue
        c = np.array(f['geometry']['coordinates']); w = c[np.argmin(c[:, 0])]
        d = np.hypot(*(w - np.array(near)))
        if best is None or d < best[0]: best = (d, w)
    return best[1]
# ---- zone E: north of Hopple: Camp Washington's E-W streets carried west to Beekman; South Cumminsville's N-S streets carried south
for nm, near in (('Stock Avenue', (712386, 4335144)), ('Ethan Avenue', (712455, 4335241)), ('Bates Avenue', (712454, 4335316)), ('Alabama Avenue', (712382, 4335399)),
                 ('Monmouth Avenue', (712460, 4335571)), ('Sassafras Street', (712466, 4335729)), ('Arlington Street', (712468, 4335803)), ('Marquis Avenue', (712380, 4335884)),
                 ('Adelaide Street', (712363, 4335972)), ('Brashears Street', (712458, 4336082)), ('Earl Avenue', (712442, 4336218))):
    w = bend(nm, near); e = ray_to(w, -unit(93.6), BEEK)
    if e is not None: P.append(('E', nm.split()[0] + ' (west)', LineString([tuple(w), tuple(e)]), 'new'))
dre = None
for nm, near, b in (('Follett Avenue', (712070, 4336465), 2.7), ('Roll Avenue', (711993, 4336469), 3.2), ('Dawson Avenue', (711913, 4336474), 3.1), ('Borden Street', (711807, 4336370), 3.1)):
    w = None
    for f in BASIN:
        if f['properties'].get('name') != nm or f['properties']['layer'] != 'street': continue
        c = np.array(f['geometry']['coordinates']); s = c[np.argmin(c[:, 1])]
        if np.hypot(*(s - np.array(near))) < 40: w = s
    if w is None: continue
    hp = [l for p, l in st.get('Hopple', [])] or []
    tgt = unary_union([shape(f['geometry']) for f in BASIN if f['properties'].get('name') == 'Hopple Street' and f['properties']['layer'] == 'street'] + [BEEK])
    e = ray_to(w, -unit(b), tgt)
    if e is not None: P.append(('E', nm.split()[0] + ' (south)', LineString([tuple(w), tuple(e)]), 'new'))
json.dump([dict(zone=z, name=n, kind=k, coords=[[round(x, 1), round(y, 1)] for x, y in l.coords], length=round(l.length)) for z, n, l, k in P], open(SP + 'lph/wb_proposal.json', 'w'))
from collections import defaultdict
tot = defaultdict(float)
for z, n, l, k in P: tot[z] += l.length
print({z: round(v) for z, v in tot.items()}, len(P))
for z, n, l, k in P: print(z, n, k, round(l.length))
