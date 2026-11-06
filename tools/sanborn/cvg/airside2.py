try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben (18 October): the traced taxiways were jagged and copied the diagram's lettering; the diagram was for inspiration. CVG here is a
# very busy transcontinental hub (Pan Am hub; United, Delta and American gates; mostly widebodies because of the APEx; GE maintenance).
# The airside is designed instead, to ICAO Code E/F practice (drawing values): taxiways 25 m wide on centre lines, parallels 190 m off
# the runway centre lines, rapid-exit taxiways at 30 degrees, entries at every runway end, fillets at every junction; aprons round each
# concourse with widebody stands (80 m wide, 70 m deep, nose-in) and a 45 m taxilane behind them; stands that would sit in a runway strip
# (150 m either side), on a taxiway strip or on another stand are dropped; cargo and maintenance aprons at the hubs and hangar areas.
# Writes deckpage/airport.json layers cvg_taxi (pavement), cvg_taxi_cl (centre lines), cvg_apron, cvg_stand.
import json, math, itertools, numpy as np
from shapely.geometry import LineString, Polygon, Point, shape, mapping, box
from shapely.ops import unary_union
S = _ws.DATA
A = json.load(open(S + 'deckpage/airport_v58b.json'))
from shapely.affinity import translate
_SH = json.load(open(S + 'cvg/gates_params.json')).get('shift', {})
for f in A['features']:
    if f['properties']['layer'] == 'cvg_building' and f['properties']['name'] in _SH:
        f['geometry'] = json.loads(json.dumps(mapping(translate(shape(f['geometry']), *_SH[f['properties']['name']])), default=float)); f['properties']['moved'] = _SH[f['properties']['name']]
RW = {f['properties']['name'].replace('Runway ', ''): [np.array(c, float) for c in f['geometry']['coordinates']] for f in A['features'] if f['properties']['layer'] == 'cvg_runway_cl'}
RWP = unary_union([shape(f['geometry']) for f in A['features'] if f['properties']['layer'] == 'cvg_runway'])
_PR = json.load(open(S + 'cvg/gates_params.json'))
for f in A['features']:            # reshaped terminals (Ben, 18 October)
    nm_ = f['properties'].get('name')
    if f['properties']['layer'] == 'cvg_building' and nm_ in _PR.get('replace', {}):
        f['geometry'] = json.loads(json.dumps(mapping(translate(Polygon(_PR['replace'][nm_]).buffer(0), *_SH.get(nm_, (0, 0)))), default=float)); f['properties']['reshaped'] = True
LAND = unary_union([translate(Polygon(c_), *_SH.get('Terminal 1B', (0, 0))) for c_ in _PR.get('landside', [])]) if _PR.get('landside') else None
if LAND is not None:
    A['features'] = [f for f in A['features'] if f['properties'].get('name') != 'Landside (T1B / T4)']
    _ub = unary_union([shape(f['geometry']) for f in A['features'] if f['properties']['layer'] == 'cvg_building'])
    A['features'].append(dict(type='Feature', properties=dict(layer='cvg_area', name='Landside (T1B / T4)', src='Ben, 18 October: arrivals and departures inside the U'), geometry=json.loads(json.dumps(mapping(LAND.difference(_ub)), default=float))))
BLD = {f['properties']['name']: shape(f['geometry']) for f in A['features'] if f['properties']['layer'] == 'cvg_building'}
AREA = {f['properties']['name']: shape(f['geometry']) for f in A['features'] if f['properties']['layer'] == 'cvg_area'}
TW, RS = 25.0, 150.0
OFF = json.load(open(S + 'cvg/gates_params.json'))['rwy_to_twy']
def frame(nm):
    a, b = RW[nm]; L = np.linalg.norm(b - a); u = (b - a) / L; n = np.array([-u[1], u[0]]); return a, b, L, u, n
def P(nm, s, o): a, b, L, u, n = frame(nm); return tuple(a + u * s + n * o)
CL = []     # (name, LineString)
def tw(name, pts): CL.append((name, LineString(pts)))
# ---------------------------------------------------------------- parallels (side +1 = left of the a->b direction)
# taxiway plan (Ben, 18 October: taxi paths trialled gate <-> runway, cvg/taxi_trial.py). 18R mostly Pan Am (A on its terminal side only);
# 18C both sides (C for T1A, D for T1B/T2/T3/T4); 18L on its terminal side only (T; nothing lies east of it, so no S); 9L: K on the
# terminal side, M for the maintenance aprons; 9R: N for the maintenance aprons, R for the cargo hubs. Rapid exits only into the
# parallels that lead somewhere (A, C, D, T, K, R)
PAR = {('18R/36L', 'E'): 'A', ('18C/36C', 'W'): 'C', ('18C/36C', 'E'): 'D', ('18L/36R', 'W'): 'T',
       ('9L/27R', 'N'): 'K', ('9L/27R', 'S'): 'M', ('9R/27L', 'N'): 'N', ('9R/27L', 'S'): 'R'}
EXITS = {'A', 'C', 'D', 'T', 'K', 'R'}
CMP = {'E': np.array([1, 0]), 'W': np.array([-1, 0]), 'N': np.array([0, 1]), 'S': np.array([0, -1])}
PRM0 = json.load(open(S + __import__('os').environ.get('GATES', 'cvg/gates.json')))['params']
RUN = OFF / math.tan(math.radians(30))          # a 30-degree rapid exit runs this far along the runway
def stn(nm, pt): a, b, L, u, n = frame(nm); return float((np.array(pt) - a) @ u)
SIDE = {}
for (nm, comp), letter in PAR.items():
    a, b, L, u, n = frame(nm); SIDE[letter] = (nm, 1 if n @ CMP[comp] > 0 else -1)
# crossings of 18C (both parallels): B carries T1A's north taxilane over to D (Pan Am T1B <-> 18R); E runs just south of T1A's stem
_t1a = BLD['Terminal 1A']; _ytop = max(q[1] for q in _t1a.exterior.coords if q[0] < 701300); _ytip = min(q[1] for q in _t1a.exterior.coords)
_cls = PRM0['classes']['L']; _yB = _ytop + PRM0['nose_clear'] + _cls['length'] + PRM0.get('tail_clear', 0) + _cls['obj']
# crossings of the departure runway sit near its two departure ends, where traffic crosses behind an aircraft that has begun its roll
# (none in the middle of the runway): B about 430 m from the 18C threshold (on T1A's north taxilane), F about 420 m from the 36C threshold
XING = {'18C/36C': [('B', stn('18C/36C', (701700, _yB))), ('F', frame('18C/36C')[2] - 420.0)]}
EX = []           # (runway, letter, station on the centre line, direction +1 / -1)
INTER = {}         # stations where another runway crosses
for nm in RW:
    for nm2 in RW:
        if nm2 == nm: continue
        q = LineString([tuple(RW[nm][0]), tuple(RW[nm][1])]).intersection(LineString([tuple(RW[nm2][0]), tuple(RW[nm2][1])]))
        if not q.is_empty and q.geom_type == 'Point': INTER.setdefault(nm, []).append(stn(nm, (q.x, q.y)))
def ok_exit(nm, letter, c, sg):
    a, b, L, u, n = frame(nm); side = SIDE[letter][1]; lo, hi = sorted((c, c + sg * RUN))
    for (nm2, l2, c2, s2) in EX:
        if nm2 != nm: continue
        if l2 == letter:
            if s2 == sg and abs(c2 - c) < 400: return False
            if s2 != sg and ((sg > 0 and c2 > c) or (sg < 0 and c2 < c)) and abs(c2 - c) < 2 * RUN + 40: return False     # pointing at each other
            if s2 != sg and abs(c2 - c) < 150: return False
        elif s2 != sg and abs(c2 - c) < 150: return False
    for (_, x) in XING.get(nm, []):
        if lo - 60 < x < hi + 60 or abs(x - c) < 100: return False
    for x_ in INTER.get(nm, []):
        if abs(c - x_) < 250 or lo - 120 < x_ < hi + 120: return False        # not at or across another runway
    end = Point(*P(nm, c + sg * RUN, side * OFF)); ln_ = LineString([P(nm, c, 0), tuple(end.coords[0])])
    for (nm4, cm4), l4 in PAR.items():
        if nm4 == nm: continue
        n4, sd4 = SIDE[l4]; a4, b4, L4, u4, nn4 = frame(n4)
        if LineString([P(n4, -100, sd4 * OFF), P(n4, L4 + 100, sd4 * OFF)]).distance(ln_) < 40: return False     # not across another runway's parallel
    for nm3, (p3, q3) in RW.items():
        if nm3 != nm and LineString([tuple(p3), tuple(q3)]).distance(end) < 230: return False
        if nm3 != nm and LineString([tuple(p3), tuple(q3)]).distance(LineString([P(nm, c, 0), tuple(end.coords[0])])) < 120: return False
    return True
for (nm, comp), letter in PAR.items():
    a, b, L, u, n = frame(nm); side = SIDE[letter][1]
    if letter in ('M',):          # M serves the maintenance aprons: from C eastward, and on to T
        c0 = stn(nm, P('18C/36C', stn('18C/36C', P(nm, 0, side * OFF)), -OFF))
        _Cl = LineString([P('18C/36C', -200, -OFF), P('18C/36C', frame('18C/36C')[2] + 200, -OFF)])
        _q = LineString([P(nm, 0, side * OFF), P(nm, L, side * OFF)]).intersection(_Cl); c0 = stn(nm, (_q.x, _q.y))      # M starts on C
    else: c0 = 0.0
    tw(f'Taxiway {letter} (parallel to {nm})', [P(nm, c0, side * OFF), P(nm, L, side * OFF)])        # threshold to threshold (no dead-end overruns)
    for s_ in ((0.0, L) if c0 == 0 else (L,)):            # entries at the runway ends (90 degrees)
        tw(f'Taxiway {letter} entry', [P(nm, s_, side * OFF), P(nm, s_, 0)])
# rapid exits (30 degrees) into the parallels that lead somewhere, staggered so no two cross or meet: per landing direction the first
# about 1,700-2,000 m from the threshold (widebody roll), the second about 600 m further, where room allows
for nm in RW:
    lets = [l_ for l_, (n2, sd) in SIDE.items() if n2 == nm and l_ in EXITS]
    if not lets: continue
    a, b, L, u, n = frame(nm)
    # runway roles (ORD and LAX practice: the inboard runway departs, the outboard runways arrive): 18R/36L and 18L/36R are the arrival
    # runways, exits every ~450 m from about 1,600 m (ICAO Doc 9157 Part 2: touchdown ~450 m in, exits ~450 m apart to within 600 m of the
    # far end); 18C/36C departs and keeps one exit a direction a side; 9L and 9R (crosswind) two a direction
    TG = {'18R/36L': (1600, 2050, 2500, 2950), '18L/36R': (1600, 2050, 2500, 2950), '18C/36C': (1900,)}.get(nm, (1750, 2350))
    for t_ in TG:
        if t_ > L - 600: continue
        for land_from, sg in ((0.0, 1), (L, -1)):
            for letter in lets:
                cand = sorted(np.arange(1450, L - 600, 25.0), key=lambda d: abs(d - t_))
                for d in cand:
                    if abs(d - t_) > 225: break
                    c = land_from + sg * d
                    if ok_exit(nm, letter, c, sg): EX.append((nm, letter, c, sg)); break
for (nm, letter, c, sg) in EX:
    side = SIDE[letter][1]; tw(f'Taxiway {letter} rapid exit', [P(nm, c, 0), P(nm, c + sg * RUN, side * OFF)])
for nm, xs in XING.items():
    for nm_x, x in xs: tw(f'Taxiway {nm_x} (crossing {nm})', [P(nm, x, -OFF), P(nm, x, OFF)])
# right-angle connectors (single-sided runways) and crossings (9L: K to M; 9R: N to R) about every 750 m, clear of the rapid exits
for nm in RW:
    if nm in XING: continue
    a, b, L, u, n = frame(nm); lets = [l_ for l_, (n2, sd) in SIDE.items() if n2 == nm]
    for x in np.arange(750, L - 450, 750.0):
        bad = False
        for (nm2, l2, c2, s2) in EX:
            if nm2 != nm: continue
            lo, hi = sorted((c2, c2 + s2 * RUN))
            if lo - 60 < x < hi + 60 or abs(x - c2) < 120: bad = True
        if bad:
            for dx in (-150, 150, -250, 250):
                ok_ = True
                for (nm2, l2, c2, s2) in EX:
                    if nm2 != nm: continue
                    lo, hi = sorted((c2, c2 + s2 * RUN))
                    if lo - 60 < x + dx < hi + 60 or abs(x + dx - c2) < 120: ok_ = False
                if ok_: x = x + dx; bad = False; break
        if any(abs(x - x_) < 200 for x_ in INTER.get(nm, [])): continue
        if bad: continue
        if len(lets) == 2:
            if nm == '9L/27R' and x < stn(nm, (701550, 4324500)) + 100: continue          # M only east of C
            tw(f'Taxiway {"".join(sorted(lets))} crossing', [P(nm, x, -OFF), P(nm, x, OFF)])
        else:
            sd = SIDE[lets[0]][1]; tw(f'Taxiway {lets[0]} connector', [P(nm, x, sd * OFF), P(nm, x, 0)])
# A carried south past 36L's threshold to K (Pan Am's way to 9L/27R and the south of the field)
_K = next(l for nm_, l in CL if nm_.startswith('Taxiway K (parallel'))
nm, sd = SIDE['A']; a, b, L, u, n = frame(nm); _e = [np.array(P(nm, 0, sd * OFF)), np.array(P(nm, L, sd * OFF))]; _s = min(_e, key=lambda q: q[1])
_r = LineString([tuple(_s), tuple(_s + np.array([0, -1]) @ np.eye(2) * 0 + (np.array([-u[0], -u[1]]) if u[1] > 0 else u) * 600)]); _q = _r.intersection(_K)
if not _q.is_empty: tw('Taxiway A (south to K)', [tuple(_s), (_q.x, _q.y)])
# C and D carried south past 36C's threshold to N (9R's maintenance and cargo side)
_N = next(l for nm_, l in CL if nm_.startswith('Taxiway N (parallel'))
for letter in ('C', 'D'):
    nm, sd = SIDE[letter]; a, b, L, u, n = frame(nm); _e = np.array(P(nm, L, sd * OFF)); _q = LineString([tuple(_e), tuple(_e + u * 400)]).intersection(_N)
    if not _q.is_empty: tw(f'Taxiway {letter} (south to N)', [tuple(_e), (_q.x, _q.y)])
# K and M carried east past 27R's threshold to taxiway T
_T = next(l for nm_, l in CL if nm_.startswith('Taxiway T (parallel'))
for letter in ('K', 'M'):
    nm, sd = SIDE[letter]; a, b, L, u, n = frame(nm)
    e0 = np.array(P(nm, L, sd * OFF)); ray = LineString([tuple(e0), tuple(e0 + u * 800)]); q = ray.intersection(_T)
    if not q.is_empty: tw(f'Taxiway {letter} (east to T)', [tuple(e0), (q.x, q.y)])
# D and T run on 160 m past the north ends of 18C and 18L so the T1B and T4 tip stands' taxilanes reach them
for _nm, _l in list(CL):
    if _nm.startswith('Taxiway T (parallel'):      # D no longer needs it: 18C moved 434 m north (Ben, 18 October)
        _c = np.array(_l.coords); _top = _c[np.argmax(_c[:, 1])]; _bot = _c[np.argmin(_c[:, 1])]; _u = (_top - _bot) / np.linalg.norm(_top - _bot)
        tw(_nm.split(' (')[0] + ' (north end)', [tuple(_top), tuple(_top + _u * 160)])
# ---------------------------------------------------------------- stands: measured (cvg/gates.py), large and small widebody
import os
G = json.load(open(S + os.environ.get('GATES', 'cvg/gates.json'))); PRM = G['params']
stands = [(x['term'], x['cls'], shape(x['env']), shape(x['tail'])) for x in G['stands']]
others = unary_union(list(BLD.values()))
# rows: consecutive stands along one face (placement order), split where the face turns or the next stand is not adjacent
rows, cur = [], []
def nrm(env, tail): c0, c1 = np.array(env.centroid.coords[0]), np.array(tail.centroid.coords[0]); v = c1 - c0; return v / np.linalg.norm(v)
for st in stands:
    if cur:
        p = cur[-1]; ang = math.degrees(math.acos(max(-1, min(1, nrm(p[2], p[3]) @ nrm(st[2], st[3])))))
        if st[0] != p[0] or ang > 25 or p[2].distance(st[2]) > 2: rows.append(cur); cur = []
    cur.append(st)
if cur: rows.append(cur)
lanes = []
for r in rows:
    n = nrm(r[0][2], r[0][3]); t = np.array([-n[1], n[0]])
    _cl = {st[1] for st in r}
    LOFF = max(v['length'] + PRM.get('tail_clear', 0) + v.get('obj', v['tlofa'] / 2) for k, v in PRM['classes'].items() if k in (_cl if not (_cl & {'L', 'S', 'X'}) else ('L', 'S', 'X')))     # taxilane centre line behind the deepest stand in the row
    def lp(st):
        c = np.array(st[2].exterior.coords); nm_ = (c[0] + c[1]) / 2; tm = (c[2] + c[3]) / 2; u = (tm - nm_) / np.linalg.norm(tm - nm_); return nm_ + u * LOFF
    cs = [lp(st) for st in r]
    w0 = PRM['classes'][r[0][1]]['span'] + PRM['wingtip_clear']; w1 = PRM['classes'][r[-1][1]]['span'] + PRM['wingtip_clear']
    tl = max(PRM['classes'][st[1]]['tlofa'] for st in r)
    if len(cs) == 1: pts = [cs[0] - t * w0 / 2, cs[0] + t * w0 / 2]
    else:
        d0 = (cs[1] - cs[0]) / np.linalg.norm(cs[1] - cs[0]); d1 = (cs[-1] - cs[-2]) / np.linalg.norm(cs[-1] - cs[-2])
        pts = [cs[0] - d0 * w0 / 2] + cs + [cs[-1] + d1 * w1 / 2]
    lanes.append(dict(l=LineString([tuple(p) for p in pts]), tl=tl, n=n))
# facing rows that share one taxilane: two near-parallel lane lines closer than half a taxilane OFA are merged at their mid line
def fit(l): c = np.array(l.coords); m = c.mean(0); u = np.linalg.svd(c - m)[2][0]; return m, u
merged = set()
for i, j in itertools.combinations(range(len(lanes)), 2):
    li, lj = lanes[i]['l'], lanes[j]['l']
    if len(li.coords) > 6 or len(lj.coords) > 6: pass
    mi, ui = fit(li); mj, uj = fit(lj)
    if abs(ui @ uj) < math.cos(math.radians(8)) or li.distance(lj) > lanes[i]['tl'] * 0.6: continue
    nn = np.array([-ui[1], ui[0]]); off = ((mj - mi) @ nn) / 2
    for k, sg in ((i, 1), (j, -1)):
        lanes[k]['l'] = LineString([tuple(np.array(p) + nn * off * sg) for p in lanes[k]['l'].coords])
    merged |= {i, j}
_parl = [l for nm, l in CL if '(parallel' in nm]
_keep = []
for k, ln in enumerate(lanes):
    pts = [ln['l'].interpolate(f_, normalized=True) for f_ in np.linspace(0, 1, 9)]
    if any(all(pl.distance(q) < 35 for q in pts) for pl in _parl): continue      # duplicate of a parallel taxiway, 35 m or less off it
    _keep.append(k)
lanes = [lanes[k] for k in _keep]; rows = [rows[k] for k in _keep]
for k, ln in enumerate(lanes): tw('Apron taxilane', list(ln['l'].coords)); ln['n_st'] = len(rows[k])
LANES = [ln['l'] for ln in lanes]
# ---------------------------------------------------------------- cargo / maintenance aprons
cargo = unary_union([AREA['Cargo Plane Parking'], BLD['Amazon Hub'].buffer(60, join_style=2), box(702420, 4322600, 703370, 4323150)]).difference(BLD['Amazon Hub']).difference(BLD['DHL Hub'])
mro = unary_union([box(702742, 4324200, 703340, 4324310), box(702062, 4324200, 702600, 4324310), box(702742, 4323725, 703340, 4323830), box(702062, 4323470, 702600, 4323570)])
def line(*p): return list(p)
def yat(letter, x):        # y of a parallel taxiway at easting x
    l = next(l for nm, l in CL if nm.startswith(f"Taxiway {letter} (parallel")); q = l.intersection(LineString([(x, 4320000), (x, 4330000)])); return q.y
for x in (702550, 703000): tw('Cargo apron link', line((x, 4323150), (x, yat('R', x))))
for x in (702300, 702900, 703080): tw("Maintenance apron link", line((x, 4324310), (x, yat("M", x))))
for x in (702900, 703200): tw('Maintenance apron link', line((x, 4323725), (x, yat('N', x))))
# each taxilane runs on at both ends to the nearest taxiway or taxilane it meets (up to 700 m), never through a stand or building
blockers = unary_union([st[2] for st in stands] + [others.buffer(3)])
ext_l = []; removed = set()
for ln in lanes:
    single = ln['n_st'] < 3            # corner and tip stands: run on only if a taxiway is close (300 m)
    l = ln['l']
    c = np.array(l.coords)
    for end, d in ((c[0], (c[0] - c[1]) / np.linalg.norm(c[0] - c[1])), (c[-1], (c[-1] - c[-2]) / np.linalg.norm(c[-1] - c[-2]))):
        ray = LineString([tuple(end + d * 1.0), tuple(end + d * (300 if single else 450))]); best = None
        for nm2, o in CL + [('x', e) for e in ext_l]:
            if o is l or (nm2 == 'Apron taxilane' and o.length < 150): continue
            x = ray.intersection(o)
            if x.is_empty: continue
            for q in ([x] if x.geom_type == 'Point' else [g for g in getattr(x, 'geoms', []) if g.geom_type == 'Point']):
                dd = Point(*end).distance(q)
                if best is None or dd < best: best = dd
        if best is not None and best > 1:
            e = LineString([tuple(end), tuple(end + d * best)])
            if e.buffer(10).intersects(others.buffer(3)) or (LAND is not None and e.buffer(TW / 2).intersects(LAND)): continue
            mine = {id(st[2]) for st in rows[lanes.index(ln)]}
            hit = [st for st in stands if id(st[2]) not in mine and id(st[2]) not in removed and st[2].buffer(-0.5).intersects(e.buffer(ln['tl'] / 2))]
            if len(hit) <= (0 if single else 2) and not any(st[1] == 'X' for st in hit):      # A380 stands are never given up (Ben: 5 of them)      # a corner or tip stand in the way of the taxilane's way out is given up
                removed.update(id(st[2]) for st in hit); ext_l.append(e)
for e in ext_l: CL.append(('Apron taxilane', e))
# a taxilane that still ends in the open is carried on and turned square to the nearest taxiway it can reach clear of stands and buildings
_blk0 = unary_union([st[2].buffer(-1) for st in stands] + [others.buffer(TW / 2 + 3), RWP.buffer(2)])
def _dead_ends():
    U_ = unary_union([l for nm, l in CL]); deg = {}
    for sg in getattr(U_, 'geoms', [U_]):
        for p_ in (sg.coords[0], sg.coords[-1]): k_ = (round(p_[0], 1), round(p_[1], 1)); deg[k_] = deg.get(k_, 0) + 1
    return {k_ for k_, v in deg.items() if v == 1}
_de = _dead_ends()
for ln in lanes:
    c = np.array(ln['l'].coords)
    for end, d in ((c[0], (c[0] - c[1]) / np.linalg.norm(c[0] - c[1])), (c[-1], (c[-1] - c[-2]) / np.linalg.norm(c[-1] - c[-2]))):
        if (round(end[0], 1), round(end[1], 1)) not in _de: continue
        best = None
        for ext in np.arange(0, 241, 20.0):
            q = end + d * ext; leg1 = LineString([tuple(end), tuple(q)]) if ext > 0 else None
            if leg1 is not None and leg1.intersects(_blk0): break
            for sd in (np.array([-d[1], d[0]]), np.array([d[1], -d[0]])):
                ray = LineString([tuple(q + sd * 1), tuple(q + sd * 450)]); hit = None
                for nm2, o in CL:
                    if nm2 == 'Apron taxilane' and o is ln['l']: continue
                    x = ray.intersection(o)
                    for g_ in ([x] if x.geom_type == 'Point' else [g for g in getattr(x, 'geoms', []) if g.geom_type == 'Point']):
                        dd = Point(*q).distance(g_)
                        if hit is None or dd < hit[0]: hit = (dd, g_)
                if hit is None: continue
                leg2 = LineString([tuple(q), (hit[1].x, hit[1].y)])
                if leg2.intersects(_blk0): continue
                tot = ext + hit[0]
                if best is None or tot < best[0]: best = (tot, leg1, leg2)
        if best:
            for g_ in best[1:]:
                if g_ is not None: CL.append(('Apron taxilane', g_))
# departure ends (FAA AC 150/5300-13B 4.8.3 bypass taxiways and 4.9 holding bays; JFK's Bay Runway hold pads let aircraft bypass those
# held): at each end of the three north-south runways, on each parallel, a holding bay (a second taxiway 91 m outboard of the parallel,
# Code F taxiway spacing, joined to it at both ends) where room allows, and a second entry 150 m in from the threshold
_OB = unary_union(list(BLD.values()) + [st[2] for st in stands] + ([LAND] if LAND is not None else []))
_GRP = Polygon(_PR['grounds']).buffer(0)
PADS = []
def _dep(nm, end):          # the departure using this end: the north end serves 18x, the south end 36x
    a, b, L, u, n = frame(nm); y = P(nm, end, 0)[1]; other = P(nm, L - end, 0)[1]; lo, hi = nm.split('/'); return lo if y > other else hi
for nm in ('18R/36L', '18C/36C', '18L/36R'):
    a, b, L, u, n = frame(nm)
    for letter in [l_ for l_, (n2, sd) in SIDE.items() if n2 == nm]:
        sd = SIDE[letter][1]
        for end in (0.0, L):
            si = 1 if end == 0 else -1
            tw(f'Taxiway {letter} entry (second)', [P(nm, end + si * 150, sd * OFF), P(nm, end + si * 150, 0)])
            others_cl = [l for nm_, l in CL if not nm_.startswith(f'Taxiway {letter} ') and 'entry' not in nm_]
            done = False
            def _clear(g_, main_):
                if g_.buffer(51).intersects(_OB) or not _GRP.contains(g_.buffer(TW / 2)): return False
                if any(LineString([tuple(RW[k][0]), tuple(RW[k][1])]).buffer(150).intersects(g_.buffer(TW / 2)) for k in RW if k != nm): return False
                return not any(main_.buffer(85).intersects(o) for o in others_cl)      # Code F taxiway / taxilane spacing from everything else
            for st0 in (90.0, 200.0, 320.0):              # a bypass: a second taxiway 91 m outboard, joined to the parallel at both ends
                for off in (91.0, 110.0):
                    for ln_ in (450.0, 350.0, 260.0):
                        s0, s1 = end + si * st0, end + si * (st0 + ln_)
                        main = LineString([P(nm, s0, sd * (OFF + off)), P(nm, s1, sd * (OFF + off))])
                        l0 = LineString([P(nm, s0 - si * 90, sd * OFF), P(nm, s0, sd * (OFF + off))]); l1 = LineString([P(nm, s1, sd * (OFF + off)), P(nm, s1 + si * 90, sd * OFF)])
                        if not _clear(unary_union([main, l0, l1]), main): continue
                        CL.append((f'Taxiway {letter} holding bay ({_dep(nm, end)} end)', main)); CL.append(('Holding bay link', l0)); CL.append(('Holding bay link', l1))
                        PADS.append((nm, letter, 'bypass', round(st0), round(ln_))); done = True; break
                    if done: break
                if done: break
            if not done:                                   # else a holding apron: a stub square off the parallel near the threshold
                for st0 in (20.0, 30.0, 60.0, 120.0, 200.0):
                    for ln_ in (260.0, 200.0, 150.0):
                        main = LineString([P(nm, end + si * st0, sd * OFF), P(nm, end + si * st0, sd * (OFF + ln_))])
                        stub = LineString([P(nm, end + si * st0, sd * (OFF + 40)), P(nm, end + si * st0, sd * (OFF + ln_))])
                        if not _clear(stub, stub): continue
                        CL.append((f'Taxiway {letter} holding apron ({_dep(nm, end)} end)', main)); PADS.append((nm, letter, 'apron', round(st0), round(ln_))); done = True; break
                    if done: break
print('holding bays', PADS)
# connectivity: any piece of taxiway not joined to the main network is joined by the shortest clear link
import networkx as _nx
def _graph():
    U_ = unary_union([l for nm, l in CL]); g_ = _nx.Graph()
    for sg in getattr(U_, 'geoms', [U_]):
        c_ = list(sg.coords)
        for p_, q_ in zip(c_[:-1], c_[1:]): g_.add_edge((round(p_[0], 1), round(p_[1], 1)), (round(q_[0], 1), round(q_[1], 1)))
    return g_
_blk = unary_union([st[2].buffer(-1) for st in stands] + [others.buffer(2), RWP.buffer(2)])
for _it in range(6):
    _g = _graph(); _cc = sorted(_nx.connected_components(_g), key=len, reverse=True)
    if len(_cc) == 1: break
    _main = np.array(list(_cc[0])); _done = False
    for _c in _cc[1:]:
        _best = None
        for k_ in _c:
            d_ = np.hypot(_main[:, 0] - k_[0], _main[:, 1] - k_[1])
            for i_ in np.argsort(d_)[:25]:
                ln_ = LineString([k_, tuple(_main[i_])])
                if d_[i_] < 400 and not ln_.intersects(_blk) and (_best is None or d_[i_] < _best[0]): _best = (d_[i_], ln_)
        if _best: CL.append(('Apron link', _best[1])); _done = True
    if not _done: break
stands = [st for st in stands if id(st[2]) not in removed]
BYT = {}
for st in stands: BYT.setdefault(st[0], {}); BYT[st[0]][st[1]] = BYT[st[0]].get(st[1], 0) + 1
# CVG Grounds.kmz: taxiways and aprons stop at the airport boundary
GR = Polygon(_PR['grounds']).buffer(0) if _PR.get('grounds') else None
if GR is not None:      # Ben, 18 October: 9R/27L's west 750 m lies outside CVG Grounds.kmz; its own taxiway corridor (N and R, the entries) goes with it
    _a9, _b9, _L9, _u9, _n9 = frame('9R/27L')
    GR = GR.union(Polygon([P('9R/27L', -80, OFF + 60), P('9R/27L', _L9 + 80, OFF + 60), P('9R/27L', _L9 + 80, -OFF - 60), P('9R/27L', -80, -OFF - 60)]))
if GR is not None:
    _cl = []
    for nm, l in CL:
        g = l.intersection(GR)
        for q in getattr(g, 'geoms', [g]):
            if q.geom_type == 'LineString' and q.length > 5: _cl.append((nm, q))
    CL = _cl
json.dump([dict(name=nm, c=list(l.coords)) for nm, l in CL], open(S + os.environ.get('TRAW', 'cvg/_taxi_raw.json'), 'w'), default=float)     # for cvg/taxi_trial.py
# ---------------------------------------------------------------- pavement: centre lines widened, filleted
cl_all = unary_union([l for nm, l in CL])
pave = unary_union([l.buffer(TW / 2, cap_style=2) for nm, l in CL]).buffer(18, join_style=1).buffer(-18, join_style=1)
apron = unary_union([st[2] for st in stands] + [st[3] for st in stands] + [b.buffer(12) for b in BLD.values() if b.distance(unary_union([st[2] for st in stands])) < 15])
apron = unary_union([apron, cargo, mro]).buffer(12, join_style=1).buffer(-12, join_style=1).difference(others)
pave = pave.difference(RWP.buffer(0.5)).difference(others)
apron = apron.difference(RWP.buffer(0.5))
if LAND is not None: apron = apron.difference(LAND); pave = pave.difference(LAND)
if GR is not None: apron = apron.intersection(GR); pave = pave.intersection(GR)
feats = [f for f in A['features'] if f['properties']['layer'] not in ('cvg_taxi', 'cvg_taxi_cl', 'cvg_apron', 'cvg_stand')]
for f in feats:                      # the parking area gives up what Terminal 1A's southward extension and its apron take (18 October)
    if f['properties']['layer'] == 'cvg_area' and f['properties'].get('name') == 'Parking':
        g = shape(f['geometry']).difference(unary_union([apron, pave]).buffer(10)).difference(unary_union(list(BLD.values())).buffer(10))
        g = max(getattr(g, 'geoms', [g]), key=lambda q: q.area); f['geometry'] = json.loads(json.dumps(mapping(g.simplify(0.5)), default=float))
def addf(layer, g, **p):
    for q in getattr(g, 'geoms', [g]):
        if q.is_empty: continue
        if q.geom_type == 'Polygon' and q.area < 50: continue
        feats.append(dict(type='Feature', properties=dict(layer=layer, **p), geometry=json.loads(json.dumps(mapping(q.simplify(0.3)), default=float))))
addf('cvg_apron', apron, name='Apron', src='designed (Code E/F stands and taxilanes); drawing values')
addf('cvg_taxi', pave, name='Taxiway', src='designed: 25 m taxiways, parallels 550 ft (167.6 m) off the runways, 30-degree rapid exits staggered so none cross, crossings of 18C only near its departure ends (B, F); holding bays and second entries at the runway ends, filleted; taxi routes trialled gate to runway (cvg/taxi_trial.py); drawing values')
for nm, l in CL:
    c = l.difference(RWP)
    for q in getattr(c, 'geoms', [c]):
        if q.geom_type == 'LineString' and q.length > 10: feats.append(dict(type='Feature', properties=dict(layer='cvg_taxi_cl', name=nm), geometry=json.loads(json.dumps(mapping(q), default=float))))
DES = {'X': 'A380 stand (A380; 777X with wingtips extended; takes everything)', 'L': 'Large widebody stand (747, 777, A340-600, A350-1000; 777X wingtips folded; takes everything but the A380)', 'S': 'Widebody stand (787, A330, A340-200/300/500, A350-900, 777-200; takes 767, A300, A310, 797)', 'D': 'Small widebody stand (797, 767-200/300 incl. winglets, A300, A310)', 'M': 'Small widebody stand (787-8)'}
def airline(nm, st):     # canon carriers (fact tracker); Delta also takes the T4 bar stands that face Terminal 2 (18 October)
    if nm in ('Terminal 1A', 'Terminal 1B'): return 'Pan Am + Gateway partners'
    if nm == 'Terminal 2': return 'Delta + SkyTeam'
    if nm == 'Terminal 3': return 'United + Star Alliance'
    c = st.centroid; bar_y = BLD['Terminal 4'].bounds[1] + 120
    return 'Delta + SkyTeam (bar stands facing Terminal 2)' if (c.y < bar_y and c.x < BLD['Terminal 4'].bounds[2] - 40) else 'American, Southwest and others'
for k, (nm, c, st, tz) in enumerate(stands): addf('cvg_stand', st, name=f'{nm} stand {k + 1}', terminal=nm, cls=c, kind=DES[c], airline=airline(nm, st), w=round(PRM['classes'][c]['span'] + PRM['wingtip_clear'], 1), d=round(PRM['classes'][c]['length'], 1))
A['features'] = feats
AL = {}
for nm, c, st, tz in stands: AL[airline(nm, st)] = AL.get(airline(nm, st), 0) + 1
A['airside'] = dict(stands=len(stands), by_terminal=BYT, by_airline=AL, removed_for_taxilanes=len(removed), params=PRM, taxiway_km=round(cl_all.length / 1000, 1),
                    pavement_km2=round(pave.area / 1e6, 2), apron_km2=round(apron.area / 1e6, 2))
json.dump(A, open(S + os.environ.get('AOUT', 'deckpage/airport.json'), 'w'))
print(json.dumps(A['airside']))
