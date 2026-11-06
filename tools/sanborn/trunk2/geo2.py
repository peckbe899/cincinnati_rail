try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# North viaduct, RER on the west (Ben, 25 October 2026, second round). Proposal geometry only (not installed).
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
LUD = np.load(SP + 'trunk2/lud_100.npy')                       # columns s, x, y (s 4,900-6,948)
pts, ss = [], []
for s in np.arange(1000.0, 4950.0, 2.0): pts.append((np.interp(s, _Sa, _Pa[:, 0]), np.interp(s, _Sa, _Pa[:, 1]))); ss.append(s)
for s, x, y in LUD:
    if 4950.0 <= s <= 6850.0: pts.append((x, y)); ss.append(s)
for s in np.arange(6852.0, 8400.1, 2.0): pts.append(G.C.interpolate(s).coords[0]); ss.append(s)
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

# ---------------------------------------------------------------- offsets (+ east)
S_J = 3200.0
S_CW0, S_CW1 = G.S_CW0, G.S_CW1
S_AR0, S_AR1 = G.S_AR0, G.S_AR1
S_NS0, S_NS1 = G.S_NSP1 - 204.2, G.S_NSP1
def o_w(k): a = (-22.5, -18.0)[k]; b = (-43.75, -39.25)[k]; c = (-34.75, -30.25)[k]; return lambda s: pw(s, [(2100, 2500, b), (4300, 4900, c)], a)
def o_e(k): return lambda s: np.full(np.shape(s), (18.0, 22.5)[k])
APX = {'Indy': (-11.25, -6.75), 'Dayton': (-2.25, 2.25), 'Norwood': (6.75, 11.25)}
def o_b(k):    # B: NB inner (east), SB outer; island spread kept from Camp Washington to past Arlington, then in by 9 m
    if k == 1: return lambda s: pw(s, [(2440, 2800, -18.0), (4300, 4900, -9.0)], 7.75)
    return lambda s: pw(s, [(2440, 2964, -32.5), (4300, 4900, -23.5)], 3.25)
def o_d(k):    # D from the junction: into the space between the B tracks, then straight to the curve
    if k == 1: return lambda s: pw(s, [(S_J, S_J + 180, -22.75)], -18.0)
    return lambda s: pw(s, [(S_J, S_J + 180, -27.25)], -32.5)
D_LEFT = (27.25, 22.75); INDY_LEFT = (11.25, 6.75)

# ---------------------------------------------------------------- levels
G_UP = 0.025
def d_z(s): return min(G.Z_TOP, G.band(S_J) + G_UP * (float(s) - S_J))
def indy_z(s): return G.sh_z(float(s))

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
        L[f'RER B {"NB" if k else "SB"}'] = dict(c=line(o_b(k), 2440, 8400), kind='rer', lvl='box to s 2,758, then viaduct')
        tr = line(o_d(k), S_J, S_TC); cv = dep_left(D_LEFT[k])
        cv = cv[[TR.proj(q) > S_TC or LineString(TR.P).distance(Point(q)) > 30 for q in cv]]
        L[f'RER D {"NB" if k else "SB"}'] = dict(c=np.vstack([tr, cv]), kind='rerd', lvl='climbing from s 3,200, upper level')
    return L
if __name__ == '__main__':
    L = build()
    print('departure curve R', R_DEP, 'TC at s', round(S_TC), 'deflection %.1f deg' % np.degrees(DEFL))
    for k, v in L.items(): print(k, len(v['c']), np.round(v['c'][0]), np.round(v['c'][-1]))
