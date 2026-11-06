"""North trunk viaduct for page version 27 (log 10za.30-10za.33): plan geometry and levels shared by tracks_gen4.py,
build_transit.py and west_valley.py.

Chainage s is along the KMZ APEx line C from CUT (nv/profile.json). Offsets are east of the drawing trunk NT (+ east,
looking north): NT = the page's smoothed approach trunk CN (tracks_gen3) from the deck tip south, and the KMZ line north
of the tip to Ludlow. West to east: Transvalley/R5 -22.5/-18, APEx Dayton/Norwood -11.25..2.25, APEx Indianapolis
6.75/11.25, TRI B/D, ORR E. Levels as nv/v5.py (band = deck + 6.5 m to the tip, then 0.787% to 155.5 m at Ludlow)."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, math, numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import substring
SP = _ws.DATA
C = LineString(json.load(open(SP + 'nv/profile.json'))['C'])
def deck(n): return 151.8 + (n - 4330700) / 4840 * 8.2

# ---------------------------------------------------------------- levels (nv/v5.py)
# 2026-10-22 (highway update, Ben): Ludlow stays at ground on its 1914 line and the trunk rises over it, so the band now falls only to
# 162.5 m at the Ludlow crossing (s 5,369, the 1922 street; 155.4 m ground, about 7 m for the street under the span). North of Ludlow the
# tracks hold 162.5 m through the RER B Northside / Spring Grove platforms (s 5,369-5,570), then fall 1.5% on fill to ground at about s 6,265.
S_TIP, S_LUD, Z_LUD = 3895.2, 5369.0, 162.5
S_NSP1, G_NFILL = 5570.0, 0.015
Z_TIP = deck(C.interpolate(S_TIP).y) + 6.5
G_BAND = (Z_TIP - Z_LUD) / (S_LUD - S_TIP)
S_MAR = 2541.0                                   # Marshall (north edge of the as-built viaduct section)
def band(s):
    if s <= S_TIP: return deck(C.interpolate(s).y) + 6.5
    if s >= S_LUD: return north_z(s)
    return max(Z_LUD, Z_TIP - G_BAND * (s - S_TIP))
def north_z(s):                                  # the trunk on fill north of Ludlow (rail level, not clipped to ground)
    return Z_LUD if s <= S_NSP1 else Z_LUD - G_NFILL * (s - S_NSP1)
S_CW0, S_CW1, S_CWC = 2964.0, 3168.0, 3066.0     # Camp Washington (B, D) platforms, on the viaduct
S_ST0, S_ST1 = 2199.0, 2403.0                    # Straight (B, D) platforms, under the deck
Z_STR = 151.64
G_DIVE = 0.033
Z_CWS = band(S_CW0)
S_BOT = S_CW0 - (Z_CWS - Z_STR) / G_DIVE         # 2,556
S_SEP = S_CW0 - 6.8 / G_DIVE                     # 2,758: 6.8 m under the band from here south
def bd_z(s):                                     # TRI B/D south of the junction
    if s >= S_CW0: return band(s)
    return max(Z_STR, Z_CWS - G_DIVE * (S_CW0 - s))
S_AR0, S_AR1, S_ARC = 4044.0, 4248.0, 4146.0     # Arlington (B), centred on the KMZ point
Z_AR = band(S_ARC)
G_BIN = (Z_TIP - Z_AR) / (S_AR0 - S_TIP)
S_BOUT = S_AR1 + (Z_AR - band(S_AR1)) / (G_BIN - G_BAND)
def b_z(s):                                      # TRI B north of the junction
    if s <= S_TIP: return band(s)
    if s <= S_AR0: return Z_TIP - G_BIN * (s - S_TIP)
    if s <= S_AR1: return Z_AR
    return max(band(s), Z_AR - G_BIN * (s - S_AR1))
S_A, G_SH, Z_TOP = 3644.0, 0.025, 174.3          # Indianapolis + D leave the band level (v5.py: 3,643.5)
S_C, R_C = 3924.0, 745.0                         # KMZ Indianapolis curve start and fitted radius
def sh_z(s):                                     # Indianapolis + D on the trunk
    return band(s) if s <= S_A else min(Z_TOP, band(S_A) + G_SH * (s - S_A))
def sh_zL(L):                                    # beyond the curve start, by length along the path
    return min(Z_TOP, sh_z(S_C) + G_SH * L)
S_JCT = 3250.0                                   # B/D split (flyover junction) begins

# ---------------------------------------------------------------- geometry helpers (as tracks_gen3)
def chaikin(pts, it=5):
    P = np.asarray(pts, float)
    for _ in range(it):
        Q = [P[0]]
        for a, b in zip(P[:-1], P[1:]): Q += [0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b]
        Q.append(P[-1]); P = np.asarray(Q)
    return [tuple(p) for p in P]
def resample(c, step=5.0):
    L = LineString(c); n = max(2, int(L.length / step) + 1)
    return [tuple(L.interpolate(d).coords[0]) for d in np.linspace(0, L.length, n)]
def smooth(pts, it=5, step=5.0): return resample(chaikin(pts, it), step)
def cut_at_N(c, N):
    out = []
    for a, b in zip(c[:-1], c[1:]):
        out.append(a)
        if (a[1] - N) * (b[1] - N) <= 0 and a[1] != b[1]:
            f = (N - a[1]) / (b[1] - a[1]); out.append((a[0] + f * (b[0] - a[0]), N)); return out
    return c
def blend(s, s0, s1, a, b):
    """cosine from a at s0 to b at s1 (vectorised)"""
    s = np.asarray(s, float); t = np.clip((s - s0) / (s1 - s0), 0, 1)
    return a + (b - a) * (1 - np.cos(np.pi * t)) / 2

# ---------------------------------------------------------------- the drawing trunk NT (north -> south)
FC, NTN = (712686.0 + 712838.0) / 2, 4332400.0
north_ctrl = [(712247, 4335576), (712242, 4335456), (712238, 4335337), (712233, 4335216), (712233, 4335092), (712271, 4334964),
              (712354, 4334857), (712437, 4334757), (712514, 4334654), (712584, 4334550), (712654, 4334447), (712721, 4334335), (712753, 4334180)]
STR0 = (712753.0, 4334180.0)
straight = [(STR0[0] + (FC - STR0[0]) * f, STR0[1] + (NTN - STR0[1]) * f) for f in np.linspace(0, 1, 12)]
CN = smooth(north_ctrl + straight[1:], it=5)
CN = cut_at_N(CN, NTN) + [(FC, NTN)] if CN[-1][1] > NTN else CN
S_NORTH = 5420.0
_cn0 = Point(CN[0]); _s0 = C.project(_cn0)
_north = [C.interpolate(s).coords[0] for s in np.arange(S_NORTH, _s0 + 60, -40.0)]    # KMZ line every 40 m, Ludlow to 60 m short of the tip
_north = chaikin(_north, 5)                      # the KMZ polyline has a corner at s 4,550-4,650; smoothed (about 300 m radius)
_nt = [tuple(p) for p in _north] + [tuple(p) for p in CN]
NT = smooth(_nt, it=4, step=2.0)                 # blends the step at the tip

# ---------------------------------------------------------------- 2026-10-15 (Ben): straight between Ethan and Brashears, centred between New streets J1 and J2
# J1 and J2 as Ben extended them on the page (deck/layout, 15 October). The viaduct between its outer tracks (Transvalley -22.5 to ORR E
# +45.0 east of NT) is centred on the line midway between the two streets, so NT runs 11.25 m west of that midline, straight from
# Ethan's south edge to Brashears' north edge; cubic curves (tangent at both ends) join the old line at Camp Washington's north
# platform end (s 3,168) and at s 4,950 on the descent to Ludlow.
J1 = ((712237.5, 4334123.0), (712365.1, 4336295.7)); J2 = ((712146.0, 4334271.7), (712274.4, 4336454.5))
def _xat(L, y): (x0, y0), (x1, y1) = L; return x0 + (x1 - x0) * (y - y0) / (y1 - y0)
_ux = ((J1[1][0] - J1[0][0]) / (J1[1][1] - J1[0][1]) + (J2[1][0] - J2[0][0]) / (J2[1][1] - J2[0][1])) / 2
J_BEAR = math.degrees(math.atan(_ux))                       # 3.36 degrees east of north
_U = np.array([math.sin(math.radians(J_BEAR)), math.cos(math.radians(J_BEAR))]); _EJ = np.array([_U[1], -_U[0]])
J_GAP = (_xat(J1, 4335600) - _xat(J2, 4335600)) * _U[1]   # perpendicular distance between the two centre lines
C_OFF = (-22.5 + 45.0) / 2                                  # viaduct centre, east of NT
def j_mid(y): return np.array([(_xat(J1, y) + _xat(J2, y)) / 2, y])
Y_ETHAN_S, Y_BRASH_N = 4335248.0, 4336099.3                 # Ethan's south edge, Brashears' north edge (at the trunk)
S_JS, S_JN = 3168.0, 4950.0                                 # joins to the old line
_P0 = np.array(NT); _S0 = np.array([C.project(Point(p)) for p in NT])
for _i in range(1, len(_S0)): _S0[_i] = min(_S0[_i], _S0[_i - 1])
def _old(s):
    i = int(np.argmin(np.abs(_S0 - s))); a = _P0[max(i - 3, 0)]; b = _P0[min(i + 3, len(_P0) - 1)]; t = a - b; return _P0[i], t / np.hypot(*t)   # point, tangent pointing north
A_S = j_mid(Y_ETHAN_S) - C_OFF * _EJ; A_N = j_mid(Y_BRASH_N) - C_OFF * _EJ
def _bez(p0, t0, p3, t3, a, b, n):
    q1, q2 = p0 + t0 * a, p3 - t3 * b; u = np.linspace(0, 1, n)[:, None]
    return (1 - u) ** 3 * p0 + 3 * (1 - u) ** 2 * u * q1 + 3 * (1 - u) * u ** 2 * q2 + u ** 3 * p3
def _minr(c):
    c = np.asarray(c); d1 = np.gradient(c, axis=0); d2 = np.gradient(d1, axis=0)
    k = np.abs(d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) / np.hypot(d1[:, 0], d1[:, 1]) ** 3; return 1 / max(k.max(), 1e-12)
def _best_bez(p0, t0, p3, t3):   # handle lengths that give the largest least radius
    L = np.hypot(*(p3 - p0)); best = None
    for fa in np.linspace(0.2, 0.6, 21):
        for fb in np.linspace(0.2, 0.6, 21):
            c = _bez(p0, t0, p3, t3, fa * L, fb * L, 400); r = _minr(c)
            if best is None or r > best[0]: best = (r, fa, fb, c)
    return best
_ps, _ts = _old(S_JS); _pn, _tn0 = _old(S_JN)
_RS, _, _, _cs = _best_bez(_ps, _ts, A_S, _U)               # south -> north: Camp Washington platform end to Ethan
_RN, _, _, _cn = _best_bez(A_N, _U, _pn, _tn0)              # Brashears to the old line
_straight = [A_S + (A_N - A_S) * f for f in np.linspace(0, 1, int(np.hypot(*(A_N - A_S)) / 2) + 1)]
_mid = list(_cs) + _straight[1:] + list(_cn)[1:]            # south -> north
NT = [tuple(p) for p, s in zip(_P0, _S0) if s > S_JN] + [tuple(p) for p in _mid[::-1]] + [tuple(p) for p, s in zip(_P0, _S0) if s < S_JS]
NT = resample(NT, 2.0)
R_SOUTH, R_NORTH = _RS, _RN
NTL = LineString(NT)
_P = np.array(NT); _t = np.gradient(_P, axis=0); _t /= np.hypot(_t[:, 0], _t[:, 1])[:, None]
for _ in range(4): _t[1:-1] = (_t[:-2] + 2 * _t[1:-1] + _t[2:]) / 4
_t /= np.hypot(_t[:, 0], _t[:, 1])[:, None]
_tn = -_t                                        # tangent pointing north
_E = np.c_[_tn[:, 1], -_tn[:, 0]]                # east normal
_S = np.array([C.project(Point(p)) for p in NT])
for i in range(1, len(_S)): _S[i] = min(_S[i], _S[i - 1])        # NT runs north -> south: s non-increasing
_in = int(np.argmax(_S <= S_JN)); _is = int(len(_S) - 1 - np.argmax(_S[::-1] >= S_JS))   # 2026-10-15: chainage by length between the joins
_arc = np.r_[0, np.cumsum(np.hypot(*np.diff(_P[_in:_is + 1], axis=0).T))]
_S[_in:_is + 1] = _S[_in] - (_S[_in] - _S[_is]) * _arc / _arc[-1]
def nt_line(fn, s0=None, s1=None, south_first=False):
    """offset line of NT, fn(s) east offset at chainage s; between s0 and s1 (any order); returned north -> south"""
    lo, hi = (min(s0, s1), max(s0, s1)) if s0 is not None else (-1e9, 1e9)
    sel = (_S >= lo) & (_S <= hi)
    o = np.asarray(fn(_S[sel]), float) * np.ones(sel.sum())
    pts = _P[sel] + _E[sel] * o[:, None]
    c = [tuple(p) for p in pts]
    return c[::-1] if south_first else c
def nt_point(s, o):
    i = int(np.argmin(np.abs(_S - s))); return tuple(_P[i] + _E[i] * o)

# ---------------------------------------------------------------- the KMZ Indianapolis line, trunk -> west (APEx 'Greensburg-CUT TRIMET')
_L = json.load(open(SP + 'nv/lines.json'))
IK = LineString([o for o in _L if o['src'] == 'APEx' and o['name'] == 'Greensburg-CUT TRIMET'][0]['c'])
_a, _b = IK.project(Point(nt_point(3700, 0))), IK.project(Point(710300, 4337010))
IKW = substring(IK, _a, _b) if _a < _b else LineString(list(substring(IK, _b, _a).coords)[::-1])
IKW = LineString(smooth(list(IKW.coords), it=3, step=3.0))
L_C = IKW.project(Point(nt_point(S_C, 0)))       # curve start along IKW
def ik_right(d):
    """IKW offset d m to its right (east on the trunk, north once it heads west), trunk -> west"""
    g = IKW.offset_curve(-d, quad_segs=16, join_style='round'); c = list(g.coords)
    if Point(c[0]).distance(Point(IKW.coords[0])) > Point(c[-1]).distance(Point(IKW.coords[0])): c = c[::-1]
    return LineString(c)
def group_track(d, d_trunk=None, settle=220.0):
    """an Indianapolis + D track: NT offset (d_trunk, default d) up to the curve start, then IKW's right offset d
    (easing from d_trunk to d over 'settle' m of path). Returns (coords south -> west, s_or_L list, kind list)."""
    d_trunk = d if d_trunk is None else d_trunk
    trunk = nt_line(lambda s: np.full(np.shape(s), d_trunk), 2541.0, S_C - 60, south_first=True)
    W = ik_right(d)
    LW = W.length
    out = []
    for L in np.arange(max(0, L_C - 60), LW, 3.0):   # 2026-10-15: eases from the trunk (now east of the KMZ line) onto the KMZ curve
        w = float(blend(L - (L_C - 60), 0, settle + 60, 1, 0)); g = IKW.interpolate(L)
        p = np.array(W.interpolate(W.project(g)).coords[0]); q = np.array(nt_point(C.project(g), d_trunk)) if w > 0 else p
        out.append(tuple(q * w + p * (1 - w)))
    c = trunk + out
    return smooth(c, it=3, step=3.0)

# ---------------------------------------------------------------- track offsets (east of NT) by chainage
TV = (-22.5, -18.0); DN = (-11.25, -6.75, -2.25, 2.25); INDY = (6.75, 11.25)
S_OE0, S_OE1 = 4430.0, 4780.0                    # 2026-10-15: ORR E moves in north of Brashears, so the viaduct keeps its width from Ethan to Brashears
def orr_e(k):                                    # ORR E tracks: as built 18/22.5 at Marshall, 40.5/45.0 from Camp Washington
    a = (18.0, 22.5)[k]; b = (40.5, 45.0)[k]; c = (20.25, 24.75)[k]
    return lambda s: np.where(np.asarray(s) <= S_OE0, blend(s, S_MAR, S_CW0, a, b), blend(s, S_OE0, S_OE1, b, c))
def bd_track(k):                                 # B/D west (k=0, southbound) and east (k=1, northbound) tracks, Marshall side to the junction
    if k == 0: return lambda s: np.full(np.shape(s), 18.0)
    return lambda s: blend(s, S_CW0 - 80, S_CW0, 22.5, 32.5)
def b_track(k):                                  # B north of the junction
    if k == 0:
        return lambda s: np.select([np.asarray(s) <= 3450, np.asarray(s) <= 4044, np.asarray(s) <= 4248],
                                   [blend(s, S_JCT, 3450, 18.0, 22.5), blend(s, 3944, 4044, 22.5, 18.0), 18.0], blend(s, 4248, 4600, 18.0, 9.0))
    return lambda s: np.select([np.asarray(s) <= 3450, np.asarray(s) <= 4044, np.asarray(s) <= 4248],
                               [blend(s, S_JCT, 3450, 32.5, 27.0), blend(s, 3944, 4044, 27.0, 32.5), 32.5], blend(s, 4248, 4600, 32.5, 13.5))
D_SB_TRUNK = 15.75; D_NB_TRUNK = 33.75

# ---------------------------------------------------------------- B/D south: from Straight's platform end to the ramp
BD_KMZ_NORTH = None                              # set by build_transit (the KMZ / bored B/D line), else C
def bd_south_centre(bd_line=None):
    """B/D centre line from Straight's north platform end (s 2,403) to s 2,758 (east of the APEx tracks), south -> north"""
    ref = bd_line if bd_line is not None else C
    out = []
    for s in np.arange(S_ST1, S_SEP + 0.1, 3.0):
        p = np.array(ref.interpolate(ref.project(C.interpolate(s))).coords[0]); q = np.array(nt_point(s, 20.25))
        w = float(blend(s, S_ST1, S_SEP, 0, 1)); out.append(tuple(p * (1 - w) + q * w))
    return smooth(out, it=2, step=3.0)
def chain(c): return [C.project(Point(p)) for p in c]
S_SCUT = 2460.0                                  # past Straight's north platform end and its 40 m taper
def _sth(ref, s0=S_SCUT, s1=S_SEP):
    out = []
    for s in np.arange(s0, s1 + 0.1, 3.0):
        p = np.array(ref.interpolate(ref.project(C.interpolate(s))).coords[0]); q = np.array(nt_point(s, 20.25))
        w = float(blend(s, s0, s1, 0, 1)); out.append(tuple(p * (1 - w) + q * w))
    return out
def tri_centre(ref=None):
    """TRI B/D (south of the junction) then B centre line, s 2,460 -> 5,300, south -> north; returns (coords, z list)"""
    ref = C if ref is None else ref
    def cen(s):
        s = np.asarray(s, float)
        return np.where(s < S_JCT, (18.0 + np.asarray(bd_track(1)(s))) / 2, (np.asarray(b_track(0)(s)) + np.asarray(b_track(1)(s))) / 2)
    c = _sth(ref) + nt_line(cen, S_SEP, 5300.0, south_first=True)[1:]
    c = smooth(c, it=2, step=3.0)
    z = [bd_z(s) if s < S_JCT else b_z(s) for s in chain(c)]
    return c, z
def bd_tracks(s0, s1, ref=None):
    """the two B/D tracks between chainages s0 < s1 (both south of the junction), south -> north"""
    ref = C if ref is None else ref
    sth = smooth(_sth(ref), it=2, step=3.0)
    out = []
    for k, d in ((0, -2.25), (1, 2.25)):
        g = LineString(sth).offset_curve(-d, quad_segs=8)            # south -> north: right side (east) is negative distance
        cc = list(g.coords); cc = cc if Point(cc[0]).distance(Point(sth[0])) < Point(cc[-1]).distance(Point(sth[0])) else cc[::-1]
        c = cc + nt_line(bd_track(k), S_SEP, S_JCT, south_first=True)[1:]
        cs = chain(c); out.append([q for q, s in zip(c, cs) if s0 <= s <= s1])
    return out
def d_centre():
    """TRI D centre line (with the Indianapolis pair) from the junction west to the edge of the plan; (coords, z list)"""
    g = group_track(18.0)
    keep = [q for q in g if C.project(Point(q)) >= 3400.0 or NTL.distance(Point(q)) > 60]
    pre = nt_line(lambda s: blend(s, S_JCT, 3400.0, 25.25, 18.0), S_JCT, 3400.0, south_first=True)
    c = smooth(pre + keep, it=2, step=3.0)
    L = LineString(c); i_c = int(np.argmin([Point(q).distance(Point(nt_point(S_C, 18.0))) for q in c])); Lc = L.project(Point(c[i_c]))
    z = []
    for i, q in enumerate(c):
        if i <= i_c: z.append(sh_z(C.project(Point(q))))
        else: z.append(sh_zL(L.project(Point(q)) - Lc))
    return c, z

if __name__ == '__main__':
    print('NT length %.0f, s range %.0f-%.0f' % (NTL.length, _S.min(), _S.max()))
    print('band tip %.2f, Ludlow %.1f; Camp Washington %.2f-%.2f; dive bottom s %.0f; Arlington %.2f (s %.0f-%.0f), B back on band s %.0f'
          % (Z_TIP, Z_LUD, band(S_CW0), band(S_CW1), S_BOT, Z_AR, S_AR0, S_AR1, S_BOUT))
    print('IKW %.0f m, curve start at %.0f m along' % (IKW.length, L_C))
    g = group_track(20.25); print('group track 20.25:', len(g), g[0], g[-1])
