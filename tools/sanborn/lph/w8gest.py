"""Analysis only: ways to put W 8th and Gest on the boulevard grid west of Garrard. Writes nothing."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, math, numpy as np
from shapely.geometry import LineString, Point, shape
from shapely.ops import unary_union
SP = _ws.DATA
D = json.load(open(SP + 'deck/deck.json')); F = D['features']
L = json.load(open(SP + 'lph/lph_streets.json'))['features']
C = json.load(open(SP + 'deckpage/context.json'))
bl = [f for f in F if f['properties']['layer'] == 'boulevard'][0]['geometry']['coordinates'][0]
U = np.array(bl[3]) - np.array(bl[0]); U /= np.linalg.norm(U); Wv = np.array([U[1], -U[0]])
ga, gb = D['garrard']['a'], D['garrard']['b']
G = LineString([(ga + gb * (n - 4332000), n) for n in (4329000, 4337000)])
st = {f['properties']['name']: LineString(f['geometry']['coordinates']) for f in F if f['properties']['layer'] == 'street' and f['properties']['name'] in ('W 8th (viaduct line)', 'Gest', 'Summer', 'Berlin', 'Evans')}
lph = {f['properties']['name']: LineString(f['geometry']['coordinates']) for f in L if f['properties']['layer'] == 'street'}
lblk = [shape(f['geometry']) for f in L if f['properties']['layer'] == 'block']
dep = lph['Depot Street']; c = np.array(dep.coords); DEPOT = LineString([tuple(c[0] - U * 50), tuple(c[-1] + U * 50)])
ST = lph['State Avenue']; sc = np.array(ST.coords); STATE = LineString([tuple(x) for x in sc] + [tuple(sc[-1] + (sc[-1] - sc[-2]) / np.linalg.norm(sc[-1] - sc[-2]) * 60)])
def ray(p, back=1500): p = np.array(p); return LineString([tuple(p + Wv * 300), tuple(p - Wv * back)])
def at(line, ns): g = line.intersection(ns); g = getattr(g, 'geoms', [g])[0]; return np.array([g.x, g.y])
ext = lambda l: LineString([tuple(np.array(l.coords[0]) - U * 100), tuple(np.array(l.coords[-1]) + U * 100)])
NSL = [('blvd W', LineString([tuple(np.array(bl[0]) - U * 100), tuple(np.array(bl[3]))])), ('Evans', ext(st['Evans'])), ('Berlin', ext(st['Berlin'])), ('Summer', ext(st['Summer'])), ('Depot', DEPOT), ('State', STATE)]
HW = {'W 8th (viaduct line)': 110 * 0.3048 / 2, 'Gest': 60 * 0.3048 / 2}
L4 = [m for m in C['metro'] if m['name'] == 'Line 4'][0]['c']
stn = {s['name']: Point(s['p']) for s in C['stations'] if s['name'] in ('State', 'Garrard')}
for nm in ('W 8th (viaduct line)', 'Gest'):
    old = st[nm]; q = old.intersection(G); q = np.array([q.x, q.y])
    sq = ray(q)                                   # on the grid from the Garrard point
    print(f'\n{nm}: Garrard point {q.round(1)}; own chord to State {math.degrees(math.atan2(*(q - np.array(old.coords[0])))) % 360:.2f} deg; grid {math.degrees(math.atan2(*Wv)) % 360:.2f}')
    row = []
    for n, ns in NSL:
        a, b = at(old, ns) if not old.intersection(ns).is_empty else None, at(sq, ns)
        if a is None: a = np.array(old.coords[0]) if n == 'State' else None
        row.append((n, round(float((b - a) @ U), 1) if a is not None else None))
    print('  bend at Garrard, slide State end (N+ / S-):', row)
    s0 = np.array(old.coords[0]); piv = LineString([tuple(s0 + Wv * 1500), tuple(s0 - Wv * 50)])
    jg = at(piv, G); print('  pivot on the State corner: jog at Garrard', round(float((jg - q) @ U), 1), 'm; moves', [(n, round(float((at(piv, ns) - at(old, ns)) @ U), 1)) for n, ns in NSL[:-1] if not old.intersection(ns).is_empty])
    if nm.startswith('W 8th'):
        newb = LineString([tuple(q), tuple(at(sq, STATE))]).buffer(HW[nm], cap_style=2); oldb = old.buffer(HW[nm], cap_style=2)
        take = sum(b.intersection(newb).difference(oldb).area for b in lblk)
        dep_x = at(sq, DEPOT); newb2 = LineString([tuple(q), tuple(dep_x)]).buffer(HW[nm], cap_style=2)
        take2 = sum(b.intersection(newb2).difference(oldb).area for b in lblk)
        print(f'  1904 blocks taken: slide State end {take:.0f} m2; jog at Depot {take2:.0f} m2')
        l4 = LineString(L4); seg = [Point(p) for p in L4 if 711570 <= p[0] <= q[0]]
        for lab, ln in (('now', old), ('slide', LineString([tuple(q), tuple(at(sq, STATE))])), ('pivot State', LineString([tuple(jg), tuple(s0)]))):
            offs = [ln.distance(p) for p in seg]
            print(f'  Line 4 off centreline ({lab}): max {max(offs):.1f} m; State stn {ln.distance(stn["State"]):.1f}; Garrard stn {ln.distance(stn["Garrard"]):.1f}; half-width {HW[nm]:.1f}')
