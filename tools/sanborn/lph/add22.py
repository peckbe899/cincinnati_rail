"""Streets the 1904 sheets do not cover, read off the 1922 atlas (vol. 1, plates 16R, 34L, 34R, 37R; lph/tf22_cw.json),
appended to the basin layer (Ben, 2026-10-13):
  1. Camp Washington: the strip between the old canal bed (Central Parkway) and West McMicken Avenue south of Marshall
     (Halstead, Klottman, West McMillan, Hukill, Eliza, Rush, McMicken itself, Straight and Marshall to McMicken),
     plus Gene Alley, Meeker (Spring Grove to Hopple), Burlington and Ledlie.
  2. Crossings to the west side: the Hopple Street viaduct (over the deck's north lobe and Mill Creek to Beekman) and
     Ludlow Avenue (Knowlton's Corner across Mill Creek and the railroads to Lafayette Avenue).
Blocks: faces of the strip's new network, as the basin builds them (street bands removed).
Reads deckpage/basin.json (the basin layer from sbg/fit/post.py), writes lph/add_streets.json and, with --install,
appends to deckpage/basin.json and sbg/fit/basin_sanborn.json."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, os, numpy as np
from shapely.geometry import LineString, Point, Polygon, mapping
from shapely.ops import unary_union, polygonize, nearest_points
SP = _ws.DATA
FT = 0.3048
T = json.load(open(SP + 'lph/tf22_cw.json'))
def ap(h, x, y):
    p = T[h]; return (p[0] * x + p[1] * y + p[4], p[2] * x + p[3] * y + p[5])
BASIN = json.load(open(SP + 'sbg/fit/basin_sanborn_n.json'))   # the clean post.py output (no 1922 or LPH additions)
ST = [f for f in BASIN['features'] if f['properties']['layer'] == 'street']
def line(name, near):
    """the basin piece of this name nearest a point"""
    c = [LineString(f['geometry']['coordinates']) for f in ST if f['properties']['name'] == name]
    return min(c, key=lambda g: g.distance(Point(near)))
def end_of(name, near):
    g = line(name, near); a, b = Point(g.coords[0]), Point(g.coords[-1])
    q = a if a.distance(Point(near)) < b.distance(Point(near)) else b
    return (q.x, q.y)
def onto(name, p, maxd=25):
    """project p onto the basin street (T end)"""
    g = line(name, p); q = g.interpolate(g.project(Point(p)))
    assert q.distance(Point(p)) < maxd, (name, p, q.distance(Point(p)))
    return (q.x, q.y)
S = []
def add(name, pts, ft, src, note='', structure=None, sheets='', kind='we_street'):
    S.append(dict(name=name, pts=[tuple(map(float, q)) for q in pts], ft=ft, src=src, note=note, structure=structure, sheets=sheets, kind=kind))
P16 = lambda x, y: ap('16R', x, y)
# ------------------------------------------------------------------------------------------------ 1. Camp Washington strip
mc_s = end_of('West McMicken Avenue', (713348, 4333592)); mc_n = end_of('West McMicken Avenue', (713406, 4334403))
MC = [mc_s, P16(3765, 6636), P16(3985, 5076), P16(4129, 4081), P16(4214, 3494), P16(4450, 2128), P16(4590, 1273),
      P16(4739, 356), P16(4485, 140), mc_n]
add('West McMicken Avenue', MC, 60, '22-16R', 'the stretch the 1904 sheets leave out, from Rush to Marshall')
MCL = LineString(MC)
def past(q, p, over=0.5):
    v = np.array([q.x - p[0], q.y - p[1]]); n = np.linalg.norm(v)
    return (q.x + v[0] / n * over, q.y + v[1] / n * over) if n > 1e-3 else (q.x, q.y)
def on_mc(p): q = MCL.interpolate(MCL.project(Point(p))); return past(q, p)
add('Marshall Avenue', [end_of('Marshall Avenue', (713391, 4334333)), on_mc(P16(4485, 140))], 60, '22-16R', 'east end at West McMicken')
st_w = end_of('Straight Street', (713248, 4334146))
add('Straight Street', [st_w, P16(3608, 2122), on_mc(P16(4450, 2128))], 60, '22-16R', 'across the old canal bed to West McMicken')
CP = line('Central Parkway', (713250, 4334000))
def on_cp(p, over=0.5):
    # T end on Central Parkway's centreline, carried 0.5 m past it so the network nodes there
    q = CP.interpolate(CP.project(Point(p))); print('  onto Central Parkway', round(q.distance(Point(p)), 1), 'm')
    v = np.array([q.x - p[0], q.y - p[1]]); n = np.linalg.norm(v)
    return (q.x + v[0] / n * over, q.y + v[1] / n * over) if n > 1e-6 else (q.x, q.y)
HAL = [P16(3608, 2122), P16(3457, 3076), P16(3378, 3491), P16(3257, 4083), P16(3124, 5074), P16(2903, 6629)]
add('Halstead Street', HAL, 40, '22-16R', 'Straight to Rush, beside the old canal bed')
HL = LineString(HAL)
def on_h(p): q = HL.interpolate(HL.project(Point(p))); return past(q, p)
add('Klottman Street', [on_cp(P16(2600, 3070)), on_h(P16(3457, 3076))], 40, '22-16R', 'west of Halstead; west end at the old canal bed')
add('Klottman Street', [on_h(P16(3378, 3491)), on_mc(P16(4214, 3494))], 25, '22-16R', 'east of Halstead')
add('West McMillan Street', [on_h(P16(3257, 4083)), P16(3671, 4083), on_mc(P16(4129, 4081))], 40, '22-16R', 'Halstead to West McMicken')
add('Hukill', [P16(3671, 4083), P16(3555, 5075), P16(3315, 6634)], 15, '22-16R', 'printed without a suffix, 10-15 ft')
add('Eliza Street', [on_h(P16(3124, 5074)), P16(3555, 5075), on_mc(P16(3985, 5076))], 40, '22-16R')
_a, _b = np.array(P16(2903, 6629)), np.array(P16(3765, 6636)); _d = (_a - _b) / np.linalg.norm(_a - _b)
_x = LineString([tuple(_a), tuple(_a + _d * 150)]).intersection(CP)   # Rush runs west of Halstead to the old canal bed (plate 16R)
rush_w = (_x.x + _d[0] * 0.5, _x.y + _d[1] * 0.5)
add('Rush Street', [rush_w, on_h(P16(2903, 6629)), P16(3315, 6634), on_mc(P16(3765, 6636))], 40, '22-16R', 'old canal bed to West McMicken')
add('Gene Alley', [P16(839, 1413), onto('Massachusetts Avenue', P16(2095, 1425))], 12, '22-16R', 'west end at an unnamed 10 ft alley', kind='we_alley')
P34 = lambda x, y: ap('34R', x, y)
add('Meeker Street', [onto('Spring Grove Avenue', P34(2156, 5358)), end_of('Meeker Street', (712553, 4334875))], 30, '22-34R', 'Spring Grove to Hopple')
add('Burlington Street', [onto('Hopple Street', P34(3193, 4858)), onto('Spring Grove Avenue', P34(3193, 5460))], 30, '22-34R')
add('Ledlie Street', [onto('Johnson Street', P34(1100, 562)), onto('Spring Grove Avenue', P34(1438, 560))], 30, '22-34R')
# ------------------------------------------------------------------------------------------------ 2. crossings
# Hopple (profile 2026-10-13, LiDAR ground and the draft deck/APEx levels): Beekman 160.8 m, up 1.0% to 165.3 m over the
# APEx ramp (158.5 m rail + 6.8 m), down 4.4% to 158.9 m over Spring Grove (152.1 m + 6.8 m), landing at Meeker (157.6 m).
# The TRIMET trunk (RER B and D) is at 151.3 m under the deck there; RER D's viaduct starts 250 m north.
from shapely.ops import substring
HOPB = line('Hopple Street', (712383, 4334882)); hop_e = end_of('Hopple Street', (712383, 4334882))
MEEK = end_of('Meeker Street', (712553, 4334875)); t_m = HOPB.project(Point(MEEK)); t_e = HOPB.project(Point(hop_e))
HOP = list(substring(HOPB, min(t_m, t_e), max(t_m, t_e)).coords)
HOP = HOP if np.hypot(HOP[0][0] - MEEK[0], HOP[0][1] - MEEK[1]) < np.hypot(HOP[-1][0] - MEEK[0], HOP[-1][1] - MEEK[1]) else HOP[::-1]
HOP = HOP + [ap('34L', 5412, 4847), ap('34L', 4322, 4848)]
HOP_CUT = (HOPB, t_m)
# 2026-10-14 (page version 27, log 10za.30): the north trunk is a viaduct over the lobe, so Hopple comes down to deck level
add('Hopple Street', HOP, 60, '22-34L, 22-34R', 'on the line of the 1904 "Hopple (Bridge Av.)" from Meeker across Spring Grove, the deck\'s north lobe and Mill Creek to Beekman Street, at deck level since the north trunk became a viaduct (2026-10-14): Beekman 160.8 m, the deck about 158.9 m, Meeker 157.6 m. It passes 6.5 m under the trunk viaduct and TRI B/D\'s Camp Washington station, and RER A\'s viaduct crosses over it near Beekman (rail 168.2 m). Johnson\'s south end and Spring Grove meet it at grade', 'deck level')
P37 = lambda x, y: ap('37R', x, y)
dods = line('Dodsworth Avenue', (712728, 4337128))      # 1904 Dodsworth Av = the first block of Ludlow from Knowlton's Corner
knowl = min(dods.coords, key=lambda q: np.hypot(q[0] - P37(2525, 0)[0], q[1] - P37(2525, 0)[1]))
LUD = [knowl, P37(2510, 600), P37(2490, 1100), P37(2475, 1350), P37(2500, 1600), P37(2570, 1850), P37(2670, 2050),
       P37(2800, 2190), P37(3000, 2290), P37(3300, 2390), P37(3500, 2470), P37(3833, 2690), P37(4213, 3014), P37(4935, 3842)]
# Ludlow (profile 2026-10-13, LiDAR ground): the TRIMET north trunk (TRIMET_Lines.kmz) crosses at (712,718, 4,336,921), 208 m
# from Dodsworth, at 155.5 m and at grade, so Ludlow rises from Knowlton's Corner (149.4 m) along Dodsworth over Mill Creek
# (bed 142 m) to 162.3 m or more over the trunk (about 3.5% over 370 m), then about 2% to the old canal bank, where the
# ground stands at 163-166 m about 400 m from Dodsworth; at grade from there over the canal bed and past Central Parkway's
# north end (167.7 m) to Lafayette (160.4 m).
_L = LineString(LUD); _tv = 400.0
add('Ludlow Avenue', list(substring(_L, 0, _tv).coords), 60, '22-37R', 'viaduct from Dodsworth Avenue (the 1904 name of its first block from Knowlton\'s Corner) over Mill Creek and the TRIMET north trunk (155.5 m, at grade; the 1922 street crossed the B&O at grade) to the old canal bank. Roadway at least 162.3 m over the trunk: about 3.5% up from Knowlton\'s Corner (149.4 m) along Dodsworth, then about 2% to the bank (163-166 m)', 'viaduct')
add('Ludlow Avenue', list(substring(_L, _tv, _L.length).coords), 60, '22-37R', 'at grade from the old canal bank over the canal bed, past Central Parkway (167.7 m) to Lafayette Avenue (160.4 m); the Lafayette junction agrees with the 1912 survey corner within 25 m')
# ------------------------------------------------------------------------------------------------ features
F = []
for i, s in enumerate(S):
    g = LineString(s['pts'])
    F.append(dict(type='Feature', properties=dict(layer='street', id=f'S22{i:03d}', name=s['name'], kind=s['kind'], width_m=round(s['ft'] * FT, 2),
                  width_ft=float(s['ft']), width_src='printed (1922)', side='', src='Sanborn 1922', sheets=s['src'], geom_src='1922 Sanborn intersections', set='1922',
                  **({'note': s['note']} if s['note'] else {}), **({'structure': s['structure']} if s['structure'] else {})),
                  geometry=dict(type='LineString', coordinates=[[round(x, 2), round(y, 2)] for x, y in g.coords])))
# blocks in the Camp Washington strip: faces of the network between the canal bed and West McMicken
from shapely.ops import substring
_t0, _t1 = sorted((CP.project(Point(P16(2400, 6800))), CP.project(Point(on_mc(P16(4485, 140))))))
_cpw = list(substring(CP, _t0, _t1).coords)
_cpw = _cpw if _cpw[0][1] < _cpw[-1][1] else _cpw[::-1]          # south to north along the canal bed
strip = Polygon(_cpw + list(MC[1:9])[::-1] + [mc_s]).buffer(5)
lines = [LineString(f['geometry']['coordinates']) for f in ST] + [LineString(s['pts']) for s in S]
net = unary_union([l for l in lines if l.intersects(strip.buffer(60))])
from shapely.geometry import shape
old_blocks = unary_union([g for g in (shape(f['geometry']).buffer(0) for f in BASIN['features'] if f['properties']['layer'] == 'block') if g.intersects(strip.buffer(100))])
bands = unary_union([LineString(f['geometry']['coordinates']).buffer(f['properties']['width_m'] / 2, cap_style=2, join_style=2, mitre_limit=3) for f in ST if LineString(f['geometry']['coordinates']).intersects(strip.buffer(80))]
                    + [LineString(s['pts']).buffer(max(s['ft'] * FT, 2.5) / 2, cap_style=2, join_style=2, mitre_limit=3) for s in S])
nb = 0
if '--debug' in sys.argv:
    for p in polygonize(net):
        if p.area < 80 or not p.intersects(strip): continue
        print('face', int(p.area), [round(v) for v in p.representative_point().coords[0]], 'in strip', strip.contains(p.representative_point()), 'old overlap', round(p.intersection(old_blocks).area / p.area, 2))
for p in polygonize(net):
    if p.area < 80 or not strip.contains(p.representative_point()): continue
    if p.intersection(old_blocks).area > 0.2 * p.area: continue
    b = p.difference(bands)
    for q in getattr(b, 'geoms', [b]):
        if q.geom_type != 'Polygon' or q.area < 60: continue
        nb += 1
        F.append(dict(type='Feature', properties=dict(layer='block', id=f'SBB22{nb:02d}', type='building', area_m2=int(q.area), name='', src='Sanborn 1922', set='1922'),
                      geometry=mapping(q.simplify(0.3))))
json.dump(dict(type='FeatureCollection', features=F), open(SP + 'lph/add_streets.json', 'w'), separators=(',', ':'))
print('streets', len(S), 'blocks', nb)
for s in S: print(f"  {s['name']:24s} {LineString(s['pts']).length:7.1f} m  {s['ft']:.0f} ft  {s['src']}")
LUDL = LineString(LUD)
def hopple_cut(D):
    # the 1904 Hopple piece ends at Meeker; the viaduct takes over from there
    HB, tm = HOP_CUT
    for f in D['features']:
        p = f['properties']
        if p['layer'] != 'street' or p['name'] != 'Hopple Street' or p.get('set'): continue
        g = LineString(f['geometry']['coordinates'])
        if g.hausdorff_distance(HB) > 0.5: continue
        t_e = HB.project(Point(hop_e)); keep = substring(g, 0, tm) if t_e > tm else substring(g, tm, g.length)
        f['geometry']['coordinates'] = [[round(x, 2), round(y, 2)] for x, y in keep.coords]
        print('Hopple 1904 piece now ends at Meeker:', round(keep.length, 1), 'm kept of', round(g.length, 1))
def cp_to_ludlow(D):
    # Central Parkway's north end (OSM) stops 17 m short of the 1922 Ludlow line: carry it on to Ludlow
    for f in D['features']:
        p = f['properties']
        if p['layer'] != 'street' or p['name'] != 'Central Parkway': continue
        c = f['geometry']['coordinates']
        for e_, q_ in ((0, 1), (-1, -2)):
            a, b = np.array(c[e_][:2]), np.array(c[q_][:2])
            if LUDL.distance(Point(a)) > 30 or LUDL.distance(Point(a)) < 0.6: continue
            d = (a - b) / np.linalg.norm(a - b); x = LineString([tuple(a), tuple(a + d * 40)]).intersection(LUDL)
            if x.geom_type != 'Point':          # the ray misses: join at the nearest point of Ludlow
                x = LUDL.interpolate(LUDL.project(Point(a))); d = (np.array([x.x, x.y]) - a) / np.linalg.norm(np.array([x.x, x.y]) - a)
            if x.geom_type == 'Point':
                pt = [round(x.x + d[0] * 0.5, 2), round(x.y + d[1] * 0.5, 2)]
                if e_ == 0: c.insert(0, pt)
                else: c.append(pt)
                print('Central Parkway carried to Ludlow Avenue', round(float(np.hypot(*(np.array(pt) - a))), 1), 'm')
def rer_cut(D):
    # RER A (rera/rera.json, Ben 2026-10-13): basin streets that the line crosses at or near street level end at its walls
    # (5.8 m clear + 1.0 m structure; over a box from 4.6 m rail depth, the portal rule); the Hopple viaduct is set over it
    import rasterio
    R = json.load(open(SP + 'rera/rera.json')); DEM = rasterio.open(SP + 'handoff/out/map3_profile_dem_dm.vrt')
    def gz(e, n):
        v = list(DEM.sample([(e, n)]))[0][0]; return None if v == -32768 else v / 10
    out = []
    for key, s_deck in (('A', R['s_edge']), ('westwood', -1)):
        L = LineString(R['lines'][key]); pr = np.array([(a, b if b is not None else np.nan) for a, b, *_ in R['profiles'][key]], float)
        corr = L.buffer(7.0, cap_style=2)
        for f in list(D['features']):
            p = f['properties']
            if p['layer'] != 'street' or p.get('structure') in ('viaduct', 'deck level'): continue
            g = LineString(f['geometry']['coordinates'])
            x = g.intersection(L)
            pts = [q for q in getattr(x, 'geoms', [x]) if not q.is_empty and q.geom_type == 'Point']
            cutg = None
            for q in pts:
                sq = L.project(q)
                if sq <= s_deck: continue
                zr = float(np.interp(sq, pr[:, 0], pr[:, 1]))
                if np.isnan(zr): continue
                zs = gz(q.x, q.y); d = zr - zs
                if d >= 6.8 - 0.05 or d <= -4.6: continue
                c_ = corr.intersection(q.buffer(80)); cutg = c_ if cutg is None else cutg.union(c_)
                out.append((p.get('name'), round(q.x), round(q.y), round(zr, 1), round(zs, 1), round(d, 1)))
                D['features'].append(dict(type='Feature', properties=dict(layer='wv_cut', street=p.get('name'), by='RER A', rail=round(zr, 1), street_z=round(float(zs), 1), diff=round(float(d), 1),
                                          label=(p.get('name') or 'street').replace(' Street', '').replace(' Avenue', '') + ' cut'), geometry=dict(type='Point', coordinates=[round(q.x, 1), round(q.y, 1)])))
            if cutg is None: continue
            rest = g.difference(cutg.buffer(1.0))
            ps = [r for r in getattr(rest, 'geoms', [rest]) if r.geom_type == 'LineString' and r.length > 6]
            D['features'].remove(f)
            for k, r in enumerate(ps):
                nf = json.loads(json.dumps(f)); nf['properties']['id'] = p['id'] + ('' if k == 0 else 'abcdef'[k])
                nf['properties']['cut'] = 'RER A'; nf['geometry']['coordinates'] = [[round(a, 2), round(b, 2)] for a, b in r.coords]
                D['features'].append(nf)
    for o in out: print('RER A cuts', o)
if '--install' in sys.argv:
    for fn in ('deckpage/basin.json', 'sbg/fit/basin_sanborn.json'):
        D = json.load(open(SP + 'sbg/fit/basin_sanborn_n.json'))
        LPHF = json.load(open(SP + 'lph/lph_streets.json'))['features'] if os.path.exists(SP + 'lph/lph_streets.json') else []
        WVF = json.load(open(SP + 'lph/wv_1904.json'))['features'] if os.path.exists(SP + 'lph/wv_1904.json') else []
        D['features'] = D['features'] + F + LPHF + WVF
        cp_to_ludlow(D); hopple_cut(D); rer_cut(D)
        json.dump(D, open(SP + fn, 'w'), separators=(',', ':'))
    print('installed')
