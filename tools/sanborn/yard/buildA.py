try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Layout A (Ben, 27 October): two long yards end to end in Ben's buildable area, extra tracks in the wide parts,
# the south yard ends at a throat; from there the departure line climbs east to the CS bridge and a CVG-type stub fan sits in the lower left.
import json, math, sys
sys.path.insert(0, (_ws.CODE + 'yard'))
from zipkit import *
from ygen import A10
from lv import deck_z, yard_z, S
D = json.load(open(S + 'deckpage/deck.json')); TK = json.load(open(S + 'deckpage/tracks.json'))
P1 = json.load(open(S + 'yard/part1.json'))
def along(p, brg, d): return (p[0] + d * math.sin(math.radians(brg)), p[1] + d * math.cos(math.radians(brg)))
def isect(p, b1, q, b2):
    d1 = (math.sin(math.radians(b1)), math.cos(math.radians(b1))); d2 = (math.sin(math.radians(b2)), math.cos(math.radians(b2)))
    den = d1[0] * d2[1] - d1[1] * d2[0]; t = ((q[0] - p[0]) * d2[1] - (q[1] - p[1]) * d2[0]) / den
    return (p[0] + d1[0] * t, p[1] + d1[1] * t)
def hdg_line(l, s):
    a = l.interpolate(max(0, s - 2)); b = l.interpolate(min(l.length, s + 2)); return math.degrees(math.atan2(b.x - a.x, b.y - a.y)) % 360
def hdgF(t):
    a, b = F.W(0, t - 2), F.W(0, t + 2); return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 360
def lead_s(start, b0, end, b1, R, room=None):
    best = None
    for a in range(20, 700, 10):
        P1_ = along(start, b0, a)
        for c in range(20, 700, 10):
            P2_ = along(end, (b1 + 180) % 360, c)
            pts = fil([start, P1_, P2_, end], R)
            if radii(pts) < R * 0.97: continue
            L_ = LineString(pts)
            if room is not None and not L_.within(room): continue
            if best is None or L_.length < best[0]: best = (L_.length, pts)
    return best[1] if best else None
T_S0, T_S1, T_N0, T_N1 = [float(v) for v in (sys.argv[1:5] if len(sys.argv) > 4 and sys.argv[1] != 'fixZ' else (1230, 2370, 2430, 5350))]
SEG = []                     # (yard, kind, line)
room = ROOM0
def add(yard_name, tr, th):
    global room
    for l in tr: SEG.append((yard_name, 'track', l))
    for l in th: SEG.append((yard_name, 'throat', l))
    room = take(room, tr + th)
def core(name, t0, t1):
    E = [edges(t) for t in range(int(t0), int(t1) + 1, 50)]
    lo = -math.floor(-max(e[0] for e in E) / SP) * SP; hi = math.floor(min(e[1] for e in E) / SP) * SP
    tr, th = yard(room, lat_range(lo, hi), 0.0, t0, t1, 250.0); add(name, tr, th)
    lat = {}
    for l in tr:
        ts_ = [F.Lc(*c)[1] for c in (l.coords[0], l.coords[-1])]; x_ = round(F.Lc(*l.interpolate(0.5, normalized=True).coords[0])[0] / SP) * SP
        lat[x_] = (min(ts_), max(ts_))
    return tr, lat
def sides(name, lat):
    global room
    for sgn in (-1, 1):
        cx = min(lat) if sgn < 0 else max(lat); a_, b_ = lat[cx]
        room2, sl = side_yards(room, None, cx if sgn < 0 else -1e9, cx if sgn > 0 else 1e9, a_ + 60, b_ - 60, minbody=200.0, only=sgn)
        sl = [l for l in sl if not (abs(F.Lc(*l.coords[0])[0] - cx) < 0.5 and abs(F.Lc(*l.coords[-1])[0] - cx) < 0.5)]   # the side ladder's lead is the core's outer track itself
        tr = [l for l in sl if len(l.coords) > 2 and abs(F.Lc(*l.coords[0])[0] - F.Lc(*l.coords[-1])[0]) < 0.5]
        th = [l for l in sl if l not in tr]
        for l in tr: SEG.append((name, 'track', l))
        for l in th: SEG.append((name, 'throat', l))
        room = room2
trS, latS = core('South yard', T_S0, T_S1); sides('South yard', latS)
trN, latN = core('North yard', T_N0, T_N1); sides('North yard', latN)
print('south yard tracks', len(trS), 'north yard tracks', len(trN))
mid_lead = LineString(F.poly([(0.0, T_S1), (0.0, T_N0)], 10))
north_lead = LineString(F.poly([(0.0, T_N1), (0.0, min(F.L, 5780.0))], 10))
# ---- departure line and freight ramp from the south yard's south throat to the CS bridge (curves R 450 m, 1.5% at most)
icw = [f for f in TK['features'] if f['properties'].get('name', '').startswith('Intercity pair (west track)')][0]
IC = LineString(icw['geometry']['coordinates'])
M = (712616.7, 4330783.7)
b3 = math.degrees(math.atan2(712616.7 - 712623.0, 4330783.7 - 4330813.0)) % 360 - math.degrees(A10)
PS = F.W(0.0, T_S0); b0 = (hdgF(T_S0) + 180) % 360
AREA_OK = A.buffer(3).union(Point(M).buffer(160))
best = None
for d1 in range(40, 400, 20):
    PIa = along(PS, b0, d1)
    for h in [170.0 + 1.0 * k for k in range(25)]:
        PIb = along(PIa, h, 10.0)
        try: PIc = isect(PIa, h, M, b3)
        except ZeroDivisionError: continue
        if not (PIc[1] < PIa[1] - 150 and PIc[1] > M[1] + 80): continue
        pts = fil([PS, PIa, PIc, M], 450.0)
        if radii(pts) < 440: continue
        L_ = LineString(pts)
        if not L_.within(AREA_OK): continue
        cl = min(L_.interpolate(d).distance(IC) for d in range(0, int(L_.length) - 170, 10))
        if cl < 12: continue
        # prefer the line as far east as it can go (more room for the fan), i.e. the smallest clearance over 12 m
        key = cl
        if best is None or key < best[0]: best = (key, pts)
cl, rpts = best; ramp = LineString(rpts)
s_F = 0
for s_ in range(0, int(ramp.length) - 50, 5):
    p = ramp.interpolate(s_); g_ = (164.0 - yard_z(p.y)) / (ramp.length - s_)
    if g_ <= 0.015: s_F = s_
s_F = max(0, s_F - 20)
Fp = ramp.interpolate(s_F); z_foot = yard_z(Fp.y); grade = (164.0 - z_foot) / (ramp.length - s_F)
def zr(s): return z_foot if s <= s_F else z_foot + grade * (s - s_F)
print('departure line and ramp: %.0f m, clearance to the intercity %.1f m, foot at N %.0f (s %.0f), grade %.2f%%, min R %.0f' % (ramp.length, cl, Fp.y, s_F, grade * 100, radii(rpts)))
if grade > 0.0151: print('  RAMP TOO SHORT for 1.5%')
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
# ---- CVG-type stub fan in the lower left: lead off the departure line (at yard level) by a No. 8 turnout, stub tracks to the river edge
FROOM = room.difference(ramp.buffer(SP / 2 + 6.0))
BZ = 183.64
def fan(frame, xs, lead, room_, minbody=150.0, it=40):
    xs = list(xs)
    def end_t(x, a):
        t = a
        while t < 2000 and Point(frame.W(x, t + 5)).within(room_): t += 5
        return t
    for _ in range(it):
        sg, bd = ladder_fan(xs, (lead, 0.0))
        keep = [x for x in xs if Point(frame.W(x, bd[x])).within(room_) and end_t(x, bd[x]) - bd[x] >= minbody]
        if keep and keep == xs:
            bad = next((p for p in sg if not LineString(frame.poly(p, 4)).within(room_.buffer(0.5))), None)
            if bad is None: break
            far = max(keep, key=lambda v: abs(v - lead)); keep = [x for x in keep if x != far]
        if not keep: return [], [], None
        xs = keep
    sg, bd = ladder_fan(xs, (lead, 0.0))
    return [LineString(frame.poly([(x, bd[x]), (x, end_t(x, bd[x]))], 10)) for x in xs], [LineString(frame.poly(p, 4)) for p in sg], xs
bestf = None
ZC = [(712485.0, 4332000.0)] if 'fixZ' in sys.argv else [(float(zx), float(zn)) for zn in range(4332000, 4331400, -25) for zx in range(712380, 712560, 15)]
for Z in ZC:
    if True:
        if not Point(Z).within(FROOM): continue
        fr = CurveFrame([Z, along(Z, BZ, 3000.0)])
        tr, th, xs = fan(fr, lat_range(-150, 150), 0.0, FROOM)
        if not tr: continue
        # the lead from the departure line, at yard level
        got = None
        for sJ in range(40, int(s_F) - 20, 10):
            J = ramp.interpolate(sJ); hl = hdg_line(ramp, sJ)
            pp = lead_s((J.x, J.y), (hl + math.degrees(A8)) % 360, Z, BZ, 300.0, room=FROOM.union(ramp.buffer(10)).union(Point(Z).buffer(25)))
            if pp: got = (sJ, pp); break
        if not got: continue
        a = fp(tr + th + [LineString(got[1])]).area
        if bestf is None or a > bestf[0]: bestf = (a, Z, tr, th, xs, got)
a, Z, trF, thF, xsF, (sJf, fl_pts) = bestf
fan_lead = LineString(fl_pts)
for l in trF: SEG.append(('South fan (stub, to the river)', 'stub', l))
for l in thF: SEG.append(('South fan (stub, to the river)', 'throat', l))
print('fan: throat at', tuple(round(v) for v in Z), 'tracks', len(trF), 'lead %.0f m R %.0f, off the line at N %.0f' % (fan_lead.length, radii(fl_pts), ramp.interpolate(sJf).y))
# ---- checks
LEADS = [('Lead between the yards', mid_lead), ('Lead to the north', north_lead), ('Departure line and freight ramp to the CS bridge', ramp), ('South fan lead', fan_lead)]
allL = [l for y, k, l in SEG] + [g for n, g in LEADS]
out = [y for y, k, l in SEG if l.difference(ROOM0.buffer(0.5)).length > 1]
print('segments outside the area:', len(out))
rm = {}
for y, k, l in SEG: rm[(y, k)] = min(rm.get((y, k), 1e9), radii(list(l.coords)))
print('min radius:', {k: round(v) for k, v in rm.items()}, 'leads', {n: round(radii(list(g.coords))) for n, g in LEADS})
nx = 0
for i, a_ in enumerate(allL):
    for b_ in allL[i + 1:]:
        if not a_.crosses(b_): continue
        g = a_.intersection(b_)
        for p in getattr(g, 'geoms', [g]):
            if p.geom_type != 'Point': continue
            if min(Point(c).distance(p) for c in (a_.coords[0], a_.coords[-1], b_.coords[0], b_.coords[-1])) > 1: nx += 1
print('crossings:', nx)
ALL = fp(allL); print('footprint ha %.1f' % (ALL.area / 1e4))
for nm in ('South yard', 'North yard', 'South fan (stub, to the river)'):
    ls = [l for y, k, l in SEG if y == nm]; print(nm, sum(1 for y, k, l in SEG if y == nm and k != 'throat'), round(fp(ls).area / 1e4, 1))
json.dump({'SEG': [(y, k, list(l.coords)) for y, k, l in SEG], 'LEADS': [(n, list(g.coords)) for n, g in LEADS], 'xings': xings, 'grade': grade, 'z_foot': z_foot, 'footprint': ALL.area}, open(S + 'yard/A.json', 'w'))
