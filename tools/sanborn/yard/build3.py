try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Part 3: the yard after the real Queensgate yard (receiving yard, hump, bowl, departure to the CS bridge, stub tracks to the river). Writes deckpage/yard.json.
import json, sys, math
sys.path.insert(0, (_ws.CODE + 'yard'))
from lv import *
from shapely.geometry import shape, mapping, LineString, Polygon, Point, box, MultiLineString
from shapely.ops import unary_union, substring
from shapely import affinity
P1 = json.load(open(S + 'yard/part1.json')); out = P1['features']
D = json.load(open(S + 'deckpage/deck.json')); TK = json.load(open(S + 'deckpage/tracks.json'))
deck = [shape(f['geometry']) for f in D['features'] if f['properties'].get('layer') == 'deck'][0]
limit = [shape(f['geometry']) for f in out if f['properties']['layer'] == 'yard_limit'][0]
BLOCK = unary_union([shape(f['geometry']) for f in out if f['properties']['layer'] == 'ud_box' and f['properties'].get('cls') == 'in'])
ROOM = limit.buffer(-3).difference(BLOCK.buffer(3))
def add(layer, g, **p):
    p['layer'] = layer; out.append({'type': 'Feature', 'properties': p, 'geometry': mapping(g)})
SP = 4.5            # track spacing: the real yard's median (OSM, 4.25-5.2 m)
TH = math.radians(17)   # spread of the real bowl fan (about 185 m over 600 m)
RF = 190.0

def fil(pts, R):
    res = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        u = (a[0] - b[0], a[1] - b[1]); lu = math.hypot(*u); v = (c[0] - b[0], c[1] - b[1]); lv_ = math.hypot(*v)
        if lu < 1e-6 or lv_ < 1e-6: continue
        u = (u[0] / lu, u[1] / lu); v = (v[0] / lv_, v[1] / lv_)
        ang = math.acos(max(-1, min(1, u[0] * v[0] + u[1] * v[1]))); defl = math.pi - ang
        if defl < 1e-3: res.append(b); continue
        T = min(R * math.tan(defl / 2), lu * 0.95, lv_ * 0.95); Rr = T / math.tan(defl / 2)
        t1 = (b[0] + u[0] * T, b[1] + u[1] * T); t2 = (b[0] + v[0] * T, b[1] + v[1] * T)
        bis = (u[0] + v[0], u[1] + v[1]); lb = math.hypot(*bis); bis = (bis[0] / lb, bis[1] / lb)
        cc = (b[0] + bis[0] * Rr / math.sin(ang / 2), b[1] + bis[1] * Rr / math.sin(ang / 2))
        a1 = math.atan2(t1[1] - cc[1], t1[0] - cc[0]); a2 = math.atan2(t2[1] - cc[1], t2[0] - cc[0]); d = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        n = max(2, int(abs(d) * Rr / 4)); res += [(cc[0] + Rr * math.cos(a1 + d * k / n), cc[1] + Rr * math.sin(a1 + d * k / n)) for k in range(n + 1)]
    res.append(pts[-1]); return res

def keep_from(line, anchor_pt, room):
    """the part of a track inside the room that holds the end nearest the throat"""
    g = line.intersection(room)
    parts = [x for x in getattr(g, 'geoms', [g]) if x.geom_type == 'LineString' and x.length > 0]
    if not parts: return None
    return min(parts, key=lambda x: x.distance(Point(anchor_pt)))

tracks = []
def track(line, yard, kind, minlen=150):
    if line is None or line.length < minlen: return
    tracks.append((yard, kind, line))

# ---------- frame helpers: build in a local frame (throat-to-throat axis pointing down the page), rotate back
def frame(p_from, p_to):
    ang = math.degrees(math.atan2(p_to[0] - p_from[0], -(p_to[1] - p_from[1])))   # rotation from 'south' to the axis
    return ang
def rot(g, ang, origin): return affinity.rotate(g, ang, origin=origin)

# ---------- 1. lead from Hopple, receiving yard in the north lobe (the real yard's receiving yard is north of its hump too)
P0 = (712150.0, 4335575.0)
RN = (712180.0, 4335130.0)     # receiving yard, north throat
RS = (712640.0, 4334090.0)     # receiving yard, south throat (to the hump)
H = (712640.0, 4333950.0)      # hump, east of the Palace
RN = (712160.0, 4335150.0)
lead_n = LineString(fil([P0, RN], 300))
spine = LineString(fil([RN, (712150.0, 4334950.0), (712230.0, 4334750.0), (712350.0, 4334550.0), (712460.0, 4334350.0), (712560.0, 4334180.0), RS], 450))
TR = TH
nrec = 0
for k in range(-45, 46):
    v = k * SP; ln = abs(v) / math.tan(TR) + 40
    if spine.length - 2 * ln < 250: continue
    off = spine.offset_curve(v) if v else spine
    if off.is_empty or off.geom_type != 'LineString': continue
    body = substring(off, ln * off.length / spine.length, off.length - ln * off.length / spine.length)
    t = LineString(fil([RN] + list(body.coords)[::max(1, len(body.coords) // 40)] + [body.coords[-1], RS], RF))
    if t.within(ROOM.buffer(0.01)): track(t, 'Receiving yard', 'yard'); nrec += 1
lead_h = LineString([RS, H])
# ---------- 2. bowl (classification yard) south of the Palace: hump H to the departure throat DT
DT = (712655.0, 4331960.0)
X0, X1 = 712405.0, 712698.0
nb = 0; xs = []
x = X0
while x <= X1 + 0.01: xs.append(x); x += SP
for x in xs:
    dn = abs(x - H[0]) / math.tan(TH) + 60; ds = abs(x - DT[0]) / math.tan(TH) + 60
    n_top, n_bot = H[1] - dn, DT[1] + ds
    if n_top - n_bot < 250: continue
    t = LineString(fil([H, (x, n_top), (x, n_bot), DT], RF))
    if t.within(ROOM.buffer(0.01)): track(t, 'Bowl (classification)', 'yard'); nb += 1
    else:
        g = keep_from(t, H, ROOM)   # a track that hits something becomes a stub from the hump end
        if g is not None and g.length > 400: track(g, 'Bowl (classification)', 'stub'); nb += 1
# ---------- 3. departure: from DT onto the intercity pair at its foot (144 m), then the CS bridge
J = (712752.0, 4331610.0)
dep = LineString(fil([DT, (712700.0, 4331800.0), J], 260))
# ---------- 4. stub tracks to the river (south deck): throat ZT off the departure lead, tracks run south and stop at the deck's south edge or at a structure in the yard space
ZT = (712570.0, 4331880.0)
TZ = TH
ns = 0
x = 712300.0
while x <= 712700.0:
    dn = abs(x - ZT[0]) / math.tan(TZ) + 40
    if ZT[1] - dn > 4330950:
        t = LineString(fil([ZT, (x, ZT[1] - dn), (x, 4330600.0)], RF))
        g = keep_from(t, ZT, ROOM)
        if g is not None and (ZT[1] - dn) - g.bounds[1] >= 200: track(g, 'Stub tracks to the river', 'stub'); ns += 1
    x += SP
lead_z = LineString(fil([DT, (712610.0, 4331920.0), ZT], 200))
print('receiving', nrec, 'bowl', nb, 'stub', ns)
# ---------- output: tracks, leads, yard footprints (selectable), totals
def footprint(name):
    ls = [l for y, k, l in tracks if y == name]
    return unary_union([l.buffer(SP / 2 + 1.5, cap_style=2) for l in ls]).buffer(6).buffer(-6), ls
for name, note in [('Receiving yard', 'Arrivals from the north (Hopple lead); trains are pushed over the hump at its south end, as at the real yard'),
                   ('Bowl (classification)', 'Hump at the north end beside the Palace; tracks run south to the departure throat (through tracks) or stop where a structure is in the yard space (stubs)'),
                   ('Stub tracks to the river', 'Unloading and team tracks off the departure throat, stub-ended at the deck’s south edge or at a structure in the yard space')]:
    fp, ls = footprint(name)
    if fp.is_empty: continue
    tl = sum(l.length for l in ls); nst = sum(1 for y, k, l in tracks if y == name and k == 'stub')
    add('yard_fan', fp, name=name, area_m2=round(fp.area), tracks=len(ls), stubs=nst, track_km=round(tl / 1000, 1), floor=[round(yard_z(fp.bounds[3]), 1), round(yard_z(fp.bounds[1]), 1)], note=note)
for y, k, l in tracks:
    add('yard_track', l, yard=y, kind=k, length_m=round(l.length))
for name, g, note in [('Lead from Hopple', lead_n, 'At grade north of Hopple (no cut north of it, 10d.4); under Hopple, west of the APEx viaduct'),
                      ('Hump lead', lead_h, 'Receiving yard to the hump crest, east of the Palace (solid ground, not decked)'),
                      ('Departure to the CS bridge', dep, 'Double track from the bowl’s south throat over RER A (deep there) onto the intercity pair at its foot (144 m), then up its 2.81% to the Cincinnati Southern bridge'),
                      ('Stub track lead', lead_z, 'Off the departure throat to the stub tracks')]:
    add('yard_lead', g, name=name, length_m=round(g.length), note=note)
tot_tr = sum(l.length for y, k, l in tracks)
print('tracks', len(tracks), 'track km', round(tot_tr / 1000, 1))
# keep the CUT box, dive cut, deck grid and marks from part 2 logic
lw = [shape(f['geometry']) for f in TK['features'] if f['properties'].get('layer') in ('lower', 'lower_plat') and f['properties'].get('level') == '-2']
cutbox = unary_union([g.buffer(4.2, cap_style=2, join_style=2) for g in lw]).intersection(box(712600, 4331600, 712900, 4332420))
add('ud_box', cutbox, name='CUT lower level (-2) and its north fan', kind='cut', cls='in', rail=[144.0, 144.0], yard=[round(yard_z(4331800), 1)] * 2, note='under the embanked platform deck, east of the limit')
for f in D['features']:
    if f['properties'].get('layer') == 'dive_cut': add('ud_box', shape(f['geometry']), name='Lower-pair dive, open cut (Bank to Findlay)', kind='cut', cls='in', note='under the north arch viaduct, east of the limit')
cols, walls = [], []
x = X0 - 20 * math.floor((X0 - limit.bounds[0]) / 20)
while x <= limit.bounds[2]:
    g = LineString([(x, limit.bounds[1] - 5), (x, limit.bounds[3] + 5)]).intersection(limit)
    if not g.is_empty: cols.append(g)
    x += 20
n = 4332000 - 20 * math.floor((4332000 - limit.bounds[1]) / 20)
while n <= limit.bounds[3]:
    g = LineString([(limit.bounds[0] - 5, n), (limit.bounds[2] + 5, n)]).intersection(limit)
    if not g.is_empty: walls.append(g)
    n += 20
add('deck_col', unary_union(cols), name='Deck column lines (every 20 m)')
add('deck_cell', unary_union(walls), name='Deck cell walls (every 20 m, across)')
for nn in range(4331000, 4335600, 500):
    ii = LineString([(711000, nn), (714000, nn)]).intersection(limit)
    xs_ = [g.bounds for g in getattr(ii, 'geoms', [ii]) if not g.is_empty]
    if xs_: add('yard_mark', Point(max(xs_, key=lambda b: b[2] - b[0])[2] - 8, nn), deck=round(deck_z(nn), 1), floor=round(yard_z(nn), 1))
def r(c): return [r(v) for v in c] if isinstance(c[0], (list, tuple)) else [round(c[0], 1), round(c[1], 1)]
for f in out:
    g = json.loads(json.dumps(f['geometry'])); f['geometry'] = g
    g['coordinates'] = r(g['coordinates']) if g['type'] != 'Point' else [round(g['coordinates'][0], 1), round(g['coordinates'][1], 1)]
FC = {'type': 'FeatureCollection', 'crs': 'EPSG:26916', 'note': 'Yards under the deck: draft 2 (27 October 2026), after the real Queensgate yard. Yard floor = deck - 8.5 m (10d.4). Track spacing 4.5 m and fan spread 17 deg measured off the real yard (OSM); curves 190 m, margins 7 m / 8 m and 20 m cells are drawing values.', 'features': out}
json.dump(FC, open(S + 'deckpage/yard.json', 'w'), separators=(',', ':'))
import os; print('yard.json', os.path.getsize(S + 'deckpage/yard.json'))
