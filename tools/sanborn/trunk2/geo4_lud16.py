try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# North viaduct, compact layout (Ben, 25 October 2026, third round). Proposal geometry only; nothing here is installed.
# West to east from CUT to the junction: ORR/TV west pair | RER B/D | APEx Indy | Dayton | Norwood | ORR/TV east pair.
# Offsets are + east of the trunk; s = KMZ chainage from CUT. 4.5 m between neighbouring tracks; RER islands 14.4 m between track centres.
import json, sys, numpy as np
from shapely.geometry import LineString, Point
from scipy.ndimage import gaussian_filter1d
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'nv')
import geom27 as G

def bl(s, s0, s1, a, b):
    s = np.asarray(s, float); t = np.clip((s - s0) / (s1 - s0), 0, 1); return a + (b - a) * (1 - np.cos(np.pi * t)) / 2
def pw(s, segs, v0):
    s = np.asarray(s, float); out = np.full(s.shape, float(v0)); cur = float(v0)
    for s0, s1, v in segs: out = np.where(s >= s0, bl(s, s0, s1, cur, v), out); cur = float(v)
    return out

# ---------------------------------------------------------------- trunk: today's line to s 4,650; the faired Ludlow line (lud14) to 7,650; the KMZ line beyond
_Sa, _ia = np.unique(G._S[::-1], return_index=True); _Pa = G._P[::-1][_ia]
LUD = np.load(SP + 'trunk2/lud16.npy')                     # s, x, y, offset: faired in the constant-width corridor, Mill Creek open only north-east of Albone, clear of the culvert
pts, ss = [], []
for s in np.arange(1000.0, 4650.0, 2.0): pts.append((np.interp(s, _Sa, _Pa[:, 0]), np.interp(s, _Sa, _Pa[:, 1]))); ss.append(s)
_lx = np.interp(np.arange(4650.0, 7650.0, 2.0), LUD[:, 0], LUD[:, 1]); _ly = np.interp(np.arange(4650.0, 7650.0, 2.0), LUD[:, 0], LUD[:, 2])
pts += list(zip(_lx, _ly)); ss += list(np.arange(4650.0, 7650.0, 2.0))
for s in np.arange(7650.0, 8600.1, 2.0): pts.append(G.C.interpolate(s).coords[0]); ss.append(s)
_P = np.array(pts); _ss = np.array(ss)
_Psm = np.c_[gaussian_filter1d(_P[:, 0], 4, mode='nearest'), gaussian_filter1d(_P[:, 1], 4, mode='nearest')]   # sub-metre: takes the corners out of the KMZ polyline
_Psm[_ss < 7600] = _P[_ss < 7600]; _Psm[_ss > 8500] = _P[_ss > 8500]
DEV = np.hypot(*(_Psm - _P).T).max()
class Frame:
    def __init__(self, P, S):
        self.P = np.asarray(P, float); self.s = np.asarray(S, float); self.L = LineString(self.P)
        t = np.gradient(self.P, axis=0); t = np.c_[gaussian_filter1d(t[:, 0], 6, mode='nearest'), gaussian_filter1d(t[:, 1], 6, mode='nearest')]
        t /= np.hypot(t[:, 0], t[:, 1])[:, None]; self.E = np.c_[t[:, 1], -t[:, 0]]; self.T = t
        self.d = np.r_[0, np.cumsum(np.hypot(*np.diff(self.P, axis=0).T))]
    def at(self, s, o=0.0):
        s = np.atleast_1d(np.asarray(s, float)); o = np.broadcast_to(np.asarray(o, float), s.shape)
        x = np.interp(s, self.s, self.P[:, 0]); y = np.interp(s, self.s, self.P[:, 1]); ex = np.interp(s, self.s, self.E[:, 0]); ey = np.interp(s, self.s, self.E[:, 1]); n = np.hypot(ex, ey)
        return np.c_[x + ex / n * o, y + ey / n * o]
    def tan(self, s):
        tx = np.interp(s, self.s, self.T[:, 0]); ty = np.interp(s, self.s, self.T[:, 1]); v = np.array([tx, ty]); return v / np.hypot(*v)
    def proj(self, p): return float(np.interp(self.L.project(Point(p)), self.d, self.s))
TR = Frame(_Psm, _ss)
def line(fn, s0, s1, step=2.0):
    s = np.arange(s0, s1, step); s = np.r_[s, s1]; return TR.at(s, fn(s))

# ---------------------------------------------------------------- the west viaduct: one 780 m curve off the trunk onto the Indianapolis KMZ straight
IK = np.array(G.IKW.coords); _L = G.IKW
i_st = 1050.0
pS = np.array(_L.interpolate(i_st).coords[0]); uS = np.array(_L.interpolate(i_st + 5).coords[0]) - np.array(_L.interpolate(i_st - 5).coords[0]); uS /= np.hypot(*uS)
S_T = 3700.0; pT = TR.at(S_T)[0]; uT = TR.tan(S_T)
t_, v_ = np.linalg.solve(np.c_[uT, -uS], pS - pT); PI = pT + uT * t_
DEFL = np.arccos(np.clip(uT @ uS, -1, 1))
R_DEP = 780.0
T_ = R_DEP * np.tan(DEFL / 2); TC = PI - uT * T_; CT = PI + uS * T_
NL = np.array([-uT[1], uT[0]])                                  # left of northbound (towards the curve centre)
O = TC + NL * R_DEP
S_TC = TR.proj(TC)
def _arc(Oc, R, p0, p1, step=2.0):
    a0 = np.arctan2(*(p0 - Oc)[::-1]); a1 = np.arctan2(*(p1 - Oc)[::-1]); da = (a1 - a0 + np.pi) % (2 * np.pi) - np.pi
    n = max(2, int(R * abs(da) / step) + 1); f = np.linspace(0, 1, n)
    return np.c_[Oc[0] + R * np.cos(a0 + da * f), Oc[1] + R * np.sin(a0 + da * f)]
_far = [np.asarray(q) for q in IK if _L.project(Point(q)) > i_st + 1.0]
_REF_TAIL = np.array([CT + uS * x for x in np.arange(0.0, float((pS - CT) @ uS), 4.0)] + [pS] + _far)
def dep_path(d):
    """the departure path d m left of the reference: arc R_DEP - d about O, then the IKW straight and line offset properly"""
    a = TC + NL * d; b = CT + np.array([-uS[1], uS[0]]) * d
    arc = _arc(O, R_DEP - d, a, b)
    g = LineString(_REF_TAIL).offset_curve(d, quad_segs=32, join_style='round'); t = np.asarray(g.coords)
    if np.hypot(*(t[0] - b)) > np.hypot(*(t[-1] - b)): t = t[::-1]
    return arc, t[1:]
def merge(o_line, d, r):
    """a track running parallel to the trunk at offset o_line (west of the deck path d m left), joining that path on the curve:
       straight on, then one arc of radius r tangent to the straight and to the deck curve (no reverse curve)."""
    R_T = R_DEP - d
    # line: points TC + uT*x + NL*(-o_line) ... in the local frame the trunk tangent line at TC; left offset = -o_line
    h = -o_line                                                  # left offset of the line
    # centre of the joining circle: C = TC + uT*x + NL*(h + r); |C - O| = R_T - r  with O = TC + NL*R_DEP
    dy = (h + r) - R_DEP
    x = np.sqrt(max((R_T - r) ** 2 - dy ** 2, 0.0))
    Cc = TC + uT * x + NL * (h + r)
    p_on = TC + uT * x + NL * h                                  # where the straight ends
    u = (Cc - O) / np.hypot(*(Cc - O)); p_join = O + u * R_T     # where it meets the deck curve
    arc = _arc(Cc, r, p_on, p_join)
    darc, dtail = dep_path(d)
    i = int(np.argmin(np.hypot(*(darc - p_join).T)))
    return TR.proj(p_on), arc, np.vstack([darc[i + 1:], dtail]), p_join

# ---------------------------------------------------------------- offsets
S_ST0, S_ST1 = G.S_ST0, G.S_ST1; S_CW0, S_CW1 = G.S_CW0, G.S_CW1; S_AR0, S_AR1 = G.S_AR0, G.S_AR1
S_NS0, S_NS1 = G.S_NSP1 - 204.2, G.S_NSP1
S_MI = 7677.0; S_MI0, S_MI1 = S_MI - 102.1, S_MI + 102.1
TP_N, TP_M = 400.0, 300.0                                       # length of each smooth S where an outer pair steps round the Northside / Mitchell islands
ISL = 14.4
W_C = (-20.25, -15.75); W_OUT = (-39.15, -34.65)
def arcfit(o1, o2, s1ref, s2):
    """one constant-radius curve from the trunk-parallel line at o1 (tangent line at s1ref) to the trunk-parallel path at o2, tangent at s2"""
    p1 = TR.at(s1ref, o1)[0]; u1 = TR.tan(s1ref); p2 = TR.at(s2, o2)[0]; u2 = TR.tan(s2)
    t, v = np.linalg.solve(np.c_[u1, -u2], p2 - p1); PIa = p1 + u1 * t
    th = np.arccos(np.clip(u1 @ u2, -1, 1)); T = float(np.hypot(*(p2 - PIa))); R = T / np.tan(th / 2)
    a1 = PIa - u1 * T; cr = u1[0] * u2[1] - u1[1] * u2[0]
    nl = np.array([-u1[1], u1[0]]) if cr > 0 else np.array([u1[1], -u1[0]]); Oc = a1 + nl * R
    return R, TR.proj(a1), _arc(Oc, R, a1, p2)
S_WOUT = 2550.0                    # west pair out (B 12.9 m below in the box): one curve from tight against Indy, no overshoot (the largest single radius that ends here)
S_LA, S_LB = 4200.0, 4900.0       # the trunk is straight through Arlington (to ~4,400) and again ~4,880-5,100
S_AN1 = S_LB                       # offsets switch to the constant-width positions here (the tracks are on the second straight by then)
def an_curve(o1, o2, R_ref=None):
    """after Arlington (Ben, 25 October 2026): one curve between the two straights, the widest that keeps B NB 4.5 m clear of Dayton.
       Concentric for W and B: radius = R_BNB + (B NB offset - this offset)."""
    def geo(o1, o2):
        p1 = TR.at(S_LA, o1)[0]; u1 = TR.tan(S_LA); p2 = TR.at(S_LB, o2)[0]; u2 = TR.tan(S_LB)
        t, v = np.linalg.solve(np.c_[u1, -u2], p2 - p1); return p1, u1, p2, u2, p1 + u1 * t, np.arccos(np.clip(u1 @ u2, -1, 1))
    R0 = R_ref if R_ref is not None else AN_R
    R = R0 + (B_NB - o1)
    p1, u1, p2, u2, PIa, th = geo(o1, o2); T = R * np.tan(th / 2); a = PIa - u1 * T; b = PIa + u2 * T
    nr = np.array([u1[1], -u1[0]]); Oc = a + nr * R                 # right-hand curve
    st1 = np.array([p1 + u1 * x for x in np.arange(0.0, float((a - p1) @ u1), 2.0)])
    st2 = np.array([b + u2 * x for x in np.arange(2.0, float((p2 - b) @ u2), 2.0)] + [p2])
    return R, TR.proj(a), TR.proj(b), np.vstack([st1, _arc(Oc, R, a, b), st2])
def _an_max():
    lo, hi = 500.0, 1200.0
    for _ in range(30):
        m = (lo + hi) / 2; R, sa, sb, c = an_curve(B_NB, B_N[1], m); offs = []
        for q in c[::5]:
            sv = TR.proj(q); p = TR.at(sv)[0]; e = TR.at(sv, 1.0)[0] - p; offs.append((q - p) @ e)
        lo, hi = (m, hi) if max(offs) <= -6.74 and sa >= S_AR1 else (lo, m)
    return lo
W_N = (-30.15, -25.65); B_N = (-21.15, -6.75)
def o_w(k):
    c0 = W_C[k]; a = (-22.5, -18.0)[k]
    return lambda s: pw(s, [(1100, 1500, c0), (S_WOUT - 1, S_WOUT, W_OUT[k]), (S_AN1 - 1, S_AN1, W_N[k]), (S_NS1, S_NS1 + TP_N, c0),
                           (S_MI0 - TP_M, S_MI0, c0 - 9.9), (S_MI1, S_MI1 + TP_M, c0)], a)
def o_e(k): return lambda s: pw(s, [(1100, 1500, (15.75, 20.25)[k])], (18.0, 22.5)[k])
APX = {'Indy': (-11.25, -6.75), 'Dayton': (-2.25, 2.25), 'Norwood': (6.75, 11.25)}
B_SB, B_NB = -30.15, -15.75                                     # Straight to Arlington: island spacing; D runs between them from the junction
def o_b(k):
    if k == 1: return lambda s: pw(s, [(S_AN1 - 1, S_AN1, B_N[1])], B_NB)
    return lambda s: pw(s, [(S_AN1 - 1, S_AN1, B_N[0]), (S_NS1, S_NS1 + TP_N, -11.25), (S_MI0 - TP_M, S_MI0, -11.25 - 9.9), (S_MI1, S_MI1 + TP_M, -11.25)], B_SB)
S_J0, S_J1 = 3200.0, 3420.0                                     # D leaves B: both D tracks turn in between the B tracks (no crossing)
D_TR = (B_SB + 4.5, B_SB + 9.0)                                 # -25.65, -21.15
def o_d(k): return lambda s: pw(s, [(S_J0, S_J1, D_TR[k])], (B_SB, B_NB)[k])
D_DECK = (20.25, 15.75); INDY_DECK = (11.25, 6.75); R5_DECK = (15.75, 11.25)   # left of the deck reference
R_DM = 700.0; R_R5 = 600.0                                      # joining radii (D onto the deck curve; R5 under the deck)

# B/D twin bores: off Ben's B/D straight at Western's north platform end, one curve to parallel at S_BX
_BD = json.load(open(SP + 'trunk/db_restore.json'))['transit']['R-BD-712316-4334957']['c']
BD_A, BD_B = np.array(_BD[11]), np.array(_BD[10])              # the long straight past Western (south end, north end)
uBD = (BD_B - BD_A) / np.hypot(*(BD_B - BD_A)); nBD = np.array([uBD[1], -uBD[0]])   # + east of the straight
S_BX = 2150.0
def bore(k):
    o_tr = (-7.2, 7.2)[k]; o_end = (B_SB, B_NB)[k]
    a = BD_A + nBD * o_tr
    p1 = TR.at(S_BX, o_end)[0]; u1 = TR.tan(S_BX)
    t_, v_ = np.linalg.solve(np.c_[uBD, -u1], p1 - a); PIb = a + uBD * t_
    dfl = np.arccos(np.clip(uBD @ u1, -1, 1)); Tb = float(v_) * -1 if v_ < 0 else float(v_)
    Tb = float(np.hypot(*(p1 - PIb))); R = Tb / np.tan(dfl / 2)
    tc = PIb - uBD * Tb; nrm = np.array([uBD[1], -uBD[0]]) if (uBD[0] * u1[1] - uBD[1] * u1[0]) < 0 else np.array([-uBD[1], uBD[0]])
    Oc = tc + nrm * R
    st = np.array([a + uBD * x for x in np.arange(0.0, (tc - a) @ uBD, 4.0)])
    st = st[[TR.proj(q) >= 1300 for q in st]]
    return R, np.vstack([st, _arc(Oc, R, tc, p1)]), TR.proj(tc)

AN_R = None
def build():
    global AN_R
    if AN_R is None: AN_R = _an_max()
    L = {}
    for k in (0, 1):
        Rw, s_wtc, arc = arcfit(W_C[k], W_OUT[k], 2000.0, S_WOUT)
        Rn, s_na, s_nb, arcn = an_curve(W_OUT[k], W_N[k])
        L[f'ORR/TV west {k+1}'] = dict(c=np.vstack([line(o_w(k), 1100, s_wtc - 2), arc, line(o_w(k), S_WOUT + 2, S_LA - 2), arcn, line(o_w(k), S_LB + 2, 8400)]),
                                       kind='orr', r_step=Rw, s_step=s_wtc, r_an=Rn, s_an=(s_na, s_nb))
        L[f'ORR/TV east {k+1}'] = dict(c=line(o_e(k), 1100, 8400), kind='orr')
        for nm in ('Dayton', 'Norwood'):
            o = APX[nm][k]; L[f'APEx {nm} {k+1}'] = dict(c=line(lambda s, o=o: np.full(np.shape(s), o), 1100, 8400), kind='apex')
        o = APX['Indy'][k]; arc, tail = dep_path(INDY_DECK[k])
        L[f'APEx Indy {k+1}'] = dict(c=np.vstack([line(lambda s, o=o: np.full(np.shape(s), o), 1100, S_TC - 2), arc, tail]), kind='indy')
        nb = 'NB' if k else 'SB'
        Rb, cb, s_btc = bore(k)
        Rn, s_na, s_nb, arcn = an_curve((B_SB, B_NB)[k], B_N[k])
        L[f'RER B {nb}'] = dict(c=np.vstack([cb, line(o_b(k), S_BX + 2, S_LA - 2), arcn, line(o_b(k), S_LB + 2, 8400)]), kind='rer', r_bore=Rb, s_btc=s_btc, r_an=Rn, s_an=(s_na, s_nb))
        s_on, arc, tail, pj = merge(D_TR[k], D_DECK[k], R_DM - 4.5 * (1 - k))
        L[f'RER D {nb}'] = dict(c=np.vstack([line(o_d(k), S_J0, s_on - 2), arc, tail]), kind='rerd', s_on=s_on, join=TR.proj(pj))
        s_on, arc, tail, pj = merge(W_OUT[k], R5_DECK[k], R_R5 - 4.5 * (1 - k))
        L[f'R5 {k+1}'] = dict(c=np.vstack([TR.at(np.arange(s_on - 120, s_on - 1, 2.0), W_OUT[k]), arc, tail]), kind='r5', s_on=s_on, join=TR.proj(pj))
    return L
if __name__ == '__main__':
    L = build()
    print('frame smoothing max shift %.2f m' % DEV, ' deck curve TC s %.0f, deflection %.1f deg' % (S_TC, np.degrees(DEFL)))
    for k, v in L.items(): print(k, len(v['c']), {a: (round(b) if isinstance(b, float) else b) for a, b in v.items() if a not in ('c', 'kind')})
