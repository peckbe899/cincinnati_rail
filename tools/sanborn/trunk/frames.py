try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Frames for the north trunk rework (option 3, Ben 25 October 2026). Chainage s is the KMZ APEx line C's (nv/geom27.py), from CUT.
# Offsets are + east (right of travel away from CUT). South of s 5,420 the frame is geom27's drawing trunk NT; north of it the KMZ line C to
# s 8,400, then the branch references: N (the APEx Southwest Chief region line's mid) and E (the APEx Transcontinental region line's mid,
# eased onto Norwood Central's frame axis before the west throat).
import json, sys, numpy as np
from shapely.geometry import LineString, Point, shape
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'nv'); import geom27 as G
T0 = json.load(open(SP + 'deckpage/tracks_v90.json'))          # the base snapshot (apply.py starts from it), so the region lines are always the KMZ's
def _feat(nm): return [f for f in T0['features'] if (f['properties'].get('name') or '') == nm][0]
def _mid(a, b, n=None):
    A, B = LineString(a), LineString(b); n = n or int(max(A.length, B.length) / 2)
    return [tuple((np.array(A.interpolate(i / n, normalized=True).coords[0]) + np.array(B.interpolate(i / n, normalized=True).coords[0])) / 2) for i in range(n + 1)]
def chaikin(P, it=4):
    P = np.asarray(P, float)
    for _ in range(it):
        Q = [P[0]]
        for a, b in zip(P[:-1], P[1:]): Q += [0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b]
        Q.append(P[-1]); P = np.asarray(Q)
    return P
def resample(P, step=2.0):
    L = LineString(P); n = max(2, int(L.length / step) + 1)
    return np.array([L.interpolate(d).coords[0] for d in np.linspace(0, L.length, n)])
NWF = json.load(open(SP + 'norwood/frame.json')); NO, NTV, NNV = np.array(NWF['o']), np.array(NWF['t']), np.array(NWF['n'])
def nw_P(s, o=0.0): return NO + NTV * (s - 4300) + NNV * o
def nw_so(p): d = np.asarray(p) - NO; return float(d @ NTV) + 4300, float(d @ NNV)
S_C0 = 5420.0          # NT -> C
S_BR = 8400.0          # C -> branch references
S_NW = 4150.0          # Norwood Central west throat (frame s)
# trunk part: NT (south of 5,420, as geom27 draws it) then C
_south = [tuple(p) for p, s in zip(G._P[::-1], G._S[::-1]) if 2300 <= s < S_C0]
_north = [G.C.interpolate(s).coords[0] for s in np.arange(S_C0, S_BR + 0.1, 4.0)]
R_N = 1000.0           # the Dayton line's curve onto the Southwest Chief straight
S_TC = 8568.0
_common = resample(chaikin(resample(list(_south) + list(_north), 8.0), 4), 2.0)
_common = _common[[LineString(_common[:i + 1]).length if False else True for i in range(len(_common))]]
def _sw_line():
    m = np.array(_mid(_feat('APEx Southwest Chief (1 of 2)')['geometry']['coordinates'][::-1], _feat('APEx Southwest Chief (2 of 2)')['geometry']['coordinates'][::-1]))
    return m
def _ref(branch):
    end = _common[-1]; u1 = np.array(G.C.interpolate(S_BR + 5).coords[0]) - np.array(G.C.interpolate(S_BR - 5).coords[0]); u1 /= np.hypot(*u1)
    if branch == 'N':
        m = _sw_line(); L = LineString(m)
        p2 = np.array(L.interpolate(300).coords[0]); u2 = np.array(L.interpolate(900).coords[0]) - p2; u2 /= np.hypot(*u2)
        t, v = np.linalg.solve(np.c_[u1, -u2], p2 - end); PI = end + t * u1
        D = np.arccos(np.clip(u1 @ u2, -1, 1)); Tn = R_N * np.tan(D / 2); TC = PI - u1 * Tn; CT = PI + u2 * Tn
        nrm = np.array([-u1[1], u1[0]]) * np.sign(u1[0] * u2[1] - u1[1] * u2[0]); O = TC + nrm * R_N
        a0 = np.arctan2(*(TC - O)[::-1]); a1 = np.arctan2(*(CT - O)[::-1]); da = (a1 - a0 + np.pi) % (2 * np.pi) - np.pi
        arc = [O + R_N * np.array([np.cos(a0 + da * f), np.sin(a0 + da * f)]) for f in np.linspace(0, 1, int(R_N * abs(da) / 2) + 2)]
        straight = [end + u1 * d for d in np.arange(2.0, t - Tn, 2.0)]
        rest = [q for q in m if (np.asarray(q) - CT) @ u2 > 2.0]
        tail = straight + arc + [CT + u2 * d for d in np.arange(2.0, 600.0, 2.0)] + [q for q in rest if (np.asarray(q) - CT) @ u2 > 600.0]
        return np.vstack([_common, resample(np.vstack([end] + tail), 2.0)[1:]])
    m = _mid(_feat('APEx Transcontinental Limited (1 of 2)')['geometry']['coordinates'], _feat('APEx Transcontinental Limited (2 of 2)')['geometry']['coordinates'])
    out = []
    for p in m:
        s, o = nw_so(p)
        if s > S_NW + 0.5: break
        w = float(np.clip((s - 2600) / 1200, 0, 1)); w = (1 - np.cos(np.pi * w)) / 2
        out.append(tuple(nw_P(s, o * (1 - w))))
    out.append(tuple(nw_P(S_NW, 0)))
    Lm = LineString(out)
    pts = [end + u1 * d for d in np.arange(0.0, 326.0, 25.0)] + [q for q in resample(out, 25.0) if Lm.project(Point(q)) > 125]   # on the KMZ line to s 8,900, then the region line
    tail = resample(chaikin(resample(pts, 25.0), 6), 2.0)
    return np.vstack([_common, tail[1:]])
class Frame:
    def __init__(self, P):
        self.P = np.asarray(P); self.L = LineString(self.P)
        t = np.gradient(self.P, axis=0); t /= np.hypot(t[:, 0], t[:, 1])[:, None]
        for _ in range(6): t[1:-1] = (t[:-2] + 2 * t[1:-1] + t[2:]) / 4
        t /= np.hypot(t[:, 0], t[:, 1])[:, None]; self.t = t; self.E = np.c_[t[:, 1], -t[:, 0]]
        d = np.r_[0, np.cumsum(np.hypot(*np.diff(self.P, axis=0).T))]
        # chainage: C chainage at the start, then by length (C and NT run at about 1:1)
        s0 = G.C.project(Point(self.P[0])); self.s = s0 + d
        # tie to C chainage at S_C0 exactly
        i = int(np.argmin(np.abs(self.s - S_C0))); k = G.C.project(Point(self.P[i])) - self.s[i]; self.s += k
    def at(self, s, o=0.0):
        s = np.atleast_1d(np.asarray(s, float)); o = np.broadcast_to(np.asarray(o, float), s.shape)
        x = np.interp(s, self.s, self.P[:, 0]); y = np.interp(s, self.s, self.P[:, 1])
        ex = np.interp(s, self.s, self.E[:, 0]); ey = np.interp(s, self.s, self.E[:, 1]); n = np.hypot(ex, ey)
        return np.c_[x + ex / n * o, y + ey / n * o]
    def line(self, fn, s0, s1, step=2.0):
        ss = np.arange(s0, s1 + 1e-6, step); return self.at(ss, fn(ss)), ss
    def proj(self, p): return float(np.interp(self.L.project(Point(p)), np.r_[0, np.cumsum(np.hypot(*np.diff(self.P, axis=0).T))], self.s))
FN, FE = Frame(_ref('N')), Frame(_ref('E'))
def minr(P, win=10):
    P = np.asarray(P); d1 = np.gradient(P, axis=0); d2 = np.gradient(d1, axis=0)
    k = np.abs(d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) / np.hypot(d1[:, 0], d1[:, 1]) ** 3
    return 1 / np.maximum(k, 1e-9)
if __name__ == '__main__':
    for nm, F in (('N', FN), ('E', FE)):
        r = minr(F.P); print(nm, 'len', round(F.L.length), 's', round(F.s[0]), round(F.s[-1]), 'end', F.P[-1].round(1))
        for a, b in ((2400, 5420), (5420, 8400), (8400, 9300), (9300, 13000)):
            sel = (F.s >= a) & (F.s < b)
            if sel.any(): j = np.argmin(r[sel]); print('   min radius s %d-%d: %.0f at s %.0f' % (a, b, r[sel][j], F.s[sel][j]))
    print('NT vs C at 5420:', np.round(G.NT[0], 1), np.round(G.C.interpolate(5420).coords[0], 1))
    print('Norwood throat on E frame: s', round(FE.proj(nw_P(S_NW))), 'end', np.round(FE.P[-1], 1), 'axis', np.round(nw_P(S_NW), 1))
