try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben (18 October): the traced taxiways were jagged and copied the diagram's lettering; the diagram was for inspiration. CVG here is a
# very busy transcontinental hub (Pan Am hub; United, Delta and American gates; mostly widebodies because of the APEx; GE maintenance).
# The airside is designed instead, to ICAO Code E/F practice (drawing values): taxiways 25 m wide on centre lines, parallels 190 m off
# the runway centre lines, rapid-exit taxiways at 30 degrees, entries at every runway end, fillets at every junction; aprons round each
# concourse with widebody stands (80 m wide, 70 m deep, nose-in) and a 45 m taxilane behind them; stands that would sit in a runway strip
# (150 m either side), on a taxiway strip or on another stand are dropped; cargo and maintenance aprons at the hubs and hangar areas.
# Writes deckpage/airport.json layers cvg_taxi (pavement), cvg_taxi_cl (centre lines), cvg_apron, cvg_stand.
import json, math, numpy as np
from shapely.geometry import LineString, Polygon, Point, shape, mapping, box
from shapely.ops import unary_union
S = _ws.DATA
A = json.load(open(S + 'deckpage/airport_v58.json'))
RW = {f['properties']['name'].replace('Runway ', ''): [np.array(c, float) for c in f['geometry']['coordinates']] for f in A['features'] if f['properties']['layer'] == 'cvg_runway_cl'}
RWP = unary_union([shape(f['geometry']) for f in A['features'] if f['properties']['layer'] == 'cvg_runway'])
BLD = {f['properties']['name']: shape(f['geometry']) for f in A['features'] if f['properties']['layer'] == 'cvg_building'}
AREA = {f['properties']['name']: shape(f['geometry']) for f in A['features'] if f['properties']['layer'] == 'cvg_area'}
TW, OFF, RS = 25.0, 190.0, 150.0
def frame(nm):
    a, b = RW[nm]; L = np.linalg.norm(b - a); u = (b - a) / L; n = np.array([-u[1], u[0]]); return a, b, L, u, n
def P(nm, s, o): a, b, L, u, n = frame(nm); return tuple(a + u * s + n * o)
CL = []     # (name, LineString)
def tw(name, pts): CL.append((name, LineString(pts)))
# ---------------------------------------------------------------- parallels (side +1 = left of the a->b direction)
PAR = {('18R/36L', 'E'): 'A', ('18C/36C', 'W'): 'C', ('18C/36C', 'E'): 'D', ('18L/36R', 'W'): 'T', ('18L/36R', 'E'): 'S',
       ('9L/27R', 'N'): 'K', ('9L/27R', 'S'): 'M', ('9R/27L', 'N'): 'N', ('9R/27L', 'S'): 'R'}
CMP = {'E': np.array([1, 0]), 'W': np.array([-1, 0]), 'N': np.array([0, 1]), 'S': np.array([0, -1])}
for (nm, comp), letter in PAR.items():
    a, b, L, u, n = frame(nm); side = 1 if n @ CMP[comp] > 0 else -1
    tw(f'Taxiway {letter} (parallel to {nm})', [P(nm, -60, side * OFF), P(nm, L + 60, side * OFF)])
    for s in (0.0, L):                                   # entries at the runway ends (90 degrees)
        tw(f'Taxiway {letter} entry', [P(nm, s, side * OFF), P(nm, s, 0)])
    # rapid exits, 30 degrees, two for each landing direction, at about 1,700 and 2,300 m from the threshold
    for land_from, sgn in ((0.0, 1), (L, -1)):
        for d in (1700.0, 2300.0):
            if d > L - 700: continue
            s0 = land_from + sgn * d; run = OFF / math.tan(math.radians(30))
            tw(f'Taxiway {letter} rapid exit', [P(nm, s0, 0), P(nm, s0 + sgn * run, side * OFF)])
    # a midfield crossing connector every ~800 m
    for s in np.arange(800, L - 400, 800.0): tw(f'Taxiway {letter} connector', [P(nm, s, side * OFF), P(nm, s, 0)])
# ---------------------------------------------------------------- piers: centre line, half width, stand sides
PIER = [('Terminal 1A', [(701366, 4325668), (701374, 4326300)], 22), ('Terminal 1A', [(700840, 4326376), (701292, 4326385)], 24),
        ('Terminal 1B', [(702068, 4325770), (702057, 4326425)], 23), ('Terminal 1B / 4', [(702330, 4325546), (703070, 4325556)], 25),
        ('Terminal 4', [(703157, 4325640), (703149, 4326186)], 26), ('Terminal 2', [(702170, 4325302), (703186, 4325319)], 22),
        ('Terminal 3', [(702010, 4325003), (703152, 4324984)], 22)]
SW, SD, GAP, LANE = 80.0, 70.0, 6.0, 45.0
strip = unary_union([LineString(RW[k]).buffer(RS, cap_style=2) for k in RW])
twy_strip = unary_union([l.buffer(47.5) for nm, l in CL if 'parallel' in nm])
others = unary_union(list(BLD.values()))
stands, lanes, kept = [], [], []
for name, pts, hw in PIER:
    l = LineString(pts); L = l.length; u = (np.array(pts[1]) - np.array(pts[0])) / L; n = np.array([-u[1], u[0]])
    for side in (1, -1):
        row = []
        for k in range(int((L - 10) // SW)):
            s0 = 5 + k * SW; c0 = np.array(pts[0]) + u * s0
            q = [c0 + n * side * (hw + GAP), c0 + u * SW + n * side * (hw + GAP), c0 + u * SW + n * side * (hw + GAP + SD), c0 + n * side * (hw + GAP + SD)]
            st = Polygon(q)
            if st.intersects(strip) or st.intersects(twy_strip) or st.buffer(-1).intersects(others) or any(st.buffer(-2).intersects(x) for x in kept): continue
            row.append(st); kept.append(st)
        if row:
            for st in row: stands.append((name, st))
            # taxilane behind the row
            s_a = min(l.project(Point(*st.exterior.coords[0])) for st in row) - 20; s_b = max(l.project(Point(*st.exterior.coords[1])) for st in row) + 20
            off = side * (hw + GAP + SD + LANE / 2)
            lanes.append(LineString([tuple(np.array(pts[0]) + u * s_a + n * off), tuple(np.array(pts[0]) + u * s_b + n * off)]))
LANES_RAW = lanes
for i, ln in enumerate(lanes): tw('Apron taxilane', list(ln.coords))
# ---------------------------------------------------------------- links from the aprons to the parallels, and the cargo / maintenance aprons
def line(*p): return list(p)
tw('Taxiway J (Terminal 1A north)', line((700560, 4326470), (701545, 4326460)))
tw('Taxiway B (Terminal 1A south)', line((700600, 4325620), (701545, 4325620)))
tw('Taxiway F (north link, 18C to 18L)', line((701910, 4326530), (703440, 4326510)))
tw('Taxiway G (courtyard)', line((702600, 4326500), (702605, 4325680)))
tw('Taxiway H (Terminal 2/3 west)', line((701915, 4325160), (702105, 4325160)))
tw('Taxiway H (Terminal 2/3 east)', line((703250, 4325160), (703440, 4325160)))
tw('Taxiway L (Terminal 3 south)', line((702000, 4324820), (703250, 4324800)))
for x in (702200, 702650, 703100): tw('Taxiway L connector', line((x, 4324825), (x, 4324715)))
# cargo: Amazon and DHL on the cargo apron south of 9R/27L, maintenance (GE) at Hangar Space, Hangar/Cargo west of it
cargo = unary_union([AREA['Cargo Plane Parking'], BLD['Amazon Hub'].buffer(60, join_style=2), box(702420, 4322600, 703370, 4323150)]).difference(BLD['Amazon Hub']).difference(BLD['DHL Hub'])
mro = unary_union([box(702742, 4324200, 703340, 4324310), box(702062, 4324200, 702600, 4324310), box(702742, 4323725, 703340, 4323830), box(702062, 4323470, 702600, 4323570)])
for x in (702550, 703000): tw('Cargo apron link', line((x, 4323150), (x, 4323180)))
for x in (702300, 702900, 703200): tw('Maintenance apron link', line((x, 4324310), (x, 4324345)))
for x in (702900, 703200): tw('Maintenance apron link', line((x, 4323725), (x, 4323550)))
# each taxilane runs on at both ends to the nearest taxiway it meets (up to 450 m), so no apron lane dead-ends
others_cl = [l for nm, l in CL if nm != 'Apron taxilane']
ext_l = []
for nm, l in CL:
    if nm != 'Apron taxilane': continue
    a, b = np.array(l.coords[0]), np.array(l.coords[-1]); u = (b - a) / np.linalg.norm(b - a); na, nb = a, b
    for end, d in ((a, -u), (b, u)):
        ray = LineString([tuple(end + d * 1.0), tuple(end + d * 450)]); best = None
        for o in others_cl + [x for x in ext_l]:
            x = ray.intersection(o)
            if x.is_empty: continue
            pts_ = [x] if x.geom_type == 'Point' else [g for g in getattr(x, 'geoms', []) if g.geom_type == 'Point']
            for q in pts_:
                dd = Point(*end).distance(q)
                if best is None or dd < best: best = dd
        if best is not None and best > 1:
            ext_l.append(LineString([tuple(end), tuple(end + d * best)]))
for e in ext_l: CL.append(('Apron taxilane', e))
# ---------------------------------------------------------------- pavement: centre lines widened, filleted
cl_all = unary_union([l for nm, l in CL])
pave = unary_union([l.buffer(TW / 2, cap_style=2) for nm, l in CL]).buffer(18, join_style=1).buffer(-18, join_style=1)
apron = unary_union([st for nm, st in stands] + [ln.buffer(LANE / 2 + 2, cap_style=2) for ln in lanes] + [e.buffer(LANE / 2, cap_style=2) for e in ext_l] + [b.buffer(4) for b in BLD.values() if b.distance(unary_union([st for nm, st in stands])) < 15])
apron = unary_union([apron, cargo, mro]).buffer(12, join_style=1).buffer(-12, join_style=1).difference(others)
pave = pave.difference(RWP.buffer(0.5)).difference(others)
apron = apron.difference(RWP.buffer(0.5))
feats = [f for f in A['features'] if f['properties']['layer'] not in ('cvg_taxi', 'cvg_taxi_cl', 'cvg_apron', 'cvg_stand')]
def addf(layer, g, **p):
    for q in getattr(g, 'geoms', [g]):
        if q.is_empty: continue
        if q.geom_type == 'Polygon' and q.area < 50: continue
        feats.append(dict(type='Feature', properties=dict(layer=layer, **p), geometry=json.loads(json.dumps(mapping(q.simplify(0.3)), default=float))))
addf('cvg_apron', apron, name='Apron', src='designed (Code E/F stands and taxilanes); drawing values')
addf('cvg_taxi', pave, name='Taxiway', src='designed: 25 m taxiways, parallels 190 m off the runways, 30 degree rapid exits, filleted; drawing values')
for nm, l in CL:
    c = l.difference(RWP)
    for q in getattr(c, 'geoms', [c]):
        if q.geom_type == 'LineString' and q.length > 10: feats.append(dict(type='Feature', properties=dict(layer='cvg_taxi_cl', name=nm), geometry=json.loads(json.dumps(mapping(q), default=float))))
for k, (nm, st) in enumerate(stands): addf('cvg_stand', st, name=f'{nm} stand {k + 1}', terminal=nm)
A['features'] = feats
A['airside'] = dict(stands=len(stands), by_terminal={t: sum(1 for nm, _ in stands if nm == t) for t in sorted(set(nm for nm, _ in stands))}, taxiway_km=round(cl_all.length / 1000, 1),
                    pavement_km2=round(pave.area / 1e6, 2), apron_km2=round(apron.area / 1e6, 2))
json.dump(A, open(S + 'deckpage/airport.json', 'w'))
print(json.dumps(A['airside']))
