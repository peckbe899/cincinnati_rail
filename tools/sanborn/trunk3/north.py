try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# North of Mitchell (Ben, 26 October 2026): the split without crossings and the rails out to the borders.
# West group (ORR X2 pair, RER B, APEx Dayton) curves left together onto the Southwest Chief straight; east group (APEx Norwood, ORR/TV shared
# pair) goes on along the Transcontinental to Norwood Central. Near Aloysius TV peels off the shared pair to the south and crosses over ORR and
# APEx at ground while they drop into the trench, landing north of APEx (Norwood Central west throat T10/T9, T7/T6, T4/T2).
# Offsets: + right of travel away from CUT. Norwood frame offsets (o_nw): + north.
import json, sys, numpy as np
from shapely.geometry import LineString, Point
from scipy.ndimage import gaussian_filter1d
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'trunk2'); sys.path.insert(0, _ws.CODE + 'trunk')
import geo4 as Q
import frames as FR
G = Q.G
def bl(s, s0, s1, a, b):
    s = np.asarray(s, float); t = np.clip((s - s0) / (s1 - s0), 0, 1); return a + (b - a) * (1 - np.cos(np.pi * t)) / 2
def pw(s, segs, v0):
    s = np.asarray(s, float); out = np.full(s.shape, float(v0)); cur = float(v0)
    for s0, s1, v in segs: out = np.where(s >= s0, bl(s, s0, s1, cur, v), out); cur = float(v)
    return out
def arc(Oc, R, p0, p1, step=1.0):
    a0 = np.arctan2(*(p0 - Oc)[::-1]); a1 = np.arctan2(*(p1 - Oc)[::-1]); da = (a1 - a0 + np.pi) % (2 * np.pi) - np.pi
    n = max(2, int(R * abs(da) / step) + 1); f = np.linspace(0, 1, n); return np.c_[Oc[0] + R * np.cos(a0 + da * f), Oc[1] + R * np.sin(a0 + da * f)]
def lnorm(u): return np.array([-u[1], u[0]])
def rnorm(u): return np.array([u[1], -u[0]])
def tangent_R(p, u, q, v, side):
    """radius of the curve that leaves line (p, u) at p and is tangent to line (q, v); side 'L' or 'R'"""
    n1 = lnorm(u) if side == 'L' else rnorm(u); n2 = lnorm(v) if side == 'L' else rnorm(v)
    R = float((p - q) @ n2) / (1 - float(n1 @ n2)); O = p + n1 * R; return R, O, O - n2 * R
class Frame:
    def __init__(self, P, s0):
        P = np.asarray(P, float); keep = np.r_[True, np.hypot(*np.diff(P, axis=0).T) > 1e-6]; P = P[keep]
        self.P = P; self.L = LineString(P); self.d = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]; self.s = s0 + self.d
        t = np.gradient(P, self.d, axis=0); t = np.c_[gaussian_filter1d(t[:, 0], 3, mode='nearest'), gaussian_filter1d(t[:, 1], 3, mode='nearest')]
        t /= np.hypot(t[:, 0], t[:, 1])[:, None]; self.T = t; self.E = np.c_[t[:, 1], -t[:, 0]]
    def at(self, s, o=0.0):
        s = np.atleast_1d(np.asarray(s, float)); o = np.broadcast_to(np.asarray(o, float), s.shape)
        x = np.interp(s, self.s, self.P[:, 0]); y = np.interp(s, self.s, self.P[:, 1]); ex = np.interp(s, self.s, self.E[:, 0]); ey = np.interp(s, self.s, self.E[:, 1]); n = np.hypot(ex, ey)
        return np.c_[x + ex / n * o, y + ey / n * o]
    def proj(self, p): return float(np.interp(self.L.project(Point(p)), self.d, self.s))
    def line(self, fn, s0, s1, step=2.0):
        ss = np.arange(s0, s1, step); ss = np.r_[ss, s1]; return self.at(ss, fn(ss))

T0 = json.load(open(SP + 'deckpage/tracks_v127.json'))
def kmz(n): return np.array([f for f in T0['features'] if f['properties'].get('name') == n][0]['geometry']['coordinates'])[:, :2]
S0 = 8080.0                                                  # end of the Mitchell step-outs: both groups leave the trunk straight here
p0 = Q.TR.at(S0)[0]; u0 = Q.TR.tan(S0)
# ------------------------------------------------------------- west group: one curve left onto the Southwest Chief straight
SWA, SWB = kmz('APEx Southwest Chief (1 of 2)')[::-1], kmz('APEx Southwest Chief (2 of 2)')[::-1]     # south -> north
SWM = np.array(FR._mid(SWA.tolist(), SWB.tolist(), n=6000)); SWL = LineString(SWM)
pS = np.array(SWL.interpolate(400).coords[0]); uS = np.array(SWL.interpolate(1400).coords[0]) - pS; uS /= np.hypot(*uS)
R_D, O_D, TD = tangent_R(p0, u0, pS, uS, 'L')
_arcD = arc(O_D, R_D, p0, TD)
# beyond the curve: the Southwest Chief straight, then the ORR APEx alignment (APX-4a, St Bernard-Middletown), which takes its own line
# through Lockland (Ben, 26 October); its polyline corners are rounded by corner cutting (Chaikin), the straights kept
ORR4A = np.load(SP + 'trunk3/orr4a.npy')                     # south -> north
_od = np.r_[0, np.cumsum(np.hypot(*np.diff(ORR4A, axis=0).T))]
_i13 = int(np.argmin(np.abs(_od - 1959.0)))
_Q = np.array(SWL.interpolate(SWL.project(Point(ORR4A[_i13]))).coords[0])
_st = np.array([TD + uS * x for x in np.arange(1.0, float((_Q - TD) @ uS), 1.0)])
_orr = FR.chaikin(np.vstack([_Q, ORR4A[_i13 + 1:]]), 6)
_orr = FR.resample(_orr, 1.0)
FD = Frame(np.vstack([_arcD, _st, _orr]), S0)
S_DT = S0 + R_D * np.arccos(np.clip(u0 @ uS, -1, 1))       # where the curve ends (Dayton centre)
C0 = json.load(open(SP + 'deckpage/context_v127.json'))
_st = {(s['name'], tuple(s['lines'])): s['p'] for s in C0['rer_stations']}
S_IV = FD.proj(_st[('Ivorydale', ('B',))]); LPL = 204.2; S_IV0, S_IV1 = S_IV - LPL / 2, S_IV + LPL / 2; TP = 300.0
S_EP = FD.proj(_st[('Elmwood Place', ('B',))]); S_EP0, S_EP1 = S_EP - LPL / 2, S_EP + LPL / 2
STEP = 9.9                                                   # island step-out, as at Mitchell
def o_dayton(k): return lambda s: np.full(np.shape(s), (-2.25, 2.25)[k])
def o_b(k):
    if k == 1: return lambda s: np.full(np.shape(s), -6.75)
    return lambda s: pw(s, [(S_IV0 - TP, S_IV0, -11.25 - STEP), (S_IV1, S_IV1 + TP, -11.25), (S_EP0 - TP, S_EP0, -11.25 - STEP), (S_EP1, S_EP1 + TP, -11.25)], -11.25)
def o_x2(k): c0 = (-20.25, -15.75)[k]; return lambda s: pw(s, [(S_IV0 - TP, S_IV0, c0 - STEP), (S_IV1, S_IV1 + TP, c0)], c0)
Y_WIN = 4339800.0                                            # plan window north edge (ORR X2 drawn to here, as in the 25 October layout)
def clip_y(c, y):
    c = np.asarray(c); i = int(np.argmax(c[:, 1] >= y))
    if c[i, 1] < y: return c
    a, b = c[i - 1], c[i]; t = (y - a[1]) / (b[1] - a[1]); return np.vstack([c[:i], a + (b - a) * t])
# ------------------------------------------------------------- east group: straight on, one curve right onto the Norwood axis
NO, NTV, NNV = FR.NO, FR.NTV, FR.NNV
S_NW = FR.S_NW                                               # Norwood Central west throat (Norwood frame s 4,150)
TA, TB = kmz('APEx Transcontinental Limited (1 of 2)'), kmz('APEx Transcontinental Limited (2 of 2)')
P70 = (TA[4:7] + TB[4:7]) / 2                                # the Transcontinental's middle straight (KMZ)
c70 = P70.mean(axis=0); _, _, vt = np.linalg.svd(P70 - c70); u70 = vt[0] * np.sign(vt[0] @ (P70[-1] - P70[0]))
def isect(p1, u1, p2, u2): t, v = np.linalg.solve(np.c_[u1, -u2], p2 - p1); return p1 + u1 * t, t
pN0 = p0 + rnorm(u0) * 9.0                                   # APEx Norwood centre on the trunk
PI1, t1 = isect(pN0, u0, c70, u70); PI2, _ = isect(c70, u70, NO, NTV)
d1 = np.arccos(u0 @ u70); d2 = np.arccos(u70 @ NTV); L12 = float(np.hypot(*(PI2 - PI1)))
R_N = L12 / (np.tan(d1 / 2) + np.tan(d2 / 2))               # one curve, tangent to the trunk line, the Transcontinental's middle straight and the axis
S_NC0 = S0 + t1 - R_N * np.tan(d1 / 2)                       # curve start (trunk chainage)
pNC0 = pN0 + u0 * (S_NC0 - S0)
_, O_N, TN = tangent_R(pNC0, u0, NO, NTV, 'R')
def nw_s(p): return FR.nw_so(p)[0]
_arcN = arc(O_N, R_N, pNC0, TN)
_axN = np.array([FR.nw_P(s) for s in np.arange(nw_s(TN) + 1.0, S_NW, 1.0)] + [FR.nw_P(S_NW)])
FWP = np.vstack([np.array([pN0 + u0 * x for x in np.arange(0.0, S_NC0 - S0, 1.0)]), _arcN, _axN])
FW = Frame(FWP, S0)
def fw_of_nw(snw): return FW.proj(FR.nw_P(snw))
S_NCE = nw_s(TN)                                             # curve end (Norwood frame s)
# ORR / TV shared pair: option A (8.25 m group gap taken inside the curve, own single curves) or B (compact; one S after the TV crossing)
def e_track_A(k):
    """ORR/TV shared track k: straight from the trunk at +15.75 / +20.25, one curve right onto the axis at o_nw -10.5 / -15 (T4 / T2)"""
    o_tr = (15.75, 20.25)[k]; o_nw = (-10.5, -15.0)[k]
    p = p0 + rnorm(u0) * o_tr + u0 * (S_NC0 - S0)
    R, O, Tt = tangent_R(p, u0, NO + NNV * o_nw, NTV, 'R')
    st = np.array([p0 + rnorm(u0) * o_tr + u0 * x for x in np.arange(0.0, S_NC0 - S0, 1.0)])
    return R, st, arc(O, R, p, Tt), nw_s(Tt)
# ------------------------------------------------------------- Norwood frame helpers (axis straight from S_NCE)
def NWL(fn, s0, s1, step=1.0):
    ss = np.arange(s0, s1, step); ss = np.r_[ss, s1]; return np.array([FR.nw_P(s, o) for s, o in zip(ss, fn(ss))])
# ------------------------------------------------------------- Transvalley peel and crossing (Norwood frame, straight axis)
DMJ = json.load(open(SP + 'topo/dem2m.json')); DEM = np.load(SP + 'topo/dem2m.npy', mmap_mode='r')
def ground(p): return float(DEM[int((DMJ['y1'] - p[1]) / 2), int((p[0] - DMJ['x0']) / 2)]) / 10.0
def gsm(snw, o, half=20.0): return float(np.mean([ground(FR.nw_P(x, o)) for x in np.arange(snw - half, snw + half + 0.1, 4.0)]))
S_J0, S_J1 = 3060.0, 3220.0                                  # the double junction east of Reading Road (Aloysius): TV off the shared pair to the south
Z_J = gsm(3150.0, -12.0, 100.0)                              # rail level at the junction, at ground
Z_ST = 178.0                                                 # Norwood Central platform rail, about 7 m under the street (platforms sunken, roofs at street level)
G_MAX = 0.020; CLR = 7.3
def tv_centre(s_c0, R, th, o0, o1):
    """TV centre in (s, o_nw): parallel at o0 to s_c0, left curve R through th, straight, right curve R onto o1. Returns (s, o) polyline and the end s"""
    lat_c = R * (1 - np.cos(th)); D = (o1 - o0 - 2 * lat_c) / np.sin(th)
    if D < 0: return None, None
    pts = []
    for f in np.linspace(0, th, 60): pts.append((s_c0 + R * np.sin(f), o0 + R * (1 - np.cos(f))))
    sa, oa = pts[-1]
    for x in np.linspace(0, D, 60)[1:]: pts.append((sa + x * np.cos(th), oa + x * np.sin(th)))
    sb, ob = pts[-1]
    for f in np.linspace(0, th, 60)[1:]: pts.append((sb + R * (np.sin(th) - np.sin(th - f)), ob + R * (np.cos(th - f) - np.cos(th))))
    return np.array(pts), pts[-1][0]
def offset_so(P, d):
    """offset an (s, o) polyline d to its left (+o side when heading +s)"""
    P = np.asarray(P); t = np.gradient(P, axis=0); t /= np.hypot(t[:, 0], t[:, 1])[:, None]; return P + np.c_[-t[:, 1], t[:, 0]] * d
def crossings(trk, o_line):
    """s where an (s, o) track crosses the line o = o_line"""
    out = []
    for a, b in zip(trk[:-1], trk[1:]):
        if (a[1] - o_line) * (b[1] - o_line) <= 0 and a[1] != b[1]: out.append(a[0] + (b[0] - a[0]) * (o_line - a[1]) / (b[1] - a[1]))
    return out
# ------------------------------------------------------------- RER B north of the split
# West of APEx Dayton from the split (no crossings there) through Ivorydale, Elmwood Place and Paddock; APEx keeps the ORR alignment through
# Lockland while B keeps its own (KMZ) line by Fairgrounds, Arlington Heights and Lockland/Reading, so B crosses over APEx once, between
# Paddock and Fairgrounds, and is on the east side from there (beside APEx again from about N 4,345,900 to the border).
sys.path.insert(0, _ws.CODE + 'rer1023')
from metro400 import _dense
_rb = [r for r in C0['rer'] if r['id'] == 'R-B-721053-4347000'][0]
BK = np.asarray(_dense(_rb['c'], _rb.get('k') or {}), float)[::-1]          # B as drawn (KMZ), south -> north
BKL = LineString(BK)
def o_kmz(s):
    p = FD.at(s)[0]; e = FD.at(s, 1.0)[0] - p; X = BKL.intersection(LineString([p - e * 700, p + e * 700]))
    if X.is_empty: return np.nan
    pts = [np.asarray(g.coords[0]) for g in getattr(X, 'geoms', [X])]; return min(((q - p) @ e for q in pts), key=abs)
def smax(a, b, k=4.0): return (a + b + np.sqrt((a - b) ** 2 + k * k)) / 2
S_PD = FD.proj(_st[('Paddock', ('B',))]); S_FG = FD.proj(_st[('Hamilton County Fairgrounds', ('B',))])
S_X0, S_X1 = S_PD + LPL / 2 + 240.0, S_FG - LPL / 2 - 150.0          # B moves across, climbing over APEx in the middle
S_FAR = 40.0                                                          # beyond this offset B is drawn on its own line, not by offset
def b_centre():
    ss = np.arange(S0, FD.s[-1] - 1, 2.0); pts = []; mode = []
    for s in ss:
        ok = o_kmz(s) if s >= S_X0 else np.nan
        if s < S_X0: o = -9.0
        elif s < S_X1: o = float(bl(s, S_X0, S_X1, -9.0, smax(ok, 9.0)))
        else: o = float(smax(ok, 9.0)) if np.isfinite(ok) else 9.0
        if s >= S_X1 and np.isfinite(ok) and ok > S_FAR: mode.append('k'); pts.append(None)
        else: mode.append('f'); pts.append(FD.at(s, o)[0])
        if pts[-1] is not None and pts[-1][1] >= 4347000.0: break
    out = []; i = 0
    while i < len(mode):
        if mode[i] == 'f': out.append(pts[i]); i += 1; continue
        j = i
        while j < len(mode) and mode[j] == 'k': j += 1
        a = BKL.project(Point(out[-1])); b = BKL.project(Point(pts[j])) if j < len(mode) else BKL.length
        out += [np.asarray(BKL.interpolate(x).coords[0]) for x in np.arange(a + 2.0, b - 1.0, 2.0)]; i = j
    return clip_y(np.array(out), 4347000.0)
