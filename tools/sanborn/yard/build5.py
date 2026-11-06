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

def through_yard(name, spine, xs, minbody=300.0, it=30):
    """tracks between two throats on a spine: tree at each end, bodies along the spine offset"""
    fN = CurveFrame(spine); fS = CurveFrame(spine[::-1]); Ls = fN.L
    xs = list(xs)
    for _ in range(it):
        sN, bN = FAN(xs); sS, bS = FAN([-x for x in xs])
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
            sN2, _ = FAN(keep); sS2, _ = FAN([-x for x in keep]); drop = None
            for p in sN2:
                if not LineString(fN.poly(p, 4)).within(ROOM.buffer(0.5)): drop = min(keep) if sum(q[0] for q in p) < 0 else max(keep); break
            if drop is None:
                for p in sS2:
                    if not LineString(fS.poly(p, 4)).within(ROOM.buffer(0.5)): drop = max(keep) if sum(q[0] for q in p) < 0 else min(keep); break
            if drop is not None: keep = [x for x in keep if x != drop]
        if keep == xs: break
        xs = keep
    sN, bN = FAN(xs); sS, bS = FAN([-x for x in xs])
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

# ---------------- main line: receiving yard -> hump (east of the Palace) -> bowl -> departure, all on one straight north-south line at E 712,575
XA = 712575.0
BB = 183.64                                  # the bowl and departure run parallel to Exposition Boulevard (the creek) south of the hump
RS = (XA, 4333990.0)
DT = (XA - math.tan(math.radians(BB - 180)) * (4333688.0 - 4332100.0), 4332100.0)
H = (XA, 4333688.0)                           # where the north-south hump lead meets the bowl line
HC = along(H, BB, 45.0); TS = along(DT, BB, 40.0); F = along(DT, BB, 80.0)
RECV = filr([(712330.0, 4336500.0), (712075.0, 4335560.0), (712140.0, 4334990.0), (XA, 4334235.0), RS], [900.0, 900.0, 900.0])
print('receiving spine min R %.0f' % radii(RECV))
xr, fRN, fRS = through_yard('Receiving yard', RECV, lat_range(-135, 135), minbody=600); take('Receiving yard')
hump = LineString(fil([RS, H, HC], 900.0))
BOWL = [HC, DT]; fb = CurveFrame(BOWL)
xb_ = through_yard('Bowl (classification)', BOWL, lat_range(-81.0, 220.5), minbody=150)[0]; take('Bowl (classification)')
# ---------------- departure and freight ramp: straights and curves of R 450 m, 1.5% ruling grade, onto the CS bridge tracks by No. 10 turnouts
icw = [f for f in TK['features'] if f['properties'].get('name', '').startswith('Intercity pair (west track)')][0]
IC = LineString(icw['geometry']['coordinates'])
M = (712616.7, 4330783.7)                     # the CS bridge's north end on the intercity west track (164.0 m)
b_ic = math.degrees(math.atan2(712616.7 - 712623.0, 4330783.7 - 4330813.0)) % 360   # intercity heading onto the bridge
b3 = b_ic - math.degrees(A10)                 # the ramp closes on it at the No. 10 frog angle
best = None
for n1 in range(4331900, 4331500, -25):
    for b2 in [170.0 + 0.5 * k for k in range(20)]:
        PI1_ = isect(F, BB, (0.0, float(n1)), 90.0)
        PI2_ = isect(PI1_, b2, M, b3)
        if not (PI2_[1] < PI1_[1] - 60 and PI2_[1] > M[1] + 60): continue
        pts_ = fil([F, PI1_, PI2_, M], 450.0)
        if radii(pts_) < 445: continue
        L_ = LineString(pts_)
        cl = min(L_.interpolate(d).distance(IC) for d in range(0, int(L_.length) - 170, 10))
        if cl < 12: continue
        if best is None or abs(cl - 18) < abs(best[0] - 18): best = (cl, PI1_, PI2_, b2)
cl, PI1, PI2, b2 = best
RR = 450.0
ramp = LineString(fil([F, PI1, PI2, M], RR))
z_foot = yard_z(F[1]); grade = (164.0 - z_foot) / ramp.length
def zr(s): return z_foot + grade * s
print('ramp: %.0f m, grade %.2f%%, min R %.0f, PI2 %s' % (ramp.length, grade * 100, radii(list(ramp.coords)), tuple(round(v) for v in PI2)))
print('  clearance to the intercity west track north of the merge: %.1f m' % min(LineString(fil([F, PI1, PI2, M], RR)).interpolate(d).distance(IC) for d in range(0, int(ramp.length) - 160, 10)))
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
ROOM = ROOM.difference(ramp.buffer(2.25 + 6.0))
# ---------------- south flat yard: lead off the departure by a No. 8 turnout, curves R 300 m, throat under the CUT park, stub tracks to the river
BZ = 183.64
best = None
for zn in range(4331990, 4331600, -10):
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
print('receiving', len(xr), 'bowl', len(xb_), 'south flat', len(xs_s))
bad = [(y, k, [round(v) for v in l.difference(ROOM0).bounds]) for y, k, l in SEG if l.difference(ROOM0).length > 2]
print('segments leaving the room:', len(bad)); [print('  ', b) for b in bad[:8]]
rmin = {}
for y, k, l in SEG:
    r_ = radii(list(l.coords)); key = (y, k); rmin[key] = min(rmin.get(key, 1e9), r_)
print('min radius by part:', {k: round(v) for k, v in rmin.items()})
def fp(lines):
    g = unary_union([l.buffer(3) for l in lines]).buffer(12).buffer(-12)
    return unary_union([x for x in getattr(g, 'geoms', [g]) if x.area > 2000])
ALL = fp([l for y, k, l in SEG] + [hump, ramp, zlead])
print('footprint ha %.1f' % (ALL.area / 1e4))
for name in ['Receiving yard', 'Bowl (classification)', 'South flat yard (to the river)']:
    ls = [l for y, k, l in SEG if y == name]; g = fp(ls); ntr = sum(1 for y, k, l in SEG if y == name and k in ('track', 'stub'))
    print(name, ntr, round(g.area / 1e4, 1))
json.dump({'SEG': [(y, k, list(l.coords)) for y, k, l in SEG], 'hump': list(hump.coords), 'ramp': list(ramp.coords), 'zlead': list(zlead.coords), 'nelead': list(hump.coords), 'xings': xings, 'grade': grade, 'z_foot': z_foot}, open(S + 'yard/d3.json', 'w'))
# ======================= output: deckpage/yard.json
def r(c): return [r(v) for v in c] if isinstance(c[0], (list, tuple)) else [round(c[0], 1), round(c[1], 1)]
F = [f for f in out if f['properties']['layer'] != 'yard_fan']
def addf(layer, g, **p):
    p['layer'] = layer; F.append({'type': 'Feature', 'properties': p, 'geometry': mapping(g)})
NOTES = {'Receiving yard': 'Arrivals; trains are pushed south over the hump beside the Palace. Compound ladders at each end (master ladder 14.3°, group ladders 7.15°, No. 8 turnouts)',
         'Bowl (classification)': 'Sorting tracks from the hump to the departure throat north of RER A; compound ladders at each end',
         'South flat yard (to the river)': 'Unloading and team tracks off the departure throat, stub-ended at the deck’s south edge or where a structure is in the yard space',
         'North flat yard (along the APEx viaduct)': 'Storage tracks off the hump lead, stub-ended to the north along the APEx viaduct'}
for name, note in NOTES.items():
    ls = [l for y, k, l in SEG if y == name]
    if not ls: continue
    g = fp(ls); ntr = sum(1 for y, k, l in SEG if y == name and k in ('track', 'stub')); nst = sum(1 for y, k, l in SEG if y == name and k == 'stub')
    addf('yard_fan', g, name=name, area_m2=round(g.area), tracks=ntr, stubs=nst, floor=[round(yard_z(g.bounds[3]), 1), round(yard_z(g.bounds[1]), 1)], note=note)
for y, k, l in SEG: addf('yard_track', l, yard=y, kind='stub' if k == 'stub' else ('throat' if k == 'throat' else 'yard'))
RN0 = RECV[0]; u0 = (RECV[0][0] - RECV[3][0], RECV[0][1] - RECV[3][1]); l0 = math.hypot(*u0)
north_lead = LineString([RN0, (RN0[0] + u0[0] / l0 * 110, RN0[1] + u0[1] / l0 * 110)])
for name, g, note in [('Lead to the north', north_lead, 'From the receiving yard’s north throat to the north edge of the flattened land; its route on beyond Millvale Boulevard is not set'),
                      ('Hump lead', hump, 'Receiving yard to the hump crest on one straight east of the Palace, then a 900 m curve onto the bowl line (parallel to Exposition Boulevard)'),
                      ('Departure and freight ramp to the CS bridge', ramp, 'Double track from the bowl’s south throat over RER A (deep there), then its own ramp at %.2f%% beside the intercity viaduct, 160.0 m over W 6th, onto the Cincinnati Southern bridge tracks by No. 10 turnouts' % (grade * 100)),
                      ('South flat yard lead', zlead, 'Off the departure by a No. 8 turnout, curves of 300 m radius, into the throat under the CUT park')]:
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
FC = {'type': 'FeatureCollection', 'crs': 'EPSG:26916', 'footprint_ha': round(ALL.area / 1e4, 1), 'note': 'Yards under the deck, draft 3 (27 October 2026): hump yard plus flat yards, own freight ramp to the CS bridge. Track spacing 4.5 m (the real yard), No. 8 turnouts in the yard and No. 10 at the bridge, compound ladders (14.3/7.15 deg), curves R 150 m and above. Footprint measured like today’s yard (tracks + 3 m, gaps under 24 m closed).', 'features': F}
json.dump(FC, open(S + 'deckpage/yard.json', 'w'), separators=(',', ':'))
import os; print('yard.json', os.path.getsize(S + 'deckpage/yard.json'), len(F))
