try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# North viaduct, RER on the west, compact (Ben, 25 October 2026, third round). Proposal geometry only (not installed).
# West to east, CUT to the B/D junction: ORR/TV west pair (viaduct level) | RER B/D | APEx Indy | APEx Dayton | APEx Norwood | ORR/TV east pair.
# The north viaduct is one level; the west viaduct (Indy + D, R5 below) has two. Offsets + east of the trunk line, s = KMZ chainage.
import json, sys, numpy as np
from shapely.geometry import LineString, Point
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'nv'); sys.path.insert(0, _ws.CODE + 'trunk')
import geom27 as G
from frames import chaikin, resample

def bl(s, s0, s1, a, b):
    s = np.asarray(s, float); t = np.clip((s - s0) / (s1 - s0), 0, 1); return a + (b - a) * (1 - np.cos(np.pi * t)) / 2
def pw(s, segs, v0):
    s = np.asarray(s, float); out = np.full(s.shape, float(v0)); cur = float(v0)
    for s0, s1, v in segs: out = np.where(s >= s0, bl(s, s0, s1, cur, v), out); cur = float(v)
    return out

# ---------------------------------------------------------------- trunk frame: geom27 NT to s 4,950, the smoothed Ludlow line (7 m west at the parkway) to 6,850, KMZ line beyond
_Sa, _ia = np.unique(G._S[::-1], return_index=True); _Pa = G._P[::-1][_ia]
LUD = np.load(SP + 'trunk2/lud12.npy')                         # columns s, x, y: faired inside the Mill Creek / OH-75 band (s 4,950-7,300)
pts, ss = [], []
for s in np.arange(1000.0, 4950.0, 2.0): pts.append((np.interp(s, _Sa, _Pa[:, 0]), np.interp(s, _Sa, _Pa[:, 1]))); ss.append(s)
for s, x, y in LUD:
    if 4950.0 <= s <= 7290.0: pts.append((x, y)); ss.append(s)
for s in np.arange(7300.0, 8400.1, 2.0): pts.append(G.C.interpolate(s).coords[0]); ss.append(s)
class Frame:
    def __init__(self, P, S):
        self.P = np.asarray(P, float); self.s = np.asarray(S, float); self.L = LineString(self.P)
        t = np.gradient(self.P, axis=0); t /= np.hypot(t[:, 0], t[:, 1])[:, None]
        for _ in range(4): t[1:-1] = (t[:-2] + 2 * t[1:-1] + t[2:]) / 4
        t /= np.hypot(t[:, 0], t[:, 1])[:, None]; self.E = np.c_[t[:, 1], -t[:, 0]]
        self.d = np.r_[0, np.cumsum(np.hypot(*np.diff(self.P, axis=0).T))]
    def at(self, s, o=0.0):
        s = np.atleast_1d(np.asarray(s, float)); o = np.broadcast_to(np.asarray(o, float), s.shape)
        x = np.interp(s, self.s, self.P[:, 0]); y = np.interp(s, self.s, self.P[:, 1]); ex = np.interp(s, self.s, self.E[:, 0]); ey = np.interp(s, self.s, self.E[:, 1]); n = np.hypot(ex, ey)
        return np.c_[x + ex / n * o, y + ey / n * o]
    def proj(self, p): return float(np.interp(self.L.project(Point(p)), self.d, self.s))
TR = Frame(pts, ss)
def line(fn, s0, s1, step=2.0):
    s = np.arange(s0, s1, step); s = np.r_[s, s1]; return TR.at(s, fn(s))

# ---------------------------------------------------------------- the west viaduct: one constant-radius curve off the trunk onto the Indianapolis KMZ straight
IK = np.array(G.IKW.coords)
def _bear(v): return np.degrees(np.arctan2(v[0], v[1]))
_L = G.IKW
i_st = 1050.0                                                    # the KMZ line is straight about 1,000-1,300 m along
pS = np.array(_L.interpolate(i_st).coords[0]); uS = np.array(_L.interpolate(i_st + 5).coords[0]) - np.array(_L.interpolate(i_st - 5).coords[0]); uS /= np.hypot(*uS)
S_T = 3700.0; pT = TR.at(S_T)[0]; uT = TR.at(S_T + 5)[0] - TR.at(S_T - 5)[0]; uT /= np.hypot(*uT)
t_, v_ = np.linalg.solve(np.c_[uT, -uS], pS - pT); PI = pT + uT * t_
DEFL = np.arccos(np.clip(uT @ uS, -1, 1))
def dep_ref(R):
    T = R * np.tan(DEFL / 2); TC = PI - uT * T; CT = PI + uS * T
    nrm = np.array([-uT[1], uT[0]])                               # left turn: centre to the left (west)
    O = TC + nrm * R; a0 = np.arctan2(*(TC - O)[::-1]); a1 = np.arctan2(*(CT - O)[::-1]); da = (a1 - a0 + np.pi) % (2 * np.pi) - np.pi
    arc = np.array([O + R * np.array([np.cos(a0 + da * f), np.sin(a0 + da * f)]) for f in np.linspace(0, 1, int(R * abs(da) / 2) + 2)])
    s_tc = TR.proj(TC)
    # on along the tangent to the KMZ line's point at 1,050 m (where it is straight and has this bearing), then the KMZ line itself
    k = float((pS - CT) @ uS)
    straight = [CT + uS * x for x in np.arange(4.0, k, 4.0)] if k > 4 else []
    far = [np.asarray(q) for q in IK if _L.project(Point(q)) > i_st + 1.0]
    tail = np.array(straight + [pS] + far)
    return s_tc, arc, tail, TC, CT
R_DEP = 780.0                                                    # the KMZ curve is about 690-860 m; one radius
S_TC, ARC, TAIL, TC, CT = dep_ref(R_DEP)
DEP = np.vstack([TR.at(np.arange(3000.0, S_TC, 2.0)), ARC, TAIL])
def dep_left(d):
    """the departure reference offset d m to the left (west / south once it heads west)"""
    g = LineString(DEP).offset_curve(d, quad_segs=16, join_style='round'); c = np.asarray(g.coords)
    if np.hypot(*(c[0] - DEP[0])) > np.hypot(*(c[-1] - DEP[0])): c = c[::-1]
    return c

# ---------------------------------------------------------------- offsets (+ east); 4.5 m between neighbouring tracks, RER islands 14.4 m
S_J = 3200.0
S_ST0, S_ST1 = G.S_ST0, G.S_ST1
S_CW0, S_CW1 = G.S_CW0, G.S_CW1
S_AR0, S_AR1 = G.S_AR0, G.S_AR1
S_NS0, S_NS1 = G.S_NSP1 - 204.2, G.S_NSP1
S_MI = 7677.0; S_MI0, S_MI1 = S_MI - 102.1, S_MI + 102.1
TP = 300.0                                                  # outer-pair bow round an island: one smooth S each side
def o_w(k):    # ORR/TV west pair: compact beside Indy, out of B/D's way before Straight, in after Arlington, bowing round the B islands
    a = (-22.5, -18.0)[k]; c0 = (-20.25, -15.75)[k]; out = (-39.15, -34.65)[k]; isl = -9.9
    return lambda s: pw(s, [(1100, 1500, c0), (1600, 2100, out), (4300, 4950, c0), (S_NS0 - TP, S_NS0, c0 + isl), (S_NS1, S_NS1 + TP, c0),
                           (S_MI0 - TP, S_MI0, c0 + isl), (S_MI1, S_MI1 + TP, c0)], a)
def o_e(k): a = (18.0, 22.5)[k]; b = (15.75, 20.25)[k]; return lambda s: pw(s, [(1100, 1500, b)], a)
APX = {'Indy': (-11.25, -6.75), 'Dayton': (-2.25, 2.25), 'Norwood': (6.75, 11.25)}
S_BX = 2150.0                                               # B/D twin bores parallel to the trunk from here
def o_b(k):    # B north of the B/D bores (s >= S_BX): NB inner, SB outer
    if k == 1: return lambda s: pw(s, [(S_DNB, S_DNB + 200, -25.65), (S_AR0 - TP, S_AR0, -15.75), (4300, 4950, -6.75)], -15.75)
    return lambda s: pw(s, [(4300, 4950, -11.25), (S_NS0 - TP, S_NS0, -21.15), (S_NS1, S_NS1 + TP, -11.25), (S_MI0 - TP, S_MI0, -21.15), (S_MI1, S_MI1 + TP, -11.25)], -30.15)
def o_d(k):    # D from the junction: southbound turns in over northbound B (which turns out under it at s 3,500-3,700), northbound straight on
    if k == 1: return lambda s: np.full(np.shape(s), -15.75)
    return lambda s: pw(s, [(S_J, S_J + 250, -20.25)], -30.15)
S_DNB = 3500.0                                              # where northbound D and B part (D southbound 7 m up there by s 3,480)
D_LEFT = (20.25, 15.75); INDY_LEFT = (11.25, 6.75)
# ---------------------------------------------------------------- levels
G_UP = 0.025
def d_z(s): return min(G.Z_TOP, G.band(S_J) + G_UP * (float(s) - S_J))
def indy_z(s): return G.sh_z(float(s))

# B/D twin bores from Western's north platform end (s 1,435; tracks -64.2 / -78.6) to parallel at S_BX, one smooth curve
_C90 = json.load(open(SP + 'deckpage/context_v124.json'))
def bore(k):
    o0 = (-78.6, -64.2)[k]; o1 = (-30.15, -15.75)[k]
    p0 = TR.at(1435.0, o0)[0]; p1 = TR.at(S_BX, o1)[0]
    # leaving Western on the old bores' bearing (4.8 degrees off the trunk), arriving parallel
    u1 = TR.at(S_BX + 5, o1)[0] - TR.at(S_BX - 5, o1)[0]; u1 /= np.hypot(*u1)
    ut = TR.at(1440, 0)[0] - TR.at(1430, 0)[0]; ut /= np.hypot(*ut); nt = np.array([ut[1], -ut[0]])
    ang = np.radians(4.8); u0 = ut * np.cos(ang) + nt * np.sin(ang)
    best = None; Lb = np.hypot(*(p1 - p0))
    for fa in np.linspace(0.2, 0.6, 17):
        for fb in np.linspace(0.2, 0.6, 17):
            q1, q2 = p0 + u0 * fa * Lb, p1 - u1 * fb * Lb; uu = np.linspace(0, 1, 400)[:, None]
            c = (1 - uu) ** 3 * p0 + 3 * (1 - uu) ** 2 * uu * q1 + 3 * (1 - uu) * uu ** 2 * q2 + uu ** 3 * p1
            d1 = np.gradient(c, axis=0); d2 = np.gradient(d1, axis=0); kk = np.abs(d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) / np.hypot(d1[:, 0], d1[:, 1]) ** 3
            r = 1 / kk.max()
            if best is None or r > best[0]: best = (r, c)
    return best
def build():
    L = {}
    for k in (0, 1):
        L[f'ORR/TV west {k+1}'] = dict(c=line(o_w(k), 1100, 8400), kind='orr', lvl='viaduct')
        L[f'ORR/TV east {k+1}'] = dict(c=line(o_e(k), 1100, 8400), kind='orr', lvl='viaduct')
        for nm in ('Dayton', 'Norwood'):
            o = APX[nm][k]; L[f'APEx {nm} {k+1}'] = dict(c=line(lambda s, o=o: np.full(np.shape(s), o), 1100, 8400), kind='apex', lvl='viaduct')
        o = APX['Indy'][k]; tr = line(lambda s, o=o: np.full(np.shape(s), o), 1100, S_TC); cv = dep_left(INDY_LEFT[k])
        cv = cv[[TR.proj(q) > S_TC or LineString(TR.P).distance(Point(q)) > 30 for q in cv]]
        L[f'APEx Indy {k+1}'] = dict(c=np.vstack([tr, cv]), kind='indy', lvl='upper from s 3,644')
        r_b, cb = bore(k)
        L[f'RER B {"NB" if k else "SB"}'] = dict(c=np.vstack([cb, line(o_b(k), S_BX + 2, 8400)]), kind='rer', lvl='bore to s 2,199, Straight and box to s 2,758, then viaduct', r_bore=r_b)
        tr = line(o_d(k), S_J if k == 0 else S_DNB, S_TC); cv = dep_left(D_LEFT[k])
        cv = cv[[TR.proj(q) > S_TC or LineString(TR.P).distance(Point(q)) > 30 for q in cv]]
        L[f'RER D {"NB" if k else "SB"}'] = dict(c=np.vstack([tr, cv]), kind='rerd', lvl='climbing from s 3,200, upper level')
    return L
if __name__ == '__main__':
    L = build()
    print('departure curve R', R_DEP, 'TC at s', round(S_TC), 'deflection %.1f deg' % np.degrees(DEFL))
    for k, v in L.items(): print(k, len(v['c']), np.round(v['c'][0]), np.round(v['c'][-1]))
