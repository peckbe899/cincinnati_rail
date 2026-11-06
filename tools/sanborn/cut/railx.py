try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben (17 October): (1) a transfer track from the freight passing track and platforms 13/14 to the CS bridge; (3) switches on the APEx.
# Run after tracks_gen4.py and apex_region.py (adds to deckpage/tracks.json; marks summary 'railx'); then structures.py.
# Switch policy (HSR: a turnout is a slow place): the routing is done in the two station throats, inside the CUT speed limits
# (ladders of 1:15 crossovers, about 80 km/h, and 1:12 throat turnouts, about 60 km/h); on the open line only a few high-speed
# crossovers (1:46, about 160 km/h on the diverging road, line speed straight through) for working round a failure, one set per line in
# the map area, on straight track and clear of the platforms, portals and junctions. Turnout numbers and speeds are drawing values.
import json, math, sys, numpy as np
from shapely.geometry import LineString, Point
S = _ws.DATA
T = json.load(open(S + 'deckpage/tracks.json'))
if T['summary'].get('railx'): sys.exit('already done')
F = T['features']
L = {f['properties'].get('name'): f for f in F if f['geometry']['type'] == 'LineString'}
C = lambda n: [tuple(q[:2]) for q in L[n]['geometry']['coordinates']]
R = lambda c: [[round(x, 2), round(y, 2)] for x, y in c]
def add(layer, c, **p): F.append(dict(type='Feature', properties=dict(layer=layer, **p), geometry=dict(type='LineString', coordinates=R(c))))
def addpt(xy, **p): F.append(dict(type='Feature', properties=dict(layer='marker', **p), geometry=dict(type='Point', coordinates=[round(xy[0], 1), round(xy[1], 1)])))
def resample(c, step=2.0):
    l = LineString(c); n = max(2, int(l.length / step) + 1); return [tuple(l.interpolate(d).coords[0]) for d in np.linspace(0, l.length, n)]
def bezt(a, ta, b, tb, k=0.4, n=60):
    a, b, ta, tb = map(np.asarray, (a, b, ta, tb)); D = np.linalg.norm(b - a); c0, c1 = a + ta * k * D, b - tb * k * D
    t = np.linspace(0, 1, n)[:, None]; return [tuple(p) for p in (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * c0 + 3 * (1 - t) * t * t * c1 + t ** 3 * b]
def tan_at(c, s):
    l = LineString(c); a = l.interpolate(max(0, s - 3)); b = l.interpolate(min(l.length, s + 3)); d = np.array([b.x - a.x, b.y - a.y]); return d / np.linalg.norm(d)
def pt(c, s): p = LineString(c).interpolate(s); return (p.x, p.y)
def s_N(c, N):   # chainage where a north-south line crosses northing N
    l = LineString(c)
    for a, b in zip(c, c[1:]):
        if (a[1] - N) * (b[1] - N) <= 0 and a[1] != b[1]: return l.project(Point(a[0] + (N - a[1]) / (b[1] - a[1]) * (b[0] - a[0]), N))
    raise ValueError(N)
def min_radius(c, win=20.0):
    c = resample(c, 5.0); k = int(win / 5); r = 1e9
    for i in range(k, len(c) - k):
        a, b, d = map(np.array, (c[i - k], c[i], c[i + k])); A = np.linalg.norm(b - a); B = np.linalg.norm(d - b); Cc = np.linalg.norm(d - a)
        u_, w_ = b - a, d - a; ar = abs(u_[0] * w_[1] - u_[1] * w_[0]) / 2
        if ar > 1e-6: r = min(r, A * B * Cc / (4 * ar))
    return r
log = dict(switches=[], crossovers=0)
def sw(xy, kind, num, kmh, where, **kw):
    addpt(xy, kind='switch', sw=kind, num=num, kmh=kmh, name=f'{kind} ({where})', label='', **kw); log['switches'].append([kind, where, num, kmh])
def crossover(ca, cb, s_a, num, kmh, where, step=1):
    """a crossover from track a at chainage s_a to track b, diagonal 1:num across the track spacing"""
    pa = np.array(pt(ca, s_a)); lb = LineString(cb); sb0 = lb.project(Point(*pa)); pb0 = np.array(pt(cb, sb0)); d = np.linalg.norm(pb0 - pa)
    ln = d * num; pb = pt(cb, sb0 + ln * step)
    add('apex', [tuple(pa), pb], kind='crossover', name=f'Crossover 1:{num} ({where})', num=num, kmh=kmh, level='0')
    sw(tuple(pa), 'turnout', num, kmh, where); sw(pb, 'turnout', num, kmh, where); log['crossovers'] += 1
    return ln
# ---------------------------------------------------------------- 1. transfer track: freight passing track (and platforms 13/14) to the intercity pair and the CS bridge
pas = C('Freight passing track'); k1 = C('APEx Kentucky 1 of 4'); ice = C('Intercity pair (east track): A-D to the Cincinnati Southern bridge')
prof = T['summary']['prof']['intercity']; pz = np.array([q[2] for q in prof['c']]); pl = LineString([q[:2] for q in prof['c']]); ps = np.array([pl.project(Point(q[:2])) for q in prof['c']])
z_ic = lambda s: float(np.interp(s, ps, pz))
APEX = lambda N: 159.9 + (164.0 - 159.9) * (4331646.0 - N) / (4331646.0 - 4330691.0) if N < 4331646 else 159.9 + (N - 4331646) / 4840 * 8.2
sp0 = s_N(pas, 4331430.0); P0 = pt(pas, sp0); t0 = tan_at(pas, sp0)
# parallel to Kentucky 1, 7 m west of it, on the viaduct, across W 8th (where the street drops to the APEx's clearance), then onto the
# intercity east track where it has climbed to the transfer's level
OFF = 7.0
kN = lambda N: pt(k1, s_N(k1, N))
def west_of_k1(N):
    s = s_N(k1, N); p = np.array(pt(k1, s)); t = tan_at(k1, s); n = np.array([t[1], -t[0]])      # right of southbound = west? southbound t points south: (t1,-t0) is west
    return tuple(p + n * OFF)
A1 = west_of_k1(4331360.0); A2 = west_of_k1(4331170.0)
# join where the intercity east track reaches the transfer's level (the APEx level abreast, minus nothing): search southward
best = None
for s in np.arange(LineString(ice).project(Point(712664, 4331150)), LineString(ice).length, 2.0):
    q = pt(ice, s); zt = APEX(q[1] + 30)
    if z_ic(pl.project(Point(*q))) >= zt - 2.0: best = s; break
J = pt(ice, best); tJ = tan_at(ice, best)
tA = np.array(A2) - np.array(A1); tA /= np.linalg.norm(tA)
seg0 = bezt(P0, t0, A1, tA, k=0.35, n=40); seg1 = [A1, A2]; seg2 = bezt(A2, tA, J, tJ, k=0.38, n=80)
tr = resample(seg0 + seg1[1:] + seg2[1:], 2.0)
rmin = min_radius(tr)
zJ = z_ic(pl.project(Point(*J)))
add('apex', tr, kind='transfer', name='Transfer track: freight passing track and platforms 13/14 to the intercity pair and the CS bridge', level='0, viaduct',
    note=f'leaves the freight passing track at N {P0[1]:,.0f}, runs on the station viaduct {OFF:.0f} m west of Kentucky 1 across W 8th, W 7th and Budd, and joins the intercity east track at N {J[1]:,.0f} ({zJ:.1f} m, easing down about 0.6% to it); tightest curve {rmin:.0f} m; single track, both ways, about 50 km/h')
sw(P0, 'turnout', 12, 60, 'transfer track off the freight passing track'); sw(J, 'turnout', 12, 60, 'transfer track onto the intercity east track')
# crossover between the intercity tracks just past the junction, so a train from the transfer can take either bridge track
icw = C('Intercity pair (west track): A-D to the Cincinnati Southern bridge')
crossover(ice, icw, LineString(ice).project(Point(*J)) + 25, 12, 60, 'intercity pair, south of the transfer')
# platforms 13 and 14 reach the passing track: track 14's throat to it (they run 7 m apart there)
t14 = C('APEx south throat, track 14'); s14 = s_N(t14, 4331585.0); q14 = pt(t14, s14); sp = LineString(pas).project(Point(*q14)) + 7 * 9
add('apex', [q14, pt(pas, sp)], kind='crossover', name='Connection 1:9, platform track 14 to the freight passing track (13 reaches 14 in the throat)', num=9, kmh=40, level='0')
sw(q14, 'turnout', 9, 40, 'track 14 to the passing track'); sw(pt(pas, sp), 'turnout', 9, 40, 'track 14 to the passing track')
addpt((J[0] - 18, J[1] + 40), kind='level', name='Transfer track joins the intercity pair', label=f'transfer track joins the intercity pair, {zJ:.1f} m', anchor='right')
log['transfer'] = dict(len=round(LineString(tr).length), rmin=round(rmin), join=[round(J[0], 1), round(J[1], 1)], join_z=round(zJ, 1), off=OFF)
# ---------------------------------------------------------------- 3. switches
# throat turnouts: where the platform tracks converge onto each approach track (the ends shared in the data), 1:12, 60 km/h
for end, N0 in (('south', 4331400.0), ('north', 4332400.0)):
    seen = set()
    for f in list(F):
        p = f['properties']; n = p.get('name') or ''
        if f['geometry']['type'] != 'LineString' or not n.startswith(f'APEx {end} throat'): continue
        c = f['geometry']['coordinates']; q = tuple(round(v, 1) for v in (c[-1] if end == 'south' else c[-1]))
        if q in seen: continue
        seen.add(q); sw(q, 'turnout', 12, 60, f'{end} throat, platform tracks onto the approach')
# throat ladders: crossovers between the approach tracks just outside the throat, two staggered rows so every platform reaches every route
def ladder(names, N_a, N_b, where):
    trk = [C(n) for n in names]
    for row, Ns, pairs in ((0, N_a, range(0, len(trk) - 1, 2)), (1, N_b, range(1, len(trk) - 1, 2))):
        for i in pairs:
            ca, cb = trk[i], trk[i + 1]; s = s_N(ca, Ns); crossover(ca, cb, s, 15, 80, where)
south = ['APEx Kentucky 1 of 4', 'APEx Kentucky 2 of 4', 'APEx Kentucky 3 of 4', 'APEx Kentucky 4 of 4', 'Cardinal branch 1 of 2 (APEx, east along the river)', 'Cardinal branch 2 of 2 (APEx, east along the river)']
south = [next(n for n in L if n and n.startswith(x[:40])) for x in south]
ladder(south, 4331385.0, 4331310.0, 'south throat ladder')
north = [f'APEx north approach {i} of 6' for i in range(1, 7)]
north = [[tuple(q[:2]) for q in L[n]['geometry']['coordinates']][::-1] for n in north]   # run them north to south like the others
for i, c in enumerate(north): L[f'_n{i}'] = dict(geometry=dict(coordinates=c))
ladder([f'_n{i}' for i in range(6)], 4332485.0, 4332560.0, 'north throat ladder')
# open-line high-speed crossovers, one pair (both directions) per line, on straight track
def hs_pair(na, nb, frac, where):
    ca, cb = C(na), C(nb); la = LineString(ca); s = la.length * frac
    ln = crossover(ca, cb, s, 46, 160, where)
    crossover(cb, ca, LineString(cb).project(Point(*pt(ca, s))) + ln + 40, 46, 160, where)
TS = next(n for n in L if n and n.startswith('APEx Southwest Chief, Transcontinental'))
ts4 = [n for n in L if n and n.startswith('APEx Southwest Chief, Transcontinental')]
ts4 = sorted(ts4, key=lambda n: C(n)[0][0])
hs_pair(ts4[1], ts4[2], 0.45, 'north trunk, Ludlow to the Southwest Chief / Transcontinental split')
hs_pair('APEx Cardinal (1 of 2)', 'APEx Cardinal (2 of 2)', 0.08, 'Cardinal, east of the river junction')
hs_pair('APEx Cardinal, Floridian (1 of 2)', 'APEx Cardinal, Floridian (2 of 2)', 0.12, 'Cardinal / Floridian, west')
T['features'] = F
T['summary']['railx'] = dict(transfer=log['transfer'], crossovers=log['crossovers'], switches=len(log['switches']),
    policy='routing in the station throats at 60-80 km/h (1:12 turnouts, 1:15 crossovers); open line: one pair of 1:46 crossovers (about 160 km/h) per line in the map area')
json.dump(T, open(S + 'deckpage/tracks.json', 'w'))
print(json.dumps(T['summary']['railx']))
