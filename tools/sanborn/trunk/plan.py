try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# North trunk, option 3 (Ben, 25 October 2026): RER B on the east edge, ORR beside APEx, connected north of Ludlow to the split and
# Norwood Central's west throat. Ben's conditions: the RER B/D split widens like the other splits, the viaduct widens at the RER
# stations, and the geometry agrees with the upper (Indianapolis + D) and lower (R5) decks across the Millvale grid.
#
# Offsets are + east of the frame (right of travel away from CUT), chainage s on the KMZ APEx line (nv/geom27.py). Working values:
# 4.5 m between the tracks of a pair, 6.75 m between groups, RER island 14.5 m between track centres (11.0 m platform), rail over rail
# 7.0 m (D over B and ORR), 7.3 m over the electrified APEx (B and ORR X2 over the Norwood tracks), 2.5% climbs.
#
# West to east, Arlington to the split: Transvalley (R5 has left), APEx Dayton, APEx Norwood, ORR, RER B.
#  - B/D comes up from the box on the east side of ORR (it passes under ORR while still 6.8 m or more below the viaduct), so ORR runs
#    straight beside the APEx from Marshall (no 22 m jog) and B/D's Camp Washington island is east of it.
#  - B/D junction north of Camp Washington, flying: southbound D keeps the west track and climbs, southbound B turns out east;
#    northbound D turns out from the east track between the two B tracks and climbs over southbound B; the D pair, at 174.3 m, drifts west
#    over ORR onto the Indianapolis deck (unchanged from the KMZ curve on).
#  - After Arlington ORR moves in beside the APEx and B onto the east edge (B and ORR swap places against v124).
#  - North of Ludlow the whole corridor bends up to 18 m west, where nothing stands, so B's Northside / Spring Grove island clears the
#    OH-75 parkway on the east; it eases back by the Mitchell Ave station.
#  - Transvalley crosses over APEx Dayton where the trunk comes down off the fill (Transvalley holds 162.5 m, then 2.5% down), so it
#    sits between the APEx pairs, which is its place at Norwood (north of APEx).
#  - ORR splits after Mitchell Ave: X2 turns out east (its southbound track crosses ORR northbound on the level: one flat crossing),
#    B moves out beside it, and B and X2 climb together and fly over the Norwood tracks where the Dayton line curves away north.
import json, sys, numpy as np
from shapely.geometry import LineString, Point, Polygon
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'trunk'); sys.path.insert(0, _ws.CODE + 'nv')
import geom27 as G
import frames as FR
from frames import FN, FE, chaikin, resample

def bl(s, s0, s1, a, b):
    s = np.asarray(s, float); t = np.clip((s - s0) / (s1 - s0), 0, 1); return a + (b - a) * (1 - np.cos(np.pi * t)) / 2
def pw(s, segs, v0):
    """piecewise cosine blends: segs = [(s0, s1, value_after)], starting from v0"""
    s = np.asarray(s, float); out = np.full(s.shape, float(v0)); cur = float(v0)
    for s0, s1, v in segs:
        out = np.where(s >= s0, bl(s, s0, s1, cur, v), out); cur = float(v)
    return out
ISL = 7.25                                    # half the island spread (11.0 m platform + 1.75 m each side)
LPL = 204.2; TAP = 100.0
DMJ = json.load(open(SP + 'topo/dem2m.json')); DEM = np.load(SP + 'topo/dem2m.npy', mmap_mode='r')
def ground(p): return float(DEM[int((DMJ['y1'] - p[1]) / 2), int((p[0] - DMJ['x0']) / 2)]) / 10.0

# ---------------------------------------------------------------- key chainages
S_J = 3200.0                                  # B/D junction (turnouts just past Camp Washington's north platform end, s 3,168)
S_AR0, S_AR1 = G.S_AR0, G.S_AR1               # Arlington 4,044-4,248
S_NS0, S_NS1 = G.S_NSP1 - LPL, G.S_NSP1       # Northside / Spring Grove, ending where the level ends (5,570)
_C = json.load(open(SP + 'deckpage/context_v90.json'))
_st = {s['name']: s['p'] for s in _C['rer_stations']}
S_MI = FN.proj(_st['Mitchell Ave / WINTON PLACE']); S_MI0, S_MI1 = S_MI - LPL / 2, S_MI + LPL / 2
S_IV = FN.proj(_st['Ivorydale']); S_IV0, S_IV1 = S_IV - LPL / 2, S_IV + LPL / 2
S_TC = 8568.0                                 # the Dayton line leaves the KMZ line here (1,000 m curve to the Southwest Chief straight)
S_FILL1 = next(float(x) for x in np.arange(G.S_NSP1, 7000, 5.0) if G.north_z(x) <= ground(G.C.interpolate(x).coords[0]))

# ---------------------------------------------------------------- the corridor's westward bend north of Ludlow (all tracks)
D_WEST = 18.0
def west(s): return pw(s, [(5050, 5400, D_WEST), (5600, 7300, 0.0)], 0.0)

# ---------------------------------------------------------------- offsets (before the westward bend)
# south of Ludlow (geom27 frame); the APEx, Transvalley and Indianapolis tracks keep their v124 offsets
def o_orr(k): a = (18.0, 22.5)[k]; b = (9.0, 13.5)[k]; return lambda s: pw(s, [(4430, 4780, b)], a)
def o_bd(k):                                  # B/D south of the junction, from where it is 6.8 m under the viaduct (S_SEP) north
    if k == 0: return lambda s: np.full(np.shape(s), 29.25)
    return lambda s: pw(s, [(G.S_CW0 - 80, G.S_CW0, 43.75)], 33.75)
def o_b(k):                                   # B from the junction to the split (both frames share the trunk)
    if k == 0:
        return lambda s: pw(s, [(S_J, S_J + 100, 33.75), (3650, 3850, 29.25), (4430, 4780, 20.25),
                               (S_MI1 + 20, S_MI1 + 220, 31.5)], 29.25)
    return lambda s: pw(s, [(S_J, S_J + 100, 42.75), (S_AR0 - TAP, S_AR0, 43.75), (S_AR1, S_AR1 + TAP, 33.75), (4430, 4780, 24.75),
                           (S_NS0 - TAP, S_NS0, 34.75), (S_NS1, S_NS1 + TAP, 24.75), (S_MI0 - TAP, S_MI0, 34.75), (S_MI1, S_MI1 + TAP, 24.75),
                           (S_MI1 + 20, S_MI1 + 220, 36.0)], 43.75)
def o_d(k):                                   # D on the trunk, from the junction to the Indianapolis curve (then geom27's group line)
    if k == 0: return lambda s: pw(s, [(3600, G.S_C - 60, 15.75)], 29.25)
    return lambda s: pw(s, [(S_J, S_J + 100, 38.25), (3500, 3590, 33.75), (3600, G.S_C - 60, 20.25)], 43.75)
# north of Ludlow (frames FN / FE)
S_TV0, S_TV1 = 6000.0, 6300.0                 # Transvalley moves east over the Dayton pair
S_AD0, S_AD1 = 6100.0, 6450.0                 # the Dayton pair moves west under it
def o_tv(k): a = (-22.5, -18.0)[k]; b = (-13.5, -9.0)[k]; return lambda s: pw(s, [(S_TV0, S_TV1, b)], a)
def o_ad(k): a = (-11.25, -6.75)[k]; b = (-24.75, -20.25)[k]; c = (-2.25, 2.25)[k]; return lambda s: pw(s, [(S_AD0, S_AD1, b), (8800, 9150, c)], a)
def o_an(k): return lambda s: np.full(np.shape(s), (-2.25, 2.25)[k])
def o_orr_n(k): return lambda s: np.full(np.shape(s), (9.0, 13.5)[k])
S_X0, S_X1 = S_MI1 + 170, S_MI1 + 370         # ORR X2 turns out (after B has moved out)
def o_x2(k):                                  # X2 on the north frame: from ORR (9 / 13.5) out to 20.25 / 24.75, then in to 9 / 13.5 over the Norwood tracks
    a = (9.0, 13.5)[k]; b = (20.25, 24.75)[k]; return lambda s: pw(s, [(S_X0, S_X1, b), (8500, 8800, a)], a)
def o_b_north(k):                             # B on the north frame from the split on
    if k == 0: return lambda s: pw(s, [(8500, 8800, 20.25)], 31.5)
    return lambda s: pw(s, [(8500, 8800, 24.75), (S_IV0 - TAP, S_IV0, 34.75), (S_IV1, S_IV1 + TAP, 24.75)], 36.0)
# the Norwood branch eases its group gaps to Norwood Central's (8.25 m) before the throat
_sNW = FE.s[-1]
def o_tv_e(k): a = (-13.5, -9.0)[k]; b = (-15.0, -10.5)[k]; return lambda s: pw(s, [(_sNW - 1600, _sNW - 400, b)], a)
def o_orr_e(k): a = (9.0, 13.5)[k]; b = (10.5, 15.0)[k]; return lambda s: pw(s, [(_sNW - 1600, _sNW - 400, b)], a)

# ---------------------------------------------------------------- line builders
S_L = 5420.0                                  # where the north frames take over from geom27's NT (Ludlow; the v124 viaduct tracks end here)
# geom27's NT, interpolated (nt_point snaps to its 2 m vertices)
_Sa, _ia = np.unique(G._S[::-1], return_index=True); _Pa = G._P[::-1][_ia]; _Ea = G._E[::-1][_ia]
def nt_at(s, o=0.0):
    s = np.atleast_1d(np.asarray(s, float)); o = np.broadcast_to(np.asarray(o, float), s.shape)
    x = np.interp(s, _Sa, _Pa[:, 0]); y = np.interp(s, _Sa, _Pa[:, 1]); ex = np.interp(s, _Sa, _Ea[:, 0]); ey = np.interp(s, _Sa, _Ea[:, 1]); n = np.hypot(ex, ey)
    return np.c_[x + ex / n * o, y + ey / n * o]
def nt_e(s): return nt_at(s, 1.0)[0] - nt_at(s, 0.0)[0]
def ss_(s0, s1, step=2.0):
    ss = np.arange(s0, s1, step); return np.r_[ss, s1] if len(ss) == 0 or s1 - ss[-1] > 1e-6 else ss
def south(fn, s0, s1=S_L):
    ss = ss_(s0, s1); return nt_at(ss, fn(ss))
def north(F, fn, s0, s1, step=2.0):
    s1 = min(s1, F.s[-1]); ss = ss_(s0, s1, step); return F.at(ss, fn(ss))
def joined(fn_s, s0, F, fn_n, s1):
    a = south(fn_s, s0) if s0 < S_L else np.zeros((0, 2)); b = north(F, fn_n, max(s0, S_L), s1)
    if len(a) and len(b) and np.hypot(*(a[-1] - b[0])) < 0.5: b = b[1:]
    return np.vstack([a, b]) if len(a) else b
def shift_west(P, F=FN):
    """the corridor's westward bend (all tracks): each point moved west(s) to the west, s from the north frame"""
    P = np.asarray(P, float); out = P.copy()
    L = F.L; d = np.r_[0, np.cumsum(np.hypot(*np.diff(F.P, axis=0).T))]
    for i, p in enumerate(P):
        s = float(np.interp(L.project(Point(p)), d, F.s)); w = float(west(s))
        if w > 1e-6:
            e = F.at(s, 1.0)[0] - F.at(s)[0]; out[i] = p - e * w
    return out
def frame_s(P, F=FN):
    L = F.L; d = np.r_[0, np.cumsum(np.hypot(*np.diff(F.P, axis=0).T))]
    return np.array([float(np.interp(L.project(Point(p)), d, F.s)) for p in np.asarray(P)])
def s_of(p): return float(G.C.project(Point(p)))
def band_poly(F, s0, s1, lo, hi, step=2.0):
    ss = np.arange(s0, s1 + 1e-6, step); a = F.at(ss, np.full(ss.shape, lo)); b = F.at(ss, np.full(ss.shape, hi))
    return np.vstack([a, b[::-1], a[:1]])
class NTF:                                    # geom27's NT as a frame-like object (for platforms south of S_L)
    at = staticmethod(nt_at)

# ---------------------------------------------------------------- profiles (rail levels)
G_UP = 0.025; CLR_RR = 7.0; CLR_APX = 7.3
def trunk_z(s):                               # the APEx / ORR / Transvalley level along the trunk: band to Ludlow, fill, then ground
    s = float(s)
    if s <= G.S_LUD: return G.band(s)
    z = G.north_z(s); g = ground(FN.at(s)[0]); return max(z, g)
Z_TV_HOLD = G.Z_LUD; S_TVD = 6300.0           # Transvalley holds 162.5 m to s 6,300, then 2.5% down
def tv_z(s):
    s = float(s); g = ground(FE.at(s)[0])
    if s <= S_TVD: return max(trunk_z(s), Z_TV_HOLD) if s >= G.S_LUD else trunk_z(s)
    return max(g, Z_TV_HOLD - G_UP * (s - S_TVD))
def d_z(s):                                   # D from the junction: 2.5% up to 174.3 m
    return min(G.Z_TOP, G.band(S_J) + G_UP * (float(s) - S_J))
S_BX0, S_BX1 = 8500.0, 8875.0                 # B and X2 over the Norwood tracks (checked below)
S_BU = S_BX0 - CLR_APX / G_UP; S_BD = S_BX1 + CLR_APX / G_UP
def bx_z(s):                                  # B / X2 at the split, as height over the ground-level trunk
    s = float(s); h = 0.0
    if S_BU < s <= S_BX0: h = G_UP * (s - S_BU)
    elif S_BX0 < s <= S_BX1: h = CLR_APX
    elif S_BX1 < s < S_BD: h = CLR_APX - G_UP * (s - S_BX1)
    return h
