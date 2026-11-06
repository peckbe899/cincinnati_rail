try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Draft 3: hump yard plus flat yards, own freight ramp to the CS bridge. Writes deckpage/yard.json.
import json, sys, math
sys.path.insert(0, (_ws.CODE + 'yard'))
from lv import *
from ygen import *
from shapely.geometry import shape, mapping, LineString, Polygon, Point, box
from shapely.ops import unary_union, substring
P1 = json.load(open(S + 'yard/part1.json')); out = P1['features']
D = json.load(open(S + 'deckpage/deck.json')); TK = json.load(open(S + 'deckpage/tracks.json'))
deck = [shape(f['geometry']) for f in D['features'] if f['properties'].get('layer') == 'deck'][0]
limit = [shape(f['geometry']) for f in out if f['properties']['layer'] == 'yard_limit'][0]
INB = [f for f in out if f['properties']['layer'] == 'ud_box' and f['properties'].get('cls') == 'in']
BLOCK = unary_union([shape(f['geometry']) for f in INB])
ROOM = limit.buffer(-2.5).difference(BLOCK.buffer(2.5))
def add(layer, g, **p):
    p['layer'] = layer; out.append({'type': 'Feature', 'properties': p, 'geometry': mapping(g)})
SEG = []      # (yard, kind, LineString)
FAN = ladder_fan
ROOM0 = ROOM
def seg(yard, kind, pts): SEG.append((yard, kind, LineString(pts)))


def _L(v): return list(v) if isinstance(v, (list, tuple)) else [v]
def neg(v): return [-a for a in _L(v)]
def near_lead(p, leads):
    m = sum(q[0] for q in p) / len(p); return min(_L(leads), key=lambda a: abs(a - m))
def MFAN(xs, leads):
    """one ladder fan per lead; each track goes to its nearest lead (leads sorted, split at midpoints)"""
    leads = sorted(_L(leads)); segs, body = [], {}
    for i, a in enumerate(leads):
        lo = -1e9 if i == 0 else (leads[i - 1] + a) / 2; hi = 1e9 if i == len(leads) - 1 else (a + leads[i + 1]) / 2
        sub = [x for x in xs if lo <= x < hi]
        if not sub: continue
        sg, bd = FAN(sub, (a, 0.0)); segs += sg; body.update(bd)
    return segs, body

def through_yard(name, spine, xs, minbody=300.0, it=30, xN=0.0, xS=0.0, tN=0.0, tS=0.0):
    def MF(xs_, leads, off):
        sg, bd = MFAN(xs_, leads); return [[(x, t + off) for x, t in q] for q in sg], {k: v + off for k, v in bd.items()}
    """tracks between two throats on a spine: tree at each end, bodies along the spine offset"""
    fN = CurveFrame(spine); fS = CurveFrame(spine[::-1]); Ls = fN.L
    xs = list(xs)
    for _ in range(it):
        sN, bN = MF(xs, xN, tN); sS, bS = MF([-x for x in xs], neg(xS), tS)
        keep = []; short = outr = 0
        for x in xs:
            t0, t1 = bN[x], Ls - bS[-x]
            if t1 - t0 < minbody: short += 1; continue
            body = LineString(fN.poly([(x, t0), (x, t1)], 10))
            if not body.within(ROOM): outr += 1; continue
            keep.append(x)
        print(name, 'pass: keep', len(keep), 'short', short, 'outside', outr)
        if not keep: return [], fN, fS
        if keep == xs:   # throats must stay in the room too: drop the outermost track on a side whose ladder leaves it
            sN2, _ = MF(keep, xN, tN); sS2, _ = MF([-x for x in keep], neg(xS), tS); drop = None
            for p in sN2:
                if not LineString(fN.poly(p, 4)).within(ROOM.buffer(0.5)): print('   N throat out:', [(round(a), round(b)) for a, b in (p[0], p[-1])]); drop = min(keep) if sum(q[0] for q in p) / len(p) < near_lead(p, xN) else max(keep); break
            if drop is None:
                for p in sS2:
                    if not LineString(fS.poly(p, 4)).within(ROOM.buffer(0.5)): print('   S throat out:', [(round(a), round(b)) for a, b in (p[0], p[-1])]); drop = max(keep) if sum(q[0] for q in p) / len(p) < near_lead(p, neg(xS)) else min(keep); break
            if drop is not None: keep = [x for x in keep if x != drop]
        if keep == xs: break
        xs = keep
    sN, bN = MF(xs, xN, tN); sS, bS = MF([-x for x in xs], neg(xS), tS)
    for p in sN: seg(name, 'throat', fN.poly(p, 4))
    for p in sS: seg(name, 'throat', fS.poly(p, 4))
    for x in xs: seg(name, 'track', fN.poly([(x, bN[x]), (x, Ls - bS[-x])], 10))
    return xs, fN, fS

def stub_yard(name, spine, xs, minbody=200.0, it=6):
    f = CurveFrame(spine); xs = list(xs)
    for _ in range(it):
        sg, bd = FAN(xs); keep, ends = [], {}
        for x in xs:
            t0 = bd[x]; t = t0
            while t < f.L + 600 and Point(f.W(x, t + 5)).within(ROOM): t += 5
            if t - t0 >= minbody and Point(f.W(x, t0)).within(ROOM): keep.append(x); ends[x] = t
        if keep == xs: break
        xs = keep
    sg, bd = FAN(xs)
    for p in sg: seg(name, 'throat', f.poly(p, 4))
    for x in xs:
        t0 = bd[x]; t = t0
        while t < f.L + 600 and Point(f.W(x, t + 5)).within(ROOM): t += 5
        seg(name, 'stub', f.poly([(x, t0), (x, t)], 10))
    return xs, f

def take(name):
    global ROOM
    ls = [l for y, k, l in SEG if y == name]
    if ls: ROOM = ROOM.difference(unary_union([l.buffer(SP / 2 + 3.0) for l in ls]))
def lat_range(a, b, s=SP): n = int(math.floor((b - a) / s + 1e-9)); return [round(a + k * s, 2) for k in range(n + 1)]


def filr(pts, rads):
    """fillet each interior vertex with its own radius (a list, one per interior vertex)"""
    out = [tuple(pts[0])]
    for i in range(1, len(pts) - 1):
        seg = fil([pts[i - 1], pts[i], pts[i + 1]], rads[i - 1])
        out += seg[1:-1]
    out.append(tuple(pts[-1])); return out
def radii(pts):
    """smallest radius along a polyline (circumradius of consecutive points where it turns)"""
    m = 1e9
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        ab = math.dist(a, b); bc = math.dist(b, c); ac = math.dist(a, c)
        cr = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(cr) < 1e-9 or ab < 0.3 or bc < 0.3: continue
        R = ab * bc * ac / (2 * abs(cr))
        if R < m: m = R
    return m
def isect(p, b1, q, b2):
    d1 = (math.sin(math.radians(b1)), math.cos(math.radians(b1))); d2 = (math.sin(math.radians(b2)), math.cos(math.radians(b2)))
    den = d1[0] * d2[1] - d1[1] * d2[0]; t = ((q[0] - p[0]) * d2[1] - (q[1] - p[1]) * d2[0]) / den
    return (p[0] + d1[0] * t, p[1] + d1[1] * t)
def along(p, brg, d): return (p[0] + d * math.sin(math.radians(brg)), p[1] + d * math.cos(math.radians(brg)))
def lead_s(start, b0, end, b1, R, room=None):
    """a lead from start (heading b0) to end (arriving heading b1): one curve if the tangents meet, else two (an S), every curve radius R or more"""
    best = None
    try:
        PI = isect(start, b0, end, (b1 + 180) % 360)
        d0 = (PI[0] - start[0]) * math.sin(math.radians(b0)) + (PI[1] - start[1]) * math.cos(math.radians(b0))
        d1 = (end[0] - PI[0]) * math.sin(math.radians(b1)) + (end[1] - PI[1]) * math.cos(math.radians(b1))
        if d0 > 0 and d1 > 0:
            pts = fil([start, PI, end], R)
            if radii(pts) >= R * 0.97: best = (LineString(pts).length, pts)
    except ZeroDivisionError: pass
    for a in range(20, 600, 15):
        P1 = along(start, b0, a)
        for c in range(20, 600, 15):
            P2 = along(end, (b1 + 180) % 360, c)
            pts = fil([start, P1, P2, end], R)
            if radii(pts) < R * 0.97: continue
            L = LineString(pts)
            if room is not None and not L.within(room.buffer(1)): continue
            if best is None or L.length < best[0]: best = (L.length, pts)
    return best[1] if best else None

# ---------------- layout (Ben, 27 October): receiving yard north of Hopple; hump at Hopple; two classification yards side by side in the lobe
# between the Mill Creek culvert and the arch viaduct (Ben's outlines); a departure yard south of them; the freight ramp to the CS bridge.
BEN = json.load(open(S + 'yard/ben_yards.json'))
OUT_W = shape(BEN['west']).buffer(8); OUT_E = shape(BEN['east']).buffer(8)
PAL = unary_union([shape(f['geometry']) for f in D['features'] if f['properties'].get('layer') in ('palace', 'forecourt')]).buffer(3)
ROOM = ROOM.union(PAL.difference(BLOCK.buffer(2.5)).intersection(OUT_W.buffer(20))).buffer(3.0).buffer(-3.0)      # Ben's west yard runs under the Palace's east part
ROOM0 = ROOM
def yard_in(outline, fn, *args, **kw):
    global ROOM
    keep = ROOM; ROOM = ROOM.intersection(outline)
    try: return fn(*args, **kw)
    finally: ROOM = keep
sys.path.insert(0, S + 'yard')
import ygen
BOWL_N1, BOWL_N2, BOWL_S = 4333150.0, 4332350.0, 4332340.0; HUMP_L = 110.0; BOWL_MINB = 150.0; BOWL_XS = [-49.5, 49.5]; BOWL_SJ = [1250.0, 1320.0]
LOBE_PI = [(712135.0, 4334980.0), (712480.0, 4334380.0), (712600.0, 4333900.0), (712605.0, 4333380.0)]; LOBE_R = [800.0, 800.0, 800.0]; LOBE_HW = 112.5; LOBE_XS = [-54.0, 54.0]; LOBE_XN = -27.0
LOBE_PI = [(712064.0, 4335300.0), (712095.0, 4335060.0), (712470.0, 4334380.0), (712560.0, 4334000.0), (712600.0, 4333100.0), (712570.0, 4332550.0)]; LOBE_R = [800.0, 1400.0, 2000.0, 2000.0]
NEST_B = 72.0; NEST_W = (-166.5, -81.0); NEST_E = (81.0, 166.5); NEST_TS = 0.0; OUT_W = -126.0; OUT_E = float(sys.argv[2]) if len(sys.argv) > 2 else 126.0; BOWL_N = 790.0; BOWL_S = 2300.0; W_END = 1160.0; E_START = 1850.0; E_END = 2750.0; OUT_MINB = float(sys.argv[1]) if len(sys.argv) > 1 else 250.0
ygen.G = 4          # groups of four tracks: shorter ladders, shorter throats
# ---- north of Hopple: staging yard on the main line; at Hopple the line splits to the receiving yard (west) and the departure yard (east)
RN = (712330.0, 4336500.0); RS = (712115.0, 4335400.0); H = (712133.0, 4335300.0)
RECV = filr([RN, (712090.0, 4335620.0), RS], [900.0])
xn, fRN, fRS = through_yard('North staging yard', RECV, lat_range(-112.5, 112.5), minbody=400); take('North staging yard')
# ---- the lobe south of Hopple: three yards nested side by side between the Mill Creek culvert and the arch viaduct (Ben, 27 October,
# after the real Queensgate yards): receiving yard on the west, the hump and sorting bowl in the middle, the departure yard on the east.
# One spine down the middle of the room; each yard has its own leads. The hump is at the bowl's north end.
def in_room(r, fn, *a, **k):
    global ROOM
    keep = ROOM; ROOM = r
    try: return fn(*a, **k)
    finally: ROOM = keep
def brg_of(spine, at_start=True):
    a_, b_ = (spine[0], spine[3]) if at_start else (spine[-4], spine[-1])
    return math.degrees(math.atan2(b_[0] - a_[0], b_[1] - a_[1])) % 360
def join(P, b, tgt, R=300.0, room=None, s0=10.0, s1=None, avoid=()):
    """shortest lead from P (heading b) onto the line tgt by a No. 8 turnout, at the first workable point along it"""
    for sJ in range(int(s0), int(s1 if s1 else tgt.length - 5), 5):
        Jp = tgt.interpolate(sJ); q_ = tgt.interpolate(sJ + 3); h = math.degrees(math.atan2(q_.x - Jp.x, q_.y - Jp.y)) % 360
        best = None
        for sd in (-1, 1):
            pp = lead_s(P, b, (Jp.x, Jp.y), (h + sd * math.degrees(A8)) % 360, R, room=room)
            if pp and LineString(pp).length > 30 and not any(LineString(pp).crosses(o) for o in avoid):
                if best is None or LineString(pp).length < best[0]: best = (LineString(pp).length, pp, sJ)
        if best: return best
    return None
LOBE = filr(LOBE_PI, LOBE_R); fL = CurveFrame(LOBE)
print('lobe spine min R %.0f, length %.0f' % (radii(LOBE), fL.L))
def hdg(f, t, sgn=1):
    a_, b_ = f.W(0, t - 2), f.W(0, t + 2); return math.degrees(math.atan2(b_[0] - a_[0], b_[1] - a_[1])) % 360 if sgn > 0 else (math.degrees(math.atan2(a_[0] - b_[0], a_[1] - b_[1])) % 360)
b_rs = brg_of(RECV, False); hump0 = LineString([RS, H])
LEADS = {}
def north_lead(name, x, start, b_start, t_list, avoid):
    for t in t_list:
        pp = lead_s(start, b_start, fL.W(x, t), hdg(fL, t), 300.0, room=ROOM.buffer(1))
        if pp and not any(LineString(pp).crosses(o) for o in avoid): return t, pp
    return None, None
def south_pt(x, tS): return fL.W(x, fL.L - tS)
Hw = along(H, (b_rs + 180) % 360, 30.0)
t_b, p_b = north_lead('hump', 0.0, H, b_rs, range(150, 700, 10), [])
hump = LineString(p_b + fL.poly([(0.0, t_b), (0.0, BOWL_N)], 10)[1:]); HB = fL.W(0.0, BOWL_N)   # option A: the crest moves south to the receiving yard's middle
# option B (Ben, 27 October): each outer yard has its lead on its outside edge and its ladders open inward; the receiving yard sits beside
# the bowl's north end and the departure yard beside its south end, where the bowl is thin
IN_E, IN_W = 81.0, -81.0                       # leads running beside the bowl (the bowl's outer track is at 72 m)
t_e, p_e = north_lead('east', IN_E, H, (b_rs - math.degrees(A8)) % 360, range(650, 1000, 10), [hump])
t_w, p_w = north_lead('west', OUT_W, Hw, (b_rs + math.degrees(A8)) % 360, range(100, 1200, 10), [hump, LineString(p_e)])
print('north leads: hump crest at t %d (%.0f m), departure lead reaches the bowl side at t %d, receiving yard at t %d (%.0f m)' % (t_b, hump.length, t_e, t_w, LineString(p_w).length))
xb_ = through_yard('Sorting yard (hump)', LOBE, lat_range(-NEST_B, NEST_B), minbody=250, xN=0.0, xS=0.0, tN=BOWL_N, tS=fL.L - BOWL_S)[0]; take('Sorting yard (hump)')
def step(x0, t0, x1, tmin, tmax):
    """S-curve from lateral x0 at t0 to lateral x1, both parallel to the spine; shortest that works"""
    for t1 in range(int(tmin), int(tmax), 10):
        pp = lead_s(fL.W(x0, t0), hdg(fL, t0), fL.W(x1, t1), hdg(fL, t1), 300.0)
        if pp: return t1, pp
    return None, None
# departure yard's north lead: beside the bowl at +81 m, then out to the yard's outside edge
t_s1, ps = step(IN_E, E_START - 480.0, OUT_E, E_START - 460.0, E_START - 79.0)
pe2 = fL.poly([(IN_E, t_e), (IN_E, E_START - 480.0)], 10)
leadE = LineString(p_e + pe2[1:] + ps[1:] + fL.poly([(OUT_E, t_s1), (OUT_E, E_START)], 10)[1:]) if t_s1 <= E_START else None
leadW = LineString(p_w)
P_PATH = fL.poly([(0.0, BOWL_S), (0.0, fL.L)], 10)            # the bowl's pull-out lead runs south from the tip down the middle
ROOM = ROOM.difference(unary_union([substring(g, 0, g.length - 60.0).buffer(SP / 2 + 3.0) for g in (hump, leadE, leadW)] + [LineString(P_PATH).buffer(SP / 2 + 3.0)]))
xw = through_yard('Receiving yard', LOBE, lat_range(OUT_W, -13.5), minbody=OUT_MINB, xN=OUT_W, xS=OUT_W, tN=t_w, tS=fL.L - W_END)[0]; take('Receiving yard')
xe = through_yard('Departure yard', LOBE, lat_range(13.5, OUT_E), minbody=OUT_MINB, xN=OUT_E, xS=OUT_E, tN=E_START, tS=fL.L - E_END)[0]; take('Departure yard')
NEST_TSE = fL.L - E_END; NEST_TSW = fL.L - W_END; NEST_E = (13.5, OUT_E); NEST_W = (OUT_W, -13.5)
hS = hdg(fL, fL.L); hSE = hdg(fL, E_END); SPE = [fL.W(OUT_E, E_END + 10.0 * k) for k in range(4)]
hSW = hdg(fL, W_END); SPW = [fL.W(OUT_W, W_END + 10.0 * k) for k in range(4)]
# ---- departure line: from the departure yard's south end down the east side, onto the freight ramp (curves R 450 m, 1.5% at most) and the CS bridge
icw = [f for f in TK['features'] if f['properties'].get('name', '').startswith('Intercity pair (west track)')][0]
IC = LineString(icw['geometry']['coordinates'])
M = (712616.7, 4330783.7)
b_ic = math.degrees(math.atan2(712616.7 - 712623.0, 4330783.7 - 4330813.0)) % 360
b3 = b_ic - math.degrees(A10)
# the departure line keeps outside the bowl: parallel to the spine at the departure yard's lateral until the bowl's south tip, then on to the ramp
E_PATH = [fL.W(OUT_E, E_END - 10.0), fL.W(OUT_E, E_END)]
S0 = E_PATH[-1]; b0 = hdg(fL, E_END)
BL = 184.0                                     # the departure line runs down the sorting yard's east side on this heading
PI1 = along(S0, b0, 100.0); PI2 = isect(PI1, BL, (712000.0, 4331950.0), 90.0)
best = None
for h3 in [170.0 + 0.5 * k for k in range(24)]:
    try: PI3_ = isect(PI2, h3, M, b3)
    except ZeroDivisionError: continue
    if not (PI3_[1] < PI2[1] - 100 and PI3_[1] > M[1] + 80): continue
    pts_ = fil([S0, PI1, PI2, PI3_, M], 450.0)
    if radii(pts_) < 440: continue
    L_ = LineString(pts_)
    cl = min(L_.interpolate(d).distance(IC) for d in range(0, int(L_.length) - 170, 10))
    if cl < 12: continue
    if best is None or abs(cl - 18) < abs(best[0] - 18): best = (cl, PI3_, h3, pts_)
cl, PI3, h3, rpts = best
print('departure line: clearance to the intercity %.1f m, middle heading %.1f' % (cl, h3))
ramp_line = LineString(E_PATH[:-1] + rpts)
# the foot: the ramp needs (164.0 - floor) / 1.5% before the bridge
z_floor = lambda n: yard_z(n)
s_F = 0
for s_ in range(0, int(ramp_line.length) - 50, 5):   # stay at yard level as long as the ramp still makes 1.5% or less
    p = ramp_line.interpolate(s_); g_ = (164.0 - z_floor(p.y)) / (ramp_line.length - s_)
    if g_ <= 0.015: s_F = s_
s_F = max(0, s_F - 20)
F = ramp_line.interpolate(s_F); z_foot = z_floor(F.y); grade = (164.0 - z_foot) / (ramp_line.length - s_F)
ramp = ramp_line
def zr(s): return z_foot if s <= s_F else z_foot + grade * (s - s_F)
print('departure line and ramp: %.0f m, foot at N %.0f (s %.0f), grade %.2f%%, min R %.0f' % (ramp.length, F.y, s_F, grade * 100, radii(rpts)))
xings = []
for f in D['features']:
    p = f['properties']
    if p.get('layer') != 'street': continue
    g = shape(f['geometry'])
    if not g.intersects(ramp): continue
    ip = g.intersection(ramp); ip = ip if ip.geom_type == 'Point' else ip.centroid
    s_ = ramp.project(ip); z = zr(s_); dz = deck_z(ip.y)
    how = 'passes under (in the yard space)' if z + 7.0 <= dz else 'passes over' if z >= dz + 6.5 else 'cut or bridge'
    xings.append((p.get('name'), round(ip.x, 1), round(ip.y, 1), round(z, 1), round(dz, 1), how))
for x in sorted(xings, key=lambda q: -q[2]): print('  ', x)
# ---- south end: the bowl's pull-out lead joins the departure line; the receiving yard's south lead joins the pull-out lead
PB0 = P_PATH[-1]
jb = join(PB0, hS, ramp, room=ROOM0.union(ramp.buffer(9)), s0=30.0, s1=s_F, avoid=[])
pulls = [LineString(P_PATH[:-1] + jb[1]) if jb else LineString(P_PATH)]
print('bowl pull-out lead: %s' % ('none' if not jb else '%.0f m R %.0f, joins the line at N %.0f' % (jb[0], radii(jb[1]), ramp.interpolate(jb[2]).y)))
BOWL_SJ = [float(jb[2]) if jb else s_F]
t_s2, pw = step(OUT_W, W_END, IN_W, W_END + 20.0, W_END + 600.0)
W_PATH = fL.poly([(OUT_W, W_END - 0.0), (OUT_W, W_END)], 10)[:1] + pw[1:] + fL.poly([(IN_W, t_s2), (IN_W, fL.L)], 10)[1:]
jw = join(W_PATH[-1], hS, ramp, room=ROOM0.union(ramp.buffer(9)), s0=BOWL_SJ[0] + 40.0, s1=s_F, avoid=[pulls[0]]) if jb else None
pulls.append(LineString(W_PATH[:-1] + jw[1]) if jw else LineString(W_PATH))
print('receiving yard south lead: %s' % ('none' if not jw else '%.0f m R %.0f, joins the line at N %.0f' % (jw[0], radii(jw[1]), ramp.interpolate(jw[2]).y)))
BOWL_SJ += [float(jw[2])] if jw else []
s_DB = max(BOWL_SJ); DB = (ramp.interpolate(s_DB).x, ramp.interpolate(s_DB).y)
pullout = pulls[0]; pullout2 = pulls[1]
s_J = s_DB
s_T = max(max(BOWL_SJ) + 60, ramp.project(Point(712600.0, 4332200.0)))
TS = (ramp.interpolate(s_T).x, ramp.interpolate(s_T).y)
qT = ramp.interpolate(s_T + 3);
ROOM = ROOM.difference(ramp.buffer(2.25 + 6.0)); BB = math.degrees(math.atan2(qT.x - TS[0], qT.y - TS[1])) % 360
elead = LineString([TS, TS])
# ---------------- south flat yard: lead off the departure by a No. 8 turnout, curves R 300 m, throat under the CUT park, stub tracks to the river
BZ = 183.64
best = None
for zn in range(4331990, 4331450, -10):
    for hm in range(194, 222, 2):
        for da in (50.0, 60.0, 70.0, 80.0):
            Z_ = (712440.0, float(zn)); PA_ = along(TS, BB + math.degrees(A8), da); PB_ = isect(PA_, hm, Z_, BZ)
            if not (PB_[1] < PA_[1] and PB_[1] > Z_[1]): continue
            pts_ = fil([TS, PA_, PB_, Z_], 300.0)
            if radii(pts_) >= 295 and (best is None or zn > best[0]): best = (zn, hm, da, Z_, PA_, PB_, pts_)
zn, hm, da, Z, PA, PB, zlead_pts = best
zlead = LineString(zlead_pts)
print('south lead: throat N %d, middle heading %d, turnout run %d m, min R %.0f' % (zn, hm, da, radii(zlead_pts)))
SOUTH = [Z, along(Z, BZ, 1000.0)]; fz = CurveFrame(SOUTH)
xs_south = lat_range(-148.5, 148.5)
xs_s, _ = stub_yard('South flat yard (to the river)', SOUTH, xs_south, minbody=150); take('South flat yard (to the river)')
nelead = None
print('staging', len(xn), 'receiving', len(xw), 'departure', len(xe), 'sorting', len(xb_), 'south flat', len(xs_s))
bad = [(y, k, [round(v) for v in l.difference(ROOM0).bounds]) for y, k, l in SEG if l.difference(ROOM0).length > 2]
print('segments leaving the room:', len(bad)); [print('  ', b) for b in bad[:8]]
rmin = {}
for y, k, l in SEG:
    r_ = radii(list(l.coords)); key = (y, k); rmin[key] = min(rmin.get(key, 1e9), r_)
print('min radius by part:', {k: round(v) for k, v in rmin.items()})
def fp(lines):
    g = unary_union([l.buffer(3) for l in lines]).buffer(12).buffer(-12)
    return unary_union([x for x in getattr(g, 'geoms', [g]) if x.area > 2000])
ALL = fp([l for y, k, l in SEG] + [hump, hump0, ramp, zlead, leadW, leadE, pullout, pullout2, elead])
print('footprint ha %.1f' % (ALL.area / 1e4))
for name in ['North staging yard', 'Receiving yard', 'Departure yard', 'Sorting yard (hump)', 'South flat yard (to the river)']:
    ls = [l for y, k, l in SEG if y == name]; g = fp(ls); ntr = sum(1 for y, k, l in SEG if y == name and k in ('track', 'stub'))
    print(name, ntr, round(g.area / 1e4, 1))
json.dump({'SEG': [(y, k, list(l.coords)) for y, k, l in SEG] + [('lead', 'lead', list(g.coords)) for g in (leadW, leadE, pullout, pullout2, elead, hump0)], 'hump': list(hump.coords), 'ramp': list(ramp.coords), 'zlead': list(zlead.coords), 'nelead': list(hump.coords), 'xings': xings, 'grade': grade, 'z_foot': z_foot}, open(S + 'yard/d3d.json', 'w'))
# ======================= output: deckpage/yard.json
def r(c): return [r(v) for v in c] if isinstance(c[0], (list, tuple)) else [round(c[0], 1), round(c[1], 1)]
F = [f for f in out if f['properties']['layer'] != 'yard_fan']
def addf(layer, g, **p):
    p['layer'] = layer; F.append({'type': 'Feature', 'properties': p, 'geometry': mapping(g)})
NOTES = {'North staging yard': 'Through tracks on the line from the north, north of Hopple; trains wait here before entering the yards. Compound ladders at each end',
         'Receiving yard': 'West of the bowl’s north end; its lead is on its outside edge and its ladders open inward. Arrivals from the north (Hopple) and from the south (CS bridge, by the bowl pull-out lead). The hump engine pulls a train out north onto the hump lead and shoves it over the crest',
         'Sorting yard (hump)': 'The bowl, between the receiving and departure yards; its ends sit beside the middles of the receiving yard (north) and the departure yard (south). Hump crest at its north end; cuts roll south into the bowl tracks; pull-out lead at the south end onto the departure line',
         'Departure yard': 'East of the bowl’s south end; its lead is on its outside edge and its ladders open inward. Trains built from the bowl leave south on the departure line and freight ramp to the CS bridge, or north by its own lead to Hopple',
         'South flat yard (to the river)': 'Unloading and team tracks off the departure line, stub-ended at the deck’s south edge or where a structure is in the yard space'}
for name, note in NOTES.items():
    ls = [l for y, k, l in SEG if y == name]
    if not ls: continue
    g = fp(ls); ntr = sum(1 for y, k, l in SEG if y == name and k in ('track', 'stub')); nst = sum(1 for y, k, l in SEG if y == name and k == 'stub')
    addf('yard_fan', g, name=name, area_m2=round(g.area), tracks=ntr, stubs=nst, floor=[round(yard_z(g.bounds[3]), 1), round(yard_z(g.bounds[1]), 1)], note=note)
for y, k, l in SEG: addf('yard_track', l, yard=y, kind='stub' if k == 'stub' else ('throat' if k == 'throat' else 'yard'))
RN0 = RECV[0]; u0 = (RECV[0][0] - RECV[3][0], RECV[0][1] - RECV[3][1]); l0 = math.hypot(*u0)
north_lead = LineString([RN0, (RN0[0] + u0[0] / l0 * 110, RN0[1] + u0[1] / l0 * 110)])
for name, g, note in [('Lead to the north', north_lead, 'From the staging yard’s north throat to the north edge of the flattened land; its route on beyond Millvale Boulevard is not set'),
                      ('Hump lead', hump, 'From Hopple down the middle, between the receiving yard and the departure lead, to the hump crest at the bowl’s north end; curves of 300 m radius or more'),
                      ('Receiving yard north lead', leadW, 'Off the line at Hopple by a No. 8 turnout, curves of 300 m radius, to the receiving yard’s north throat'),
                      ('Departure yard north lead', leadE, 'Off the line at Hopple by a No. 8 turnout, curves of 300 m radius, then beside the bowl’s east side to the departure yard’s north throat'),
                      ('Bowl pull-out lead', pullout, 'From the bowl’s south tip down the middle, past the departure yard, onto the departure line by a No. 8 turnout'),
                      ('Receiving yard south lead', pullout2, 'From the receiving yard’s south throat, beside the bowl’s west side, onto the departure line by a No. 8 turnout; trains from the CS bridge enter the receiving yard this way'),
                      ('Departure line and freight ramp to the CS bridge', ramp, 'From the departure yard’s south throat at yard level, then its own ramp at %.2f%% beside the intercity viaduct onto the Cincinnati Southern bridge tracks by No. 10 turnouts' % (grade * 100)),
                      ('South flat yard lead', zlead, 'Off the departure line by a No. 8 turnout, curves of 300 m radius, into the throat under the CUT park')]:
    addf('yard_lead', g, name=name, length_m=round(g.length), note=note)
for nm, x, y, z, dz, how in xings:
    if how == 'cut or bridge': addf('yard_xing', Point(x, y), name=nm, rail=z, deck=dz, label=nm + ': ramp %.1f m, deck %.1f m' % (z, dz))
lw = [shape(f['geometry']) for f in TK['features'] if f['properties'].get('layer') in ('lower', 'lower_plat') and f['properties'].get('level') == '-2']
cutbox = unary_union([g.buffer(4.2, cap_style=2, join_style=2) for g in lw]).intersection(box(712600, 4331600, 712900, 4332420))
addf('ud_box', cutbox, name='CUT lower level (-2) and its north fan', kind='cut', cls='in', rail=[144.0, 144.0], yard=[round(yard_z(4331800), 1)] * 2, note='under the embanked platform deck, east of the limit')
for f in D['features']:
    if f['properties'].get('layer') == 'dive_cut': addf('ud_box', shape(f['geometry']), name='Lower-pair dive, open cut (Bank to Findlay)', kind='cut', cls='in', note='under the north arch viaduct, east of the limit')
cols, walls = [], []
x = 712400 - 20 * math.floor((712400 - limit.bounds[0]) / 20)
while x <= limit.bounds[2]:
    g = LineString([(x, limit.bounds[1] - 5), (x, limit.bounds[3] + 5)]).intersection(limit)
    if not g.is_empty: cols.append(g)
    x += 20
n = 4332000 - 20 * math.floor((4332000 - limit.bounds[1]) / 20)
while n <= limit.bounds[3]:
    g = LineString([(limit.bounds[0] - 5, n), (limit.bounds[2] + 5, n)]).intersection(limit)
    if not g.is_empty: walls.append(g)
    n += 20
addf('deck_col', unary_union(cols), name='Deck column lines (every 20 m)')
addf('deck_cell', unary_union(walls), name='Deck cell walls (every 20 m, across)')
for nn in range(4331000, 4336700, 500):
    ii = LineString([(711000, nn), (714000, nn)]).intersection(limit)
    xs_ = [g.bounds for g in getattr(ii, 'geoms', [ii]) if not g.is_empty]
    if xs_ and nn <= 4335500: addf('yard_mark', Point(max(xs_, key=lambda b: b[2] - b[0])[2] - 8, nn), deck=round(deck_z(nn), 1), floor=round(yard_z(nn), 1))
for f in F:
    g = json.loads(json.dumps(f['geometry'])); f['geometry'] = g
    if g['type'] == 'GeometryCollection': continue
    g['coordinates'] = r(g['coordinates']) if g['type'] != 'Point' else [round(g['coordinates'][0], 1), round(g['coordinates'][1], 1)]
FC = {'type': 'FeatureCollection', 'crs': 'EPSG:26916', 'footprint_ha': round(ALL.area / 1e4, 1), 'note': 'Yards under the deck, draft 5 (27 October 2026): three yards nested side by side south of Hopple (receiving, hump bowl, departure), staging north of Hopple, flat yard to the river, own freight ramp to the CS bridge. Track spacing 4.5 m (the real yard), No. 8 turnouts in the yard and No. 10 at the bridge, compound ladders (14.3/7.15 deg), curves R 200 m and above in the yards, 300 m on leads, 450 m on the ramp. Footprint measured like today’s yard (tracks + 3 m, gaps under 24 m closed).', 'features': F}
json.dump(FC, open(S + 'yard/yard_d.json', 'w'), separators=(',', ':'))
import os; print('yard.json', os.path.getsize(S + 'yard/yard_d.json'), len(F))
