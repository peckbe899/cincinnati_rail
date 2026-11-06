try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben 2026-10-21: (1) RER D continuous at the plan window's west edge; (2) RER A through Millvale / South Cumminsville redrawn from
# his KMZ: the trunk viaduct follows the Millvale grid north from the Hopple curve and splits at a new South Cumminsville station
# (RER-1a north-east to Northside, RER-1b north), and ORR R5 comes in on the Cumminsville Spur and passes through the station on a
# centre track in the gaps between RER A trains (3 tracks: southbound, passing, northbound; Ben's choice of one passing track).
# Ben's edited trunk (layout transit edit, his redraw) is kept south of the Hopple curve and baked into context.json here.
#   python3 rer1023/apply.py        -> deckpage/context.json, deckpage/tracks.json (backups *_v90.json)
import json, math, sys, shutil, os, numpy as np
from shapely.geometry import LineString, Point
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'arcs'); import fitarcs
for fn in ('context', 'tracks'):
    if not os.path.exists(SP + f'deckpage/{fn}_v90.json'): shutil.copy(SP + f'deckpage/{fn}.json', SP + f'deckpage/{fn}_v90.json')
C = json.load(open(SP + 'deckpage/context_v90.json')); T = json.load(open(SP + 'deckpage/tracks_v90.json'))
BEN = json.load(open(SP + 'rer1023/ben_1021.json')); ED = json.load(open(SP + 'dbread2/deck/layout.json'))['transit']
RER = {f['id']: f for f in C['rer']}
TR, B1 = 'R-A-712835-4331872', 'R-A-711904-4336687'
H0, EDGE, TAPER, LPL, ISL, SIDE = 2.25, 1.75, 40.0, 204.2, 11.0, 6.0
U = lambda v: np.asarray(v, float) / np.linalg.norm(v)
A = lambda p: np.asarray(p, float)

def inter(p, d, q, e):                      # intersection of p + t d and q + u e
    M = np.array([[d[0], -e[0]], [d[1], -e[1]]]); t = np.linalg.solve(M, q - p)[0]; return p + t * d
def fillet(p1, d1, p2, d2, R):              # arc from line 1 (direction d1, travelling) to line 2 (direction d2): tangent points, centre, sweep
    X = inter(p1, d1, p2, d2); phi = math.atan2(d1[0] * d2[1] - d1[1] * d2[0], d1 @ d2); t = R * math.tan(abs(phi) / 2)
    Ta, Tb = X - d1 * t, X + d2 * t; n = np.array([-d1[1], d1[0]]) * np.sign(phi); O = Ta + n * R
    return dict(Ta=Ta, Tb=Tb, O=O, R=R, phi=phi, X=X)
def arc_pieces(F):                          # quadratic pieces of 15 degrees or less (as the page draws curves): vertices after Ta, controls
    a0 = math.atan2(*(F['Ta'] - F['O'])[::-1]); sw = abs(F['phi']); s = math.copysign(1, F['phi']); m = max(1, math.ceil(math.degrees(sw) / 15))
    V, K = [], []
    for j in range(m):
        t1 = a0 + s * sw * (j + 1) / m; tm = a0 + s * sw * (j + 0.5) / m; th = sw / m
        V.append(F['O'] + F['R'] * np.array([math.cos(t1), math.sin(t1)])); K.append(F['O'] + F['R'] / math.cos(th / 2) * np.array([math.cos(tm), math.sin(tm)]))
    return V, K
def fit_R(p1, d1, p2, d2, pts, lo, hi):     # radius whose fillet lies closest to the drawn curve points
    best = None
    for R in np.arange(lo, hi, 5.0):
        F = fillet(p1, d1, p2, d2, R); e = [abs(np.hypot(*(A(q) - F['O'])) - R) for q in pts]; v = float(np.sqrt(np.mean(np.square(e))))
        if best is None or v < best[0]: best = (v, R)
    return best[1], best[0]
def dense(V, K, step=2.0):
    out = [A(V[0])]
    for i in range(len(V) - 1):
        a, b = A(V[i]), A(V[i + 1]); q = K.get(str(i))
        if q is None:
            n = max(1, int(math.ceil(np.hypot(*(b - a)) / step))); out += [a + (b - a) * j / n for j in range(1, n + 1)]; continue
        q = A(q); n = max(4, int(np.hypot(*(b - a)) * 1.1 / step)); out += [(1 - t) ** 2 * a + 2 * (1 - t) * t * q + t * t * b for t in (np.arange(1, n + 1) / n)]
    return np.array(out)
def chain(c): return np.r_[0, np.cumsum(np.hypot(*np.diff(c, axis=0).T))]
def normals(c):
    n = len(c); nx = np.zeros(n); ny = np.zeros(n)
    for i in range(n):
        a, b = c[max(0, i - 3)], c[min(n - 1, i + 3)]; d = b - a; L = np.hypot(*d) or 1; nx[i] = -d[1] / L; ny[i] = d[0] / L
    return nx, ny
def offs(c, h):                             # h > 0 left of travel, h < 0 right
    nx, ny = normals(c); return np.c_[c[:, 0] + nx * h, c[:, 1] + ny * h]
def proj(c, cs, q):
    L = LineString(c); return L.project(Point(q))
def r1(a): return [[round(float(x), 1), round(float(y), 1)] for x, y in a]

# ---------------------------------------------------------------- RER A trunk
old = ED[TR]; OV, OK = old['c'], old['k']
v26, v27, v35, v36 = A(OV[26]), A(OV[27]), A(OV[35]), A(OV[36])
d1 = U(v27 - v26)
K2a, S = A(BEN['RER-1b_trunk'][30]), A(BEN['RER-1b_trunk'][31]); d2 = U(S - K2a)
d3 = U(v36 - v35)
R1, e1 = fit_R(v26, d1, K2a, d2, BEN['RER-1b_trunk'][25:30], 300, 2500); F1 = fillet(v26, d1, K2a, d2, R1)
R2, e2 = fit_R(K2a, d2, v35, d3, BEN['RER-1a'][1:6], 80, 400); F2 = fillet(K2a, d2, v35, d3, R2)
print(f'Hopple curve R {R1:.0f} m (rms {e1:.1f} m to the drawn curve), split curve R {R2:.0f} m (rms {e2:.1f} m); deflections {math.degrees(F1["phi"]):.1f}, {math.degrees(F2["phi"]):.1f}')
assert np.dot(F1['Ta'] - v26, d1) > 0 and np.dot(v27 - F1['Ta'], d1) > -400, 'Hopple curve starts before vertex 26'
assert np.dot(v35 - F2['Tb'], d3) > 0, 'split curve ends past vertex 35'
s_T2a = np.dot(F2['Ta'] - S, d2); print('split curve starts', round(float(s_T2a), 1), 'm from the split point (KMZ)')
V = [A(p) for p in OV[:27]]; K = {k: A(v) for k, v in OK.items() if int(k) < 26}
V.append(F1['Ta']); av, ak = arc_pieces(F1)
for q, p in zip(ak, av): K[str(len(V) - 1)] = q; V.append(p)
V.append(F2['Ta']); av, ak = arc_pieces(F2)
for q, p in zip(ak, av): K[str(len(V) - 1)] = q; V.append(p)
off = len(V) - 35
for i, p in enumerate(OV[35:]): V.append(A(p))
for k, v in OK.items():
    if int(k) >= 35: K[str(int(k) + off)] = A(v)
# clean tiny segments at the joins
Vt, Kt = V, K
ctr = dense(Vt, Kt); cst = chain(ctr)
s_S = proj(ctr, cst, S); print('trunk length', round(float(cst[-1])), 'split at s', round(float(s_S)))

# ---------------------------------------------------------------- RER-1b
o1 = RER[B1]; OV1, OK1 = o1['c'], (o1.get('k') or {})
P1 = S + d2 * np.dot(A(BEN['RER-1b_north'][1]) - S, d2)
Vin = [S, P1] + [A(p) for p in BEN['RER-1b_north'][2:19]] + [A(OV1[18])]
fb = fitarcs.fit(Vin)
V1 = [A(p) for p in fb['verts']]; K1 = {k: A(v) for k, v in fb['k'].items()}
assert np.hypot(*(V1[-1] - A(OV1[18]))) < 0.5
off1 = len(V1) - 1 - 18
for p in OV1[19:]: V1.append(A(p))
for k, v in OK1.items():
    if int(k) >= 18: K1[str(int(k) + off1)] = A(v)
c1 = dense(V1, K1); cs1 = chain(c1)
h1 = math.degrees(math.atan2(*(c1[3] - c1[0]))) ; print('RER-1b leaves the split at', round(h1, 1), 'deg (trunk straight', round(math.degrees(math.atan2(*d2)), 1), ');', 'curves', [(c['R'], c['sweep']) for c in fb['curves']])

# ---------------------------------------------------------------- stations, platforms, tracks of the trunk
SC = S + d2 * (np.dot(A(BEN['South_Cumminsville_stn']) - S, d2) - 50.0)   # Ben's point, on the straight, moved 50 m south (Ben 2026-10-22) so the junction's switches sit on straight track
for s in C['rer_stations']:
    if s['name'] == 'South Cumminsville' and 'A' in s['lines']: s['p'] = [round(float(SC[0]), 1), round(float(SC[1]), 1)]
# ---------------------------------------------------------------- R5 spur alignment (Ben 2026-10-22: no wider than it needs, and not angular or slow)
# R5 leaves the lower west pair under the point where the Indianapolis + D deck crosses over it, curves left at 500 m onto the deck's centre
# line (between the D pair and the Indianapolis pair) inside the existing structure, runs beneath the deck, and leaves it on a 200 m curve
# (Ben's KMZ curve and junction point) onto the trunk centre track
R5_RE, R5_RW = 500.0, 200.0
def r5_res(L, step=2.0):
    n = int(L.length // step); return A([L.interpolate(i * L.length / n).coords[0] for i in range(n + 1)])
def r5_near(L, p): return A(L.interpolate(L.project(Point(p))).coords[0])
def r5_nrm(c):
    t = np.gradient(c, axis=0); t /= np.hypot(*t.T)[:, None]; return np.c_[-t[:, 1], t[:, 0]]
def r5_tangent(line_pts, curve_pts, R, side_line, side_curve):
    L = LineString(line_pts); O = curve_pts + r5_nrm(curve_pts) * side_curve * R; f = []
    for o in O:
        q = r5_near(L, o); u = L.project(Point(o)); t = A(L.interpolate(min(u + 1, L.length)).coords[0]) - A(L.interpolate(max(u - 1, 0)).coords[0])
        f.append(np.dot(o - q, np.array([-t[1], t[0]]) / np.hypot(*t)) * side_line - R)
    for i in range(len(f) - 1):
        if f[i] == 0 or f[i] * f[i + 1] < 0:
            w = f[i] / (f[i] - f[i + 1]); o = O[i] * (1 - w) + O[i + 1] * w; return i + w, o, r5_near(L, o)
    raise SystemExit('no tangent arc at R %s' % R)
def r5_arc(O, P0, P1, R, turn, step=2.0):
    a0 = math.atan2(*(P0 - O)[::-1]); a1 = math.atan2(*(P1 - O)[::-1])
    if turn > 0:
        while a1 < a0: a1 += 2 * math.pi
    else:
        while a1 > a0: a1 -= 2 * math.pi
    n = max(2, int(abs(a1 - a0) * R / step)); a = np.linspace(a0, a1, n + 1); return O + R * np.c_[np.cos(a), np.sin(a)]
_F = {t['properties'].get('name'): LineString(t['geometry']['coordinates']) for t in T['features'] if t['geometry']['type'] == 'LineString'}
_w1 = r5_res(_F['Lower-level pair W, track 1, on the viaduct']); _W2 = _F['Lower-level pair W, track 2, on the viaduct']
Wn = A([(q + r5_near(_W2, q)) / 2 for q in _w1])
if Wn[0, 1] > Wn[-1, 1]: Wn = Wn[::-1]
Wn = Wn[(Wn[:, 1] > 4335300) & (Wn[:, 1] < 4336300)]                       # west pair centre, northward
_Dl = LineString(RER['R-D-710306-4337028']['c']); _dD = r5_res(_Dl); _sD = chain(_dD)
deckc = A([(2 * q + r5_near(_F['APEx north approach 5 of 6'], q) + r5_near(_F['APEx north approach 6 of 6'], q)) / 4 for q in _dD])
Gr, sGr = deckc[::-1], _sD[::-1]                                           # deck centre, travelling north-west (R5's direction)
me = (sGr > 1700) & (sGr < 2500); mw = (sGr > 1450) & (sGr < 2000); trw = ctr[(cst > 4700) & (cst < 5400)]
iJe, Oe, Ke = r5_tangent(Wn, Gr[me], R5_RE, +1, +1); Je = Gr[me][int(round(iJe))]
iJw, Ow, Kw = r5_tangent(trw, Gr[mw], R5_RW, -1, -1); Jw = Gr[mw][int(round(iJw))]
ge = int(np.nonzero(me)[0][0] + round(iJe)); gw = int(np.nonzero(mw)[0][0] + round(iJw))
cspur = np.r_[r5_arc(Oe, Ke, Je, R5_RE, +1)[:-1], Gr[ge:gw], r5_arc(Ow, Jw, Kw, R5_RW, -1)]
css = chain(cspur); SP1 = Kw
s_Je, s_Jw = float(sGr[ge]), float(sGr[gw]); S_JW = float(css[-1] - LineString(r5_arc(Ow, Jw, Kw, R5_RW, -1)).length)
print('R5 leaves the west pair at', Ke.round(1), '(500 m) onto the deck centre at D s', round(s_Je), '; leaves it at D s', round(s_Jw), '(200 m) onto the trunk at', Kw.round(1), '; spur', round(float(css[-1])), 'm')
s_sc, s_sp = proj(ctr, cst, SC), proj(ctr, cst, SP1)
print('South Cumminsville platform s', round(float(s_sc - LPL / 2)), '-', round(float(s_sc + LPL / 2)), '; spur off the centre at s', round(float(s_sp)), '; split', round(float(s_S)))
TST = [s['name'] for s in C['rer_stations'] if 'A' in s['lines']]
trunk_st = []
for p in C['plats']:
    if p.get('pid') == TR and p['st'] not in [q[0] for q in trunk_st]:
        q = next(s['p'] for s in C['rer_stations'] if s['name'] == p['st'] and 'A' in s['lines'] and LineString(ctr).distance(Point(s['p'])) < 60)
        trunk_st.append((p['st'], q))
print('trunk stations', [t[0] for t in trunk_st])
n = len(ctr); hL = np.full(n, H0); hR = np.full(n, H0); W = np.zeros(n)
for name, q in trunk_st:
    if name == 'South Cumminsville': continue
    sc = proj(ctr, cst, q); s0, s1 = sc - LPL / 2, sc + LPL / 2; t = ISL / 2 + EDGE
    for i in range(n):
        dd = max(s0 - cst[i], cst[i] - s1, 0)
        if dd >= TAPER: continue
        w = 1 - dd / TAPER
        if w > W[i]: W[i] = w; hL[i] = H0 + (t - H0) * w; hR[i] = H0 + (t - H0) * w
HS = 4.5; a0, a1 = s_sp - 60, s_S                      # 3 tracks: southbound and northbound 4.5 m out from the centre (passing) track
for i in range(n):
    dd = max(a0 - cst[i], cst[i] - a1, 0)
    if dd >= 60: continue
    w = 1 - dd / 60; hL[i] = max(hL[i], H0 + (HS - H0) * w); hR[i] = max(hR[i], H0 + (HS - H0) * w)
nx, ny = normals(ctr)
trL = np.c_[ctr[:, 0] + nx * hL, ctr[:, 1] + ny * hL]; trR = np.c_[ctr[:, 0] - nx * hR, ctr[:, 1] - ny * hR]
C['tracks'] = [t for t in C['tracks'] if t.get('pid') not in (TR, B1, 'R-D-700348-4341340')]
C['tracks'] += [dict(sys='rer', line='A', pid=TR, c=r1(trL)), dict(sys='rer', line='A', pid=TR, c=r1(trR))]
h1L = np.full(len(c1), H0); h1L[cs1 < 40] = HS - (HS - H0) * cs1[cs1 < 40] / 40; n1x, n1y = normals(c1)
C['tracks'] += [dict(sys='rer', line='A', pid=B1, c=r1(np.c_[c1[:, 0] + n1x * h1L, c1[:, 1] + n1y * h1L])),
                dict(sys='rer', line='A', pid=B1, c=r1(np.c_[c1[:, 0] - n1x * h1L, c1[:, 1] - n1y * h1L]))]
def ring(c, cs, s0, s1, a, b):              # band between offsets a < b (left positive) from s0 to s1
    m = max(2, int(math.ceil((s1 - s0) / 4))); ss = np.linspace(s0, s1, m + 1); L = LineString(c)
    pts = np.array([L.interpolate(s).coords[0] for s in ss]); nx, ny = normals(pts)
    return r1(np.r_[np.c_[pts[:, 0] + nx * b, pts[:, 1] + ny * b], np.c_[pts[::-1, 0] + nx[::-1] * a, pts[::-1, 1] + ny[::-1] * a], [[pts[0, 0] + nx[0] * b, pts[0, 1] + ny[0] * b]]])
newp = []
for p in C['plats']:
    if p.get('pid') != TR: newp.append(p); continue
for name, q in trunk_st:
    sc = proj(ctr, cst, q)
    if name == 'South Cumminsville':
        for tag, (a, b) in (('W', (HS + EDGE, HS + EDGE + SIDE)), ('E', (-(HS + EDGE + SIDE), -(HS + EDGE)))):
            newp.append(dict(sys='rer', line='A', pid=TR, st=name, id=f'P-R-A-{int(SC[0])}-{int(SC[1])}{tag}', c=ring(ctr, cst, sc - LPL / 2, sc + LPL / 2, a, b)))
    else:
        pid0 = next(p['id'] for p in C['plats'] if p.get('pid') == TR and p['st'] == name)
        newp.append(dict(sys='rer', line='A', pid=TR, st=name, id=pid0, c=ring(ctr, cst, sc - LPL / 2, sc + LPL / 2, -ISL / 2, ISL / 2)))
C['plats'] = newp

# ---------------------------------------------------------------- lines into context
def curves_of(Vx, Kx):
    out = []
    for i in range(len(Vx) - 1):
        q = Kx.get(str(i))
        if q is None: continue
        a, b, q = A(Vx[i]), A(Vx[i + 1]), A(q); m = 0.25 * a + 0.5 * q + 0.25 * b
        # radius of the quadratic piece from its chord and sagitta
        ch = np.hypot(*(b - a)); sg = np.hypot(*(m - (a + b) / 2)); R = (ch * ch / 4 + sg * sg) / (2 * sg) if sg > 1e-6 else 1e9
        out.append([round(float(R), 1), round(float(m[0]), 1), round(float(m[1]), 1)])
    return out
f = RER[TR]; f['c'] = r1(Vt); f['k'] = {k: [round(float(v[0]), 1), round(float(v[1]), 1)] for k, v in Kt.items()}; f['curves'] = curves_of(Vt, Kt)
f['sub'] = 'RER-1a: trunk and Northside branch; through Millvale on the grid to South Cumminsville (Ben, 2026-10-21)'
f = RER[B1]; f['c'] = r1(V1); f['k'] = {k: [round(float(v[0]), 1), round(float(v[1]), 1)] for k, v in K1.items()}; f['curves'] = curves_of(V1, K1)
f['sub'] = 'RER-1b: from the South Cumminsville split (Ben, 2026-10-21)'

# ---------------------------------------------------------------- RER D west of the plan window: beside the Indianapolis pair, as inside
apx = [LineString(t['geometry']['coordinates']) for t in T['features'] if str(t['properties'].get('name')).startswith('APEx Cardinal, Floridian')]
a1c, a2c = np.array(apx[0].coords), np.array(apx[1].coords)
acen = (a1c + a2c) / 2 if len(a1c) == len(a2c) else a1c
fD = RER['R-D-700348-4341340']; cD = np.array(fD['c'])[::-1]               # from the seam westward
dD = dense([A(p) for p in cD], {}, 10.0); csD = chain(dD)
Lc = LineString(acen); inside = A(RER['R-D-710306-4337028']['c'][0])
q0 = A(Lc.interpolate(Lc.project(Point(inside))).coords[0]); hD = float(np.hypot(*(inside - q0)))
t0 = A(Lc.interpolate(Lc.project(Point(inside)) + 1).coords[0]) - q0; side = math.copysign(1, t0[0] * (inside - q0)[1] - t0[1] * (inside - q0)[0])
print('D inside starts', round(hD, 1), 'm from the APEx centre line, side', side)
newD = []
for i, p in enumerate(dD):
    s = csD[i]; tt = Lc.project(Point(p)); q = A(Lc.interpolate(tt).coords[0]); qq = A(Lc.interpolate(min(tt + 1, Lc.length)).coords[0]); tg = U(qq - q) if np.hypot(*(qq - q)) > 0 else np.array([1.0, 0])
    nrm = np.array([-tg[1], tg[0]]) * side; target = q + nrm * hD
    w = 1.0 if s < csD[-1] - 700 else max(0.0, (csD[-1] - s) / 700)      # back onto the KMZ line over the last 700 m (the RER-1c junction)
    newD.append(target * w + p * (1 - w))
newD = np.array(newD)[::-1]; newD[0] = A(fD['c'][0]); newD[-1] = inside if np.hypot(*(newD[-1] - inside)) < 3 else newD[-1]
# keep vertices every 50 m (straight-ish region line)
keep = [0] + [i for i in range(1, len(newD) - 1) if i % 5 == 0] + [len(newD) - 1]
fD['c'] = r1(newD[keep]); fD['k'] = None; fD['sub'] = fD['sub'] + '; beside the Indianapolis pair on the same side as inside the window (2026-10-21)'
cDd = dense([A(p) for p in fD['c']], {}, 10.0)
C['tracks'] += [dict(sys='rer', line='D', pid='R-D-700348-4341340', c=r1(offs(cDd, H0))), dict(sys='rer', line='D', pid='R-D-700348-4341340', c=r1(offs(cDd, -H0)))]
print('D seam gap now', round(float(np.hypot(*(A(fD['c'][-1]) - inside))), 1), 'm')

# ---------------------------------------------------------------- structures and marks along the trunk
def sub(c, cs, s0, s1):
    m = (cs >= s0) & (cs <= s1); L = LineString(c)
    return r1([L.interpolate(s0).coords[0]] + c[m].tolist() + [L.interpolate(s1).coords[0]])
bounds = [(712341.5, 4332783.0), (712346.0, 4332843.0), (712364.3, 4333102.0), (713085.0, 4337671.0), (713382.0, 4337815.0), (713508.0, 4337876.0)]
sb = [0.0] + [proj(ctr, cst, b) for b in bounds]
states = ['deck', 'tunnel', 'ramp', 'viaduct', 'ramp', 'tunnel']
newS = [r for r in C['rer_struct'] if r['line'] != 'A']
for st, s0, s1 in zip(states, sb[:-1], sb[1:]): newS.append(dict(line='A', state=st, s0=int(round(s0)), s1=int(round(s1)), c=sub(ctr, cst, s0, s1)))
newS.append(dict(line='A (RER-1b)', state='viaduct', s0=0, s1=300, c=sub(c1, cs1, 0, 300)))
for r in newS:                                                            # the Indianapolis + D deck's structure line was a stale alignment drawn across the Millvale grid
    if r['line'] == 'D (with the Indianapolis pair)': r['c'] = sub(_dD, _sD, 0.0, 2450.0); r['s0'], r['s1'] = 0, 2450
C['rer_struct'] = newS
xD = LineString(ctr).intersection(LineString(RER['R-D-710306-4337028']['c']))
marks = [m for m in C['rer_marks'] if not m['label'].startswith('under RER D')]
marks += [dict(p=[round(xD.x, 1), round(xD.y, 1)], label='under RER D (174.3 m), rail 167.0 m', anchor='right'),
          dict(p=[round(float(SC[0]), 1), round(float(SC[1]), 1)], label='South Cumminsville, 167.0 m: 3 tracks, R5 passes on the centre track', anchor='left'),
          dict(p=[round(float(S[0]), 1), round(float(S[1]), 1)], label=f'split: RER-1a north-east (curve {R2:.0f} m), RER-1b north', anchor='left'),
          dict(p=r1([SP1])[0], label='R5 off the centre track, over the northbound track at grade', anchor='right'),
          dict(p=r1([c1[min(len(c1) - 1, 150)]])[0], label='RER-1b viaduct, descent not set', anchor='left')]
C['rer_marks'] = marks

# ---------------------------------------------------------------- R5 on the Cumminsville Spur (tracks.json, lower layer)
old5 = [t for t in T['features'] if str(t['properties'].get('name')).startswith('R5 to the Cumminsville Spur')]
props = old5[0]['properties']; st5 = [A(t['geometry']['coordinates'][0]) for t in old5]
s_conv = css[-1] - 60                                                     # double track until 60 m before the trunk, then one track
s_one = S_JW                                                            # one track through the 200 m curve (it joins the single centre track)
hS = np.where(css < s_one - 40, H0, np.where(css < s_one, H0 * (s_one - css) / 40, 0.0))
W5, E5 = offs(cspur, hS), offs(cspur, -hS)
# the centre track: along the trunk centre from the spur point to the split, on along RER-1b 40 m, then into both RER-1b tracks
ctrm = (cst >= s_sp) & (cst <= s_S); cen = np.r_[ctr[ctrm], c1[(cs1 > 0) & (cs1 <= 40)]]
nb, sb_ = offs(c1, -H0), offs(c1, H0); j80 = int(np.argmin(abs(cs1 - 90)))
T['features'] = [t for t in T['features'] if t not in old5]
mk = lambda name, c, note: dict(type='Feature', properties=dict(props, name=name, note=note, level='167.0 m on the RER A viaduct at South Cumminsville; leaves the west pair at 164.6 m', state='viaduct'), geometry=dict(type='LineString', coordinates=r1(c)))
note5 = ('ORR R5 leaves the Transvalley/R5 pair (lower level, about 164.6 m) under the point where the Indianapolis + D deck crosses over it, curves left at 500 m onto the deck centre line, '
         'and runs on a lower level beneath the Indianapolis + D deck across the Millvale grid (two-level viaduct; the crossing is no wider than the four-track deck), rising to 167.0 m. '
         'Where the deck crosses RER A it leaves the deck on a 200 m curve, single track, crosses the northbound RER A track at grade and joins the centre (passing) track at South Cumminsville; '
         'north of the station it runs on the RER-1b tracks (Northside-Northgate) in the gaps between RER A trains')
T['features'] += [mk('R5 to the Cumminsville Spur (west track)', W5, note5), mk('R5 to the Cumminsville Spur (east track)', E5, note5),
                  mk('R5 centre (passing) track through South Cumminsville', np.r_[cspur[css >= s_conv], cen], note5),
                  mk('R5 onto RER-1b (northbound track)', np.r_[cen[-1:], nb[j80:j80 + 1]], note5),
                  mk('R5 onto RER-1b (southbound track)', np.r_[cen[-1:], sb_[j80:j80 + 1]], note5)]
# ---------------------------------------------------------------- Metro Line 3 realigned (Ben, 23 October: Line_3.kmz, from topographic maps of the real
# Cincinnati subway right-of-way through Camp Washington, St Bernard, Bond Hill and Norwood). The KMZ pieces (South Ext 1, Line 3, MCE, North Ext) are
# joined, clipped to the Metro window, fitted to constant-radius curves (arcs/fitarcs.py) and given tracks and island platforms as the transit build does
# (twin tubes). The line keeps its id so Ben's station settings on it still apply. Stations: a station shared with a lower-numbered line keeps that
# line's point (the build's merge rule); Line 3's own stations take the KMZ point.
import re as _re
from pyproj import Transformer as _Tr
from shapely.geometry import box as _box, Polygon as _Poly
_T4 = _Tr.from_crs(4326, 26916, always_xy=True); _WIN = _box(710300, 4329650, 716800, 4339800)
_k3 = open(SP + 'rer1023/line3_1023.kml', encoding='utf-8').read(); _L3, _S3 = {}, {}
for _pm in _re.findall(r'<Placemark.*?</Placemark>', _k3, _re.S):
    _nm = _re.search(r'<name>(.*?)</name>', _pm, _re.S).group(1).strip()
    _cs = [_T4.transform(*map(float, q.split(',')[:2])) for q in _re.search(r'<coordinates>(.*?)</coordinates>', _pm, _re.S).group(1).split()]
    (_S3 if '<Point' in _pm else _L3)[_nm] = _cs
_chain3 = []
for _nm in ('Line 3 South Ext 1', 'Line 3', 'Line 3 MCE', 'Line 3 North Ext Line'):     # south -> north, each piece starting where the last ended
    _c = _L3[_nm]
    if _chain3 and np.hypot(*np.subtract(_c[-1], _chain3[-1])) < np.hypot(*np.subtract(_c[0], _chain3[-1])): _c = _c[::-1]
    _chain3 += _c if not _chain3 else _c[1:]
_g3 = LineString(_chain3[::-1]).intersection(_WIN)                                       # north -> south, as before
_g3 = _g3 if _g3.geom_type == 'LineString' else max(_g3.geoms, key=lambda g: g.length)
_f3 = fitarcs.fit(list(_g3.coords)); _g3f = LineString(fitarcs.dense(_f3['verts'], _f3['k'], step=2.0))
_old3 = next(m for m in C['metro'] if m['name'] == 'Line 3'); _id3 = _old3['id']
_old3.update(c=_f3['verts'], k=_f3['k'], curves=[[q['R'], q['mid'][0], q['mid'][1]] for q in _f3['curves']])
_old3['sub'] = 'realigned 23 October on the real subway right-of-way (Ben, Line_3.kmz)'
_kmzst = {n.replace('Goverment', 'Goverment'): Point(c[0]) for n, c in _S3.items() if _WIN.contains(Point(c[0]))}
_moved3 = []
for st in C['stations']:
    ls = st['line'].split('Line ')[1:]; ls = [int(x) for x in ' '.join(ls).split() if x.isdigit()]
    if 3 not in ls or st['name'] not in _kmzst: continue
    if min(ls) < 3:                                                                       # shared with Line 1 or 2: that line's point stays, unless the
        _oth = [LineString(fitarcs.dense(m['c'], m['k'], step=2.0)) if m.get('k') else LineString(m['c']) for m in C['metro'] if m['name'] in ['Line %d' % x for x in ls if x != 3]]
        if not (_g3f.distance(Point(st['p'])) >= 60 and all(min(g.distance(_kmzst[st['name']]) for g in _oth if g.distance(Point(st['p'])) < 200) < 5 for _ in [0])): continue
        # new Line 3 runs over 60 m from it and Ben's point lies on the other line too (Kenard: the Line 1 / Line 3 crossing), so the station moves there
    q = _kmzst[st['name']]; d = q.distance(Point(st['p']))
    if d > 0.5: _moved3.append((st['name'], round(d))); st['p'] = [round(q.x, 1), round(q.y, 1)]
_MB3, _MT3, _MPL3 = C['meta']['metro_bore'], C['meta']['metro_twin'], C['meta'].get('metro_platform_m', 152.4)
def _rebuild_metro(mid, lname, g, era):                         # tracks and platforms of one Metro piece, as transit/build_transit.py makes them
    cfg = _MT3 if era == 'twin' else _MB3
    stp = [Point(st['p']) for st in C['stations'] if lname in st['line'].replace('Line ', 'Line ').split(' Line ') or (' ' + st['line'] + ' ').find(' ' + lname.split()[-1] + ' ') >= 0 and lname in st['line']]
    ch = sorted(g.project(q) for q in stp if g.distance(q) < 60)
    n = max(2, int(g.length / 2.0)); ds = np.linspace(0, g.length, n + 1); P = np.array([g.interpolate(d).coords[0] for d in ds])
    tg = np.gradient(P, axis=0); tg /= np.hypot(*tg.T)[:, None] + 1e-9
    for _ in range(3): tg[1:-1] = (tg[:-2] + 2 * tg[1:-1] + tg[2:]) / 4
    tg /= np.hypot(*tg.T)[:, None] + 1e-9; nr = np.c_[-tg[:, 1], tg[:, 0]]
    h = np.full(len(ds), cfg['h0'])
    if era == 'twin':
        hs = cfg['island'] / 2 + cfg['edge']
        for c_ in ch: h = np.maximum(h, cfg['h0'] + (hs - cfg['h0']) * np.clip(1 - (np.abs(ds - c_) - _MPL3 / 2) / 40.0, 0, 1))
    C['tracks'] = [t for t in C['tracks'] if t.get('pid') != mid] + [dict(sys='metro', line=lname, pid=mid, c=r1(np.asarray(LineString(P + nr * h[:, None] * sg).simplify(0.2).coords))) for sg in (1, -1)]
    newp = []
    for c_ in ch:
        a_, b_ = max(0, c_ - _MPL3 / 2), min(g.length, c_ + _MPL3 / 2)
        if b_ - a_ < _MPL3 * 0.6: continue
        sel = (ds >= a_) & (ds <= b_); Q, N_ = P[sel], nr[sel]
        bands = [(-cfg['island'] / 2, cfg['island'] / 2)] if era == 'twin' else [(cfg['h0'] + cfg['edge'], cfg['h0'] + cfg['edge'] + cfg['side']), (-(cfg['h0'] + cfg['edge'] + cfg['side']), -(cfg['h0'] + cfg['edge']))]
        for lo, hi in bands:
            pg = _Poly(np.r_[Q + N_ * hi, (Q + N_ * lo)[::-1]]).simplify(0.2); cen = pg.centroid
            near = min(C['stations'], key=lambda st: Point(st['p']).distance(cen))
            newp.append(dict(sys='metro', line=lname, pid=mid, c=r1(np.asarray(pg.exterior.coords)), st=near['name'] if Point(near['p']).distance(cen) < 400 else '',
                             id=f"P-M-{lname.replace('Line ', 'L')}-{round(cen.x)}-{round(cen.y)}"))
    C['plats'] = [p for p in C['plats'] if p.get('pid') != mid] + newp
    return ch, newp
_ch3, _np3 = _rebuild_metro(_id3, 'Line 3', _g3f, 'twin')
_far3 = [st['name'] for st in C['stations'] if 'Line 3' in st['line'] and _g3f.distance(Point(st['p'])) >= 60]
for _nm, _d in _moved3:                                          # other lines at a moved shared station (Kenard: Line 1) get their platform re-centred
    _st = next(st for st in C['stations'] if st['name'] == _nm)
    for m in C['metro']:
        if m['name'] == 'Line 3' or m['name'] not in ['Line %d' % int(x) for x in _re.findall(r'\d+', _st['line'])]: continue
        g_ = LineString(fitarcs.dense(m['c'], m['k'], step=2.0)) if m.get('k') else LineString(m['c'])
        if g_.distance(Point(_st['p'])) < 60: _rebuild_metro(m['id'], m['name'], g_, m.get('era', 'twin')); print('re-centred', m['name'], 'at', _nm)
print('Line 3 realigned:', round(_g3f.length), 'm in the window,', len(_f3['curves']), 'curves; stations moved', _moved3, '; platforms', len(_np3), '; stations over 60 m off the line', _far3)
# ---------------------------------------------------------------- Metro out to the RER limits (Ben, 23 October)
# The transit build drew the Metro inside its window only (E 710,300-716,800, N 4,329,650-4,339,800). Every line is now drawn out to the RER limits
# (E 699,000-736,900, N 4,320,800-4,347,000): the whole line from the Metro line files (Line 3 from Ben's 23 October KMZ) is fitted and given tracks and
# platforms as the build does; the parts outside the window are added as their own pieces, so the pieces inside (and Ben's edits on them) are unchanged.
# Stations outside the window are added; a station of the same name within 150 m of one already listed joins it (the build's merge rule).
_REG = _box(699000, 4320800, 736900, 4347000); _OUTW = _REG.difference(_WIN)
def _lnum(x): return int(_re.sub(r'\D', '', x) or 0)
_full = []
for _it in json.load(open(SP + 'handoff/page/lines/index.json')):
    _d = json.load(open(SP + f"handoff/page/lines/{_it['id']}.json"))
    if _d['line'] == 'Line 3':
        _gl = LineString(_chain3[::-1]); _sts = [(n, Point(c[0])) for n, c in _S3.items()]
    else:
        _gl = LineString([_T4.transform(lon, lat) for _, lon, lat in _d['path']]); _sts = [(s_['name'].strip(), Point(_T4.transform(s_['lon'], s_['lat']))) for s_ in _d['stations']]
    _full.append((_d['line'], _gl, _sts))
_nadd = _nst = 0; _ids = {m['id'] for m in C['metro']}
for _ln, _gl, _sts in _full:
    _gr = _gl.intersection(_REG)
    if _gr.is_empty or _gl.intersection(_OUTW).length < 30: continue
    _parts = [g for g in (_gr.geoms if _gr.geom_type == 'MultiLineString' else [_gr]) if g.geom_type == 'LineString' and g.length > 30]
    _era = 'twin' if _lnum(_ln) <= 7 else 'bore'
    for _st_n, _st_p in _sts:                                                  # stations outside the window
        if not _OUTW.contains(_st_p): continue
        _hit = next((st for st in C['stations'] if st['name'] == _st_n and Point(st['p']).distance(_st_p) < 150), None)
        if _hit:
            ls_ = set(_re.findall(r'Line \w+', _hit['line'])) | {_ln}; _hit['line'] = ' '.join(sorted(ls_, key=_lnum))
        else:
            C['stations'].append(dict(name=_st_n, line=_ln, p=[round(_st_p.x, 1), round(_st_p.y, 1)])); _nst += 1
    for _pt in _parts:
        _fr = fitarcs.fit(list(_pt.coords))
        _gf = LineString(fitarcs.dense(_fr['verts'], _fr['k'], step=2.0)) if not _fr.get('skipped') else _pt
        _tmp = 'TMP-' + _ln
        _rebuild_metro(_tmp, _ln, _gf, _era)                                    # tracks and platforms along the whole part (stations near the window edge too)
        _outer = _gf.intersection(_OUTW)
        for _op in [g for g in (_outer.geoms if _outer.geom_type == 'MultiLineString' else [_outer]) if g.geom_type == 'LineString' and g.length > 30]:
            _x0, _y0 = _op.coords[0]; _mid_ = 'M-%s-%d-%d' % (_ln.replace('Line ', 'L').replace(' ', ''), round(_x0), round(_y0))
            while _mid_ in _ids: _mid_ += 'x'
            _ids.add(_mid_)
            C['metro'].append(dict(id=_mid_, name=_ln, era=_era, c=r1(np.asarray(_op.simplify(0.5).coords)), outer=True, sub='outside the plan window, to the RER limits (23 October)'))
            for t in C['tracks']:
                if t.get('pid') != _tmp: continue
                tt = LineString(t['c']).intersection(_op.buffer(12, cap_style=2))
                for q in (tt.geoms if tt.geom_type == 'MultiLineString' else [tt]):
                    if q.geom_type == 'LineString' and q.length > 5: C['tracks'].append(dict(sys='metro', line=_ln, pid=_mid_, c=r1(np.asarray(q.coords))))
            for pl in C['plats']:
                if pl.get('pid') == _tmp and _Poly(pl['c']).centroid.distance(_op) < 15 and _OUTW.contains(_Poly(pl['c']).centroid): pl['pid'] = _mid_
            _nadd += 1
        C['tracks'] = [t for t in C['tracks'] if t.get('pid') != _tmp]
        C['plats'] = [pl for pl in C['plats'] if pl.get('pid') != _tmp]
print('Metro to the RER limits: outer pieces', _nadd, '; stations added', _nst, '; metro pieces now', len(C['metro']), '; metro platforms', sum(1 for pl in C['plats'] if pl['sys'] == 'metro'))
# ---------------------------------------------------------------- Metro termini without platforms (Ben 2026-10-22: Wayne had one)
# the transit build clipped each platform to its line and dropped any left under 60% of its length, so a station at a line end
# (Wayne on Line 13, Kirby on Line 12, Northside on Line 8, Pennsylvania on Line 5) got none; here the platform is slid to lie
# wholly on the line, ending at the station point's end
_MB, _MT, _MPL = C['meta']['metro_bore'], C['meta']['metro_twin'], C['meta'].get('metro_platform_m', 152.4)
_have = {(q['sys'], q.get('pid'), q['st']) for q in C['plats']}
_added = []
for _m in C['metro']:
    _g = LineString(dense([A(v) for v in _m['c']], {kk: A(vv) for kk, vv in (_m.get('k') or {}).items()}, 2.0)) if _m.get('k') else LineString(_m['c'])
    if _g.length < _MPL: continue
    for _st in C['stations']:
        if _m['name'] not in [('Line ' + x) for x in _st['line'].replace('Line ', '').split()]: continue
        if _g.distance(Point(_st['p'])) >= 60 or ('metro', _m['id'], _st['name']) in _have: continue
        if any(q['sys'] == 'metro' and q['line'] == _m['name'] and q['st'] == _st['name'] for q in C['plats']): continue
        _c = _g.project(Point(_st['p'])); _a, _b = _c - _MPL / 2, _c + _MPL / 2
        if _a >= 0 and _b <= _g.length: continue                                # an inside station: not this case
        _a, _b = (0.0, _MPL) if _a < 0 else (_g.length - _MPL, _g.length)
        _q = r5_res(_g, 2.0); _qs = chain(_q); _sel = (_qs >= _a - 0.01) & (_qs <= _b + 0.01); Q = _q[_sel]; Nn = r5_nrm(_q)[_sel]
        _twin = _m.get('era') == 'twin'
        if _twin:
            _bands = [(-_MT['island'] / 2, _MT['island'] / 2)]
        else:
            _i0 = _MB['h0'] + _MB['edge']; _bands = [(_i0, _i0 + _MB['side']), (-_i0 - _MB['side'], -_i0)]
        for _lo, _hi in _bands:
            _ring = np.r_[Q + Nn * _hi, (Q + Nn * _lo)[::-1]]; _ring = np.r_[_ring, _ring[:1]]
            _cen = _ring[:-1].mean(axis=0)
            C['plats'].append(dict(sys='metro', line=_m['name'], pid=_m['id'], st=_st['name'], id=f"P-M-{_m['id'].split('-')[1]}-{int(_cen[0])}-{int(_cen[1])}", c=r1(_ring)))
        _added.append((_st['name'], _m['name'], 'island' if _twin else 'side x2', round(_a), round(_b)))
        _have.add(('metro', _m['id'], _st['name']))
print('terminus platforms added', _added)
for t in T['features']:                                                    # the level marker follows the new divergence
    if t['properties'].get('name') == 'R5 leaves the west pair':
        t['geometry']['coordinates'] = r1([Ke])[0]; t['properties']['label'] = 'R5 leaves the west pair under the deck, 164.6 m'
_B = LineString(RER['R-B-712689-4336858']['c'])                            # RER B's structure line was the same stale alignment through Millvale; now its line on the viaduct, south of the Ludlow descent
for r in C['rer_struct']:
    if r['line'] == 'B' and r['state'] == 'viaduct':
        _bb = r5_res(_B); _bb = _bb if _bb[0, 1] < _bb[-1, 1] else _bb[::-1]; _bb = _bb[_bb[:, 1] < 4336600]; r['c'] = r1(_bb); r['s0'], r['s1'] = 0, int(round(float(chain(_bb)[-1])))
# ---------------------------------------------------------------- Ludlow at ground, the trunk over it (highway update, Ben 2026-10-22)
# Ludlow Avenue stays at ground on its 1914 line; the trunk came later and rises on fill to a span over it. Levels from nv/geom27.py:
# 162.5 m over Ludlow (s 5,369), level through the RER B Northside / Spring Grove platforms, then 1.5% down to ground.
sys.path.insert(0, _ws.CODE + 'nv'); import geom27 as G27
_DMJ = json.load(open(SP + 'topo/dem2m.json')); _DEM = np.load(SP + 'topo/dem2m.npy', mmap_mode='r')
def _gz(p): return float(_DEM[int((_DMJ['y1'] - p[1]) / 2), int((p[0] - _DMJ['x0']) / 2)]) / 10.0
S_FILL1 = next(float(x) for x in np.arange(G27.S_NSP1, 7000, 5.0) if G27.north_z(x) <= _gz(G27.C.interpolate(x).coords[0]))
LUD_TXT = f'rails {G27.Z_LUD:.1f} m over Ludlow Avenue (at ground on its 1914 line)'
for t in T['features']:
    pr = t['properties']; nm_ = str(pr.get('name'))
    if pr.get('note') and 'rails at ground, 155.5 m' in pr['note']:
        pr['note'] = pr['note'].replace('on the viaduct from Ludlow (rails at ground, 155.5 m)', f'on the viaduct from just north of Ludlow, where the rails stand {G27.Z_LUD:.1f} m over Ludlow Avenue at ground on its 1914 line (fill north of there),')
    if nm_.startswith('APEx Southwest Chief, Transcontinental Limited'):
        pr['note'] = (pr.get('note') or '') + (f' North of Ludlow on fill: {G27.Z_LUD:.1f} m over Ludlow, level through the RER B Northside / Spring Grove platforms to s {G27.S_NSP1:,.0f}, '
                                               f'then {100 * G27.G_NFILL:.1f}% down to ground at about s {S_FILL1:,.0f} (2026-10-22)')
        pr['level'] = 'fill'
    if pr.get('layer') == 'marker' and nm_.startswith('Ludlow: rails at ground'):
        lab = f'Ludlow: {LUD_TXT}; viaduct south to CUT, fill north'
        pr['name'] = pr['label'] = lab
    if pr.get('layer') == 'marker' and nm_.startswith('deck tip: viaduct'):
        lab = f'deck tip: viaduct {G27.Z_TIP:.1f} m, {100 * G27.G_BAND:.2f}% down to Ludlow'
        pr['name'] = pr['label'] = lab
_z5 = G27.band(G27.C.project(Point(Ke)))                                 # the band is higher north of the deck tip now, so R5 leaves the west pair higher
for t in T['features']:
    pr = t['properties']; nm_ = str(pr.get('name'))
    if nm_ == 'R5 leaves the west pair': pr['label'] = f'R5 leaves the west pair under the deck, {_z5:.1f} m'
    for k in ('note', 'level'):
        if nm_.startswith('R5 ') and pr.get(k): pr[k] = pr[k].replace('about 164.6 m', f'about {_z5:.1f} m').replace('at 164.6 m', f'at {_z5:.1f} m')
    if pr.get('layer') == 'marker' and str(pr.get('label', '')).startswith('Indianapolis + D 173.1 m'):
        _s = G27.C.project(Point(t['geometry']['coordinates']))
        pr['label'] = pr['name'] = pr['label'].replace('(6.8 m over the viaduct)', f'({173.1 - G27.band(_s):.1f} m over the viaduct)')
_lab = {str(t['properties'].get('label')) for t in T['features'] if t['properties'].get('layer') == 'marker'}
_nm = T.get('summary', {}).get('north', {}).get('marks')
if _nm:
    _new = {m.split(':')[0][:12]: m for m in _lab}
    T['summary']['north']['marks'] = [next((m for m in _lab if m[:14] == x[:14] and m != x), x) for x in _nm]
_fill_end = G27.C.interpolate(S_FILL1).coords[0]
T['features'].append(dict(type='Feature', properties=dict(layer='marker', kind='level', name='trunk fill ends', label=f'trunk back at ground, {G27.north_z(S_FILL1):.1f} m (fill from Ludlow)', anchor='right'),
                          geometry=dict(type='Point', coordinates=[round(_fill_end[0] + 25, 1), round(_fill_end[1] - 10, 1)])))
_Bs = LineString(RER['R-B-712689-4336858']['c']); _Bn = LineString(RER['R-B-715612-4338596']['c'])
_lud = LineString([(712724, 4336957), (712717, 4336910), (712713, 4336861)])            # Ludlow (S22015) where the trunk crosses it
_xb = _Bn.intersection(_lud); _xb = _xb if _xb.geom_type == 'Point' else (list(_xb.geoms)[0] if not _xb.is_empty else Point(_Bn.coords[0]))
_bn = r5_res(_Bn); _bn = _bn if np.hypot(*(_bn[0] - A(_Bs.coords[-1]))) < np.hypot(*(_bn[-1] - A(_Bs.coords[-1]))) else _bn[::-1]; _bns = chain(_bn)
_sx = LineString(_bn).project(_xb); _sf = next((float(_bns[i]) for i in range(len(_bn)) if G27.C.project(Point(_bn[i])) >= S_FILL1), float(_bns[-1]))
_newS = []
for r in C['rer_struct']:
    if r['line'] == 'B' and r['state'] == 'viaduct':
        _bb = r5_res(_Bs); _bb = _bb if _bb[0, 1] < _bb[-1, 1] else _bb[::-1]; r['c'] = r1(_bb); r['s0'], r['s1'] = 0, int(round(float(chain(_bb)[-1])))
    _newS.append(r)
_newS.append(dict(line='B', state='viaduct', s0=0, s1=int(round(_sx + 25)), c=r1(_bn[_bns <= _sx + 25])))
_newS.append(dict(line='B', state='embankment', s0=int(round(_sx + 25)), s1=int(round(_sf)), c=r1(_bn[(_bns >= _sx + 25) & (_bns <= _sf)])))
C['rer_struct'] = _newS
_m = []
for mm in C['rer_marks']:
    if mm['label'].startswith('B at ground at Ludlow'):
        mm = dict(mm, label=f'B over Ludlow, {G27.Z_LUD:.1f} m; Northside / Spring Grove on the trunk fill (level), ground again about {S_FILL1 - G27.S_LUD:,.0f} m north')
    if mm['label'].startswith('Arlington (B) on the viaduct'):
        mm = dict(mm, label=f'Arlington (B) on the viaduct, {G27.Z_AR:.1f} m')
    if mm['label'].startswith('RER-1b viaduct, descent not set'):
        mm = dict(mm, label='RER-1b viaduct, descent not set (stays up over OH-74)')
    _m.append(mm)
_HW = json.load(open(SP + 'hwy/data.json')); _HO = _HW['origin']
def _seg(r, a, t): return LineString([(x + _HO[0], y + _HO[1]) for x, y in next(q for q in _HW['segs'] if q['r'] == r and q['a'] == a and q['t'] == t)['c']])
_x74 = LineString(c1).intersection(_seg('OH-74', 18.67, 'Boulevard'))
if not _x74.is_empty:
    _x74 = _x74 if _x74.geom_type == 'Point' else list(_x74.geoms)[0]
    _m.append(dict(p=[round(_x74.x, 1), round(_x74.y, 1)], label=f'RER-1b over OH-74 on viaduct: rail 160 m or more, road {_gz((_x74.x, _x74.y)):.1f} m', anchor='right'))
_xmb = _Bs.intersection(_seg('OH-75', 19.4, 'Boulevard'))
if not _xmb.is_empty:
    _xmb = _xmb if _xmb.geom_type == 'Point' else list(_xmb.geoms)[0]; _zb = G27.band(G27.C.project(_xmb))
    _m.append(dict(p=[round(_xmb.x, 1), round(_xmb.y, 1)], label=f'B over Millvale Boulevard, rail about {_zb:.1f} m (ground {_gz((_xmb.x, _xmb.y)):.1f} m)', anchor='left'))
_m.append(dict(p=[round(float(G27.C.interpolate(5465).x) + 30, 1), round(float(G27.C.interpolate(5465).y) - 15, 1)], label=f'Northside / Spring Grove (B) on the fill, {G27.Z_LUD:.1f} m', anchor='right'))
C['rer_marks'] = _m
print('Ludlow raise: fill to s', round(S_FILL1), '; B over Ludlow at B s', round(_sx), '; B fill to B s', round(_sf), '; RER-1b x OH-74', _x74, '; B x Millvale', _xmb)
# ---------------------------------------------------------------- Metro platforms 400 ft (Ben, 23 October; was 500 ft from 2026-10-05)
sys.path.insert(0, _ws.CODE + 'rer1023'); import metro400 as _m400
_r400 = _m400.apply(C, 121.92); print('Metro platforms to 400 ft (121.92 m):', _r400['plats'], 'platforms on', _r400['pieces'], 'pieces; twin tracks re-spread; joined', _r400['joined'], '; dropped', _r400['dropped'])
import norwood_pass as _nwp; print('Norwood Central below ground (sketch v10):', _nwp.apply(C)); print('Metro 3 to Norwood Central (Ben, 24 October):', _nwp.apply_l3(C)); print('TRI A through Norwood Central:', _nwp.apply_tria(C))
import gaps_pass as _gp                                                    # Line 5 through Pennsylvania, then every line unbroken (Ben, 24 October)
print('Line 5 at Pennsylvania:', _gp.apply_l5(C)); import l10_pass as _l10; print('Line 10 new right of way:', _l10.apply(C)); print('Lines joined:', len(_gp.apply(C, json.load(open(SP + 'dbread/deck/layout.json'))['transit'])))
json.dump(C, open(SP + 'deckpage/context.json', 'w'), separators=(',', ':')); json.dump(T, open(SP + 'deckpage/tracks.json', 'w'), separators=(',', ':'))
json.dump(dict(trunk=r1(ctr), b1=r1(c1), spur=r1(cspur), S=r1([S])[0], SC=r1([SC])[0], R1=R1, R2=R2, s_sc=float(s_sc), s_S=float(s_S), s_sp=float(s_sp)), open(SP + 'rer1023/geom.json', 'w'))
print('written')
