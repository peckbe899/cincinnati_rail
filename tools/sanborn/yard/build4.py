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

# ---------------- receiving yard: north throat in today's north yard, south throat feeding the hump
RECV = [(712360.0, 4336530.0), (712245.0, 4336300.0), (712165.0, 4336050.0), (712080.0, 4335750.0), (712070.0, 4335400.0), (712110.0, 4335100.0), (712220.0, 4334850.0), (712360.0, 4334600.0), (712500.0, 4334330.0), (712570.0, 4334170.0), (712575.0, 4334080.0)]
RECV = fil(RECV, 900)
xr, fRN, fRS = through_yard('Receiving yard', RECV, lat_range(-135, 135), minbody=600); take('Receiving yard')
# ---------------- hump and bowl
H = (712592.0, 4333690.0); DTP = (712555.0, 4332000.0)
hump = LineString(fil([fRS.W(0, 0), H], 400))
BOWL = [H, DTP]
fb = CurveFrame(BOWL)
xa = fb.Lc(712430.0, 4332900)[0]; xb = fb.Lc(712700.0, 4332900)[0]
xb_ = through_yard('Bowl (classification)', BOWL, lat_range(min(xa, xb), max(xa, xb)), minbody=150)[0]; take('Bowl (classification)')
# ---------------- departure and own freight ramp to the CS bridge
icw = [f for f in TK['features'] if f['properties'].get('name', '').startswith('Intercity pair (west track)')][0]
IC = LineString(icw['geometry']['coordinates'])
if IC.coords[0][1] < IC.coords[-1][1]: IC = LineString(list(IC.coords)[::-1])
def ic_off(N, off):   # point 'off' m west of the intercity west track at northing N
    s = IC.project(Point(IC.interpolate(IC.project(Point(712700, N))).x, N)); p = IC.interpolate(s); q = IC.interpolate(min(IC.length, s + 2))
    u = (q.x - p.x, q.y - p.y); l = math.hypot(*u); u = (u[0] / l, u[1] / l); wv = (-u[1], u[0])   # heading south: w east
    return (p.x - wv[0] * off, p.y - wv[1] * off)
RC = 8.25   # ramp centre: its east track 6 m west of the intercity west track, tracks 4.5 m apart (drawing values)
ramp_pts = [DTP, (712572.0, 4331860.0)] + [ic_off(N, RC) for N in range(4331520, 4330880, -40)] + [ic_off(4330840, 4.0), ic_off(4330800, 0.0)]
ramp = LineString(fil(ramp_pts, 350))
# levels: foot at the yard floor where it leaves the bowl throat; onto the CS bridge at 164.0 m (the Deck page's intercity pair: 162.3 m over W 6th, 164.0 m at the bridge)
s_foot = ramp.project(Point(712572.0, 4331860.0)); z_foot = yard_z(4331860)
grade = (164.0 - z_foot) / (ramp.length - s_foot)
def zr(s): return z_foot if s <= s_foot else z_foot + grade * (s - s_foot)
print('ramp grade %.2f%% over %d m' % (grade * 100, ramp.length - s_foot))
# street crossings on the ramp
xings = []
for f in D['features']:
    p = f['properties']
    if p.get('layer') != 'street': continue
    g = shape(f['geometry'])
    if not g.intersects(ramp): continue
    ip = g.intersection(ramp); ip = ip if ip.geom_type == 'Point' else ip.centroid
    s = ramp.project(ip); z = zr(s); dz = deck_z(ip.y)
    how = 'passes under (in the yard space)' if z + 7.0 <= dz else 'passes over' if z >= dz + 6.5 else 'cut or bridge'
    xings.append((p.get('name'), round(ip.x, 1), round(ip.y, 1), round(z, 1), round(dz, 1), how))
for x in sorted(xings, key=lambda q: -q[2]): print(x)
# ---------------- flat yards: south stub yard off the departure throat, to the river; north-east flat yard beside the receiving yard
Z = (712548.0, 4331830.0)
SOUTH = [Z, (712470.0, 4330900.0)]
fz = CurveFrame(SOUTH)
xs_south = lat_range(fz.Lc(712325, 4331300)[0], fz.Lc(712625, 4331300)[0])
xs_s, _ = stub_yard('South flat yard (to the river)', SOUTH, xs_south, minbody=120)
zlead = LineString(fil([(712566.0, 4331900.0), Z], 300)); take('South flat yard (to the river)')
# north-east flat yard: off the hump lead, stub tracks north along the APEx viaduct (fills what the curved receiving yard leaves)
NE = fil([(712640.0, 4333930.0), (712650.0, 4334150.0), (712520.0, 4334420.0), (712360.0, 4334700.0), (712270.0, 4335000.0), (712250.0, 4335500.0), (712300.0, 4336000.0), (712400.0, 4336450.0)], 700)
fne = CurveFrame(NE)
xs_ne = lat_range(-99, 99)
xs_n, _ = stub_yard('North flat yard (along the APEx viaduct)', NE, xs_ne, minbody=150); take('North flat yard (along the APEx viaduct)')
nelead = LineString(fil([(712590.0, 4333860.0), (712640.0, 4333930.0)], 200))
print('receiving', len(xr), 'bowl', len(xb_), 'south flat', len(xs_s))
bad = [(y, k, [round(v) for v in l.difference(ROOM0).bounds]) for y, k, l in SEG if l.difference(ROOM0).length > 2]
print('segments leaving the room:', len(bad)); [print('  ', b) for b in bad[:12]]
# ---------------- footprint, measured as today's yard (tracks + 3 m, gaps under 24 m closed)
def fp(lines):
    g = unary_union([l.buffer(3) for l in lines]).buffer(12).buffer(-12)
    return unary_union([x for x in getattr(g, 'geoms', [g]) if x.area > 2000])
ALL = fp([l for y, k, l in SEG] + [hump, ramp, zlead, nelead])
print('footprint ha %.1f' % (ALL.area / 1e4))
for name in ['Receiving yard', 'Bowl (classification)', 'South flat yard (to the river)', 'North flat yard (along the APEx viaduct)']:
    ls = [l for y, k, l in SEG if y == name]; g = fp(ls); ntr = sum(1 for y, k, l in SEG if y == name and k in ('track', 'stub'))
    print(name, ntr, round(g.area / 1e4, 1))
json.dump({'SEG': [(y, k, list(l.coords)) for y, k, l in SEG], 'hump': list(hump.coords), 'ramp': list(ramp.coords), 'zlead': list(zlead.coords), 'nelead': list(nelead.coords), 'xings': xings, 'grade': grade, 'z_foot': z_foot}, open(S + 'yard/d3.json', 'w'))

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
                      ('Hump lead', hump, 'Receiving yard to the hump crest, east of the Palace'),
                      ('Departure and freight ramp to the CS bridge', ramp, 'Double track from the bowl’s south throat over RER A (deep there), then its own ramp at %.2f%% beside the intercity viaduct, 160.0 m over W 6th, onto the Cincinnati Southern bridge tracks by No. 10 turnouts' % (grade * 100)),
                      ('South flat yard lead', zlead, 'Off the departure throat'),
                      ('North flat yard lead', nelead, 'Off the hump lead')]:
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
