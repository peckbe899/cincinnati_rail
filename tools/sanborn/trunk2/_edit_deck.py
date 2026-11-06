p='geo4.py'; s=open(p).read()
a=s.index("S_T = 3700.0; pT = TR.at(S_T)[0]; uT = TR.tan(S_T)"); b=s.index("# ---------------------------------------------------------------- offsets")
s=s[:a]+'''# the deck reference is the Indianapolis pair's centre: from the trunk (9 m west of it) onto the Cardinal / Floridian line beyond the window,
# which runs 9 m right (north) of the Indianapolis KMZ line (push of 26 October 2026: D on the south side of Indy, R5 under them)
REF_O = -9.0; REF_R = 9.0                                       # trunk offset of the Indy centre; its distance right of the KMZ line on the far straight
nRS = np.array([uS[1], -uS[0]]); pS = pS + nRS * REF_R
S_T = 3700.0; pT = TR.at(S_T, REF_O)[0]; uT = TR.tan(S_T)
t_, v_ = np.linalg.solve(np.c_[uT, -uS], pS - pT); PI = pT + uT * t_
DEFL = np.arccos(np.clip(uT @ uS, -1, 1))
R_DEP = 771.0                                                   # the Indy centre's radius (780 m on the old trunk-centre reference, less 9 m)
T_ = R_DEP * np.tan(DEFL / 2); TC = PI - uT * T_; CT = PI + uS * T_
NL = np.array([-uT[1], uT[0]])                                  # left of northbound (towards the curve centre)
O = TC + NL * R_DEP
S_TC = TR.proj(TC)
def _arc(Oc, R, p0, p1, step=2.0):
    a0 = np.arctan2(*(p0 - Oc)[::-1]); a1 = np.arctan2(*(p1 - Oc)[::-1]); da = (a1 - a0 + np.pi) % (2 * np.pi) - np.pi
    n = max(2, int(R * abs(da) / step) + 1); f = np.linspace(0, 1, n)
    return np.c_[Oc[0] + R * np.cos(a0 + da * f), Oc[1] + R * np.sin(a0 + da * f)]
_far = [np.asarray(q) for q in IK if _L.project(Point(q)) > i_st + 1.0]
_kmz_tail = LineString([np.array(_L.interpolate(i_st).coords[0])] + _far).offset_curve(-REF_R, quad_segs=32, join_style='round')
_kt = np.asarray(_kmz_tail.coords)
if np.hypot(*(_kt[0] - pS)) > np.hypot(*(_kt[-1] - pS)): _kt = _kt[::-1]
_REF_TAIL = np.vstack([np.array([CT + uS * x for x in np.arange(0.0, float((pS - CT) @ uS), 4.0)]), _kt])
def dep_path(d):
    """the departure path d m left of the reference: arc R_DEP - d about O, then the far straight and line offset properly"""
    a = TC + NL * d; b = CT + np.array([-uS[1], uS[0]]) * d
    arc = _arc(O, R_DEP - d, a, b)
    g = LineString(_REF_TAIL).offset_curve(d, quad_segs=32, join_style='round'); t = np.asarray(g.coords)
    if np.hypot(*(t[0] - b)) > np.hypot(*(t[-1] - b)): t = t[::-1]
    return arc, t[1:]
def merge(o_line, d, r):
    """a track running parallel to the trunk at offset o_line (west of the deck path d m left), joining that path on the curve:
       straight on, then one arc of radius r tangent to the straight and to the deck curve (no reverse curve)."""
    R_T = R_DEP - d
    h = REF_O - o_line                                           # left offset of the line from the reference's start line
    dy = (h + r) - R_DEP
    x = np.sqrt(max((R_T - r) ** 2 - dy ** 2, 0.0))
    Cc = TC + uT * x + NL * (h + r)
    p_on = TC + uT * x + NL * h                                  # where the straight ends
    u = (Cc - O) / np.hypot(*(Cc - O)); p_join = O + u * R_T     # where it meets the deck curve
    arc = _arc(Cc, r, p_on, p_join)
    darc, dtail = dep_path(d)
    i = int(np.argmin(np.hypot(*(darc - p_join).T)))
    return TR.proj(p_on), arc, np.vstack([darc[i + 1:], dtail]), p_join

'''+s[b:]
s=s.replace("D_DECK = (20.25, 15.75); INDY_DECK = (11.25, 6.75); R5_DECK = (15.75, 11.25)   # left of the deck reference",
            "D_DECK = (11.25, 6.75); INDY_DECK = (2.25, -2.25); R5_DECK = (6.75, 2.25)       # left of the deck reference (the Indy centre)")
open(p,'w').write(s)
