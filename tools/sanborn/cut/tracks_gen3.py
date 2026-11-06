try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# CUT approach tracks, v3 (2026-10-10). Arch-viaduct basis (Ben): APEx a set height above the deck cross streets
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
XP = FW + 2.5                                           # passing track inside the zone, west edge (the 1955 position)
U = (FE - FW - 5.0) / 8                                 # 18.375 m per two-track unit
tx = [FW + 5.0 + U * (i // 2) + (2.25 if i % 2 == 0 else U - 2.25) for i in range(16)]   # i = 0 west .. 15 east
for u in range(8):
    x0 = FW + 5.0 + U * u
    addpoly('apex_plat', [(x0 + 4.5, FN0), (x0 + U - 4.5, FN0), (x0 + U - 4.5, FN1), (x0 + 4.5, FN1), (x0 + 4.5, FN0)],
            name=f'APEx platform, tracks {16 - 2*u} / {15 - 2*u}', level='0', rail=round(APEX(FCN), 1), length_m=round(FN1 - FN0, 1))
for i, x in enumerate(tx):
    add('apex', [(x, FN1), (x, FN0)], name=f'APEx track {16 - i}', level='0', kind='platform')

# ---------------------------------------------------------------- trunk: smooth curve from the deck's north end, then straight to the throat
north_ctrl = [(712247, 4335576), (712242, 4335456), (712238, 4335337), (712233, 4335216), (712233, 4335092), (712271, 4334964),
              (712354, 4334857), (712437, 4334757), (712514, 4334654), (712584, 4334550), (712654, 4334447), (712721, 4334335), (712753, 4334180)]
STR0 = (712753.0, 4334180.0)
straight = [(STR0[0] + (FC - STR0[0]) * f, STR0[1] + (NT - STR0[1]) * f) for f in np.linspace(0, 1, 12)]
CN = smooth(north_ctrl + straight[1:], it=5)
CN = cut_at_N(CN, NT) + [(FC, NT)] if CN[-1][1] > NT else CN
A_OFF = [-11.25, -6.75, -2.25, 2.25, 6.75, 11.25]
appr_n = []
for j, d in enumerate(A_OFF):
    c = offs(CN, d); appr_n.append(c)
    add('apex', c, name=f'APEx north approach {j+1} of 6', level='0', kind='approach', note='3 in + 3 out')
for i, x in enumerate(tx):
    j = min(5, int(i * 6 / 16)); e = appr_n[j][-1]
    add('apex', bezt((x, FN1), (0, 1), e, -tangent(appr_n[j], 'end')), name=f'APEx north throat, track {16 - i}', level='0', kind='throat')
# passing track
e_n = appr_n[0][-1]; s_ = None
j_n = from_N(appr_n[0], 4332520)[0]
pas_n = bezt(j_n, tangent(appr_n[0], 'end'), (XP, FN1), (0, -1), k=0.42, n=60)
# ---------------------------------------------------------------- south approach (viaduct level)
CSB = (np.array([712595.0, 4330684.0]), np.array([712526.0, 4330371.0]))          # TRIMET CS bridge, north and south bank
_d = (CSB[1] - CSB[0]) / np.linalg.norm(CSB[1] - CSB[0]); _n = np.array([-_d[1], _d[0]])
if _n[0] < 0: _n = -_n                                                              # east-pointing normal
KMZ_MID = np.array([(712678 + 712553) / 2, (4330647 + 4330366) / 2])
APB_OFF = float(np.dot(KMZ_MID - CSB[0], _n))                                       # perpendicular offset of the KMZ crossing east of the CS bridge
APB = (CSB[0] + _n * APB_OFF, CSB[1] + _n * APB_OFF)                                # APEx bridge centre line, parallel to the CS bridge
APB_X = APB[1] + _d * 120                                                           # into Ludlow
_w = -_n * 4.5                                                                      # APEx 4 tracks are centred 4.5 m east of the approach centre line
_p1 = APB[0] + _w - _d * 150                                                       # straight from the throat to here, then onto the bridge line
CS_CTRL = [tuple(np.array([FC, ST]) + (_p1 - np.array([FC, ST])) * f) for f in np.linspace(0, 1, 6)] + \
          [tuple(APB[0] + _w - _d * 50), tuple(APB[0] + _w), tuple(APB[1] + _w), tuple(APB_X + _w)]
CSL = smooth(CS_CTRL, it=5)
S_OFF = [-11.25, -6.75, -2.25, 2.25, 6.75, 11.25]
S_NAME = ['CVG Express', 'CVG Express', 'APEx (Kentucky)', 'APEx (Kentucky)', 'APEx (Kentucky, Cardinal)', 'APEx (Kentucky, Cardinal)']
appr_s = [offs(CSL, d) for d in S_OFF]
for i, x in enumerate(tx):
    num = 16 - i
    j = 0 if num == 16 else 1 if num == 15 else 2 + min(3, int((i - 2) * 4 / 14))
    add('apex', bezt((x, FN0), (0, -1), appr_s[j][0], tangent(appr_s[j], 'start')), name=f'APEx south throat, track {num}', level='0', kind='throat')
j_s = from_N(appr_s[2], 4331290)[0]
pas_s = bezt((XP, FN0), (0, -1), j_s, tangent(from_N(appr_s[2], 4331290), 'start'), k=0.42, n=60)
add('passing', pas_n + pas_s, name='Freight passing track', level='0',
    note='bypasses the platforms end to end on the west side, as in 1955; joins the westmost APEx main north and the first APEx main south')

# TRIMET CS viaduct and bridge
TCS = smooth([tuple(p[:2]) for p in TB['cs']], it=4)
CVG_DIV_N = 4331080.0
cvg_lines = []
for j in range(6):
    c = appr_s[j]
    if j < 2:
        top = cut_at_N(c, CVG_DIV_N + 60); tc = offs(TCS, S_OFF[j] + 9.0)
        top = cut_at_N(c, CVG_DIV_N + 120); tcj = from_N(tc, 4330900)
        c = top + bezt(top[-1], tangent(top, 'end'), tcj[0], tangent(tcj, 'start'), k=0.42, n=70)[1:] + tcj[1:]
        cvg_lines.append(c)
    elif j >= 4:
        car_ctrl = [(712800, 4331100), (712808, 4331000), (712832, 4330890), (712882, 4330800), (712962, 4330720), (713060, 4330652),
                    (713258, 4330549), (713497, 4330450), (713624, 4330422), (713776, 4330431)]
        CAR = smooth(car_ctrl, it=4); co = offs(CAR, -2.25 if j == 4 else 2.25)
        top = cut_at_N(c, 4331260)
        coj = from_N(co, 4330860)
        add('apex', top + bezt(top[-1], tangent(top, 'end'), coj[0], tangent(coj, 'start'), k=0.42, n=70)[1:] + coj[1:],
            name='Cardinal branch (APEx, east along the river)', level='0', kind='branch')
    add('apex', c, name=f'South approach {j+1} of 6: {S_NAME[j]}', level='0', kind='approach')
add('bridge', [tuple(APB[0] - _n * 0), tuple(APB[1])], name='APEx bridge (APEx Routes.kmz crossing)', rail_m='about 164',
    note=f'parallel to the CS bridge, {APB_OFF:.0f} m east of it; the KMZ line meets the CS line about 300 m into Ludlow')
s_b8 = s_at_N(CSL, STREETS['W 8th']); s_bb = s_at_N(CSL, float(APB[0][1]))
G_APB = (164.0 - APEX(STREETS['W 8th'])) / (s_bb - s_b8)
addpt('marker', tuple(APB[0] + _n * 14), kind='level', name='APEx bridge', label=f'APEx bridge, about 164 m ({100*G_APB:.1f}% up from W 8th)')

# ---------------------------------------------------------------- lower level (-2), centred under the field
EH_N, EH_S = FCN + 152.5, FCN - 152.5                 # E-H 305 m, centred
AD_N, AD_S = EH_N, EH_S                               # Ben: all eight lower platforms the longer 305 m
bx = [712700 + 20 * (i // 2) + (2.25 if i % 2 == 0 else 17.75) for i in range(8)]
LET = 'ABCDEFGH'
for u in range(4):
    x0 = 712700 + 20 * u; n_, s_ = (AD_N, AD_S) if u < 2 else (EH_N, EH_S)
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
STR_G = {f['properties']['name']: (LineString(f['geometry']['coordinates']), f['properties']['width_m'])
         for f in DK['features'] if f['properties']['layer'] == 'street'}
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
        c = offs(CN, d)
        v = cut_at_N(c, DIVE_N0); rest = from_N(c, DIVE_N0)
        r = cut_at_N(rest, PORTAL_N); u = from_N(rest, PORTAL_N)
        Lr = DIVE_N0 - PORTAL_N                                 # straight trunk: along-track = northing difference
        dive_info = dict(g_dive=(Z_DIVE0 - Z_PORT) / Lr, L_dive=Lr)
        add('lower', v, name=f'Lower-level pair {side}, track {k+1}, on the viaduct', level='0', state='surface',
            note='climbs with the APEx at the deck north end and rides the viaduct to Bank')
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
CS0 = (712712.0, AD_S - LAD)
MERGE = (712600.0, 4330705.0)
BANK_N = 4330684.0
cs_ctrl = [(712712, AD_S - 40), CS0, (712704, 4331540), (712686, 4331430), (712672, 4331290), (712664, 4331150), (712655, 4331020), (712638, 4330900), (712618, 4330790)]
tc_after = [p for p in TCS if p[1] < MERGE[1]]
cs_full = joinsmooth([cs_ctrl, [MERGE], tc_after], d=45)
cs_full = from_N(cs_full, CS0[1])
s_bank = s_at_N(cs_full, BANK_N); s_merge = s_at_N(cs_full, MERGE[1])
sG, s8, s6 = (s_at_N(cs_full, STREETS[n]) for n in ('Gest', 'W 8th', 'W 6th'))
# CVG pair profile: leaves the APEx approach at N 4,331,200 at viaduct level, constant grade to 164.0 m at the bank
cvg_c = resample(cvg_lines[1], 5.0)
s_cvg_div = s_at_N(cvg_c, CVG_DIV_N); s_cvg_bank = s_at_N(cvg_c, BANK_N); s_cvg_merge = s_at_N(cvg_c, MERGE[1])
z_div = APEX(CVG_DIV_N); g_cvg = (164.0 - z_div) / (s_cvg_bank - s_cvg_div)
z_merge = z_div + g_cvg * (s_cvg_merge - s_cvg_div)
def cs_profile(h):
    """Rail at 144 to the ladder end, under Gest, under W 8th with an h m street hump, then straight to the merge level."""
    z8 = DECK(STREETS['W 8th']) - UNDER + h
    g0 = (z8 - LOWER) / s8; g1 = (z_merge - z8) / (s_merge - s8)
    zG = LOWER + g0 * sG; z6 = z8 + g1 * (s6 - s8)
    return dict(h=h, z8=z8, g0=g0, g1=g1, zG=zG, gest_ok=zG <= DECK(STREETS['Gest']) - UNDER + 1e-6, z6=z6, six_ok=z6 >= DECK(STREETS['W 6th']) + CLR - 1e-6)
OPTS = {h: cs_profile(h) for h in (0.0, 1.0, 2.0, 3.0, 4.0, 5.0)}
H = 3.0
P = OPTS[H]
for d, nm in ((-2.25, 'west'), (2.25, 'east')):
    add('lower', offs(cs_full[:int(s_bank / 5) + 1], d), name=f'CS pair ({nm} track): A-D to the Cincinnati Southern bridge', level='-2 to bridge',
        state='climb', note=f'{100*P["g0"]:.2f}% to W 8th ({P["z8"]:.1f} m, street humped {H:.0f} m), then {100*P["g1"]:.2f}% to join the CVG pair at {z_merge:.1f} m')
for i in range(4):
    add('lower', bezt((bx[i], AD_S), (0, -1), offs(cs_full, -2.25 if i < 2 else 2.25)[0], tangent(cs_full, 'start'), k=0.4), name=f'Lower track {LET[i]} to CS pair', level='-2', state='under')
add('bridge', [p for p in TCS if p[1] <= BANK_N + 2], name='Cincinnati Southern bridge (1922, double track)', rail_m='164.0-164.7 (TRIMET)',
    clearance_ft=78.9, note='TRIMET_Lines.kmz 3D alignment; Waterway Guide: fixed, 78.9 ft vertical clearance, mile 472.3')
zc = lambda s: LOWER + P['g0'] * s if s <= s8 else P['z8'] + P['g1'] * (s - s8)
for s, lab, kind in ((0, f'CS climbs from {LOWER:.0f} m', 'level'), (sG, f'Gest: CS {zc(sG):.1f} m, under', 'level'),
                     (s8, f'W 8th: CS {P["z8"]:.1f} m, street humped {H:.0f} m', 'flag'), (s6, f'W 6th: CS {P["z6"]:.1f} m, over', 'level'),
                     (s_merge, f'joins CVG pair, {z_merge:.1f} m', 'level'), (s_bank, 'CS bridge, 164.0 m (TRIMET)', 'level')):
    addpt('marker', pt_at(cs_full, s), kind=kind, name='CS pair: ' + lab, label=lab, anchor='left')

# ---------------------------------------------------------------- C&O pair (E-H): level at -2 to W 6th, then up onto the TRIMET C&O viaduct
CO0 = (712770.0, EH_S - LAD)
TCO = [tuple(p) for p in TB['co']]
MI = min(range(len(TCO)), key=lambda i: math.dist(TCO[i][:2], (713433, 4330462)))
co_ctrl = [(712770, EH_S - 40), CO0, (712792, 4331500), (712820, 4331380), (712838, 4331250), (712850, 4331100), (712868, 4330960),
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
add('bridge', [p[:2] for p in TCO if p[1] <= 4329962], name='C&O bridge (1929)', rail_m='163.1-165.3 (TRIMET)', note='TRIMET_Lines.kmz 3D alignment')
addpt('marker', pt_at(co_full, s_co6), kind='level', name='C&O pair under W 6th', label=f'W 6th: C&O {z_co6:.1f} m, under')
addpt('marker', TCO[MI][:2], kind='level', name='C&O pair joins the TRIMET C&O viaduct', label=f'joins C&O viaduct, {TCO[MI][2]:.1f} m')

# ---------------------------------------------------------------- viaduct levels along the trunk
s_m = s_at_N(CN, STREETS['Marshall']); L_ramp = s_m                     # CN starts at the deck's north end
g_ramp = (APEX(STREETS['Marshall']) - 151.8) / L_ramp
addpt('marker', CN[0], kind='portal', name='APEx and lower pairs climb onto the viaduct', label=f'APEx and lower pairs climb {100*g_ramp:.1f}% onto the viaduct', anchor='left')
for nm in ('Marshall', 'W Liberty'):
    N = STREETS[nm]; x = min(CN, key=lambda p: abs(p[1] - N))[0]
    addpt('marker', (x + 45, N - 25), kind='level', name=f'Viaduct over {nm}', label=f'APEx {APEX(N):.1f} m over {nm}')
Z6_APEX = APEX(STREETS['W 8th']) + G_APB * (s_at_N(CSL, STREETS['W 6th']) - s_b8)
for nm, dn, z in (('W 8th', 0, APEX(STREETS['W 8th'])), ('W 6th', -60, Z6_APEX)):
    N = STREETS[nm]; c = appr_s[5]; x = min(c, key=lambda p: abs(p[1] - (N + dn)))[0]
    addpt('marker', (x + 20, N + dn), kind='level', name=f'Viaduct over {nm}', label=f'{z:.1f} m over {nm}')

# ---------------------------------------------------------------- labels
addpt('label', (713090, 4332230), text=f'APEx 1-16  ·  level 0, {APEX(FCN):.1f} m (real 1933 platforms {TRIMET_CUT} m)', kind='big')
addpt('label', (713090, 4332165), text=f'Lower A-H  ·  -2, {LOWER:.0f} m', kind='lower')
addpt('label', (712930, 4333600), text='Arch viaduct: 6 APEx + 4 lower', kind='small')
addpt('label', (712560, 4331420), text='CS pair', kind='lower')
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
               apex_levels=dict({k: round(APEX(v), 1) for k, v in STREETS.items()}, **{'W 6th': round(Z6_APEX, 1)}), ramp_pct=round(100 * g_ramp, 2), ramp_len=round(L_ramp),
               north_tracks=10, south_tracks=10, eh=[round(EH_N), round(EH_S)], ad=[round(AD_N), round(AD_S)],
               cs_opts={h: dict(z8=round(o['z8'], 1), g0=round(100 * o['g0'], 2), g1=round(100 * o['g1'], 2), zG=round(o['zG'], 1), gest_ok=bool(o['gest_ok']),
                                z6=round(o['z6'], 1), six_ok=bool(o['six_ok'])) for h, o in OPTS.items()},
               cs_hump=H, cs_g=round(100 * P['g1'], 2), cs_z8=round(P['z8'], 1), cs_z6=round(P['z6'], 1), cs_zG=round(P['zG'], 1),
               need6=round(DECK(STREETS['W 6th']) + CLR, 1), z_merge=round(z_merge, 1), cvg_g=round(100 * g_cvg, 2), z_div=round(z_div, 1),
               dive=dict(n0=round(DIVE_N0), portal=round(PORTAL_N), z0=round(Z_DIVE0, 1), z1=round(Z_PORT, 1), g=round(100 * G_DIVE, 2), L=round(dive_info['L_dive']),
                         L_cover=round(tun_len), g_tun=round(100 * G_TUN, 2), z_sherman=round(z_S, 1), streets=street_fix, opts=DIVE_OPTS, over_tunnel=over_tunnel),
               apb_off=round(APB_OFF, 1), apb_g=round(100 * G_APB, 2), co_z6=round(z_co6, 1), co_g=round(100 * g_co, 2), co_merge_z=TCO[MI][2],
               min_radius=[(round(r), n) for r, n in worst], kinks=len(kinks))
json.dump(dict(crs='EPSG:26916', summary=summary, features=F), open(OUT, 'w'))
print(json.dumps(summary, indent=1)); print('features', len(F))
for k in kinks[:12]: print('KINK', k)
