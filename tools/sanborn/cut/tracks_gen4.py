try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# CUT approach tracks, v4 (2026-10-14; page version 27): the north trunk viaduct from Ludlow (log 10za.30-10za.33, nv/geom27.py).
# v3 (2026-10-10): Arch-viaduct basis (Ben): APEx a set height above the deck cross streets
# from Marshall to W 6th; lower level at -2 (144 m) centred under the APEx field; A-D aligned with E-H at the south end.
# All alignments smoothed (Chaikin corner cutting) and junctions drawn with tangent-matched Beziers.
import json, math
import numpy as np
from shapely.geometry import LineString, Point

S = _ws.DATA
OUT = S + 'deckpage/tracks.json'
APX = json.load(open(S + 'cut/apex_cut.json'))
TB = json.load(open(S + 'cut/trimet_bridges.json'))

DECK = lambda N: 151.8 + (N - 4330700) / 4840 * 8.2       # map 3 deck surface (10d.4)
CLR = 6.5                                                 # cross-street clearance 4.9 m + arch crown, fill and track 1.6 m (working)
APEX = lambda N: DECK(N) + CLR                            # viaduct rail, Marshall to W 6th
LOWER = 144.0                                             # -2 rail
UNDER = 6.8                                               # street over an open track: canon RER clear height 5.8 m + 1.0 m street deck (10j.7)
TRIMET_CUT = 156.3
FW, FE = 712686.0, 712838.0
FN0, FN1 = 4331646.0, 4332134.0
FCN = (FN0 + FN1) / 2
NT, ST = 4332400.0, 4331400.0
FC = (FW + FE) / 2
STREETS = {'Marshall': 4334371, 'Straight': 4334183, 'Alfred': 4333995, 'W Liberty': 4332395, 'Gest': 4331557, 'W 8th': 4331225, 'W 6th': 4330846}
# through streets where they cross the APEx trunk, read from the deck layer (realigned onto the basin streets 2026-10-11)
_DK0 = json.load(open(S + 'deckpage/deck.json'))
for _nm, _dn in (('W Liberty', 'W Liberty'), ('Gest', 'Gest'), ('W 8th', 'W 8th (viaduct line)'), ('W 6th', 'W 6th')):
    for _f in _DK0['features']:
        if _f['properties'].get('layer') == 'street' and _f['properties'].get('name') == _dn:
            _h = LineString(_f['geometry']['coordinates']).intersection(LineString([(712760, 4329000), (712760, 4336000)]))
            if _h.geom_type == 'Point': STREETS[_nm] = round(_h.y, 1)

F = []
R = lambda c: [[round(x, 1), round(y, 1)] for x, y in c]
def add(layer, coords, **p): F.append(dict(type='Feature', properties=dict(layer=layer, **p), geometry=dict(type='LineString', coordinates=R(coords))))
def addpoly(layer, ring, **p): F.append(dict(type='Feature', properties=dict(layer=layer, **p), geometry=dict(type='Polygon', coordinates=[R(ring)])))
def addpt(layer, xy, **p): F.append(dict(type='Feature', properties=dict(layer=layer, **p), geometry=dict(type='Point', coordinates=[round(xy[0], 1), round(xy[1], 1)])))

# ---------------------------------------------------------------- geometry helpers
def chaikin(pts, it=5):
    P = np.asarray(pts, float)
    for _ in range(it):
        Q = [P[0]]
        for a, b in zip(P[:-1], P[1:]):
            Q += [0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b]
        Q.append(P[-1]); P = np.asarray(Q)
    return [tuple(p) for p in P]
def resample(c, step=5.0):
    L = LineString(c); n = max(2, int(L.length / step) + 1)
    return [tuple(L.interpolate(d).coords[0]) for d in np.linspace(0, L.length, n)]
def smooth(pts, it=5, step=5.0): return resample(chaikin(pts, it), step)
def thin(c, d=40.0):
    o = [c[0]]
    for p in c[1:-1]:
        if math.dist(p, o[-1]) >= d: o.append(p)
    o.append(c[-1]); return o
def joinsmooth(parts, d=40.0, it=5):
    c = []
    for p in parts:
        c += [tuple(q) for q in p if not c or math.dist(q, c[-1]) > 0.5]
    return smooth(thin(c, d), it=it)
def tangent(c, at='start'):
    a, b = (c[0], c[min(3, len(c) - 1)]) if at == 'start' else (c[max(-4, -len(c))], c[-1])
    d = np.subtract(b, a); return d / np.linalg.norm(d)
def bezt(a, ta, b, tb, k=0.4, n=40):
    """Cubic from a (leaving along ta) to b (arriving along tb)."""
    a, b, ta, tb = map(np.asarray, (a, b, ta, tb)); L = np.linalg.norm(b - a)
    c0, c1 = a + ta * k * L, b - tb * k * L
    t = np.linspace(0, 1, n)[:, None]
    return [tuple(p) for p in (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * c0 + 3 * (1 - t) * t * t * c1 + t ** 3 * b]
def offs(c, d):
    """Offset a polyline by d, +d = east (right of southbound travel), keeping its direction."""
    south = c[-1][1] < c[0][1]
    g = LineString(c).offset_curve(d if south else -d, quad_segs=16, join_style='round')
    if g.geom_type == 'MultiLineString':                             # a tiny kink splits the offset: rebuild it point by point
        out = []
        for i, q in enumerate(c):
            a_, b_ = c[max(0, i - 1)], c[min(len(c) - 1, i + 1)]; t = np.subtract(b_, a_); L = np.linalg.norm(t)
            if L < 1e-9: continue
            t = t / L; nl = np.array([-t[1], t[0]]); out.append(tuple(np.array(q) + nl * (d if south else -d)))
        return out
    return list(g.coords)
def cut_at_N(c, N):
    """Keep the part of a north->south polyline north of N, ending exactly at N."""
    out = []
    for a, b in zip(c[:-1], c[1:]):
        out.append(a)
        if (a[1] - N) * (b[1] - N) <= 0 and a[1] != b[1]:
            f = (N - a[1]) / (b[1] - a[1]); out.append((a[0] + f * (b[0] - a[0]), N)); return out
    return c
def from_N(c, N):
    """Keep the part of a north->south polyline south of N, starting exactly at N."""
    for i, (a, b) in enumerate(zip(c[:-1], c[1:])):
        if (a[1] - N) * (b[1] - N) <= 0 and a[1] != b[1]:
            f = (N - a[1]) / (b[1] - a[1]); return [(a[0] + f * (b[0] - a[0]), N)] + c[i + 1:]
    return c
def s_at_N(c, N):
    acc = 0
    for a, b in zip(c[:-1], c[1:]):
        if (a[1] - N) * (b[1] - N) <= 0 and a[1] != b[1]:
            return acc + math.dist(a, (a[0] + (N - a[1]) / (b[1] - a[1]) * (b[0] - a[0]), N))
        acc += math.dist(a, b)
    return None
def pt_at(c, s): p = LineString(c).interpolate(s); return (p.x, p.y)
def min_radius(c, win=20.0):
    c = resample(c, 5.0); r = 1e9
    k = int(win / 5)
    for i in range(k, len(c) - k):
        a, b, d = np.array(c[i - k]), np.array(c[i]), np.array(c[i + k])
        ab, bd, ad = np.linalg.norm(b - a), np.linalg.norm(d - b), np.linalg.norm(d - a)
        u_, v_ = b - a, d - a; cr = abs(u_[0] * v_[1] - u_[1] * v_[0])
        if cr > 1e-6: r = min(r, ab * bd * ad / (2 * cr))
    return r

# ---------------------------------------------------------------- APEx platform field and freight passing track (viaduct level)
# 2026-10-15 (Ben): the field as on the architects' plot plan of 1 June 1931 (cutplan/field1931.py): straight parallel tracks at
# bearing 178.8 degrees, 3.97 m pair centres, 11.68 m across an island (8.3 m platforms, edges 1.68 m from track centres), 15.65 m a unit.
# Seven concourse islands carry APEx 1-14 from the building westward; island M beside the building, track 16 and the platform running
# the full length (Ben), is the 1933 mail platform, now CVG Express 15-16; the westmost through track is the freight
# passing track. The platform zone keeps the ruled N 4,331,646-4,332,134 (the plan is cut off north of N 4,332,094).
FLD = json.load(open(S + 'cut/field1931.json'))
F_P0 = np.array(FLD['p0']); F_DIR = np.array(FLD['dir']); F_E = np.array(FLD['east']); F_OFF = FLD['off_m']; F_EDGE = FLD['edge_m']
B_N, B_S = FLD['building_north_N'], FLD['building_south_N']           # track 16's stubs end at the building's north and south faces
def fpt(n, N):
    """Point on field track n (or a numeric offset) at northing N."""
    o = F_OFF[n] if isinstance(n, str) else n
    base = F_P0 + F_E * o; t = (N - base[1]) / F_DIR[1]; return tuple(base + F_DIR * t)
def fline(n, Na, Nb): return [fpt(n, Na), fpt(n, Nb)]
FTR = [str(i) for i in range(1, 17)]
ISL = [(f'APEx platform {u + 1}, tracks {2*u + 1} / {2*u + 2}', str(2 * u + 1), str(2 * u + 2), FN0, FN1) for u in range(7)] + \
      [('Platform M, CVG Express tracks 15 / 16: the 1933 mail platform', '16', '15', FN0, FN1)]
for nm, te, tw, Na, Nb in ISL:
    oe, ow = F_OFF[te] - F_EDGE, F_OFF[tw] + F_EDGE
    ring = [fpt(oe, Na), fpt(oe, Nb), fpt(ow, Nb), fpt(ow, Na), fpt(oe, Na)]
    addpoly('apex_plat', ring, name=nm, level='0', rail=round(APEX(FCN), 1), length_m=round(Nb - Na, 1), width_m=round(oe - ow, 2),
            src='plot plan, 1 June 1931 (HABS OH-705)', **({'service': 'CVG Express'} if 'M' in nm.split(',')[0] else {}))
TRK = {}                                                # track -> (north end, south end) of its platform line
for n in FTR:
    add('apex', fline(n, FN1, FN0), name=(f'Track {n} (CVG Express)' if n in ('15', '16') else f'APEx track {n}'), level='0', kind='platform',
        **({'service': 'CVG Express'} if n in ('15', '16') else {}))
    TRK[n] = (fpt(n, FN1), fpt(n, FN0))
FC_NEW = (fpt('1', FCN)[0] + fpt('14', FCN)[0]) / 2     # centre of APEx 1-14

# ---------------------------------------------------------------- trunk: smooth curve from the deck's north end, then straight to the throat
north_ctrl = [(712247, 4335576), (712242, 4335456), (712238, 4335337), (712233, 4335216), (712233, 4335092), (712271, 4334964),
              (712354, 4334857), (712437, 4334757), (712514, 4334654), (712584, 4334550), (712654, 4334447), (712721, 4334335), (712753, 4334180)]
STR0 = (712753.0, 4334180.0)
straight = [(STR0[0] + (FC - STR0[0]) * f, STR0[1] + (NT - STR0[1]) * f) for f in np.linspace(0, 1, 12)]
import sys as _sys; _sys.path.insert(0, _ws.CODE + 'nv')
import geom27 as G27
CN = [tuple(p) for p in G27.NT]                       # 2026-10-14: the trunk now starts at Ludlow (s 5,420) and runs over the deck tip
A_OFF = [-11.25, -6.75, -2.25, 2.25, 6.75, 11.25]
appr_n = []
for j, d in enumerate(A_OFF):
    if j < 4:
        c = offs(CN, d)
        add('apex', c, name=f'APEx north approach {j+1} of 6', level='0', kind='approach', note='Dayton and Norwood lines: on the viaduct from Ludlow (rails at ground, 155.5 m) to CUT')
    else:   # the Indianapolis pair: from the west edge of the plan over the trunk and down the approach
        south = offs(CN, d); south = [q for q in south if G27.C.project(Point(q)) < 2600]
        gt = G27.group_track(d)[::-1]                    # west -> trunk -> Marshall
        gt = [q for q in gt if not (G27.C.project(Point(q)) < 2600 and LineString(CN).distance(Point(q)) < 60)]
        c = smooth(thin(gt + south, 6.0), it=2, step=3.0)
        add('apex', c, name=f'APEx north approach {j+1} of 6', level='0', kind='approach',
            note=f'Indianapolis line: in the viaduct to s {G27.S_A:,.0f}, then 2.5% up on one deck with TRI D to 174.3 m and west on the KMZ curve over the Dayton/Norwood and Transvalley/R5 tracks')
    appr_n.append(c)
W2E = sorted(FTR, key=lambda n: F_OFF[n])                # 14, 13, ... 2, 1, 15, 16
for i, n in enumerate(W2E):
    j = min(5, int(i * 6 / 16)); e = appr_n[j][-1]
    add('apex', bezt(TRK[n][0], tuple(-F_DIR), e, -tangent(appr_n[j], 'end')), name=f'APEx north throat, track {n}', level='0', kind='throat')
# passing track (the plan's westmost through track)
j_n = from_N(appr_n[0], 4332520)[0]
pas_n = bezt(j_n, tangent(appr_n[0], 'end'), fpt('F', FN1), tuple(F_DIR), k=0.42, n=60) + fline('F', FN1, FN0)[1:]
# ---------------------------------------------------------------- south approach (viaduct level)
CSB = (np.array([712595.0, 4330684.0]), np.array([712526.0, 4330371.0]))          # TRIMET CS bridge, north and south bank
_dc = (CSB[1] - CSB[0]) / np.linalg.norm(CSB[1] - CSB[0]); _nc = np.array([-_dc[1], _dc[0]])
if _nc[0] < 0: _nc = -_nc                                                           # east-pointing normal of the CS bridge
# 2026-10-15 (Ben, General CUT Path of APEx.kmz): straight south from the field, one curve between W 8th and W 6th, then a single
# straight across the Ohio on the four-track APEx bridge (bearing about 204 degrees) toward Erlanger, centred on the KMZ line.
# v37: the approach carries APEx Kentucky 4 + the Cardinal pair (6 tracks, centre line CSL 4.5 m east of the bridge line); the Cardinal
# pair leaves east south of W 8th; the CVG Express pair comes from platform M beside the building and flies over the six APEx tracks
# to the TRIMET CS viaduct and the CS bridge, joining the intercity pair (A-D) at the abutment.
GP_BANK = np.array([712695.9, 4330688.2]); GP_END = np.array([710371.1, 4325459.5])  # KMZ: Ohio bank, south-west end
_d = (GP_END - GP_BANK) / np.linalg.norm(GP_END - GP_BANK); _n = np.array([-_d[1], _d[0]])
if _n[0] < 0: _n = -_n                                                              # east-pointing normal of the bridge line
# Ben (17 October): no reverse curve in Ludlow; the APEx runs straight off its bridge on the KMZ bearing (204 degrees), as the KMZ line
# itself does through Ludlow and the hills. The CS line (CS Bridge KY Approach.kmz) bends to the west at its Kentucky end and passes within
# 8.4 m of that straight (at N 4,330,200), so the APEx line is drawn the least distance east of the KMZ line that keeps 15.75 m (CS pair
# centre to APEx centre, group spacing 6.75 m): bridge and straight together, no curve.
CS_KY_KMZ = [tuple(q) for q in json.load(open(S + 'cskmz/cs_ky.json'))['c']]
def _clear(sh):
    _kb = GP_BANK + _n * sh + _d * ((GP_BANK[1] - 4330371.0) / -_d[1]); _csl = LineString(CS_KY_KMZ)
    return min(_csl.distance(Point(tuple(_kb + _d * t))) for t in np.arange(0, 500, 5.0))
APEX_SHIFT = next(sh for sh in np.arange(0, 20.01, 0.25) if _clear(sh) >= 15.75)
GP_BANK = GP_BANK + _n * APEX_SHIFT; GP_END = GP_END + _n * APEX_SHIFT
# Ben (17 October, Bridge Spans.kmz): where the bridge structures start and end (river spans only, no viaducts)
SPANS = {q['name'].replace('&amp;', '&'): [np.array(c) for c in q['c']] for q in json.load(open(S + 'spankmz/spans.json'))}
_on = lambda q: GP_BANK + _d * float(np.dot(np.array(q) + _n * APEX_SHIFT - GP_BANK, _d))
APB = (_on(SPANS['APEx 4Track'][0]), _on(SPANS['APEx 4Track'][-1]))                 # APEx bridge centre line (the four tracks), the KMZ span moved with the line
CSB = (SPANS['CS'][0], SPANS['CS'][-1])                                             # the 1922 CS bridge span
_w = _n * 4.5                                                                       # approach centre line: 4.5 m east of the four tracks
APB_OFF = float(np.dot(APB[0] - CSB[0], _nc)); APB_OFF_S = float(np.dot(APB[1] - CSB[1], _nc))
FCA = FC_NEW + 4.5 - 4.5                                                            # straight part on the APEx field's centre line
_E2 = APB[0] + _w
_tP = (FCA - _E2[0]) / _d[0]; _PI = _E2 + _d * _tP                                  # the field centre line meets the bridge line
T_APP = float(np.linalg.norm(_PI - _E2)); DEFL = math.acos(float(np.dot([0.0, -1.0], _d)))
R_APP = T_APP / math.tan(DEFL / 2)                                                  # curve ends at the Ohio bank: the bridge is straight
_CS0 = np.array([FCA, _PI[1] + T_APP]); _CC = _CS0 + np.array([-R_APP, 0.0])       # right-hand curve (south to south-south-west)
_arc = [tuple(_CC + R_APP * np.array([math.cos(a), math.sin(a)])) for a in np.linspace(0, -DEFL, max(8, int(R_APP * DEFL / 5)))]
CSL = resample([(FCA, ST), tuple(_CS0)] + _arc[1:] + [tuple(APB[1] + _w)], 5.0)
S_OFF = [-11.25, -6.75, -2.25, 2.25, 6.75, 11.25]
appr_s = [offs(CSL, d) for d in S_OFF]
W2E_A = sorted([str(i) for i in range(1, 15)], key=lambda n: F_OFF[n])
for i, n in enumerate(W2E_A):
    j = min(5, int(i * 6 / 14))
    add('apex', bezt(TRK[n][1], tuple(F_DIR), appr_s[j][0], tangent(appr_s[j], 'start')), name=f'APEx south throat, track {n}', level='0', kind='throat')
j_s = from_N(appr_s[0], 4331290)[0]
pas_s = bezt(fpt('F', FN0), tuple(F_DIR), j_s, tangent(from_N(appr_s[0], 4331290), 'start'), k=0.42, n=60)
add('passing', pas_n + pas_s[1:], name='Freight passing track', level='0',
    note='the plot plan’s westmost through track (1931), end to end beside platform 7; joins the westmost APEx main north and south')

# ---------------------------------------------------------------- Ludlow: the APEx leaves the CS line over it (Ben: 4 APEx + 2 intercity, 6-8 tracks)
_K = json.load(open(S + 'ludlow/kmz_south.json'))
LW3 = [tuple(c) for c in [r for r in _K['TRIMET_Lines.kmz'] if r['name'] == 'Lebanon-Walton 3D'][0]['c']]
CV3 = [tuple(c) for c in [r for r in _K['TRIMET_Lines.kmz'] if r['name'] == 'CVG Express 3D'][0]['c']]
_LWg = LineString([c[:2] for c in LW3])
def cs_z(p):                                                       # TRIMET rail level on the CS line nearest p
    s = _LWg.project(Point(p)); acc = 0.0
    for a, b in zip(LW3[:-1], LW3[1:]):
        L = math.dist(a[:2], b[:2])
        if acc + L >= s: f = (s - acc) / max(L, 1e-9); return a[2] + f * (b[2] - a[2])
        acc += L
    return LW3[-1][2]
_kzc = [q for q in CS_KY_KMZ if q[1] < 4330300]                     # Ben (17 October): the CS line's Kentucky approach as it runs (CS Bridge KY Approach.kmz), then TRIMET
LWS = smooth(_kzc + [c[:2] for c in LW3 if c[1] < _kzc[-1][1] - 40 and c[1] > 4320000], it=4)      # the CS line south of the CS bridge, smoothed
def cs_off(p):                                                     # signed offset of p from the CS line, + east
    g = LineString(LWS); s = g.project(Point(p)); a = g.interpolate(max(0, s - 5)); b = g.interpolate(s + 5)
    t = np.array([b.x - a.x, b.y - a.y]); t /= np.linalg.norm(t); q = g.interpolate(s)
    nE = np.array([-t[1], t[0]]); nE = nE if nE[0] > 0 else -nE
    return float(np.dot(np.array(p) - np.array([q.x, q.y]), nE)), (q.x, q.y), nE
LUD_GAP = 2.25 + 6.75 + 6.75                                       # CS pair centre to APEx centre: 15.75 m (group spacing 6.75 m, 10za.6)
def cs_plus(N, d):                                                 # point d m east of the CS line at northing N
    g = LineString(LWS); best = min(LWS, key=lambda q: abs(q[1] - N)); o, q, nE = cs_off(best)
    return tuple(np.array(q) + nE * d)
kmz_at = lambda N: tuple(GP_BANK + _d * ((N - GP_BANK[1]) / _d[1]))
LUD_CTRL = [tuple(APB[1]), kmz_at(4328800)]                         # straight off the bridge (17 October)
LUD = resample(LUD_CTRL, 5.0)
KC = resample(offs(CSL, -4.5)[:-1] + LUD, 5.0)                       # APEx Kentucky centre line: approach, bridge, Ludlow
KC = smooth(thin(KC, 25.0), it=4, step=5.0)
# Ben (15 October): the APEx is tunnelled through the hills, so it is already grade-separated from the ORR/intercity tracks, which keep
# the existing CS line at grade; RER E leaves the APEx tunnel corridor and passes over it, and at one point the three are stacked:
# ORR/intercity on top, RER E, then the APEx. Profile (working values): 2.0% down from the Kentucky bank (164.0 m) into a cut-and-cover
# portal in Ludlow, under the CS line, 8 m under the valley floor at about N 4,329,000 (ground about 154 m), then 1.0% up in bored
# tunnel toward Erlanger.
_DMJ = json.load(open(S + 'topo/dem2m.json')); _DEM = np.load(S + 'topo/dem2m.npy', mmap_mode='r')
def ground(p):
    r = int((_DMJ['y1'] - p[1]) / 2); c = int((p[0] - _DMJ['x0']) / 2); v = _DEM[r, c]
    return None if v == _DMJ['nodata'] else float(v) / 10.0
Z_KB, G_DN, Z_LOW, S_UP, G_UP = 164.0, 0.020, 146.0, 1650.0, 0.010
S_LOW = (Z_KB - Z_LOW) / G_DN
def apex_kz(sk):                                                     # APEx rail by distance from the Kentucky bank
    if sk <= 0: return Z_KB
    if sk <= S_LOW: return Z_KB - G_DN * sk
    if sk <= S_UP: return Z_LOW
    return Z_LOW + G_UP * (sk - S_UP)
COVER = 7.8                                                          # rail to ground over a box: 6.8 m (5.8 m clear + 1.0 m roof) + 1.0 m fill
s_kb = LineString(KC).project(Point(APB[1]))
_KCL = LineString(KC)
S_PORT = next(sk for sk in np.arange(0, 1500, 5.0) if (ground(_KCL.interpolate(s_kb + sk).coords[0]) or 0) - apex_kz(sk) >= COVER)
_xing = _KCL.intersection(LineString(LWS))
_xp = [g for g in getattr(_xing, 'geoms', [_xing]) if g.geom_type == 'Point' and g.y < APB[1][1] - 50]
X_LUD = max(_xp, key=lambda g: g.y) if _xp else None
s_xl = _KCL.project(X_LUD); z_apx_x = apex_kz(s_xl - s_kb); z_cs_x = cs_z((X_LUD.x, X_LUD.y))
_kc_dir = np.subtract(_KCL.interpolate(s_xl + 10).coords[0], _KCL.interpolate(s_xl - 10).coords[0])
_o, _q, _nE = cs_off((X_LUD.x, X_LUD.y)); _csdir = np.array([_nE[1], -_nE[0]])
SKEW = math.degrees(math.acos(abs(float(np.dot(_kc_dir / np.linalg.norm(_kc_dir), _csdir)))))
# the three-level point: where RER E (Cincinnati Rail.kmz) crosses the APEx KMZ line beside the CS line
_RE = [LineString([q[:2] for q in r['c']]) for r in json.load(open(S + 'deckpage/context.json'))['rer'] if r['lines'] == ['E']]
_GPL = LineString([tuple(GP_BANK), tuple(GP_END)])
_cand = []
for g in _RE:
    x = g.intersection(_GPL)
    for p in getattr(x, 'geoms', [x]):
        if p.geom_type == 'Point': _cand.append((LineString(LWS).distance(p), p))
STKS = sorted([p for d_, p in _cand if d_ < 40.0], key=lambda p: -p.y)               # RER E over the APEx where the CS line passes too
STK = STKS[0]
def stack_levels(p):
    sk = math.dist((p.x, p.y), APB[1]); za = apex_kz(sk); zc = cs_z((p.x, p.y)); return sk, zc, (za + zc) / 2, za
s_stk, z_cs_stk, z_re_stk, z_apx_stk = stack_levels(STK)
_rex = []                                                            # RER E over the APEx: every RER E crossing of the KMZ line south of Ludlow
for d_, p in sorted(_cand, key=lambda t: -t[1].y):
    if p.y < X_LUD.y: _rex.append([round(p.x), round(p.y)])
LUD_INFO = dict(g_down=100 * G_DN, z_low=Z_LOW, g_up=100 * G_UP, s_up=S_UP, portal=round(S_PORT), xing=[round(X_LUD.x, 1), round(X_LUD.y, 1)], s_from_bank=round(s_xl - s_kb),
                z_apex=round(z_apx_x, 1), z_cs=round(z_cs_x, 1), under=round(z_cs_x - z_apx_x, 1), skew=round(SKEW, 1), gap=LUD_GAP,
                stack=[dict(at=[round(p.x), round(p.y)], s_from_bank=round(stack_levels(p)[0]), z_cs=round(stack_levels(p)[1], 1), z_rer_e=round(stack_levels(p)[2], 1),
                            z_apex=round(stack_levels(p)[3], 1), ground=round(ground((p.x, p.y)) or 0, 1), cs_off=round(LineString(LWS).distance(p), 1)) for p in STKS],
                rer_e_over=_rex, r_min=None)
K_OFF = [-6.75, -2.25, 2.25, 6.75]
_ip = int((s_kb + S_PORT) / 5)
for j, d in enumerate(K_OFF):
    add('apex', offs(KC[:_ip + 1], d), name=f'APEx Kentucky {j + 1} of 4', level='0, then 2.0% down from the Kentucky bank', kind='approach',
        note=f'six-track approach from the field, curve {R_APP:.0f} m between W 8th and W 6th, four-track bridge on the KMZ line; in Ludlow '
             f'{LUD_GAP:.2f} m east of the CS line (centres), {100*G_DN:.1f}% down into a tunnel {S_PORT:.0f} m from the bank')
    add('apex', offs(KC[_ip:], d), name=f'APEx Kentucky {j + 1} of 4, tunnel', level='tunnel', kind='approach', state='tunnel',
        note=f'tunnel through the hills on the KMZ line: under the CS line (ORR/intercity, at grade) at about {z_apx_x:.1f} m ({z_cs_x - z_apx_x:.1f} m below), '
             f'{Z_LOW:.0f} m under the valley at about N 4,329,000, then {100*G_UP:.1f}% up toward Erlanger; RER E passes over it')
LUD_INFO['r_min'] = round(min_radius(KC[int(s_kb / 5):], win=40.0))

# Cardinal pair: leaves the approach east south of W 8th
car_ctrl = [(712800, 4331100), (712808, 4331000), (712832, 4330890), (712882, 4330800), (712962, 4330720), (713060, 4330652),
            (713258, 4330549), (713497, 4330450), (713624, 4330422), (713776, 4330431)]
CAR = smooth(car_ctrl, it=4)
for j in (4, 5):
    co = offs(CAR, -2.25 if j == 4 else 2.25)
    top = cut_at_N(appr_s[j], 4331260); coj = from_N(co, 4330860)
    add('apex', top + bezt(top[-1], tangent(top, 'end'), coj[0], tangent(coj, 'start'), k=0.42, n=70)[1:] + coj[1:],
        name=f'Cardinal branch {j - 3} of 2 (APEx, east along the river)', level='0', kind='branch')

# ---------------------------------------------------------------- CVG Express: platform M, its own span beside the APEx bridge, with the APEx through the hills, its own line to CVG
# Ben (16 October): option A with a separate span; CVG Express Final.kmz: from CUT with the APEx across the river and through the hills to Erlanger,
# then its own line west under the RER B/E line to the split east of CVG, then the 'Today' route: deep-bored under 18L/36R, north-north-west through
# T3, T2 and T4 (under the shallow RER), west on the 1969 line through T1B and T1A, and north to the yard. Five stations (option 1), GoA3, platform
# screen doors. The 1969 line ('Original' in the KMZ) ran west across the north end of 18L to T1A; the 18L extension north cut it and the new
# Terminals 2 and 3 took the line south in a bore.
TCS = smooth([tuple(p[:2]) for p in TB['cs']], it=4)
MERGE = tuple(SPANS['CS'][0]); BANK_N = float(SPANS['CS'][0][1])          # the intercity pair reaches the CS bridge at its span (Bridge Spans.kmz)
def tcs_z(p):                                                       # TRIMET CS viaduct rail level nearest p
    pts = TB['cs']; g = LineString([q[:2] for q in pts]); s = g.project(Point(p)); acc = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        L = math.dist(a[:2], b[:2])
        if acc + L >= s: f = (s - acc) / max(L, 1e-9); return a[2] + f * (b[2] - a[2])
        acc += L
    return pts[-1][2]
z_merge = tcs_z(MERGE)                                              # the intercity pair's target where it meets the TRIMET CS viaduct
_KF = json.load(open(S + 'cvgkmz/cvg_final.json'))                  # CVG Express Final.kmz (pieces 1-3 are the same as in CVG Express New.kmz)
_P2 = [tuple(c) for c in _KF['CVG Express 2']['c']][::-1]; _P3 = [tuple(c) for c in _KF['CVG Express 3']['c']]; _P4 = [tuple(c) for c in _KF['CVG Express 4']['c']]
_TD = [tuple(c) for c in _KF['CVG Express 5 - Today']['c']]; _OG = [tuple(c) for c in _KF['CVG Express 5 - Original']['c']]
_STP = {k: tuple(_KF['Terminal ' + k]['c'][0]) for k in ('3', '2', '4', '1B', '1A')}
CV3_ = [tuple(c) for c in [r for r in json.load(open(S + 'ludlow/kmz_south.json'))['TRIMET_Lines.kmz'] if r['name'] == 'CVG Express 3D'][0]['c']]
def z_on3(L3, p):
    g = LineString([c[:2] for c in L3]); s = g.project(Point(p)); acc = 0.0
    for a, b in zip(L3[:-1], L3[1:]):
        Lg = math.dist(a[:2], b[:2])
        if acc + Lg >= s: f = (s - acc) / max(Lg, 1e-9); return a[2] + f * (b[2] - a[2])
        acc += Lg
    return L3[-1][2]
_AK = [r for r in json.load(open(S + 'ludlow/kmz_south.json'))['APEx Routes.kmz'] if r['kind'] == 'line' and r['name'] == 'Cincinnati-Lexington 1' and r['n'] == 9][0]['c']
_AK = [tuple(c[:2]) for c in _AK]; _AK = _AK if _AK[0][1] > _AK[-1][1] else _AK[::-1]      # the APEx KMZ line, Ludlow -> south past Erlanger
CORR = resample(KC + [q for q in offs(_AK, APEX_SHIFT) if q[1] < KC[-1][1] - 30], 5.0)   # the KMZ line moved as the bridge was (APEX_SHIFT)  # the APEx Kentucky centre line: approach, bridge, Ludlow, the KMZ line through the hills
_CORRL = LineString(CORR); s_kb_c = _CORRL.project(Point(APB[1]))
_cvx = SPANS['CVX']; CVG_OFF = round(float(np.dot(np.array(_cvx[0]) - (GP_BANK - _n * APEX_SHIFT), _n)), 2)   # the CVG span's line east of the APEx span (Bridge Spans.kmz), about 25 m
N_JOIN = 4331300.0
N_DIV0 = 4326050.0                                                  # the CVG leaves the side of the APEx here and crosses over it to the west
CVG_TUN = 15.75                                                     # Ben (17 October): beside the APEx off the bridge, 15.75 m (APEx outer track 6.75, CVG inner 13.5: group spacing 6.75)
L_TR = 250.0                                                        # from the span's 24.75 m to 15.75 m in 250 m past the Kentucky bank
_s_kbc = _CORRL.project(Point(APB[1]))
def cvg_d(s):
    if s <= _s_kbc: return CVG_OFF
    t = (s - _s_kbc) / L_TR
    return CVG_TUN if t >= 1 else CVG_TUN + (CVG_OFF - CVG_TUN) * 0.5 * (1 + math.cos(math.pi * t))
def var_offs(c, dfun):                                             # + east (left of southbound travel), distance by chainage
    out, acc = [], 0.0
    for i, q in enumerate(c):
        if i: acc += math.dist(c[i - 1], q)
        a, b2 = c[max(0, i - 1)], c[min(len(c) - 1, i + 1)]; t = np.subtract(b2, a); t = t / np.linalg.norm(t)
        out.append(tuple(np.array(q) + np.array([-t[1], t[0]]) * dfun(acc)))
    return out
_par = from_N(var_offs(CORR, cvg_d), N_JOIN)
_par = cut_at_N(_par, N_DIV0)
_d3 = np.subtract(_P3[5], _P3[4]); _d3 = _d3 / np.linalg.norm(_d3)
_P2pt = tuple(np.array(_P3[4]) + _d3 * 250.0)                        # on the KMZ line west of the APEx, 250 m past where it leaves it
_xo = bezt(tuple(_par[-1]), tuple(tangent(_par, 'end')), _P2pt, tuple(_d3), k=0.42, n=120)
_tail = [_P2pt] + [_P3[5]] + _P4[1:]
_tail = smooth(thin(_tail, 25.0), it=5, step=5.0)
_CA = resample(_par + _xo[1:] + _tail[1:], 5.0)
_CA = smooth(thin(_CA, 12.0), it=3, step=5.0)                       # CUT to the split (end of KMZ piece 4)
# ---- the Today route: Ben's straights, joined by circular curves (radii from his drawing, except where a platform would be on the curve)
def _fit(pts):
    P = np.array(pts, float); c = P.mean(0); u = np.linalg.svd(P - c)[2][0]; return c, u / np.linalg.norm(u)
def _meet(c1, u1, c2, u2):
    t = np.linalg.solve(np.array([u1, -u2]).T, np.subtract(c2, c1)); return np.array(c1) + u1 * t[0]
def _turn(a, b, c):
    u = (a - b) / np.linalg.norm(a - b); w = (c - b) / np.linalg.norm(c - b); return math.pi - math.acos(np.clip(np.dot(u, w), -1, 1))
def _on(c, u, p): return np.array(c) + u * np.dot(np.subtract(p, c), u)
_e0 = np.array(_CA[-1]); _u1 = np.array(tangent(_CA, 'end'))
_c2, _u2 = _fit([_TD[5], _TD[6]])                                    # the long straight under 18L/36R
_c3, _u3 = _fit([_TD[11], _TD[12], _STP['3'], _STP['2'], _STP['4']])  # north-north-west through T3, T2 and T4
_c4, _u4 = _fit([_TD[17], _TD[18], _STP['1B'], _STP['1A']])          # west on the 1969 line through T1B and T1A
_c5, _u5 = _fit([_TD[-2], _TD[-1]])                                  # north into the yard
_END = np.array(_TD[-1])
_V = [_meet(_e0, _u1, _c2, _u2), _meet(_c2, _u2, _c3, _u3), _meet(_c3, _u3, _c4, _u4), _meet(_c4, _u4, _c5, _u5)]
CVX_ST = {k: tuple(_on(_c3, _u3, _STP[k]) if k in ('3', '2', '4') else _on(_c4, _u4, _STP[k])) for k in ('3', '2', '4', '1B', '1A')}
PLAT_CVX = 200.0                                                    # platform length (Ben, 16 October): four 50 m units (DB 610 based) or three 67 m (DB 420 lengths)
_seq = [_e0] + _V + [_END]
_ben_T = [min(math.dist(_V[0], _e0), math.dist(_V[0], _TD[5])), (math.dist(_V[1], _TD[6]) + math.dist(_V[1], _TD[11])) / 2,
          (math.dist(_V[2], _TD[12]) + math.dist(_V[2], _TD[17])) / 2, (math.dist(_V[3], _TD[18]) + math.dist(_V[3], _TD[-2])) / 2]
_lim_T = [math.dist(_V[0], _e0) - 20, 1e9, 1e9, math.dist(_V[3], _END) - 20]   # Ben's radii; the platforms move along the straights instead (v42)
CVX_R = []
_today = [tuple(_e0)]
CVX_V = [tuple(_e0)]; CVX_K = {}                                     # the airside line for the page's station editor: vertices, and a quadratic control per curved piece
for i in range(1, len(_seq) - 1):
    a, b, c = _seq[i - 1], _seq[i], _seq[i + 1]; th = _turn(a, b, c); T_ = min(_ben_T[i - 1], _lim_T[i - 1]); R_ = T_ / math.tan(th / 2)
    u = (a - b) / np.linalg.norm(a - b); w = (c - b) / np.linalg.norm(c - b); p1, p2 = b + u * T_, b + w * T_
    CVX_R.append(dict(at=[round(b[0]), round(b[1])], turn=round(math.degrees(th), 1), r=round(R_), r_ben=round(_ben_T[i - 1] / math.tan(th / 2)), limited=bool(_lim_T[i - 1] < _ben_T[i - 1]),
                      p1=[round(p1[0], 1), round(p1[1], 1)], p2=[round(p2[0], 1), round(p2[1], 1)]))
    bis = (u + w) / np.linalg.norm(u + w); cen = b + bis * (R_ / math.sin((math.pi - th) / 2))
    a1, a2 = math.atan2(*(p1 - cen)[::-1]), math.atan2(*(p2 - cen)[::-1]); dd = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
    nseg = max(8, int(abs(dd) * R_ / 5))
    _today += [tuple(p1)] + [tuple(cen + R_ * np.array([math.cos(a1 + dd * k / nseg), math.sin(a1 + dd * k / nseg)])) for k in range(1, nseg)] + [tuple(p2)]
    CVX_V.append(tuple(p1)); _m_ = max(1, math.ceil(abs(math.degrees(dd)) / 10.0)); _ph = dd / _m_
    for j in range(1, _m_ + 1):
        _am = a1 + _ph * (j - 0.5); CVX_K[str(len(CVX_V) - 1)] = tuple(cen + (R_ / math.cos(_ph / 2)) * np.array([math.cos(_am), math.sin(_am)]))
        CVX_V.append(tuple(cen + R_ * np.array([math.cos(a1 + _ph * j), math.sin(a1 + _ph * j)])))
_today.append(tuple(_END)); CVX_V.append(tuple(_END))
_today = resample(_today, 5.0)
CVGC = _CA + _today[1:]
for n, d in (('15', -2.25), ('16', 2.25)):
    tgt = offs(CVGC, d)
    add('apex', bezt(TRK[n][1], tuple(F_DIR), tgt[0], tangent(tgt, 'start'), k=0.42, n=60), name=f'CVG Express south throat, track {n}', level='0', kind='throat')
_CVL = LineString(CVGC)
s_cv_bank = _CVL.project(Point(tuple(np.array(APB[1]) + _n * CVG_OFF)))
s_split = _CVL.project(Point(tuple(_e0)))
CVX_S = {k: _CVL.project(Point(CVX_ST[k])) for k in CVX_ST}
# generated platform centres: on the stop point unless that would put a platform end within 15 m of a curve; then along the straight just enough
_str = {'3': (CVX_R[1]['p2'], CVX_R[2]['p1']), '2': (CVX_R[1]['p2'], CVX_R[2]['p1']), '4': (CVX_R[1]['p2'], CVX_R[2]['p1']),
        '1B': (CVX_R[2]['p2'], CVX_R[3]['p1']), '1A': (CVX_R[2]['p2'], CVX_R[3]['p1'])}
CVX_C = {}
for k, (qa, qb) in _str.items():
    sa, sb = _CVL.project(Point(qa)), _CVL.project(Point(qb))
    CVX_C[k] = min(max(CVX_S[k], sa + PLAT_CVX / 2 + 15), sb - PLAT_CVX / 2 - 15)
def apex_zN(N):                                                     # APEx rail on the approach (CUT to the Ohio bank) by northing
    if N >= FN0: return APEX(N)                                     # 17 October (Ben): one straight grade from the platforms' south end to the bridge, no dip at W 8th
    _top = CSL[0][1]                                                # the approach line starts south of the field; it runs straight north from there
    _sN = lambda n: (s_at_N(CSL, n) if n <= _top else None) if n <= _top else -(n - _top)
    s0_ = _sN(FN0); sbk = s_at_N(CSL, float(APB[0][1]))
    s_ = -(N - _top) if N > _top else LineString(CSL).project(Point(min(CSL, key=lambda q: abs(q[1] - N))))
    return min(164.0, APEX(FN0) + (164.0 - APEX(FN0)) / (sbk - s0_) * (s_ - s0_))
def apex_at(p):                                                     # APEx rail level nearest p (by corridor chainage)
    sc = _CORRL.project(Point(p))
    return apex_zN(p[1]) if sc < s_kb_c else apex_kz(sc - s_kb_c)
_DMJ2 = json.load(open(S + 'topo/dem2m.json')); _DEM2 = np.load(S + 'topo/dem2m.npy', mmap_mode='r')
def ground2(p):
    r = int((_DMJ2['y1'] - p[1]) / 2); c = int((p[0] - _DMJ2['x0']) / 2)
    if not (0 <= r < _DEM2.shape[0] and 0 <= c < _DEM2.shape[1]): return None
    v = _DEM2[r, c]; return None if v == _DMJ2['nodata'] else float(v) / 10.0
# the airport level: deep-bored under the shallow RER (Ben). Working values: RER rail about 12 m below the apron where it crosses at T4,
# the CVG Express 15 m under that (as for bore over bore elsewhere on the line).
RER_DOWN, CVX_UNDER = 12.0, 15.0
Z_RER_T4 = ground2(CVX_ST['4']) - RER_DOWN
Z_DEEP = math.floor(2 * (Z_RER_T4 - CVX_UNDER)) / 2
# the climb from the Ohio: as before (set by the 15 m over the APEx before Erlanger), now to the airport level instead of the TRIMET line at J
_J = (707194.0, 4323703.0); s_J = _CVL.project(Point(_J)); z_J = z_on3(CV3_, _J)
s_X0 = _CVL.project(Point(_par[-1]))
# the yard (Final.kmz), graded level at its south end; the line climbs to it from T1A
_YD = [tuple(c) for c in _KF['CVG Express Yard']['c']]; _SHOP = [tuple(c) for c in _KF['Maintenance Building']['c']]
s_yd0 = _CVL.project(Point(min(_YD, key=lambda q: q[1])))
Z_YD = round(ground2(_CVL.interpolate(s_yd0).coords[0]) - 2.0, 1)
s_up0 = CVX_C['1A'] + PLAT_CVX / 2 + 15
G_YD = (Z_YD - Z_DEEP) / (s_yd0 - s_up0)
# the creek valley east of the airport (between the split and 18L/36R): the bore stays under it, 12 m from rail to the valley floor (working value),
# level from where the climb from the Ohio reaches that level, then up under the airfield to the airport level 50 m before T3
VALLEY_UNDER = 12.0
_ssv = np.arange(s_split, CVX_S['3'], 10.0); _gv = np.array([ground2(_CVL.interpolate(s).coords[0]) for s in _ssv])
s_vmin = float(_ssv[int(np.argmin(_gv))]); G_VMIN = float(_gv.min())
Z_HOLD = math.floor(2 * (G_VMIN - VALLEY_UNDER)) / 2
s_r0 = s_vmin + 300.0; s_r1 = CVX_C['3'] - PLAT_CVX / 2 - 50.0
G_RISE = (Z_DEEP - Z_HOLD) / (s_r1 - s_r0)
def cvg_profile(s_c0):
    z0 = apex_at(_CVL.interpolate(s_c0).coords[0]); g = (z_J - z0) / (s_J - s_c0)
    def z(s):
        q = _CVL.interpolate(s).coords[0]
        if s <= s_cv_bank: return apex_zN(q[1])
        if s <= s_c0: return apex_at(q)
        if s <= s_r0: return min(Z_HOLD, z0 + g * (s - s_c0))
        if s <= s_r1: return Z_HOLD + G_RISE * (s - s_r0)
        if s <= s_up0: return Z_DEEP
        if s <= s_yd0: return Z_DEEP + G_YD * (s - s_up0)
        return Z_YD
    return g, z
# choose where the CVG starts to climb away from the APEx: as late as possible with the climb at 2.5% or less and 15 m over the APEx where it crosses (working value for bore over bore)
_best = None
for s_c0 in np.arange(s_cv_bank + 1000, s_X0 + 1, 50.0):
    g, zf = cvg_profile(s_c0)
    if g > 0.025: continue
    clr = min((zf(s) - apex_at(_CVL.interpolate(s).coords[0]), s) for s in np.arange(s_X0, s_X0 + 1600, 5.0) if _CORRL.distance(_CVL.interpolate(s)) < 6.75 + 2.25 + 2.0)
    if clr[0] >= 15.0: _best = (s_c0, g, clr)
S_C0, G_CV, CLR_X = _best
_, cvz = cvg_profile(S_C0)
s_hold = S_C0 + (Z_HOLD - apex_at(_CVL.interpolate(S_C0).coords[0])) / G_CV
# the CS line crossing near Erlanger, ground cover, portals
_csx = _CVL.intersection(LineString(LWS))
_csx = [p for p in getattr(_csx, 'geoms', [_csx]) if p.geom_type == 'Point' and p.y < 4325000]
_csxi = [dict(at=[round(p.x), round(p.y)], z_cvg=round(cvz(_CVL.project(p)), 1), z_cs=round(cs_z((p.x, p.y)), 1)) for p in _csx]
SS = np.arange(s_cv_bank, _CVL.length, 10.0)
_state = []
for s in SS:
    gz = ground2(_CVL.interpolate(s).coords[0]); z = cvz(s)
    _state.append('tunnel' if (gz is not None and gz - z >= COVER) else 'open')
_runs = []                                                          # [(state, s0, s1)]
for s, st in zip(SS, _state):
    if _runs and _runs[-1][0] == st: _runs[-1][2] = s
    else: _runs.append([st, s, s])
_runs = [r for r in _runs if r[2] - r[1] >= 60 or r[0] == 'open']
_m = []                                                             # past the split: short open blips (ditches in the DEM) between tunnel runs stay tunnel
for r in _runs:
    if _m and r[0] == 'open' and r[1] > s_split and r[2] - r[1] < 150 and r is not _runs[-1]: r = ['tunnel', r[1], r[2]]
    if _m and _m[-1][0] == r[0]: _m[-1][2] = r[2]
    else: _m.append(list(r))
_runs = _m
M_TO_C0 = FN0 - N_JOIN                                             # south end of platform M to the start of the line (N 4,331,300)
def _run_t(d, a=0.8, vmax=22.2):                                    # rough stop-to-stop time: accelerate and brake at a, capped at vmax (80 km/h)
    return 2 * math.sqrt(d / a) if d <= vmax ** 2 / a else 2 * vmax / a + (d - vmax ** 2 / a) / vmax
_ord = ['3', '2', '4', '1B', '1A']
_gaps = [CVX_S[_ord[i + 1]] - CVX_S[_ord[i]] for i in range(4)]
CVG_INFO = dict(z_m=round(APEX(FN0), 1), offset=CVG_OFF, offset_ky=CVG_TUN, apex_shift=float(APEX_SHIFT), span_gap=round(CVG_OFF - 2.25 - 4.75 - (6.75 + 4.75), 2),
                climb_from=round(S_C0 - s_cv_bank), g=round(100 * G_CV, 2), over_apex=dict(clear=round(CLR_X[0], 1), at=[round(_CVL.interpolate(CLR_X[1]).x), round(_CVL.interpolate(CLR_X[1]).y)]),
                cs_crossing=_csxi, end=[round(CVGC[-1][0]), round(CVGC[-1][1])], z_end=round(cvz(_CVL.length), 1),
                length_km=round((_CVL.length - s_cv_bank) / 1000, 1), runs=[(r[0], round(r[1] - s_cv_bank), round(r[2] - s_cv_bank)) for r in _runs],
                r_min_throat=round(min(min_radius(f['geometry']['coordinates'], win=20.0) for f in F if f['properties'].get('name', '').startswith('CVG Express south throat'))),
                r_min=round(min_radius(CVGC, win=30.0)),
                split=[round(_e0[0]), round(_e0[1])], z_deep=Z_DEEP, z_rer_t4=round(Z_RER_T4, 1), rer_down=RER_DOWN, under_rer=CVX_UNDER,
                hold=dict(z=Z_HOLD, from_bank=round(s_hold - s_cv_bank), valley=dict(ground=round(G_VMIN, 1), at=[round(_CVL.interpolate(s_vmin).x), round(_CVL.interpolate(s_vmin).y)], under=VALLEY_UNDER)),
                rise=dict(g=round(100 * G_RISE, 2), from_bank=round(s_r0 - s_cv_bank), to_bank=round(s_r1 - s_cv_bank)), curves=CVX_R, plat=PLAT_CVX,
                stations=[dict(name='T' + k, at=[round(CVX_ST[k][0]), round(CVX_ST[k][1])], z=Z_DEEP, ground=round(ground2(CVX_ST[k]), 1),
                               km_from_M=round((CVX_S[k] + M_TO_C0) / 1000, 2), s=round(CVX_S[k]), o0=round(CVX_C[k] - CVX_S[k], 1)) for k in _ord],
                gaps=[round(d) for d in _gaps], first_to_last_min=round((sum(_run_t(d) for d in _gaps) + 30 * 4) / 60, 1),
                yard=dict(z=Z_YD, g_up=round(100 * G_YD, 2), from_T1A_m=round(s_yd0 - CVX_S['1A'])))
# the Cardinal pair crosses the CVG pair (at grade, south of W 8th)
_car = [LineString(f['geometry']['coordinates']) for f in F if f['properties'].get('name', '').startswith('Cardinal branch')]
_xc = []
for a in _car:
    for d in (-2.25, 2.25):
        x = a.intersection(LineString(offs(CVGC, d))); _xc += [p for p in getattr(x, 'geoms', [x]) if p.geom_type == 'Point' and p.y > 4330800]
_xcN = sorted(p.y for p in _xc)
CVG_INFO.update(cardinal_x=len(_xc), cardinal_N=[round(_xcN[-1]), round(_xcN[0])] if _xcN else None)
# draw: tunnel runs dashed
_cuts = [(r[0], r[1], r[2]) for r in _runs]
from shapely.ops import substring
def piece(c, s0, s1):
    g = LineString(c); return list(substring(g, max(0, s0), min(g.length, s1)).coords)
for d, nm in ((-2.25, 'west'), (2.25, 'east')):
    c = offs(CVGC, d)
    add('apex', offs(piece(CVGC, 0, s_cv_bank), d), name=f'CVG Express ({nm} track): platform M to the Ohio, on its own span', level='0, span', kind='cvg',
        note='east of the APEx approach from platform M (at grade across the Cardinal pair south of W 8th), then its own double-track span beside the APEx bridge')
    for st, s0, s1 in _cuts:
        if s0 >= s_split: continue
        s1 = min(s1, s_split - 10)                                       # the airside line from the split is drawn by the page's station editor (tracks.json 'cvx')
        add('apex', offs(piece(CVGC, s0, s1 + 10), d), name=f'CVG Express ({nm} track), ' + ('tunnel' if st == 'tunnel' else 'open'), level=st, kind='cvg', **({'state': 'tunnel'} if st == 'tunnel' else {}),
            note=f'CVG Express Final.kmz: beside the APEx (own bores, {CVG_TUN:.2f} m east of its centre off the bridge) through Ludlow and the hills, {100*G_CV:.2f}% up from {S_C0 - s_cv_bank:,.0f} m past the bank, '
                 f'over the APEx ({CLR_X[0]:.1f} m) before Erlanger, level at {Z_HOLD:.1f} m under the CS line, the RER B/E line (to the split) and the creek valley, then {100*G_RISE:.2f}% up to {Z_DEEP:.1f} m before T3; '
                 f'stations T3, T2, T4, T1B, T1A; up {100*G_YD:.1f}% to the yard')
add('bridge', [tuple(np.array(q) + _n * APEX_SHIFT) for q in (_cvx[0], _cvx[-1])], name='CVG Express span (double track), beside the APEx bridge',
    rail_m='about 164', note=f'its own structure, {CVG_INFO["span_gap"]:.1f} m clear of the APEx bridge (drawing values: 4.75 m from outer track to deck edge)')
# the airside line from the split to the yard, for the page's station editor (as the RER and Metro): line, stations, generated platforms and tracks
_NAMES = {'3': 'Terminal 3', '2': 'Terminal 2', '4': 'Terminal 4', '1B': 'Terminal 1B', '1A': 'Terminal 1A'}
def _offp(c, d):                                                    # offset a piece; the longest part if shapely splits it
    g = LineString(c).offset_curve(d, quad_segs=16, join_style='round')
    if g.geom_type == 'MultiLineString': g = max(g.geoms, key=lambda q: q.length)
    return [list(map(lambda v: round(v, 1), q)) for q in g.coords]
_plats, _sts, _trk = [], [], []
for k in _ord:
    s0, s1 = CVX_C[k] - PLAT_CVX / 2, CVX_C[k] + PLAT_CVX / 2
    _a, _b = np.array(_CVL.interpolate(s0).coords[0]), np.array(_CVL.interpolate(s1).coords[0]); _u = (_b - _a) / np.linalg.norm(_b - _a); _nl = np.array([-_u[1], _u[0]])
    for sg in (1, -1):                                                 # side platforms, straight chords: edge 1.6 m from the track, 6 m wide (drawing values)
        i0, i1 = sg * (2.25 + 1.6), sg * (2.25 + 7.6)
        ring = [_a + _nl * i0, _b + _nl * i0, _b + _nl * i1, _a + _nl * i1, _a + _nl * i0]
        _plats.append(dict(sys='cvx', line='CVG Express', pid='CVX', st=_NAMES[k], id=f'P-CVX-{k}-{"L" if sg > 0 else "R"}', c=[[round(q[0], 1), round(q[1], 1)] for q in ring]))
    _sts.append(dict(name=_NAMES[k], p=[round(CVX_ST[k][0], 1), round(CVX_ST[k][1], 1)], z=Z_DEEP, ground=round(ground2(CVX_ST[k]), 1), depth=round(ground2(CVX_ST[k]) - Z_DEEP, 1),
                     km=round((CVX_S[k] + M_TO_C0) / 1000, 2), o0=round(CVX_C[k] - CVX_S[k], 1)))
for st_, r0_, r1_ in _cuts:
    if r1_ <= s_split: continue
    _pc = piece(CVGC, max(r0_, s_split), r1_ + 10)
    for d in (2.25, -2.25): _trk.append(dict(sys='cvx', line='CVG Express', pid='CVX', open=(st_ == 'open'), c=_offp(_pc, d)))
CVX_DATA = dict(id='CVX', name='CVG Express (airside)', platform_m=PLAT_CVX, island_m=10.0, side_m=6.0, h0=2.25, edge=1.6,
                v=[[round(q[0], 1), round(q[1], 1)] for q in CVX_V], k={i: [round(q[0], 1), round(q[1], 1)] for i, q in CVX_K.items()},
                stations=_sts, plats=_plats, tracks=_trk,
                note='From the split east of CVG (E %.0f N %.0f) to the yard; deep-bored at %.1f m through the stations; Ben\'s stop points, curves at his radii' % (_e0[0], _e0[1], Z_DEEP))
addpoly('cvg_yard', _YD, name='CVG Express yard', note=f'Final.kmz; graded at about {Z_YD:.0f} m at its south end; stabling tracks not drawn')
addpoly('cvg_shop', _SHOP, name='CVG Express maintenance building', note='Final.kmz')
# the 1969 line west of where the RER leaves it: across the north end of 18L (cut when the runway was extended north) to the junction east of T1B
_OGL = LineString(_OG)
_rerL = [LineString([q[:2] for q in r['c']]) for r in json.load(open(S + 'deckpage/context.json'))['rer'] if LineString([q[:2] for q in r['c']]).distance(Point(tuple(_e0))) < 15]
_og_s0 = next((s for s in np.arange(0, _OGL.length, 5.0) if all(g.distance(_OGL.interpolate(s)) > 10.0 for g in _rerL)), 0.0)
_jn_s = _OGL.project(Point(CVX_R[2]['p2']))                        # where the bore from the south joins the 1969 line (end of the curve east of T1B)
add('apex', list(substring(_OGL, _og_s0, _jn_s).coords), name='CVG Express, 1969 line (former)', kind='cvg_former', state='former', level='former',
    note='CVG Express Final.kmz, Original: west across the north end of 18L to T1A; cut when 18L was extended north, and replaced by the bore from the south through the new Terminals 2 and 3; the RER uses its line from the split to about E 705,000')
_cut18 = _OGL.intersection(LineString([(703697.9, 4322563.5), (703620.0, 4326400.0)]))
if not _cut18.is_empty: addpt('marker', (_cut18.x, _cut18.y), kind='level', name='1969 line cut by 18L', label='1969 CVG Express line, cut when 18L was extended north', anchor='left')
CVG_INFO.update(former=dict(s0=round(_og_s0), s1=round(_jn_s), start=[round(_OGL.interpolate(_og_s0).x), round(_OGL.interpolate(_og_s0).y)]))
if _xc: addpt('marker', (np.mean([p.x for p in _xc]), np.mean([p.y for p in _xc])), kind='level', name='Cardinal crosses the CVG Express', label='Cardinal crosses the CVG Express at grade', anchor='left')
_qx = _CVL.interpolate(CLR_X[1])
addpt('marker', (_qx.x, _qx.y), kind='level', name='CVG Express over the APEx', label=f'CVG Express {cvz(CLR_X[1]):.0f} m over the APEx tunnel ({CLR_X[0]:.0f} m clear)', anchor='left')
for x in _csxi: addpt('marker', tuple(x['at']), kind='level', name='CVG Express under the CS line', label=f'CVG Express {x["z_cvg"]:.0f} m, under the CS line ({x["z_cs"]:.0f} m)', anchor='left')
addpt('marker', _CVL.interpolate(s_vmin).coords[0], kind='level', name='CVG Express under the creek valley', label=f'CVG Express {Z_HOLD:.1f} m, under the creek valley ({G_VMIN:.0f} m)', anchor='left')
addpt('marker', tuple(_e0), kind='level', name='CVG Express leaves the RER B/E line', label=f'CVG Express leaves the RER B/E line (its own bores below it from the CS line)', anchor='left')
_q4 = _CVL.interpolate(CVX_S['4'] - 130).coords[0]
addpt('marker', _q4, kind='level', name='CVG Express under the RER', label=f'T4 platforms {Z_DEEP:.1f} m, under the shallow RER (about {Z_RER_T4:.0f} m, working value)')
_port = next((r for r in _runs if r[0] == 'open' and r[1] > CVX_S['1A']), None)
if _port: addpt('marker', _CVL.interpolate(_port[1]).coords[0], kind='portal', name='CVG Express portal', label=f'CVG Express portal, {cvz(_port[1]):.1f} m ({100*G_YD:.1f}% up to the yard)', anchor='left')
CVG_INFO.update(portal=(round(_port[1] - CVX_S['1A']) if _port else None))
add('bridge', [tuple(APB[0]), tuple(APB[1])], name='APEx bridge (four tracks, General CUT Path of APEx.kmz; span ends from Bridge Spans.kmz)', rail_m='about 164',
    note=f'on the KMZ line, bearing {math.degrees(math.atan2(_d[0], _d[1])) % 360:.1f} degrees; {APB_OFF:.0f} m east of the CS bridge at the Ohio bank, {APB_OFF_S:.0f} m at the Kentucky bank; approach curve {R_APP:.0f} m radius between W 8th and W 6th')
s_b8 = s_at_N(CSL, STREETS['W 8th']); s_bb = s_at_N(CSL, float(APB[0][1]))
s_f0 = -(FN0 - CSL[0][1]) if FN0 > CSL[0][1] else s_at_N(CSL, FN0); G_APB = (164.0 - APEX(FN0)) / (s_bb - s_f0)
addpt('marker', tuple(APB[0] + _n * 14), kind='level', name='APEx bridge', label=f'APEx bridge, about 164 m ({100*G_APB:.2f}% up from the platforms)')
addpt('marker', (X_LUD.x, X_LUD.y), kind='level', name='APEx under the CS line', label=f'APEx tunnel {z_apx_x:.1f} m, {z_cs_x - z_apx_x:.1f} m under the CS line (ORR/intercity)', anchor='left')
addpt('marker', tuple(_KCL.interpolate(s_kb + S_PORT).coords[0]), kind='portal', name='APEx tunnel portal', label=f'APEx tunnel portal, {apex_kz(S_PORT):.1f} m', anchor='left')
for _P in STKS:
    _s, _zc, _zr, _za = stack_levels(_P)
    addpt('marker', (_P.x, _P.y), kind='level', name='Three levels', label=f'Three levels: ORR/intercity {_zc:.1f} m, RER E about {_zr:.0f} m, APEx {_za:.1f} m', anchor='left')
for _p in _rex:
    if min(math.dist(_p, (q.x, q.y)) for q in STKS) > 50: addpt('marker', tuple(_p), kind='level', name='RER E over the APEx tunnel', label='RER E over the APEx tunnel', anchor='left')
addpt('marker', tuple(np.array(APB[1]) + _n * 30), kind='level', name='Ludlow: APEx up from the bank', label=f'Kentucky bank: APEx 164.0 m, {100*G_DN:.1f}% down, east of the CS line', anchor='left')

# ---------------------------------------------------------------- lower level (-2), centred under the field
EH_N, EH_S = FCN + 152.5, FCN - 152.5                 # E-H 305 m, centred
AD_N, AD_S = EH_N, EH_S                               # Ben: all eight lower platforms the longer 305 m
# Ben (15 October): the lower platforms centred under the APEx platforms (platform 7's west edge to platform M's east edge)
PF_C = (fpt(F_OFF['14'] + F_EDGE, FCN)[0] + fpt(F_OFF['16'] - F_EDGE, FCN)[0]) / 2
LX0 = round(PF_C - 40.0, 2)
bx = [LX0 + 20 * (i // 2) + (2.25 if i % 2 == 0 else 17.75) for i in range(8)]
LET = 'ABCDEFGH'
for u in range(4):
    x0 = LX0 + 20 * u; n_, s_ = (AD_N, AD_S) if u < 2 else (EH_N, EH_S)
    addpoly('lower_plat', [(x0 + 4.5, s_), (x0 + 15.5, s_), (x0 + 15.5, n_), (x0 + 4.5, n_), (x0 + 4.5, s_)],
            name=f'Lower platform {LET[2*u]} / {LET[2*u+1]}', level='-2', rail=LOWER, length_m=round(n_ - s_, 1), label=f'{LET[2*u]}{LET[2*u+1]}')
for i, x in enumerate(bx):
    n_ = AD_N if i < 4 else EH_N
    add('lower', [(x, n_), (x, EH_S)], name=f'Lower track {LET[i]}', level='-2', state='under', rail=LOWER, kind='platform')
# north: the lower pairs stay under the deck on the trunk flanks from the deck's north end; 150 m ladder into the box
LAD_N = 150.0
L_OFF = {'W': [-22.5, -18.0], 'E': [18.0, 22.5]}
# The lower pairs ride the viaduct with the APEx and dive between Bank (over) and Findlay (under), both kept
# (Ben): Bank is lowered and Findlay raised END_REGRADE m to ease the ramp. Streets in between are re-graded where
# 3 m or less does it, otherwise they end at the dive; Poplar, Sherman and Liberty pass over the tunnel.
DK = json.load(open(S + 'deckpage/deck.json'))
STR_G = {}
for f in DK['features']:     # 2026-10-14: a name can now have several pieces (west-side stubs); keep the one across the trunk
    if f['properties']['layer'] != 'street': continue
    g_ = LineString(f['geometry']['coordinates']); nm_ = f['properties']['name']
    hit_ = g_.intersects(LineString([(712700, 4332000), (712800, 4332000), (712800, 4333200), (712700, 4333200), (712700, 4332000)]).buffer(60))
    if nm_ not in STR_G or (hit_ and g_.length > STR_G[nm_][0].length): STR_G[nm_] = (g_, f['properties']['width_m'])
for _nm, _c in DK.get('dive_cut', {}).items():      # streets cut at the dive: their line before the cut, for the levels
    STR_G[_nm] = (LineString(_c), STR_G[_nm][1])
def street_N(name, x):
    g, w = STR_G[name]; hit = g.intersection(LineString([(x, 4330000), (x, 4336000)]))
    return (hit.y if hit.geom_type == 'Point' else None), w
XW = [p for p in offs(CN, -22.5) if abs(p[1] - 4332700) < 6][0][0]
XE = [p for p in offs(CN, 22.5) if abs(p[1] - 4332700) < 6][0][0]
END_REGRADE = 2.0
nB, wB = street_N('Bank', XW); nL, wL = street_N('Findlay', XW)
DIVE_N0 = nB - wB / 2                                          # south edge of Bank
PORTAL_N = nL + wL / 2                                         # north edge of Findlay
Z_DIVE0 = APEX(nB) - END_REGRADE; Z_PORT = DECK(nL) - UNDER + END_REGRADE
DIVE_OPTS = {h: round(100 * ((APEX(nB) - h) - (DECK(nL) - UNDER + h)) / (DIVE_N0 - PORTAL_N), 2) for h in (0, 1, 1.5, 2, 2.5, 3)}
MID_STREETS = ['Dayton', 'Exeter', 'York']
dive_info = {}
for side, ds in L_OFF.items():
    for k, d in enumerate(ds):
        c = offs(CN, d) if side == 'W' else G27.nt_line(G27.orr_e(k))
        v = cut_at_N(c, DIVE_N0); rest = from_N(c, DIVE_N0)
        r = cut_at_N(rest, PORTAL_N); u = from_N(rest, PORTAL_N)
        Lr = DIVE_N0 - PORTAL_N                                 # straight trunk: along-track = northing difference
        dive_info = dict(g_dive=(Z_DIVE0 - Z_PORT) / Lr, L_dive=Lr)
        add('lower', v, name=f'Lower-level pair {side}, track {k+1}, on the viaduct', level='0', state='surface',
            note=('Transvalley and R5' if side == 'W' else 'ORR/intercity (E-H); 22 m further east from Camp Washington to Brashears, beside TRI B/D') + ': on the viaduct from Ludlow (rails at ground, 155.5 m) to Bank')
        add('lower', r, name=f'Lower-level pair {side}, track {k+1}, dive', level='viaduct to tunnel', state='ramp',
            note=f'{100*dive_info["g_dive"]:.2f}% down from {Z_DIVE0:.1f} m over Bank to {Z_PORT:.1f} m under Findlay, open between them')
        top = r
        if len(u) > 1 and LineString(u).length > 2:
            add('lower', u, name=f'Lower-level pair {side}, track {k+1}, under the deck', level='under deck', state='under'); top = u
        if k == 0:
            addpt('marker', r[0], kind='level', name=f'Lower pair {side} leaves the viaduct', label=(f'lower pairs start down, {Z_DIVE0:.1f} m' if side == 'W' else ''), anchor='left')
            addpt('marker', r[-1], kind='portal', name=f'Portal {side}', label=(f'portals under Findlay, {Z_PORT:.1f} m' if side == 'W' else ''), anchor='left', dy=16)
        base = 0 if side == 'W' else 4
        for m in (0, 1):
            t_ = base + 2 * k + m
            n_ = AD_N if t_ < 4 else EH_N
            add('lower', bezt(top[-1], tangent(top, 'end'), (bx[t_], n_), (0, -1), k=0.38), name=f'Lower north fan to {LET[t_]}', level='-2', state='under')
G_DIVE = dive_info['g_dive']
street_fix = []
for nm in MID_STREETS:
    worst = None
    for x in (XW, XE):
        n_, w_ = street_N(nm, x)
        if n_ is None: continue
        rail = Z_DIVE0 - G_DIVE * (DIVE_N0 - n_)
        dip = DECK(n_) + CLR - rail                      # street lowered to pass under the lower pairs
        hump = rail + UNDER - DECK(n_)                   # street raised to pass over them
        need = min(max(dip, 0), max(hump, 0)); how = 'dip' if max(dip, 0) <= max(hump, 0) else 'hump'
        if worst is None or need > worst[0]: worst = (need, how, n_, rail, x)
    if worst is None: continue
    need, how, n_, rail, x = worst
    street_fix.append(dict(name=nm, need=round(need, 1), how=how, rail=round(rail, 1), keep=bool(need <= 3.0)))
    lab = f'{nm}: {"lowered" if how == "dip" else "raised"} {need:.1f} m' if need <= 3.0 else f'{nm} ends at the dive'
    addpt('marker', (XE + 22, n_), kind=('level' if need <= 3.0 else 'flag'), name=f'{nm} at the dive', label=lab, rail=round(rail, 1))
    if need > 3.0:   # cut on both sides of the ramps: flag the west wall too
        nW_, _ = street_N(nm, XW - 30)
        addpt('marker', (XW - 22, nW_ if nW_ else n_), kind='flag', name=f'{nm} at the dive (west side)', label=f'{nm} ends', anchor='left')
for nm, how in (('Bank', 'dip'), ('Findlay', 'hump')):
    n_, w_ = street_N(nm, XE)
    if n_ is None: n_, w_ = street_N(nm, XW)
    street_fix.insert(0 if nm == 'Bank' else len(street_fix), dict(name=nm, need=END_REGRADE, how=how, rail=round(Z_DIVE0 if nm == 'Bank' else Z_PORT, 1), keep=True))
    addpt('marker', (XE + 22, n_), kind='level', name=f'{nm} at the dive', label=f'{nm}: {"lowered" if how == "dip" else "raised"} {END_REGRADE:.1f} m')
# streets over the tunnel
# in the tunnel: keep the dive grade past Findlay to Sherman's north edge, then ease to the platforms
nS, wS = street_N('Sherman', XW); N_S = nS + wS / 2
z_S = Z_DIVE0 - G_DIVE * (DIVE_N0 - N_S); G_TUN2 = (z_S - LOWER) / (N_S - EH_N)
rail_at = lambda N: Z_DIVE0 - G_DIVE * (DIVE_N0 - N) if N >= N_S else LOWER + G_TUN2 * (N - EH_N)
over_tunnel = []
for nm in ('Poplar', 'Sherman', 'W Liberty'):
    n_, w_ = street_N(nm, XW); edge = n_ + w_ / 2; rail = rail_at(edge)
    over_tunnel.append(dict(name=nm, cover=round(DECK(n_) - rail, 1), ok=bool(DECK(n_) - rail >= UNDER - 0.05)))
tun_len = PORTAL_N - EH_N
G_TUN = G_TUN2

# ---------------------------------------------------------------- CS pair (A-D) to the CS bridge, west of the APEx throat, beside Horne
LAD = 120.0
CS0 = (LX0 + 12.0, AD_S - LAD)
MERGE = tuple(SPANS['CS'][0]); BANK_N = float(SPANS['CS'][0][1])          # the intercity pair reaches the CS bridge at its span (Bridge Spans.kmz)
cs_ctrl = [(LX0 + 12, AD_S - 40), CS0, (LX0 + 2, 4331530), (712708, 4331430), (712684, 4331330), (712670, 4331220), (712664, 4331150), (712655, 4331020), (712638, 4330900), (712618, 4330790)]
_s0, _s1 = np.array(SPANS['CS'][0]), np.array(SPANS['CS'][-1]); _sd = (_s1 - _s0) / np.linalg.norm(_s1 - _s0)
_north = joinsmooth([cs_ctrl[:-2], [tuple(_s0 - _sd * 120)], [tuple(_s0 - _sd * 60)]], d=45)        # onto the span's own line 120 m before it
cs_full = resample(_north + [tuple(_s0 - _sd * 30)] + [tuple(_s0 + _sd * t) for t in np.arange(0, float(np.linalg.norm(_s1 - _s0)) + 0.1, 5.0)] + [tuple(_s1 + _sd * 40)], 5.0)
cs_full = from_N(cs_full, CS0[1])
s_bank = s_at_N(cs_full, BANK_N); s_merge = s_at_N(cs_full, MERGE[1])
sG, s8, s6 = (s_at_N(cs_full, STREETS[n]) for n in ('Gest', 'W 8th', 'W 6th'))
# z_merge: the TRIMET CS viaduct level where the intercity pair meets it (south approach block)
def cs_profile(h):
    """Rail at 144 to the ladder end, under Gest, under W 8th with an h m street hump, then straight to the merge level."""
    z8 = DECK(STREETS['W 8th']) - UNDER + h
    g0 = (z8 - LOWER) / s8; g1 = (z_merge - z8) / (s_merge - s8)
    zG = LOWER + g0 * sG; z6 = z8 + g1 * (s6 - s8)
    return dict(h=h, z8=z8, g0=g0, g1=g1, zG=zG, gest_ok=zG <= DECK(STREETS['Gest']) - UNDER + 1e-6, z6=z6, six_ok=z6 >= DECK(STREETS['W 6th']) + CLR - 1e-6)
OPTS = {h: cs_profile(h) for h in (0.0, 1.0, 2.0, 3.0, 4.0, 5.0)}
H = 5.0                                                              # 17 October (Ben): W 8th raised 5 m on retaining walls; the pair leaves through a portal in the south wall
P = OPTS[H]
W8 = [f for f in json.load(open(S + 'deckpage/deck.json'))['features'] if f['properties'].get('id') == 'S001'][0]['properties']['width_m']
s_port = s8 + W8 / 2; z_port = P['z8'] + P['g1'] * (W8 / 2)
s_grd = next(s for s in np.arange(s_port, s_merge, 1.0) if P['z8'] + P['g1'] * (s - s8) >= DECK(pt_at(cs_full, s)[1]))
W8_APEX = apex_zN(STREETS['W 8th']) - CLR - DECK(STREETS['W 8th'])     # how high W 8th may stand under the APEx
CS_PORTAL = dict(z=round(z_port, 1), trough_m=round(s_grd - s_port), street_apex_m=round(W8_APEX, 1))
for d, nm in ((-2.25, 'west'), (2.25, 'east')):
    add('lower', offs(cs_full[:int(s_bank / 5) + 1], d), name=f'Intercity pair ({nm} track): A-D to the Cincinnati Southern bridge', level='-2 to bridge',
        state='climb', note=f'{100*P["g0"]:.2f}% to W 8th ({P["z8"]:.1f} m, street humped {H:.0f} m), then {100*P["g1"]:.2f}% onto the TRIMET CS viaduct at {z_merge:.1f} m and the CS bridge')
for i in range(4):
    add('lower', bezt((bx[i], AD_S), (0, -1), offs(cs_full, -2.25 if i < 2 else 2.25)[0], tangent(cs_full, 'start'), k=0.4), name=f'Lower track {LET[i]} to CS pair', level='-2', state='under')
add('bridge', [tuple(CSB[0]), tuple(CSB[1])], name='Cincinnati Southern bridge (1922, double track)', rail_m='164.0-164.7 (TRIMET)',
    clearance_ft=78.9, note='TRIMET_Lines.kmz 3D alignment; Waterway Guide: fixed, 78.9 ft vertical clearance, mile 472.3')
zc = lambda s: LOWER + P['g0'] * s if s <= s8 else P['z8'] + P['g1'] * (s - s8)
for s, lab, kind in ((0, f'Intercity pair climbs from {LOWER:.0f} m', 'level'), (sG, f'Gest: intercity pair {zc(sG):.1f} m, under', 'level'),
                     (s8, f'W 8th: intercity pair {P["z8"]:.1f} m, street raised {H:.0f} m ({W8_APEX:.1f} m at the APEx)', 'flag'),
                     (s_port, f'Intercity portal in the W 8th south wall, {z_port:.1f} m; at ground {s_grd - s_port:.0f} m south', 'portal'), (s6, f'W 6th: intercity pair {P["z6"]:.1f} m, over', 'level'),
                     (s_merge, f'onto the TRIMET CS viaduct, {z_merge:.1f} m', 'level'), (s_bank, 'CS bridge, 164.0 m (TRIMET)', 'level')):
    addpt('marker', pt_at(cs_full, s), kind=kind, name='Intercity pair: ' + lab, label=lab, anchor='left')
addpt('marker', (712600, 4331262), kind='level', name='Horne at W 8th', label=f'Horne raised {H:.0f} m at W 8th (ramps about 100 m)', anchor='right')
# across the CS bridge and through Ludlow on the TRIMET CS line (Lebanon-Walton), with the CVG Express branch (Ben: the pink tracks to Ludlow)
REG = (699000, 4320800, 736900, 4347000)
_inreg = lambda q: REG[0] <= q[0] <= REG[2] and REG[1] <= q[1] <= REG[3]
cs_ky = [tuple(q) for q in cs_full[int(s_bank / 5):]]
lw_after = [q for q in LWS if q[1] < cs_ky[-1][1] - 20 and _inreg(q)]
CSK = joinsmooth([cs_ky, lw_after], d=30, it=4)
CV3S = smooth([c[:2] for c in CV3 if c[1] < 4330300], it=4)
_div = max(i for i, q in enumerate(CV3S) if LineString(LWS).distance(Point(q)) < 30.0)          # the CVG line rides the CS line to Erlanger, then turns west
_dpt = CV3S[max(0, _div - 6)]
s_div_k = LineString(CSK).project(Point(_dpt))
_cvt = [q for q in CV3S[_div:] if _inreg(q)]; _cvl = LineString(_cvt); _e = _cvl.interpolate(450)
_a0 = LineString(CSK).interpolate(s_div_k - 350); _a1 = LineString(CSK).interpolate(s_div_k - 340)
_e1 = _cvl.interpolate(460)
_jn = bezt((_a0.x, _a0.y), np.subtract(_a1.coords[0], _a0.coords[0]) / 10.0, (_e.x, _e.y), np.subtract(_e1.coords[0], _e.coords[0]) / 10.0, k=0.45, n=80)
CVK = smooth(thin(_jn + [q for q in _cvt if _cvl.project(Point(q)) > 470], 40.0), it=5)
for d, nm in ((-2.25, 'west'), (2.25, 'east')):
    add('lower', offs(CSK, d), name=f'CS line ({nm} track): intercity, Ohio bank to Ludlow and on', level='bridge, then at grade', state='surface',
        note='across the 1922 CS bridge (164.0 m) and through Ludlow at grade on the TRIMET Lebanon-Walton line')
CSK_INFO = dict(div=[round(_dpt[0], 1), round(_dpt[1], 1)], km=round(LineString(CSK).length / 1000, 1), cvg_km=round(LineString(CVK).length / 1000, 1))
addpt('marker', tuple(LineString(CSK).interpolate(LineString(CSK).project(Point(CSB[1])) + 260).coords[0]), kind='level', name='Ludlow: CS line at grade',
      label='Ludlow: CS line at grade (TRIMET), intercity', anchor='right')

# ---------------------------------------------------------------- C&O pair (E-H): level at -2 to W 6th, then up onto the TRIMET C&O viaduct
CO0 = (LX0 + 70.0, EH_S - LAD)
TCO = [tuple(p) for p in TB['co']]
MI = min(range(len(TCO)), key=lambda i: math.dist(TCO[i][:2], (713433, 4330462)))
co_ctrl = [(LX0 + 70, EH_S - 40), CO0, (LX0 + 78, 4331500), (712820, 4331380), (712838, 4331250), (712850, 4331100), (712868, 4330960),
           (712905, 4330845), (712975, 4330752), (713075, 4330680), (713195, 4330614), (713310, 4330548)]
co_full = joinsmooth([co_ctrl, [p[:2] for p in TCO[MI:]]], d=45)
co_full = from_N(co_full, CO0[1])
s_co6 = s_at_N(co_full, STREETS['W 6th']); s_com = LineString(co_full).project(Point(TCO[MI + 2][:2])); MI = MI + 2
z_co6 = min(LOWER, DECK(STREETS['W 6th']) - UNDER)
g_co = (TCO[MI][2] - z_co6) / (s_com - s_co6)
for d, nm in ((2.25, 'west'), (-2.25, 'east')):
    add('lower', offs(co_full, d), name=f'C&O pair ({nm} track): E-H to the C&O viaduct and bridge', level='-2 to viaduct', state='climb',
        note=f'level at {LOWER:.0f} m under Gest, W 8th and W 6th, then {100*g_co:.2f}% to the TRIMET C&O viaduct at {TCO[MI][2]:.1f} m')
for i in range(4, 8):
    add('lower', bezt((bx[i], EH_S), (0, -1), offs(co_full, 2.25 if i < 6 else -2.25)[0], tangent(co_full, 'start'), k=0.4), name=f'Lower track {LET[i]} to C&O pair', level='-2', state='under')
add('bridge', [tuple(q) for q in SPANS['C&O']], name='C&O bridge (1929)', rail_m='163.1-165.3 (TRIMET)', note='span ends from Bridge Spans.kmz')
for _nm, _lab in (('CWB', 'Clay Wade Bailey Bridge (road)'), ('Roebling', 'Roebling Suspension Bridge (road)'), ('Cincy-Newport', 'Cincinnati-Newport bridge (Bridge Spans.kmz)'), ('L&N', 'L&N bridge (Bridge Spans.kmz)')):
    add('bridge', [tuple(q) for q in SPANS[_nm]], name=_lab, kind='other', note='span ends from Bridge Spans.kmz (Ben, 17 October)')
addpt('marker', pt_at(co_full, s_co6), kind='level', name='C&O pair under W 6th', label=f'W 6th: C&O {z_co6:.1f} m, under')
# rail profiles of the climbing pairs, for the structures layer (cut/structures.py)
def _prof(c, zf, s1):
    out = []
    for s in np.arange(0, s1, 10.0):
        q = pt_at(c, s); out.append([round(q[0], 1), round(q[1], 1), round(float(zf(s)), 2)])
    return out
PROF = dict(intercity=dict(c=_prof(cs_full, zc, s_bank), portal_s=round(s_port, 1)),
            co=dict(c=_prof(co_full, lambda s: z_co6 if s <= s_co6 else z_co6 + g_co * (s - s_co6), s_com)))
addpt('marker', TCO[MI][:2], kind='level', name='C&O pair joins the TRIMET C&O viaduct', label=f'joins C&O viaduct, {TCO[MI][2]:.1f} m')

# ---------------------------------------------------------------- R5 (ORR) leaves the west pair for the Cumminsville Spur (ORR Segments.kmz SW-10)
_ORR = json.load(open(S + 'nv/orr_near.json'))['lines']
_sp = [tuple(p) for p in [r for r in _ORR if r['name'] == 'Cumminsville Spur'][0]['pts']]
_sp = _sp if _sp[0][1] < _sp[-1][1] else _sp[::-1]                 # trunk -> west and north
_nn = [tuple(p) for p in [r for r in _ORR if r['name'] == 'Northside-Northgate'][0]['pts']]
_nn = _nn if _nn[0][1] < _nn[-1][1] else _nn[::-1]
S_R5 = 4150.0
_r0 = G27.nt_point(S_R5, -20.25); _r0b = G27.nt_point(S_R5 + 30, -20.25)
_spl = LineString(_sp); _j = _spl.interpolate(_spl.project(Point(712178, 4336042)))
_tail = [q for q in _sp if _spl.project(Point(q)) > _spl.project(_j)] + _nn[1:]
_tl = LineString([(_j.x, _j.y)] + _tail)
_t0 = np.subtract(_r0b, _r0); _t0 = _t0 / np.linalg.norm(_t0)
R5C = bezt(_r0, _t0, (_j.x, _j.y), tangent(list(_tl.coords), 'start'), k=0.45, n=50) + list(_tl.coords)[1:]
R5C = smooth(thin(R5C, 8.0), it=3, step=4.0)
R5C = [q for q in R5C if q[1] <= 4339800]
for d, nm in ((-2.25, 'west'), (2.25, 'east')):
    g_ = LineString(R5C).offset_curve(-d, quad_segs=8)              # + = right of travel (trunk -> west): the east/north rail first
    add('lower', list(g_.coords), name=f'R5 to the Cumminsville Spur ({nm} track)', level='viaduct, then down to grade (not set)', state='surface',
        note=f'ORR R5 leaves the Transvalley/R5 pair at s {S_R5:,.0f} at about {G27.band(S_R5):.1f} m, runs under the Indianapolis + D deck and under RER A '
             '(167.0 m) on the SW-10 Cumminsville Spur line to South Cumminsville and on as Northside-Northgate; its descent and street crossings west of the trunk are not set (log 10za.19, 10za.24)')
addpt('marker', R5C[30], kind='level', name='R5 leaves the west pair', label=f'R5 leaves the west pair, {G27.band(S_R5):.1f} m (levels west not set)', anchor='right')

# ---------------------------------------------------------------- viaduct levels along the trunk
s_m = s_at_N(CN, STREETS['Marshall']); L_ramp = s_m                     # CN starts at the deck's north end
g_ramp = (APEX(STREETS['Marshall']) - 151.8) / L_ramp
# 2026-10-14: no portal at the deck tip; the viaduct runs on north to Ludlow (log 10za.30)
NV = []
def nmark(s, o, label, kind='level', anchor='left', dy=0):
    addpt('marker', G27.nt_point(s, o), kind=kind, name=label, label=label, anchor=anchor, **({'dy': dy} if dy else {})); NV.append(label)
nmark(5300, -30, f'Ludlow: rails at ground, {G27.Z_LUD:.1f} m; viaduct from here to CUT')
nmark(G27.S_TIP - 40, 60, f'deck tip: viaduct {G27.Z_TIP:.1f} m, {100*G27.G_BAND:.2f}% down to Ludlow', anchor='right')
nmark(3170, -30, f'Hopple at deck level, {G27.band(3170) - G27.deck(G27.C.interpolate(3170).y):.1f} m under the viaduct')
nmark(G27.S_A, 2, f'Indianapolis + D leave the viaduct level, {100*G27.G_SH:.1f}% up', anchor='left')
nmark(G27.S_C, -30, f'Indianapolis + D {G27.sh_z(G27.S_C):.1f} m ({G27.sh_z(G27.S_C) - G27.band(G27.S_C):.1f} m over the viaduct), west on the KMZ curve; 174.3 m from s {G27.S_A + (174.3 - G27.band(G27.S_A)) / G27.G_SH:,.0f}')
for nm in ('Marshall', 'W Liberty'):
    N = STREETS[nm]; x = min(CN, key=lambda p: abs(p[1] - N))[0]
    addpt('marker', (x + 45, N - 25), kind='level', name=f'Viaduct over {nm}', label=f'APEx {APEX(N):.1f} m over {nm}')
Z6_APEX = apex_zN(STREETS['W 6th'])
for nm, dn, z in (('W 8th', 0, apex_zN(STREETS['W 8th'])), ('W 6th', -60, Z6_APEX)):
    N = STREETS[nm]; c = appr_s[5]; x = min(c, key=lambda p: abs(p[1] - (N + dn)))[0]
    addpt('marker', (x + 20, N + dn), kind='level', name=f'Viaduct over {nm}', label=f'{z:.1f} m over {nm}')

# ---------------------------------------------------------------- labels
addpt('label', (713090, 4332230), text=f'APEx 1-16  ·  level 0, {APEX(FCN):.1f} m (real 1933 platforms {TRIMET_CUT} m)', kind='big')
addpt('label', (713090, 4332165), text=f'Lower A-H  ·  -2, {LOWER:.0f} m', kind='lower')
addpt('label', (712930, 4333600), text='Arch viaduct: 6 APEx + 4 lower', kind='small')
addpt('label', G27.nt_point(4800, 70), text='Viaduct: Transvalley/R5, APEx 4, TRI B, ORR E', kind='small')
addpt('label', G27.nt_point(3330, 175), text='Viaduct: Transvalley/R5, APEx 6, TRI B/D, ORR E (12)', kind='small')
addpt('label', (712560, 4331420), text='Intercity pair', kind='lower')
addpt('label', tuple(np.array(fpt('16', FN0 + 60)) + F_E * 26), text='M: CVG Express 15-16 (1933 mail platform)', kind='small')
addpt('label', tuple((np.array(APB[0]) + np.array(APB[1])) / 2 + _n * 270), text='Ohio crossing: CS bridge 2 (intercity), APEx bridge 4, CVG span 2', kind='small')
addpt('label', (712925, 4331330), text='C&O pair', kind='lower')
addpt('label', (712600, 4332000), text='Freight passing track', kind='small')

# ---------------------------------------------------------------- checks and summary
lines = [f for f in F if f['geometry']['type'] == 'LineString']
worst = sorted(((min_radius(f['geometry']['coordinates']), f['properties']['name']) for f in lines if len(f['geometry']['coordinates']) > 8))[:6]
kinks = []
for f in lines:
    c = f['geometry']['coordinates']
    for i in range(1, len(c) - 1):
        v1, v2 = np.subtract(c[i], c[i - 1]), np.subtract(c[i + 1], c[i])
        if np.linalg.norm(v1) > 0.5 and np.linalg.norm(v2) > 0.5:
            ang = math.degrees(math.acos(max(-1, min(1, np.dot(v1, v2) / np.linalg.norm(v1) / np.linalg.norm(v2)))))
            if ang > 6: kinks.append((round(ang, 1), f['properties']['name'], c[i]))
summary = dict(basis='arch viaduct', apex_cut=round(APEX(FCN), 1), apex_raise=round(APEX(FCN) - TRIMET_CUT, 1), lower_rail=LOWER,
               apex_levels={k: round(apex_zN(v), 1) for k, v in STREETS.items()},
               north=dict(s_ludlow=G27.S_LUD, z_ludlow=G27.Z_LUD, z_tip=round(G27.Z_TIP, 2), g_band=round(100 * G27.G_BAND, 3), len_tip_ludlow=round(G27.S_LUD - G27.S_TIP),
                          s_indy=G27.S_A, g_indy=100 * G27.G_SH, s_curve=G27.S_C, r_curve=G27.R_C, z_indy=G27.Z_TOP, marks=NV),
               north_tracks=10, south_tracks=10, field=dict(src=FLD['src'], unit=FLD['unit_m'], island=FLD['island_m'], pair=FLD['pair_m'], edge=F_EDGE, m_north=[round(B_N), FN1], m_south=[FN0, round(B_S)]),
               cvg=CVG_INFO, lud=LUD_INFO, csk=CSK_INFO, eh=[round(EH_N), round(EH_S)], ad=[round(AD_N), round(AD_S)],
               cs_opts={h: dict(z8=round(o['z8'], 1), g0=round(100 * o['g0'], 2), g1=round(100 * o['g1'], 2), zG=round(o['zG'], 1), gest_ok=bool(o['gest_ok']),
                                z6=round(o['z6'], 1), six_ok=bool(o['six_ok'])) for h, o in OPTS.items()},
               cs_hump=H, cs_portal=CS_PORTAL, prof=PROF, cs_g=round(100 * P['g1'], 2), cs_z8=round(P['z8'], 1), cs_z6=round(P['z6'], 1), cs_zG=round(P['zG'], 1),
               need6=round(DECK(STREETS['W 6th']) + CLR, 1), z_merge=round(z_merge, 1), 
               dive=dict(n0=round(DIVE_N0), portal=round(PORTAL_N), z0=round(Z_DIVE0, 1), z1=round(Z_PORT, 1), g=round(100 * G_DIVE, 2), L=round(dive_info['L_dive']),
                         L_cover=round(tun_len), g_tun=round(100 * G_TUN, 2), z_sherman=round(z_S, 1), streets=street_fix, opts=DIVE_OPTS, over_tunnel=over_tunnel),
               apb_off=round(APB_OFF, 1), apb_off_s=round(APB_OFF_S, 1), apb_r=round(R_APP), apb_brg=round(math.degrees(math.atan2(_d[0], _d[1])) % 360, 1), apb_g=round(100 * G_APB, 2), co_z6=round(z_co6, 1), co_g=round(100 * g_co, 2), co_merge_z=TCO[MI][2],
               min_radius=[(round(r), n) for r, n in worst], kinks=len(kinks))
json.dump(dict(crs='EPSG:26916', summary=summary, features=F, cvx=CVX_DATA), open(OUT, 'w'))
print(json.dumps(summary, indent=1)); print('features', len(F))
for k in kinks[:12]: print('KINK', k)
