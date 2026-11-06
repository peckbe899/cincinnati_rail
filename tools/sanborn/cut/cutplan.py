try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben (17 October): the CUT box (Kenner, Hopkins, Freeman and the terminal) was still wrong. He gave a GeoTIFF of the 1931 plot plan
# (CUT_Layout.tif, EPSG:3857) lined up with the real ground, and said the blocks are right. Everything in the box is redrawn from it:
# the plan's own axis (-3.35 degrees, symmetric to within its drafting), Kenner and Hopkins parallel to it between the plaza's property
# line and the blocks, the terminal group moved onto that axis, and the plaza traced from the plan (north half, mirrored).
# Coordinates below are (u, v) on the plan axis: u east along it (0 at Freeman), v north of it. Traced by eye on cutgeo/rect.png (2 m grid).
# Replaces the cutclean layout. Reads deckpage/*.json and plots/live4/deck/layout.json; imported by cutplan2.py (block and lot recut).
import json, math, sys
from shapely.geometry import shape, mapping, LineString, Polygon, MultiPolygon, Point, box
from shapely.affinity import affine_transform, translate
from shapely.ops import unary_union
S = _ws.DATA
D = json.load(open(S + 'deckpage/deck.json')); B = json.load(open(S + 'deckpage/basin.json')); P = json.load(open(S + 'deckpage/plots.json'))
if D.get('plan17'): sys.exit('already done')
LAY = json.load(open(S + 'plots/live4/deck/layout.json'))
FE = D['features'] + B['features']
SF = {f['properties']['id']: f for f in FE if f['properties'].get('layer') == 'street'}
SC = lambda i: [tuple(q) for q in SF[i]['geometry']['coordinates']]
# ---------------------------------------------------------------- frames
J = json.load(open(S + 'cutgeo/rect.json')); A = math.radians(J['th']); CX, CY = J['cx'], J['cy']
EU = (math.cos(A), math.sin(A)); EV = (-math.sin(A), math.cos(A))
X = lambda u, v: (CX + u * EU[0] + v * EV[0], CY + u * EU[1] + v * EV[1])
U = lambda p: (p[0] - CX) * EU[0] + (p[1] - CY) * EU[1]
V = lambda p: (p[0] - CX) * EV[0] + (p[1] - CY) * EV[1]
to_uv = lambda g: affine_transform(g, [EU[0], EU[1], EV[0], EV[1], -(CX * EU[0] + CY * EU[1]), -(CX * EV[0] + CY * EV[1])])
from_uv = lambda g: affine_transform(g, [EU[0], EV[0], EU[1], EV[1], CX, CY])
uvpoly = lambda pts: Polygon([X(u, v) for u, v in pts])
mir = lambda pts: [(u, -v) for u, v in pts]
TH0 = math.radians(-3.0); O0 = (713377.77, 4331846.72)        # the cutclean axis the terminal group was built on
to_uv0 = lambda g: affine_transform(g, [math.cos(TH0), math.sin(TH0), -math.sin(TH0), math.cos(TH0), -(O0[0] * math.cos(TH0) + O0[1] * math.sin(TH0)), -(-O0[0] * math.sin(TH0) + O0[1] * math.cos(TH0))])
DU = -5.0                                                         # the terminal's front onto the plan's (fitted by eye on the ramps and front)
def regroup(g): return from_uv(translate(to_uv0(g), DU, 0))
def rg(g, nd=2):
    if g.geom_type == 'LinearRing': g = LineString(g.coords)
    g = g.simplify(0.02)
    if g.geom_type == 'Polygon': return dict(type='Polygon', coordinates=[[[round(x, nd), round(y, nd)] for x, y in g.exterior.coords]] + [[[round(x, nd), round(y, nd)] for x, y in i.coords] for i in g.interiors])
    if g.geom_type == 'MultiPolygon': return dict(type='MultiPolygon', coordinates=[rg(p)['coordinates'] for p in g.geoms])
    if g.geom_type == 'LineString': return dict(type='LineString', coordinates=[[round(x, nd), round(y, nd)] for x, y in g.coords])
    raise ValueError(g.geom_type)
def line_x(p, q, a, b):
    x1, y1 = p; x2, y2 = q; x3, y3 = a; x4, y4 = b
    d = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4); t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / d
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
Lv = lambda v: (X(-2000, v), X(200, v))                          # a line parallel to the axis at v
log = dict(axis=dict(theta=J['th'], through=[CX, CY]))
OLD_ST = {}
def corr(c, w): return LineString(c).buffer(w / 2, cap_style=2, join_style=2, mitre_limit=3)
def set_street(i, c, w=None, note=None):
    f = SF[i]; OLD_ST.setdefault(i, corr(SC(i), f['properties']['width_m']))
    f['geometry'] = dict(type='LineString', coordinates=[[round(x, 2), round(y, 2)] for x, y in c])
    if w: f['properties']['width_m'] = w; f['properties']['width_ft'] = round(w / 0.3048)
    if note: f['properties']['plan17'] = note
# ---------------------------------------------------------------- streets (plan: plaza property line v +83.8 / -85.0; Kenner's north
# property line 104.0 (blocks at 104.3-107.6); the blocks south of Hopkins at -99.8 to -102.1, so Hopkins runs to -100.8)
KN0, KN1 = 86.0, 104.3; HO0, HO1 = -86.0, -105.5       # Kenner and Hopkins on the plan's property lines (Ben: follow the plans; the blocks south of Hopkins give way)
KC, KW = (KN0 + KN1) / 2, KN1 - KN0; HC, HW = (HO0 + HO1) / 2, HO0 - HO1
FRE = [c for c in zip(SC('SB0727'), SC('SB0727')[1:]) if min(c[0][1], c[1][1]) < 4331850 < max(c[0][1], c[1][1])][0]
BAY = [c for c in zip(SC('SB0559'), SC('SB0559')[1:]) if min(c[0][1], c[1][1]) < 4331850 < max(c[0][1], c[1][1])][0]
G_S, G_N = SC('S040')[0], SC('S041')[-1]                         # Garrard, far ends (the stub ends move)
kc0, hc0 = SC('SB0799'), SC('SB0775')
set_street('SB0799', kc0[:2] + [line_x(*Lv(KC), G_S, G_N), line_x(*Lv(KC), *FRE)], KW, f'Kenner on the 1931 plot plan (CUT_Layout.tif): plaza property line to its north property line, {KW:.1f} m, parallel to the plan axis')
set_street('SB0775', hc0[:2] + [line_x(*Lv(HC), G_S, G_N), line_x(*Lv(HC), *FRE)], HW, f'Hopkins: the plan’s plaza property line to the blocks south of it, {HW:.1f} m, parallel to the plan axis')
d1, d2 = SC('SB0631')[0], SC('SB0631')[-1]; DH = line_x(*Lv(HC), d1, d2); d4 = SC('SB0630')[-1]; DK = line_x(*Lv(KC), DH, d4)
set_street('SB0631', [d1, DH]); set_street('SB0631U', [DH, DK]); set_street('SB0630', [DK, d4])
for i, Lc in (('SB0641', KC), ('SB0355', KC), ('SB0399', HC), ('SB0759', HC)):
    if i not in SF: continue
    c = SC(i); far = max(c, key=lambda q: abs(V(q))); near = min(c, key=lambda q: abs(V(q)))
    if abs(V(near)) > 140: continue
    set_street(i, [far, line_x(far, near, *Lv(Lc))] if c[0] == far else [line_x(far, near, *Lv(Lc)), far])
EZA = line_x(*Lv(0), *FRE); EZB = line_x(*Lv(0), *BAY)
DRV = 23.5                                                       # the plaza driveways' outer edges (plan, v +-23.5)
set_street('EZ1', [EZA, EZB], 2 * DRV, 'on the plan axis, Freeman to Baymiller, as wide as the plaza driveways outer edge to outer edge (1931 plot plan, CUT_Layout.tif)')
SF['EZ1']['properties']['width_src'] = 'the CUT plaza driveways, outer edge to outer edge (1931 plot plan, GeoTIFF), carried on to Baymiller (17 October)'
e2 = LAY['streets'].get('EZ2', {}).get('c') or SC('EZ2')
log['streets'] = dict(kenner=[KN0, KN1], hopkins=[HO0, HO1], ezzard_w=2 * DRV)
# ---------------------------------------------------------------- the terminal group onto the plan axis (rigid: turned 0.35 degrees)
DF = {f['properties'].get('layer'): f for f in D['features'] if f['properties'].get('layer', '').startswith('cut_')}
OLD_OCC = unary_union([shape(DF[k]['geometry']) for k in ('cut_building', 'cut_headhouse', 'cut_concourse', 'cut_precinct', 'cut_park', 'cut_square')])
for k in ('cut_building', 'cut_headhouse', 'cut_concourse', 'cut_park', 'cut_square'):
    DF[k]['geometry'] = rg(regroup(shape(DF[k]['geometry']))); DF[k]['properties']['plan17'] = True
# the terminal footprint from Ben's georeferenced first-floor plan (Cincinnati_Union_Terminal_First_Floor.tif), traced on the plan axis
# (north half, mirrored; the sheet's own centre line lies 0.5 m south of the plot plan's, taken out); the train concourse 24.5 m wide
def _arc(cu, cv, r, a0, a1, n=14): return [(cu + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)), cv + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]
_fn = [(-545.5, 12.25), (-545.5, 25.0), (-512.0, 25.0), (-512.0, 57.0), (-493.5, 57.0), (-493.5, 43.8), (-467.5, 43.8)] + _arc(-419, 35.5, 49.5, 170.3, 90)[1:] + \
      [(-417.5, 78.0), (-415.5, 77.8), (-414.0, 68.2), (-416.0, 55.1)] + _arc(-419, 35.5, 19.6, 81, 178)[1:] + [(-438.0, 26.5), (-434.0, 24.5), (-434.0, 0.0)]
_fp = Polygon([(-545.5, 0)] + _fn + [(u, -v) for u, v in _fn[::-1]]).buffer(0)
# (18 October, Ben: wings and back section did not match) the outline is now the sheet's own cut-out edge (its alpha mask, cutgeo/mask.py),
# not a hand trace and not mirrored; west of u -534 the track sheet covers it, so the back section's west face (u -545.5) is from the drawing
_mk = to_uv(shape(json.load(open(S + 'cutgeo/ff_mask.json')))).intersection(box(-534, -200, 0, 200))
_wu = lambda v: -545.3 - 0.08 * (v - 11.8)       # the back section's west wall, parallel to the tracks (first floor: -546.3 at v 24.3, -541.8 at v -26.2)
_fp = unary_union([_mk, Polygon([(_wu(24.4), 24.4), (-534, 24.4), (-534, -26.2), (_wu(-26.2), -26.2)])]).buffer(0.05, join_style=2).buffer(-0.05, join_style=2).simplify(0.1)
_old_b = shape(DF['cut_building']['geometry'])
DF['cut_building']['geometry'] = rg(from_uv(_fp)); DF['cut_building']['properties'].update(src='First-floor plan, Cincinnati Union Terminal (Ben\u2019s georeferenced sheet, Cincinnati_Union_Terminal_First_Floor.tif)', area_m2=round(_fp.area),
    note='first floor: wings, rotunda, front and the bus and cab arms (17 October, from the georeferenced sheet)')
_hb0 = to_uv(shape(DF['cut_headhouse']['geometry'])).bounds
_cc = Polygon([(_hb0[2], -12.25), (-545.5, -12.25), (-545.5, 12.25), (_hb0[2], 12.25)])
DF['cut_concourse']['geometry'] = rg(from_uv(_cc)); DF['cut_concourse']['properties'].update(length_m=round(-545.5 - _hb0[2], 1), area_m2=round(_cc.area), src='First-floor plan (georeferenced sheet): 24.5 m wide, carried on west to the west headhouse')
log['terminal'] = dict(building_m2=round(_fp.area), was_m2=round(_old_b.area), front_u=-434.0, arms_u=-414.0, concourse_w=24.5)
pr = to_uv(regroup(shape(DF['cut_precinct']['geometry'])))
c = list(pr.exterior.coords)[:-1]; west = sorted(c, key=lambda q: q[0])[:2]; east = sorted(c, key=lambda q: -q[0])[:2]
lxu = lambda pa, pb, v: (pa[0] + (pb[0] - pa[0]) * (v - pa[1]) / (pb[1] - pa[1]), v)
prec = Polygon([lxu(*west, KN0), lxu(*east, KN0), lxu(*east, HO0), lxu(*west, HO0)])
DF['cut_precinct']['geometry'] = rg(from_uv(prec)); DF['cut_precinct']['properties']['plan17'] = True
# Ben: the park and buildings linked: headhouse, west park and terminal square one band with the platforms, Kenner to Hopkins
hb = to_uv(shape(DF['cut_headhouse']['geometry'])).bounds; pb = to_uv(shape(DF['cut_park']['geometry'])).bounds; sb = to_uv(shape(DF['cut_square']['geometry'])).bounds
# Ben: the west headhouse overlapped the station viaduct; its east face goes to the viaduct's west edge (structures.json), same depth
_st = unary_union([to_uv(shape(f['geometry'])) for f in json.load(open(S + 'deckpage/structures.json'))['features'] if f['properties']['layer'] == 'struct'])
_vw = _st.intersection(box(-900, HO0, -560, KN0)).bounds[0] - 0.3
if hb[2] > _vw: _d = hb[2] - _vw; hb = (hb[0] - _d, hb[1], _vw, hb[3]); log['headhouse_moved_m'] = round(_d, 2)
prec = Polygon([(hb[2], KN0), (-434.0, KN0), (-434.0, HO0), (hb[2], HO0)])        # the terminal grounds end at the building front
DF['cut_precinct']['geometry'] = rg(from_uv(prec))
band = lambda u0, u1: from_uv(Polygon([(u0, HO0), (u1, HO0), (u1, KN0), (u0, KN0)]))
DF['cut_concourse']['geometry'] = rg(from_uv(Polygon([(hb[2], -12.25), (_wu(-12.25), -12.25), (_wu(12.25), 12.25), (hb[2], 12.25)]))); DF['cut_concourse']['properties']['length_m'] = round(-545.5 - hb[2], 1)
DF['cut_headhouse']['geometry'] = rg(band(hb[0], hb[2])); DF['cut_park']['geometry'] = rg(band(pb[0], hb[0])); DF['cut_square']['geometry'] = rg(band(sb[0], pb[0]))
for k in ('cut_headhouse', 'cut_park', 'cut_square'): DF[k]['properties']['note'] = 'one band with the platforms and the terminal, Kenner to Hopkins (Ben, 17 October)'
DF['cut_park']['properties']['area_m2'] = round(shape(DF['cut_park']['geometry']).area)
set_street('S040', SC('S040')[:-1] + [line_x(G_S, G_N, *Lv(HC))]); set_street('S041', [line_x(G_S, G_N, *Lv(KC))] + SC('S041')[1:])
# ---------------------------------------------------------------- the plaza, traced (north half; the south half is its mirror)
NEW = []
def add(layer, name, g, **kw):
    NEW.append(dict(type='Feature', properties=dict(layer=layer, name=name, src='Plot plan, Cincinnati Union Terminal, 1 June 1931 (HABS OH-705, sheet 1), traced on Ben’s GeoTIFF (CUT_Layout.tif)', plan17=True, **kw), geometry=rg(g)))
def both(layer, name, pts, **kw):
    for nm, q in ((name + (' (north)' if name else ''), pts), (name + (' (south)' if name else ''), mir(pts))):
        add(layer, nm, uvpoly(q).buffer(0), **kw)
def arc(cu, cv, r, a0, a1, n=12): return [(cu + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)), cv + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]
FW = U(FRE[0]) if False else None
fre_w = SF['SB0727']['properties']['width_m']; FU = U(line_x(*Lv(0), *FRE)) - fre_w / 2          # Freeman's west edge on the axis
# whole box east of the terminal (the former Lincoln Park): from the terminal front to Freeman, plaza property line to plaza property line
boxp = Polygon([X(-440, KN0), X(FU, KN0), X(FU, HO0), X(-440, HO0)]).difference(shape(DF['cut_building']['geometry']))
add('cut_lincoln', 'Former Lincoln Park: the terminal approach (1933)', boxp)
LP = next(f for f in B['features'] if f['properties'].get('id') == 'SBB0453')
LP['geometry'] = rg(boxp); LP['properties']['area_m2'] = round(boxp.area); LP['properties']['plan17'] = 'the whole plaza east of the terminal, Kenner to Hopkins to Freeman (one park lot)'
E0, N0 = P['o']
def enc1(poly):
    c = list(poly.exterior.coords)[:-1]; q = [(round((x - E0) * 10), round((y - N0) * 10)) for x, y in c]; a = [q[0][0], q[0][1]]
    for i in range(1, len(q)): a += [q[i][0] - q[i - 1][0], q[i][1] - q[i - 1][1]]
    return a
bp = max(getattr(boxp, 'geoms', [boxp]), key=lambda g: g.area)
P['plots'] = [p for p in P['plots'] if p[1] != 'SBB0453'] + [['SBB0453-001', 'SBB0453', 'l', None, None, [], [enc1(bp.simplify(0.05))]]]
# forecourt (Plaza Driveway) with the two straight driveways: one paved area
fc = [(-437, 0), (-437, 22)] + arc(-417, 26, 20, 180, 112, 6)[1:] + [(-401, 49.5), (-386, 56), (-366, 49.5), (-306, 49.5)] + arc(-306, 45.5, 4, 90, 0, 3)[1:] + [(-302, 24), (FU, 24), (FU, 0)]
pz = uvpoly(fc + mir(fc[::-1])).buffer(0).difference(shape(DF['cut_building']['geometry']))
add('cut_plaza', 'Terminal plaza (1933)', pz)
both('cut_road', 'Driveway', [(-302, 10.5), (FU, 10.5), (FU, 23.5), (-302, 23.5)], kind='drive')
both('cut_road', 'Drive along the street', [(-420, 75.5), (-264, 75.5), (-256, 77), (-248, 80), (-248, 83.5), (-420, 83.5)], kind='drive')
# terrace group: outer curb, the arched pergola pools, two lawn panels, terrace steps, cascade
tg = [(-421, 0)] + arc(-411, 25, 10, 180, 90, 6) + [(-373, 35), (-346, 15), (-346, 0)]
add('cut_terrace', 'Terrace and cascade', uvpoly(tg + mir(tg[::-1])).buffer(0))
both('cut_lawn', 'Lawn', [(-400, 14), (-400, 29)] + arc(-397, 29, 3, 180, 90, 3)[1:] + [(-380, 32)] + arc(-380, 29, 3, 90, 0, 3)[1:] + [(-377, 14)])
both('cut_lawn', 'Lawn', [(-374.5, 29.5), (-356, 21), (-366.5, 10.5), (-371, 13.5), (-374.5, 14)])
both('cut_lawn', 'Lawn', [(-366.5, 8.5), (-354.5, 17.5), (-347.5, 14), (-349, 3), (-351, 2), (-362.5, 2), (-363, 5)])
both('cut_lawn', 'Lawn', [(-339, 32), (-334, 34), (-320, 34.5), (-318.5, 30), (-319, 25.5), (-322, 24.5), (-326, 25.5)])
for v in (1,):
    for s in (1, -1):
        add('cut_walk', 'Pool and pergola', LineString([X(-416, s * 0.5), X(-416, s * 24.5)] + [X(u, s * w) for u, w in arc(-410, 24.5, 6, 180, 0, 8)] + [X(-404, s * 0.5)]))
add('cut_walk', 'Fountain circle', uvpoly(arc(-368, 20, 3, 0, 360, 16)).buffer(0)); add('cut_walk', 'Fountain circle', uvpoly(arc(-368, -20, 3, 0, 360, 16)).buffer(0))
# north lawn (and its mirror): west arm north of the driveway curve, then the long lawn to the Freeman corner
nl = [(-411, 75.5), (-384, 61), (-377, 52.5), (-300, 52.5), (-300, 24), (-46, 24), (-39, 24.5), (-38, 35), (-22, 41), (-22, 76)] + arc(-26, 76, 4, 0, 90, 3)[1:] + [(-248, 80), (-256, 77), (-264, 75.5)]
both('cut_lawn', 'Lawn', nl)
# central lawn: west part (round west end), fountain ring, east part (round east end)
cw = arc(-308, 0, 10.5, 90, 270, 10) + [(-138, -10.5), (-138, 10.5)]
add('cut_lawn', 'Lawn', uvpoly(cw).buffer(0))
add('cut_lawn', 'Lawn', uvpoly([(-95, 10.5), (-95, -10.5)] + arc(-50.5, 0, 10.5, -90, 90, 10)).buffer(0))
add('cut_lawn', 'Lawn', uvpoly(arc(-116.5, 0, 9, 0, 360, 24)).buffer(0))
add('cut_walk', 'Fountain circle', uvpoly(arc(-116.5, 0, 11.5, 0, 360, 24)).exterior)
add('cut_walk', 'Fountain circle', uvpoly(arc(-116.5, 0, 1.5, 0, 360, 12)).buffer(0))
# walks in the north lawn (lines; mirrored)
WALK = [[(-320, 50.5), (-292, 50.5)], [(-292, 44), (-252, 44)], [(-292, 56), (-252, 56)], [(-252, 50.5), (-232, 50.5)],
        [(-245.5, 80), (-245.5, 24)], [(-258, 40), (-232, 40), (-232, 58), (-258, 58), (-258, 40)],
        [(-232, 59), (-136, 59)], [(-232, 41), (-136, 41)], [(-300, 32), (-52, 32)],
        [(-135, 24), (-135, 58)] + arc(-116, 58, 19, 180, 0, 10)[1:] + [(-97, 24)], [(-116.5, 80), (-116.5, 24)], [(-135, 50), (-97, 50)],
        [(-97, 51), (-55.5, 51)], [(-49, 53), (-24, 76)], [(-49, 48), (-30, 36)], [(-60, 24), (-60, 32)]]
for w in WALK:
    for s in (1, -1): add('cut_walk', 'Walk', LineString([X(u, s * v) for u, v in w]))
for cu, cv, r in ((-245.5, 50.5, 6), (-116.5, 50, 5), (-52, 50.5, 3.5)):
    for s in (1, -1): add('cut_walk', 'Fountain circle', uvpoly(arc(cu, s * cv, r, 0, 360, 16)).exterior)
for s in (1, -1): add('cut_walk', 'Monument', uvpoly(arc(-28, s * 30, 2.2, 0, 360, 12)).buffer(0))
# ---------------------------------------------------------------- bus and cab ramps go with the terminal; the old plaza layers are replaced
EL = ('cut_plaza', 'cut_lincoln', 'cut_road', 'cut_terrace', 'cut_lawn', 'cut_walk')
OLD_OCC = unary_union([OLD_OCC] + [shape(f['geometry']).buffer(0) for f in B['features'] if f['properties'].get('layer') in EL and f['geometry']['type'] != 'LineString'])
keep = []
for f in B['features']:
    p = f['properties']
    if p.get('layer') == 'cut_road' and p.get('kind') == 'ramp': continue          # redrawn from the main-floor sheet below
    if p.get('layer') in EL: continue
    keep.append(f)
# bus and cab drives in the terminal's arms (main-floor sheet, Cincinnati_Union_Terminal_Main_Floor.tif): bus drive outside, cab drive inside
for side, cv in (('north', 35.9), ('south', -35.9)):          # arcs fitted to the sheet's arm edges: centre (-420.1, +-35.9), radii 18.3 and 49.4
    for nm, r0, r1 in (('Bus drive', 33.0, 49.4), ('Cab drive', 18.3, 33.0)):
        a0, a1 = (88, 173) if cv > 0 else (-173, -88)
        ring = _arc(-420.1, cv, r1, a0, a1) + _arc(-420.1, cv, r0, a1, a0)
        add('cut_road', f'{nm} ({side})', uvpoly(ring).buffer(0).intersection(_fp), kind='ramp', note='down to the bus and cab concourse at track level, under the arms (main-floor plan)')
B['features'] = keep + NEW
NEW_OCC = unary_union([shape(DF[k]['geometry']) for k in ('cut_building', 'cut_headhouse', 'cut_concourse', 'cut_precinct', 'cut_park', 'cut_square')] + [shape(f['geometry']).buffer(0) for f in NEW if f['geometry']['type'] != 'LineString'])
log['plaza'] = dict(features=len(NEW))
# the cutclean2 interface
STATE = None
HW_ = None
if __name__ == '__main__':
    print(json.dumps(log, indent=1))
