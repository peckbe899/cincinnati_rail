try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Part 2: proposed fan yards (CVG yard shape), their lead, the CUT lower box and dive cut, the deck cell grid. Writes deckpage/yard.json.
import json, sys, math
sys.path.insert(0, (_ws.CODE + 'yard'))
from lv import *
from shapely.geometry import shape, mapping, LineString, Polygon, Point, box
from shapely.ops import unary_union
P1 = json.load(open(S + 'yard/part1.json')); out = P1['features']
D = json.load(open(S + 'deckpage/deck.json')); TK = json.load(open(S + 'deckpage/tracks.json'))
deck = [shape(f['geometry']) for f in D['features'] if f['properties'].get('layer') == 'deck'][0]
limit = [shape(f['geometry']) for f in out if f['properties']['layer'] == 'yard_limit'][0]
def add(layer, g, **p):
    p['layer'] = layer; out.append({'type': 'Feature', 'properties': p, 'geometry': mapping(g)})

# ---- fillet a polyline with circular arcs of radius R at its interior vertices
def fillet(pts, R, step=4.0):
    res = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = map(lambda q: (float(q[0]), float(q[1])), (pts[i - 1], pts[i], pts[i + 1]))
        u = ((a[0] - b[0]), (a[1] - b[1])); lu = math.hypot(*u); u = (u[0] / lu, u[1] / lu)
        v = ((c[0] - b[0]), (c[1] - b[1])); lv_ = math.hypot(*v); v = (v[0] / lv_, v[1] / lv_)
        ang = math.acos(max(-1, min(1, u[0] * v[0] + u[1] * v[1])))   # interior angle
        defl = math.pi - ang
        if defl < 1e-4: res.append(b); continue
        T = R * math.tan(defl / 2); t1 = (b[0] + u[0] * T, b[1] + u[1] * T); t2 = (b[0] + v[0] * T, b[1] + v[1] * T)
        bis = (u[0] + v[0], u[1] + v[1]); lb = math.hypot(*bis); bis = (bis[0] / lb, bis[1] / lb)
        dc = R / math.sin(ang / 2); cc = (b[0] + bis[0] * dc, b[1] + bis[1] * dc)
        a1 = math.atan2(t1[1] - cc[1], t1[0] - cc[0]); a2 = math.atan2(t2[1] - cc[1], t2[0] - cc[0])
        d = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi; n = max(2, int(abs(d) * R / step))
        res += [(cc[0] + R * math.cos(a1 + d * k / n), cc[1] + R * math.sin(a1 + d * k / n)) for k in range(n + 1)]
    res.append(pts[-1]); return res

# ---- the CVG yard shape: straight side from the lead, the ladder side out at the ladder angle with fillets, then the body
TH, RF = math.radians(24.0), 150.0   # read off the CVG Express yard (Final.kmz): about 24 deg ladder, fillets about 150 m (drawing values)
def fan(xs, Na, Ns, w, sd=+1):
    Ld = (w - 2 * RF * (1 - math.cos(TH))) / math.sin(TH)
    p0 = (xs, Na); p1 = (xs + sd * RF * (1 - math.cos(TH)), Na - RF * math.sin(TH))
    pv1 = (xs, Na - RF * math.tan(TH / 2))   # vertex of the first fillet
    pv2 = (xs + sd * w, Na - RF * math.tan(TH / 2) - (w / math.tan(TH)))
    lad = fillet([p0, pv1, pv2, (xs + sd * w, Ns)], RF)
    ring = [(xs, Ns), p0] + lad[1:] + [(xs + sd * w, Ns)]
    return Polygon(ring), Na - (pv2[1] - RF * math.tan(TH / 2) - Na) * -1
# lead: from the deck's north end at Hopple, west of the APEx viaduct and the B/D ramp, under the B/D viaduct at Camp Washington,
# then east of the Palace (solid ground, not decked) into the yard's straight east side
RL = 400.0
XE, WID, NA, NS = 712675.0, 215.0, 4333880.0, 4332140.0
P0, P1_, P2 = (712150.0, 4335575.0), (712160.0, 4335050.0), (XE, 4334050.0)
lead = LineString(fillet([P0, P1_, P2, (XE, NA)], RL))
fanN, _ = fan(XE, NA, NS, WID, sd=-1)
print('fan area', round(fanN.area), 'inside limit', fanN.within(limit.buffer(0.5)), round(fanN.difference(limit).area), ' lead inside', lead.within(limit.buffer(0.5)))
hits = [(g['properties']['name'], g['properties'].get('cls'), round(shape(g['geometry']).intersection(fanN).area)) for g in out if g['properties']['layer'] == 'ud_box' and shape(g['geometry']).intersects(fanN)]
print('fan touches', hits)
print('lead touches', [(g['properties']['name'], g['properties'].get('cls')) for g in out if g['properties']['layer'] == 'ud_box' and shape(g['geometry']).intersects(lead.buffer(4.5))])
ym = lambda f: (round(yard_z(f.bounds[3]), 1), round(yard_z(f.bounds[1]), 1))
add('yard_fan', fanN, name='North yard (draft)', area_m2=round(fanN.area), width_m=WID, length_m=round(fanN.bounds[3] - fanN.bounds[1]), floor=list(ym(fanN)),
    note='CVG yard shape: straight east side from the lead, ladder side out to the west, stub ends at the south (unloading, no through running)')
add('yard_lead', lead, name='Yard lead (Hopple to the North yard)', length_m=round(lead.length), note='at grade north of Hopple (no cut north of it, 10d.4); under Hopple, west of the APEx viaduct and the B/D ramp, under the B/D viaduct by Camp Washington, east of the Palace; curves 400 m (drawing value)')

# ---- CUT lower level box (-2, 144 m) and the dive cut, east of the limit, for reference
lw = [shape(f['geometry']) for f in TK['features'] if f['properties'].get('layer') in ('lower', 'lower_plat') and f['properties'].get('level') == '-2']
cutbox = unary_union([g.buffer(4.2, cap_style=2, join_style=2) for g in lw]).intersection(box(712600, 4331600, 712900, 4332420))
add('ud_box', cutbox, name='CUT lower level (-2) and its north fan', kind='cut', cls='in', rail=[144.0, 144.0], yard=[round(yard_z(4331800), 1)] * 2, note='under the embanked platform deck, east of the limit')
for f in D['features']:
    if f['properties'].get('layer') == 'dive_cut': add('ud_box', shape(f['geometry']), name='Lower-pair dive, open cut (Bank to Findlay)', kind='cut', cls='in', note='under the north arch viaduct, east of the limit')

# ---- deck cells: column lines along the yard tracks and cell walls across, 20 m each way (4 tracks a bay at 5 m: drawing values)
cols, walls = [], []
x = XE - 20 * math.floor((XE - limit.bounds[0]) / 20)
while x <= limit.bounds[2]:
    g = LineString([(x, limit.bounds[1] - 5), (x, limit.bounds[3] + 5)]).intersection(limit)
    if not g.is_empty: cols.append(g)
    x += 20
n = NS - 20 * math.floor((NS - limit.bounds[1]) / 20)
while n <= limit.bounds[3]:
    g = LineString([(limit.bounds[0] - 5, n), (limit.bounds[2] + 5, n)]).intersection(limit)
    if not g.is_empty: walls.append(g)
    n += 20
add('deck_col', unary_union(cols), name='Deck column lines (every 20 m, along the yard tracks)')
add('deck_cell', unary_union(walls), name='Deck cell walls (every 20 m, across)')
# yard floor marks
for nn in range(4331000, 4335600, 500):
    xs = [g.bounds for g in getattr(LineString([(711000, nn), (714000, nn)]).intersection(limit), 'geoms', [LineString([(711000, nn), (714000, nn)]).intersection(limit)]) if not g.is_empty]
    if xs: add('yard_mark', Point(max(xs, key=lambda b: b[2] - b[0])[2] - 8, nn), deck=round(deck_z(nn), 1), floor=round(yard_z(nn), 1))
FC = {'type': 'FeatureCollection', 'crs': 'EPSG:26916', 'note': 'Yards under the deck: draft (27 October 2026). Yard floor = deck - 8.5 m (10d.4). Classes: in = rail within the yard space (blocks the yard); under = rail 7 m or more under the yard floor (yard can run over it); over = rail 8 m or more over the yard floor (piers only); unset = no level set. The 7 m and 8 m margins, the 20 m cells, the 400 m lead curves and the fan geometry are drawing values, not checked figures.', 'features': out}
for f in out:   # round coordinates
    def r(c): return [r(v) for v in c] if isinstance(c[0], (list, tuple)) else [round(c[0], 1), round(c[1], 1)]
    f['geometry'] = json.loads(json.dumps(f['geometry'])); g = f['geometry']
    if g['type'] == 'GeometryCollection': continue
    g['coordinates'] = r(g['coordinates']) if g['type'] != 'Point' else [round(g['coordinates'][0], 1), round(g['coordinates'][1], 1)]
json.dump(FC, open(S + 'deckpage/yard.json', 'w'), separators=(',', ':'))
import os; print('yard.json', os.path.getsize(S + 'deckpage/yard.json'), 'features', len(out))
