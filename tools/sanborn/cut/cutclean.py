try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben (17 October): the CUT and Ezzard Charles area was choppy (streets overlapping, the station and park off the streets, the plaza not
# symmetrical). One axis for the whole composition: Kenner and Hopkins straight and parallel from Garrard to Freeman (Ben's merged
# streets SB0799 and SB0775, baked into the base data), the terminal, concourse, headhouse, platforms, west park and terminal square
# centred between their inner edges, the plaza mirror-symmetric about the axis (drives that sat on Kenner, Hopkins and Freeman removed),
# Ezzard Charles Freeman to Baymiller on the axis, Dalton and Garrard ends on the new lines. Blocks and lots along every change recut.
# Reads deckpage/deck.json, basin.json, plots.json and plots/live2/deck/layout.json. Marks deck.json 'clean17'; will not run twice.
import json, math, sys
from shapely.geometry import shape, mapping, LineString, Polygon, MultiPolygon, Point, box
from shapely.affinity import rotate, translate, affine_transform
from shapely.ops import unary_union
S = _ws.DATA
DRY = '--dry' in sys.argv
D = json.load(open(S + 'deckpage/deck.json')); B = json.load(open(S + 'deckpage/basin.json')); P = json.load(open(S + 'deckpage/plots.json'))
if D.get('clean17'): sys.exit('already done')
LAY = json.load(open(S + 'plots/live2/deck/layout.json'))
FE = D['features'] + B['features']
SF = {f['properties']['id']: f for f in FE if f['properties'].get('layer') == 'street'}
SC = lambda i: [tuple(q) for q in SF[i]['geometry']['coordinates']]
rj = lambda g: json.loads(json.dumps(mapping(g), default=float))
def rg(g, nd=2):
    g = g.simplify(0.02)
    if g.geom_type == 'Polygon': return dict(type='Polygon', coordinates=[[[round(x, nd), round(y, nd)] for x, y in g.exterior.coords]] + [[[round(x, nd), round(y, nd)] for x, y in i.coords] for i in g.interiors])
    if g.geom_type == 'MultiPolygon': return dict(type='MultiPolygon', coordinates=[rg(p)['coordinates'] for p in g.geoms])
    if g.geom_type == 'LineString': return dict(type='LineString', coordinates=[[round(x, nd), round(y, nd)] for x, y in g.coords])
    raise ValueError(g.geom_type)
# ---------------------------------------------------------------- the axis
TH = -3.0; T = math.tan(math.radians(-TH)); cs, sn = math.cos(math.radians(TH)), math.sin(math.radians(TH))
EU = (cs, sn); EV = (-sn, cs)                                   # along the axis (east) and across it (north)
K_E = (713382.7, 4331938.5); H_E = (713372.8, 4331751.9)          # Kenner and Hopkins at Freeman (kept)
WK, WH = SF['SB0799']['properties']['width_m'], SF['SB0775']['properties']['width_m']   # 18.29, 24.38 (Ben's merged streets)
dKH = (K_E[0] - H_E[0]) * EV[0] + (K_E[1] - H_E[1]) * EV[1]       # perpendicular distance between the centre lines
W = dKH - WK / 2 - WH / 2; HW = W / 2                             # inner edge to inner edge
O = (H_E[0] + EV[0] * (WH / 2 + HW), H_E[1] + EV[1] * (WH / 2 + HW))   # a point on the axis
U = lambda p: (p[0] - O[0]) * EU[0] + (p[1] - O[1]) * EU[1]
V = lambda p: (p[0] - O[0]) * EV[0] + (p[1] - O[1]) * EV[1]
X = lambda u, v: (O[0] + u * EU[0] + v * EV[0], O[1] + u * EU[1] + v * EV[1])
def uvpoly(pts): return Polygon([X(u, v) for u, v in pts])
def to_uv(g): return affine_transform(g, [EU[0], EU[1], EV[0], EV[1], -(O[0] * EU[0] + O[1] * EU[1]), -(O[0] * EV[0] + O[1] * EV[1])])
def from_uv(g): return affine_transform(g, [EU[0], EV[0], EU[1], EV[1], O[0], O[1]])
MIR = lambda g: from_uv(affine_transform(to_uv(g), [1, 0, 0, -1, 0, 0]))
def line_x(p, q, a, b):   # intersection of infinite lines pq and ab
    x1, y1 = p; x2, y2 = q; x3, y3 = a; x4, y4 = b
    d = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4); t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / d
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
LK = (K_E, (K_E[0] - 1000 * EU[0], K_E[1] - 1000 * EU[1])); LH = (H_E, (H_E[0] - 1000 * EU[0], H_E[1] - 1000 * EU[1]))
LA = (O, X(-1000, 0))
log = dict(axis=dict(theta=TH, point=[round(O[0], 2), round(O[1], 2)], inner_width=round(W, 2), kenner_w=WK, hopkins_w=WH))
OLD_ST = {}                                                      # street id -> old corridor (for the block recut)
def corr(c, w): return LineString(c).buffer(w / 2, cap_style=2, join_style=2, mitre_limit=3)
def set_street(i, c, w=None, note=None):
    f = SF[i]; OLD_ST.setdefault(i, corr(SC(i), f['properties']['width_m']))
    f['geometry'] = dict(type='LineString', coordinates=[[round(x, 2), round(y, 2)] for x, y in c])
    if w: f['properties']['width_m'] = w
    if note: f['properties']['clean17'] = note
def drop_street(i):
    f = SF[i]; OLD_ST.setdefault(i, corr(SC(i), f['properties']['width_m'])); f['_drop'] = True
# ---------------------------------------------------------------- streets
G_S, G_N = SC('S040')[-1], SC('S041')[0]                          # Garrard (the line through both stubs)
GK = line_x(*LK, G_S, G_N); GH = line_x(*LH, G_S, G_N)
kc = [tuple(q) for q in LAY['streets']['SB0799']['c']]; hc = [tuple(q) for q in LAY['streets']['SB0775']['c']]
assert abs(kc[2][0] - 712520.2) < 1 and abs(hc[2][0] - 712509.4) < 1, 'merged Kenner or Hopkins changed'
set_street('SB0799', kc[:2] + [GK, K_E], note='Kenner merged with S013 (Ben), straight and parallel to the CUT axis, Garrard to Freeman')
set_street('SB0775', hc[:2] + [GH, H_E], note='Hopkins merged with S012, SB0776, SB0777 (Ben), straight and parallel to the CUT axis, Garrard to Freeman')
for i in ('S013', 'S012', 'SB0776', 'SB0777'): drop_street(i)
d1, d2 = SC('SB0631'); DH = line_x(*LH, d1, d2); d3, d4 = SC('SB0630')[:2]; DK = line_x(*LK, d3, d4)
set_street('SB0631', [d1, DH]); set_street('SB0631U', [DH, DK]); set_street('SB0630', [DK] + SC('SB0630')[1:])
FRE = [c for c in zip(SC('SB0727'), SC('SB0727')[1:]) if min(c[0][1], c[1][1]) < 4331850 < max(c[0][1], c[1][1])][0]
BAY = [c for c in zip(SC('SB0559'), SC('SB0559')[1:]) if min(c[0][1], c[1][1]) < 4331850 < max(c[0][1], c[1][1])][0]
EZA = line_x(*LA, *FRE); EZB = line_x(*LA, *BAY)
e2 = SC('EZ2'); E2B = line_x(e2[1], e2[2], *BAY)
set_street('EZ1', [EZA, EZB], note='on the CUT axis, Freeman to Baymiller (the plaza driveways run straight on into it)')
set_street('EZ2', [E2B] + e2[1:], note='starts at Baymiller')
# ---------------------------------------------------------------- the terminal group: turned onto the axis, centred on it
def fit_axis(g, a0, x0, y0):
    from scipy.optimize import minimize
    def mirror(g, ang, x0, y0):
        a = math.radians(ang); c, s = math.cos(2 * a), math.sin(2 * a)
        return affine_transform(g, [c, s, s, -c, x0 - c * x0 - s * y0, y0 - s * x0 + c * y0])
    r = minimize(lambda v: g.symmetric_difference(mirror(g, v[0], x0, v[1])).area, [a0, y0], method='Nelder-Mead', options={'xatol': 1e-4, 'fatol': 0.5})
    return r.x[0], (x0, r.x[1])
DF = {f['properties'].get('layer'): f for f in D['features'] if f['properties'].get('layer', '').startswith('cut_')}
bld = shape(DF['cut_building']['geometry'])
ab, pb = fit_axis(bld, -3.8, 712905, bld.centroid.y)
dth = TH - ab; dv = -V(rotate(Point(pb), 0, origin=pb).coords[0])
def move_b(g): return translate(rotate(g, dth, origin=pb, use_radians=False), dv * EV[0], dv * EV[1])
def symm(g):   # north half and its mirror
    h = from_uv(to_uv(g).intersection(box(-1e4, 0, 1e4, 1e4)))
    return unary_union([h, MIR(h)]).buffer(0.01, join_style=2).buffer(-0.01, join_style=2)
bld2 = symm(move_b(bld))
ramps = [f for f in B['features'] if f['properties'].get('layer') == 'cut_road' and f['properties'].get('kind') == 'ramp']
log['terminal'] = dict(was_deg=round(ab, 3), turned_deg=round(dth, 3), shifted_m=round(dv, 2), building_v=[round(to_uv(bld2).bounds[1], 2), round(to_uv(bld2).bounds[3], 2)])
def rect_uv(g):   # (u0, u1, v-half) of a shape turned onto the axis
    b = to_uv(g).bounds; return b[0], b[2], (b[3] - b[1]) / 2
hh = move_b(shape(DF['cut_headhouse']['geometry'])); cc = move_b(shape(DF['cut_concourse']['geometry']))
hu0, hu1, hhv = rect_uv(hh); cu0, cu1, ccv = rect_uv(cc)
hh2 = uvpoly([(hu0, -hhv), (hu1, -hhv), (hu1, hhv), (hu0, hhv)])
bu0 = to_uv(bld2).bounds[0]
cc2 = uvpoly([(hu1, -ccv), (bu0 + 2, -ccv), (bu0 + 2, ccv), (hu1, ccv)]).difference(bld2).buffer(0)
cc2 = max(getattr(cc2, 'geoms', [cc2]), key=lambda q: q.area)
# platforms and terminal: top and bottom on the street inner edges, ends along the platforms (bearing 178.84 degrees)
pg = shape(DF['cut_precinct']['geometry']); px0, px1 = pg.bounds[0], pg.bounds[2]
tb = math.radians(178.84); tdir = (math.sin(tb), math.cos(tb))
def end_line(x_at_axis):
    a = line_x(*LA, (x_at_axis, 0), (x_at_axis, 1)); return (a, (a[0] + tdir[0] * 500, a[1] + tdir[1] * 500))
eW = end_line(X(hu0, 0)[0]); eE = end_line(px1)
LKs = (X(0, HW), X(-1000, HW)); LHs = (X(0, -HW), X(-1000, -HW))
prec2 = Polygon([line_x(*eW, *LKs), line_x(*eE, *LKs), line_x(*eE, *LHs), line_x(*eW, *LHs)])
# west park and terminal square: rectangles centred on the axis, the park against the headhouse
park = shape(DF['cut_park']['geometry']); sq = shape(DF['cut_square']['geometry'])
def mrr(g):
    c = list(g.minimum_rotated_rectangle.exterior.coords); a, b = math.dist(c[0], c[1]), math.dist(c[1], c[2]); return max(a, b), min(a, b)
pl_L, pl_H = mrr(park); sq_L, sq_H = mrr(sq)
park2 = uvpoly([(hu0 - pl_L, -pl_H / 2), (hu0, -pl_H / 2), (hu0, pl_H / 2), (hu0 - pl_L, pl_H / 2)])
sq2 = uvpoly([(hu0 - pl_L - sq_H, -sq_L / 2), (hu0 - pl_L, -sq_L / 2), (hu0 - pl_L, sq_L / 2), (hu0 - pl_L - sq_H, sq_L / 2)])
log['west'] = dict(park=[round(pl_L, 1), round(pl_H, 1)], square=[round(sq_L, 1), round(sq_H, 1)], headhouse_u=[round(hu0, 1), round(hu1, 1)])
# Garrard stubs to the park edges
set_street('S040', SC('S040')[:-1] + [line_x(G_S, G_N, X(0, -pl_H / 2), X(-1000, -pl_H / 2))])
set_street('S041', [line_x(G_S, G_N, X(0, pl_H / 2), X(-1000, pl_H / 2))] + SC('S041')[1:])
OLD_OCC = unary_union([shape(DF[k]['geometry']) for k in ('cut_building', 'cut_headhouse', 'cut_concourse', 'cut_precinct', 'cut_park', 'cut_square')])
for k, g in (('cut_building', bld2), ('cut_headhouse', hh2), ('cut_concourse', cc2), ('cut_precinct', prec2), ('cut_park', park2), ('cut_square', sq2)):
    DF[k]['geometry'] = rg(g); DF[k]['properties']['clean17'] = True
    if 'area_m2' in DF[k]['properties']: DF[k]['properties']['area_m2'] = round(g.area)
DF['cut_concourse']['properties']['length_m'] = round(to_uv(cc2).bounds[2] - to_uv(cc2).bounds[0], 1)
# ---------------------------------------------------------------- the plaza: onto the axis, mirror-symmetric, inside the street edges
EL = ('cut_plaza', 'cut_lincoln', 'cut_road', 'cut_terrace', 'cut_lawn', 'cut_walk')
PF = [f for f in B['features'] if f['properties'].get('layer') in EL]
OLD_OCC = unary_union([OLD_OCC] + [shape(f['geometry']).buffer(0) for f in PF if f['geometry']['type'] != 'LineString'])
GONE = {'North drive (Kenner side)', 'South drive (Hopkins side)', 'Freeman end drive'}
grp = unary_union([shape(f['geometry']) if f['geometry']['type'] != 'LineString' else shape(f['geometry']).buffer(1) for f in PF if f['properties'].get('kind') != 'ramp' and f['properties'].get('name') not in GONE])
ap, pp = fit_axis(grp, -3.0, 713150, 4331858.5)
d_p = TH - ap
def move_p(g):
    g = rotate(g, d_p, origin=pp); return translate(g, -V(pp) * EV[0], -V(pp) * EV[1])
for f in ramps: f['_g'] = move_b(shape(f['geometry']))       # the ramps go with the building
for f in PF:
    if '_g' not in f: f['_g'] = move_p(shape(f['geometry']))
log['plaza'] = dict(was_deg=round(ap, 3), turned_deg=round(d_p, 3), shifted_m=round(-V(pp), 2))
for f in PF:
    if f['properties'].get('name') in GONE: f['_drop'] = True
live = [f for f in PF if not f.get('_drop')]
def vc(f): return V(f['_g'].centroid.coords[0])
def same(a, b):
    if a.geom_type == 'LineString': return a.hausdorff_distance(b)
    i = a.intersection(b).area; return 1 - i / max(a.union(b).area, 1e-9)
pairs, selfs, alone = [], [], []
for f in live:
    g = f['_g']; m = MIR(g); s = same(g, m)
    if (g.geom_type == 'LineString' and s < 3) or (g.geom_type != 'LineString' and s < 0.5): selfs.append(f)
for f in live:
    if f in selfs or vc(f) <= 0: continue
    m = MIR(f['_g']); best = None
    for h in live:
        if h in selfs or vc(h) >= 0 or h['properties']['layer'] != f['properties']['layer'] or h.get('_paired'): continue
        s = same(m, h['_g'])
        if best is None or s < best[0]: best = (s, h)
    ok = best and ((f['_g'].geom_type == 'LineString' and best[0] < 8) or (f['_g'].geom_type != 'LineString' and best[0] < 0.7))
    if ok: best[1]['_paired'] = True; best[1]['_g'] = m; pairs.append((f['properties'].get('name'), round(best[0], 2)))
    else: alone.append(f['properties'].get('name'))
for f in live:
    if vc(f) < 0 and f not in selfs and not f.get('_paired'): alone.append(f['properties'].get('name') + ' (south)')
cross = []
for f in live:   # unpaired shapes across the axis (the central lawn, the fountain): centred on it, then made symmetric
    if f in selfs or f.get('_paired') or f['_g'].geom_type == 'LineString': continue
    b = to_uv(f['_g']).bounds
    if b[1] < -1 and b[3] > 1:
        m = (b[1] + b[3]) / 2; f['_g0'] = f['_g']; f['_g'] = translate(f['_g'], -m * EV[0], -m * EV[1]); selfs.append(f); cross.append([f['properties'].get('name'), round(-m, 2)]); f['_m'] = m
        alone.remove(f['properties'].get('name')) if f['properties'].get('name') in alone else None
for f in live:   # small pieces inside a centred shape (the fountain's basin) move with it
    if f in selfs or f.get('_paired') or f['_g'].geom_type == 'LineString': continue
    host = next((h for h in selfs if '_g0' in h and f['_g'].within(h['_g0'].envelope.buffer(1))), None)
    if host:
        f['_g'] = translate(f['_g'], -host['_m'] * EV[0], -host['_m'] * EV[1]); selfs.append(f); cross.append([f['properties'].get('name'), round(-host['_m'], 2)])
        if f['properties'].get('name') in alone: alone.remove(f['properties'].get('name'))
for f in selfs:
    f.pop('_g0', None); f.pop('_m', None)
    g = f['_g']
    if g.geom_type == 'LineString':
        a, b = g.coords[0], g.coords[-1]; mb = MIR(Point(b)).coords[0]; a2 = ((a[0] + mb[0]) / 2, (a[1] + mb[1]) / 2)
        f['_g'] = LineString([a2, MIR(Point(a2)).coords[0]])
    else: f['_g'] = symm(g)
log['plaza'].update(pairs=len(pairs), self_symmetric=len(selfs), unpaired=alone)
# clip to the street inner edges and Freeman's west edge
fre_l = LineString(FRE); fre_w = SF['SB0727']['properties']['width_m']
ZONE = uvpoly([(-1000, -HW), (1000, -HW), (1000, HW), (-1000, HW)]).difference(fre_l.buffer(fre_w / 2, cap_style=2).union(box(fre_l.bounds[2], 4.3e6, 7.2e5, 4.34e6)))
ZONE = max(getattr(ZONE, 'geoms', [ZONE]), key=lambda q: q.area if q.centroid.x < 713380 else 0)
ezs = []
for f in PF:
    if f.get('_drop'): continue
    g = f['_g'].intersection(ZONE)
    if g.is_empty: f['_drop'] = True; continue
    if g.geom_type == 'GeometryCollection': g = unary_union([q for q in g.geoms if q.geom_type in ('Polygon', 'MultiPolygon')]) if f['_g'].geom_type != 'LineString' else unary_union([q for q in g.geoms if 'Line' in q.geom_type])
    if g.geom_type == 'MultiLineString': g = max(g.geoms, key=lambda q: q.length)
    if g.geom_type == 'MultiPolygon':
        g = MultiPolygon([q for q in g.geoms if q.area > 2]);
        if len(g.geoms) == 1: g = g.geoms[0]
    f['_g'] = g
    if f['properties'].get('kind') == 'drive' and 'driveway' in f['properties'].get('name', ''): ezs.append(to_uv(g).bounds)
log['plaza']['driveways_v'] = [[round(b[1], 2), round(b[3], 2)] for b in ezs]
log['plaza']['centred'] = cross
EZW = round(2 * max(max(abs(b[1]), abs(b[3])) for b in ezs), 2)   # Ezzard Charles as wide as the plaza driveways' outer edges
SF['EZ1']['properties'].update(width_m=EZW, width_ft=round(EZW / 0.3048), width_src='the CUT plaza driveways, outer edge to outer edge (1931 plot plan), carried on to Baymiller (17 October)')
log['ezzard_w'] = EZW
for f in PF:
    if f.get('_drop'): continue
    f['geometry'] = rg(f.pop('_g')); f['properties']['clean17'] = True; f['properties'].pop('aligned17', None); f.pop('_paired', None)
    if 'area_m2' in f['properties']: f['properties']['area_m2'] = round(shape(f['geometry']).area)
NEW_OCC = unary_union([shape(DF[k]['geometry']) for k in ('cut_building', 'cut_headhouse', 'cut_concourse', 'cut_precinct', 'cut_park', 'cut_square')] + [shape(f['geometry']).buffer(0) for f in PF if not f.get('_drop') and f['geometry']['type'] != 'LineString'])
# other street ends that sat in the old or new Ezzard Charles (alleys run to its centre line); the alley north of it goes
ez_old = OLD_ST['EZ1']; ez_new = corr(SC('EZ1'), SF['EZ1']['properties']['width_m'])
for i, f in SF.items():
    if i in ('EZ1', 'EZ2', 'SB0727', 'SB0559') or f['properties'].get('kind') == 'NS' and False: continue
    c = SC(i); l = LineString(c)
    if i == 'SB0021' or (l.within(ez_new.buffer(1))): drop_street(i); log.setdefault('dropped', []).append(i); continue
    for end in (0, -1):
        p = Point(c[end])
        if (p.within(ez_old) or p.within(ez_new)) and len(c) >= 2:
            q = c[1] if end == 0 else c[-2]; ang = abs(math.degrees(math.atan2(c[end][1] - q[1], c[end][0] - q[0])) % 180 - 90)
            if ang > 45: continue                                   # only cross streets and alleys
            nc = list(c); nc[end] = line_x(q, c[end], *LA); set_street(i, nc); log.setdefault('ends_moved', []).append(i)
STATE = dict(D=D, B=B, P=P, LAY=LAY, OLD_ST=OLD_ST, OLD_OCC=OLD_OCC, NEW_OCC=NEW_OCC, SF=SF, log=log, corr=corr, rg=rg, X=X, U=U, V=V, HW=HW, EV=EV, EU=EU)
if __name__ == '__main__':
    print(json.dumps(log, indent=1))
def strip(F): return [f for f in F['features'] if not f.get('_drop')]
if DRY and __name__ == '__main__':
    json.dump(dict(D, features=strip(D)), open(S + 'cut/prev_deck.json', 'w')); json.dump(dict(B, features=strip(B)), open(S + 'cut/prev_basin.json', 'w'))
