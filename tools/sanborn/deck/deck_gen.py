"""Mill Creek deck street layer, first pass (EPSG:26916, metres).
Inputs: georeferenced 1904 Sanborn fits (lph/tf_all.json + lph/tps.pkl; was sheet_tf.json), OSM / 1912 lines, map 3 deck corridor (corr.geojson),
CUT footprint (cut_osm.geojson). Output: deck.json (params + features + anchors) for the page.
Design (Ben, 2026-10-10): new boulevard on the Mill Creek line, straight, from the Palace roundabout
(Queen City / Harrison) south past CUT to W 6th; Liberty, Gest and 8th continuous; other streets T in;
CUT rear headhouse with a shorter, plainer park on CUT's axis to a square on the boulevard;
only yards and the culverted creek under the deck; blocks over the yards a mixture."""
import json, math, numpy as np, sys
from shapely.geometry import LineString, Point, Polygon, MultiPolygon, mapping, shape, box
from shapely.ops import unary_union, nearest_points
from shapely import affinity
sys.path.insert(0, '.')
from joint import apply

FT = 0.3048
# 2026-10-13: sheets from the joint refit (lph/tf_all.json, basin method) with the Lower Price Hill spline onto the 1922
# plates (lph/tps.pkl); deck/sheet_tf.json is the superseded deck fit
import pickle
sys.path.insert(0, '../lph')
import tps as _tps
TF = json.load(open('../lph/tf_all.json')); _M = pickle.load(open('../lph/tps.pkl', 'rb'))
L12 = json.load(open('lines1912.json'))
def P(s, x, y):
    f = s if s in TF else s + 'm'
    e, n = apply(np.array(TF[f]), x, y); dE, dN = _tps.disp(f, np.array([e]), np.array([n]), _M)
    return (float(e + dE[0]), float(n + dN[0]))

PAR = dict(blvd_w=70.0, rb_r=80.0, sq=140.0, park_w=100.0, hh_w=110.0, hh_d=35.0, plat_w=152.0,
           palace_w=180.0, palace_d=80.0, palace_gap=55.0, t_w=60 * FT, ns_w=60 * FT)

# ---------------------------------------------------------------- basin streets the deck streets continue (Sanborn 1904 layer, 2026-10-11)
# Each deck street that carries a West End street across the yards starts where that street's basin centreline meets the
# deck edge and runs on the basin street's own line, so the two read as one street.
BASIN = [f for f in json.load(open('../sbg/fit/basin_sanborn.json'))['features'] if f['properties']['layer'] == 'street']
BKEY = {'W 7th': 'West 7th Street', 'Budd': 'Budd Street', 'W 9th': 'West 9th Street', 'Richmond': 'Richmond Street',
        'Hopkins': 'Hopkins Street', 'Kenner': 'Kenner', 'Courtland': 'Courtland', 'Wilstach': 'Wilstach Street', 'Wade': 'Wade Street',
        'Flint': 'Flint', 'Findlay': 'Findlay Street', 'Poplar': 'Poplar Street', 'Sherman': 'Sherman Avenue', 'Bank': 'Bank Street',
        'Dayton': 'Dayton Street', 'Exeter': 'Exeter Street', 'York': 'York Street', 'Clark': 'Clark Street', 'Oehler': 'Oehler Street',
        'W 6th': 'West 6th Street', 'W 8th (viaduct line)': 'West 8th Street', 'Gest': 'Gest Street', 'W Liberty': 'West Liberty Street',
        'Dolph': 'Dolph Street', 'McRoberts': 'McRoberts Street', 'Western': 'Western Avenue', 'Harrison': 'Harrison Avenue'}
def basin_end(dname, near, maxd=250.0):
    """(west end, unit vector pointing west along the basin street's west run) of the basin piece named for dname whose
    west end is nearest 'near'; None if there is none within maxd."""
    bn = BKEY.get(dname); best = None
    if not bn: return None
    for f in BASIN:
        if f['properties']['name'] != bn: continue
        c = np.array(f['geometry']['coordinates'])
        if c[0][0] > c[-1][0]: c = c[::-1]
        d = float(np.hypot(*(c[0] - np.asarray(near))))
        if best is None or d < best[0]: best = (d, c)
    if best is None or best[0] > maxd: return None
    c = best[1]; j = 1
    while j < len(c) - 1 and np.hypot(*(c[j] - c[0])) < 40: j += 1
    v = c[0] - c[j]; return (float(c[0][0]), float(c[0][1])), v / np.linalg.norm(v)
# ---------------------------------------------------------------- boulevard axis (fit to the 1904 creek)
creek = [P('464', 6250, 3000), P('468', 6224, 1770), P('201', 1720, 7000), P('201', 1720, 600),
         P('211', 1180, 4000), P('221', 250, 3000), P('233', 300, 6000), P('245', 350, 3000)]
c = np.array(creek); b1, a1 = np.polyfit(c[:, 1] - 4332000, c[:, 0], 1)
def axE(n): return a1 + b1 * (n - 4332000)
QCW = LineString(L12['QC_w1912']); QCE = LineString(L12['QC1912'])
far = LineString([(axE(4330000), 4330000), (axE(4335000), 4335000)])
RB = far.intersection(QCE); RB = (RB.x, RB.y)
W6 = LineString([(712016, 4330962), (712108, 4330898), (712655, 4330863), (712788, 4330855)])
S0 = far.intersection(W6); S0 = (S0.x, S0.y)
AX = LineString([S0, RB])
ux, uy = (RB[0] - S0[0]) / AX.length, (RB[1] - S0[1]) / AX.length   # unit along axis (north)
px, py = uy, -ux                                                      # unit to the east (right of north)

def off_line(d):   # line parallel to the axis, d metres east
    return LineString([(S0[0] + px * d - ux * 50, S0[1] + py * d - uy * 50), (RB[0] + px * d + ux * 50, RB[1] + py * d + uy * 50)])
BW = PAR['blvd_w']
BLVD = Polygon([(S0[0] - px * BW / 2, S0[1] - py * BW / 2), (S0[0] + px * BW / 2, S0[1] + py * BW / 2),
                (RB[0] + px * BW / 2, RB[1] + py * BW / 2), (RB[0] - px * BW / 2, RB[1] - py * BW / 2)])
EDGE_E, EDGE_W = off_line(BW / 2), off_line(-BW / 2)
def ax_line(pts, s0=-3000.0, s1=3000.0):
    """best-fit line parallel to the boulevard through pts (it passes through their centroid)"""
    c0 = np.array(pts, float).mean(0); return LineString([(c0[0] + ux * s0, c0[1] + uy * s0), (c0[0] + ux * s1, c0[1] + uy * s1)])
def proj(line, p): return line.interpolate(line.project(Point(p))).coords[0]

# ---------------------------------------------------------------- roundabout + Palace
RBC = Point(RB).buffer(PAR['rb_r'], 64)
pal_c = (RB[0] + ux * (PAR['rb_r'] + PAR['palace_gap'] + PAR['palace_d'] / 2), RB[1] + uy * (PAR['rb_r'] + PAR['palace_gap'] + PAR['palace_d'] / 2))
def rect(cx, cy, w_across, d_along):   # w across the axis (E-W), d along it
    return Polygon([(cx + px * w_across / 2 + ux * d_along / 2, cy + py * w_across / 2 + uy * d_along / 2),
                    (cx - px * w_across / 2 + ux * d_along / 2, cy - py * w_across / 2 + uy * d_along / 2),
                    (cx - px * w_across / 2 - ux * d_along / 2, cy - py * w_across / 2 - uy * d_along / 2),
                    (cx + px * w_across / 2 - ux * d_along / 2, cy + py * w_across / 2 - uy * d_along / 2)])
PALACE = rect(pal_c[0], pal_c[1], PAR['palace_w'], PAR['palace_d'])
FORECOURT = rect(RB[0] + ux * (PAR['rb_r'] + PAR['palace_gap'] / 2), RB[1] + uy * (PAR['rb_r'] + PAR['palace_gap'] / 2), 90, PAR['palace_gap'] + 10)

# radial avenues (Exposition plan): QC west and east straight through; Harrison re-aligned to meet the circle
def radial(target, w):
    t = Point(target); d = math.hypot(target[0] - RB[0], target[1] - RB[1])
    s = (RB[0] + (target[0] - RB[0]) / d * (PAR['rb_r'] - 2), RB[1] + (target[1] - RB[1]) / d * (PAR['rb_r'] - 2))
    return LineString([s, target])
RADIALS = [
    ('Queen City Avenue (west)', radial((712350.0, QCW.interpolate(QCW.project(Point(712350, 4333650))).y), 60 * FT), 60 * FT),
    ('Queen City Avenue (east)', radial((712640.0, QCE.interpolate(QCE.project(Point(712640, 4333640))).y), 60 * FT), 60 * FT),
    ('Harrison Avenue (west, re-aligned)', radial((712150.0, 4333480.0), 70 * FT), 70 * FT),
    ('Harrison Avenue (east, re-aligned)', radial(basin_end('Harrison', (712784.0, 4333349.0))[0], 70 * FT), 70 * FT),
]

# ---------------------------------------------------------------- CUT: axis, square, park, rear headhouse
cut = shape(json.load(open('cut_osm.geojson'))['geometry'])
cc = (cut.centroid.x, cut.centroid.y)
ab = math.radians(93.5)                       # Ezzard Charles Dr axis, CUT to Linn St
cdx, cdy = -math.sin(ab), -math.cos(ab)       # unit pointing west along the axis
cutax = LineString([cc, (cc[0] + cdx * 900, cc[1] + cdy * 900)])
SQC = cutax.intersection(far); SQC = (SQC.x, SQC.y)
SQ = rect(SQC[0], SQC[1], PAR['sq'], PAR['sq'])
west_face = cut.bounds[0]
plat_w_edge = west_face - PAR['plat_w']
def on_axis_at_E(E):
    t = (E - cc[0]) / cdx; return (cc[0] + cdx * t, cc[1] + cdy * t)
hh_c = on_axis_at_E(plat_w_edge - PAR['hh_d'] / 2)
def rect_ax(cx, cy, along, across):   # along the CUT axis (E-W), across it
    a = math.degrees(math.atan2(cdy, cdx))
    r = box(-along / 2, -across / 2, along / 2, across / 2)
    return affinity.translate(affinity.rotate(r, a, origin=(0, 0)), cx, cy)
HH = rect_ax(hh_c[0], hh_c[1], PAR['hh_d'], PAR['hh_w'])
park_e = plat_w_edge - PAR['hh_d']
sq_e = SQC[0] + PAR['sq'] / 2
pk_c = on_axis_at_E((park_e + sq_e) / 2)
PARK = rect_ax(pk_c[0], pk_c[1], park_e - sq_e, PAR['park_w'])
plat_c = on_axis_at_E((plat_w_edge + west_face) / 2)

# ---------------------------------------------------------------- 1904 anchors (street centre where it meets the valley edge)
A_E = [  # east side, at Garrard Ave (1904 Sanborn)
    ('W 7th', '34', 1865, 1084, 60), ('Budd', '34', 1865, 1931, 60), ('W 9th', '33', 2040, 3298, 60),
    ('Richmond', '33', 2026, 2444, 60), ('Hopkins', '68', 3582, 2265, 60), ('Sedgewick', '68', 2496, 2265, 50),
    ('Kenner', '68', 1446, 2265, 50), ('Courtland', '68', 398, 2265, 50), ('Wilstach', '67', 1171, 2238, 50),
    ('Wade', '67', 1974, 2238, 50), ('Flint', '67', 2723, 2238, 50), ('Findlay', '201', 5088, 2400, 60),
    ('Poplar', '201', 5088, 3988, 60), ('Sherman', '201', 5088, 5551, 60), ('Bank', '211', 4925, 762, 60),
    ('Dayton', '211', 4925, 2459, 60), ('Exeter', '211', 4925, 4015, 60), ('York', '211', 4925, 5202, 60),
    ('Court', '47', 2240, 1290, 50), ('Clark', '58', 1930, 2054, 50), ('Oehler', '58', 1932, 2901, 50)]
A_W = [  # west side, at Evans St (Lower Price Hill) or State Ave (South Fairmount)
    ('Perin', '464', 1150, 4753, 50)]
# 2026-10-13 (Ben, option C with changes): Lower Price Hill north of W 8th is razed for the deck and the Exposition, so
# South and Hopkins (LPH) give way: the basin's W 9th, Richmond, Court, Oehler, Clark and Hopkins are carried west across
# the boulevard to Depot (Hopkins to Summer), against Lower Price Hill's north-south streets (Depot, Summer, Berlin, Evans),
# and Gest is drawn straight from State Avenue to the basin's Gest.
# 2026-10-13, later (Ben, the combined grid): Depot, Summer, Berlin and Evans are straight and parallel to the boulevard
# (best fit through their 1904 centres: 2.5, 1.0, 1.4, 3.4 m at most), and the streets carried west meet them square
# (the Garrard seam, below). W 9th and Richmond meet Depot about 10 m short of Dutton and South (a jog: the strip between
# State and Depot keeps its 1904 streets).
LPH_X = ('W 9th', 'Richmond', 'Court', 'Oehler', 'Clark', 'Hopkins')
DEPOT_1904 = [(711689.0, 4331251.0), (711690.0, 4331305.0), (711699.0, 4331460.0), (711708.0, 4331601.0), (711719.0, 4331777.0)]
_dl = ax_line(DEPOT_1904)
DEPOT = LineString([proj(_dl, DEPOT_1904[0]), proj(_dl, DEPOT_1904[-1])])
LPH_NS = {   # 1904 centres (vol. 5 sheets 467, 496, with the Lower Price Hill spline); drawn straight, south ends at W 8th
    'Summer': [(711858.0, 4331593.0), (711873.0, 4331827.0), (711879.0, 4331898.0)],
    'Berlin': [(711934.0, 4331589.0), (711947.0, 4331822.0), (711952.0, 4331909.0)],
    'Evans': [(711988.0, 4331282.0), (711985.0, 4331332.0), (711990.0, 4331400.0), (711992.0, 4331443.0), (712005.0, 4331585.0), (712022.0, 4331818.0)]}
A_N = [  # north of Queen City, at Garrard; these run west from Garrard to the deck edge (Palace grounds side)
    ('Alfred', '253', 3910, 7570, 60), ('Straight', '253', 3880, 3875, 60)]
anchors = []
for nm, s, x, y, w in A_E: anchors.append(dict(name=nm, side='E', sheet=s, px=[x, y], pt=P(s, x, y), w_ft=w))
for nm, s, x, y, w in A_W: anchors.append(dict(name=nm, side='W', sheet=s, px=[x, y], pt=P(s, x, y), w_ft=w))
for nm, s, x, y, w in A_N: anchors.append(dict(name=nm, side='N', sheet=s, px=[x, y], pt=P(s, x, y), w_ft=w))
anchors.append(dict(name='Marshall', side='N', sheet='OSM', px=None, pt=(712670.0, 4334360.0), w_ft=60))
# the West End grid bearing: perpendicular to Garrard (fitted 3.6 deg) -> 93.6 deg; LPH similar; Saratoga/Oscar follow their own line
GB = math.radians(93.6)
gdx, gdy = math.sin(GB), math.cos(GB)
sar_d = np.array(P('493', 4173, 3073)) - np.array(P('493', 3429, 2941)); sar_d = sar_d / np.linalg.norm(sar_d)

# ---------------------------------------------------------------- N-S deck streets on old lines (Garrard, Horne)
G = np.array([P('34', 1865, 1084), P('33', 2025, 583), P('57', 1980, 1162), P('201', 5088, 3000), P('211', 4900, 4000),
              P('221', 3350, 4000), P('233', 3870, 2000), P('245', 4060, 3000)])
bg, ag = np.polyfit(G[:, 1] - 4332000, G[:, 0], 1)
# 2026-10-13 (Ben): the whole Garrard line moves west so that its north end runs into Camp Washington's Garrard Avenue
# (the 1904 sheets put Garrard Avenue 8.7-9.4 m west of the fitted line, the 1922 plates 6.6-14.1 m); Garrard was not a set
# street across the yards, so the line is moved, not bent
G_SHIFT = 9.0
AG_FIT = ag; ag = ag - G_SHIFT * math.sqrt(1 + bg * bg)
GARRARD = LineString([(ag + bg * (n - 4332000), n) for n in (4330860, 4335000)])
H = np.array([P('35', 335, 1300), P('34', 3785, 1084), P('47', 491, 2460), P('47', 491, 550), P('57', 3850, 1156),
              P('69', 232, 2410), P('77', 304, 2297)])
bh, ah = np.polyfit(H[:, 1] - 4332000, H[:, 0], 1)
HORNE = LineString([(ah + bh * (n - 4332000), n) for n in (4330860, 4332345)])

# ---------------------------------------------------------------- the Garrard seam (Ben, 2026-10-13)
# East of the Garrard line the deck streets keep the basin streets' own lines; at Garrard each bends onto the boulevard's
# square (axis bearing + 90 deg), so west of Garrard every street meets the boulevard and Lower Price Hill's north-south
# streets at right angles. Gest does too, meeting State Avenue 11 m north of its 1904 corner (the upper part of Lower Price
# Hill is cleared for the Exposition); W 8th, which fronts surviving 1904 blocks, is straightened part way (below).
TH_AX = math.degrees(math.atan2(ux, uy)); TH_W = TH_AX + 90
wdx, wdy = math.sin(math.radians(TH_W)), math.cos(math.radians(TH_W))   # unit east on the boulevard square
G_INF = LineString([(ag + bg * (n - 4332000), n) for n in (4329000, 4337000)])
def seam(seg, target):
    """seg runs east -> west; keep it to Garrard, then run west on the boulevard square to target"""
    c = list(seg.coords)
    if c[0][0] < c[-1][0]: return seg
    q = seg.intersection(G_INF)
    if q.is_empty or q.geom_type != 'Point' or Point(c[0]).distance(q) < 1: return seg
    h = LineString([(q.x, q.y), (q.x - wdx * 2000, q.y - wdy * 2000)]).intersection(target)
    if h.is_empty: return seg
    h = min(getattr(h, 'geoms', [h]), key=lambda g: g.distance(q))
    return LineString([c[0], (q.x, q.y), (h.x, h.y)])

# ---------------------------------------------------------------- through streets
THRU = [('W 6th', W6, 60 * FT), ('W 8th (viaduct line)', LineString([[711570, 4331314]] + L12['W8th_w'] + [[712831, 4331220]]), 110 * FT),
        ('Gest', LineString(L12['Gest1904']), 60 * FT),
        ('W Liberty', LineString([(711876, 4332405), (712540, 4332388), (713040, 4332346)]), 60 * FT)]

def onto_basin(name, line):
    """Through street: keep its own line west of the boulevard, cross the boulevard, then run on the basin street's line to
    the basin street's west end (no overlap with the basin piece, no gap before it)."""
    c = np.array(line.coords)
    be = basin_end(name, c[np.argmax(c[:, 0])])
    if be is None: return line
    P0, v = be
    # on the basin street's line across the whole deck east of the boulevard and across the boulevard itself; the bend
    # that takes up any offset to the west-bank line falls at the boulevard's west edge
    pw = LineString([P0, (P0[0] + v[0] * 2000, P0[1] + v[1] * 2000)]).intersection(EDGE_W)
    west = [q for q in line.coords if q[0] < pw.x - 0.5]
    return LineString(west + [(pw.x, pw.y), P0])
THRU = [(n, onto_basin(n, l), w) if n != 'Gest' else None for n, l, w in THRU]
_gb = basin_end('Gest', (712869.0, 4331543.0))
THRU = [t for t in THRU if t] + [('Gest', LineString([(711632.5, 4331606.0), _gb[0]]), 60 * FT)]
def _seam_thru(l):   # W Liberty takes the seam (its west end is on the undrawn west bank; the same x, new N)
    c = list(l.coords); q = l.intersection(G_INF); t = (q.x - c[0][0]) / wdx
    return LineString([(q.x - wdx * t, q.y - wdy * t), (q.x, q.y), c[-1]])
THRU = [(n, _seam_thru(l) if n == 'W Liberty' else l, w) for n, l, w in THRU]
# Gest and W 8th from Garrard to State Avenue (Ben, 2026-10-13): Gest on the grid; W 8th one straight run from Garrard to
# State on the bearing halfway between its own (Garrard to its 1904 corner at State) and the grid, the moderate
# straightening of a long-lived street, so its south frontage moves no more than about 2.5 m.
STATE_1904 = [(711559.0, 4331258.0), (711570.0, 4331314.0), (711586.0, 4331391.0), (711601.0, 4331466.0), (711632.5, 4331606.0)]
_sc = np.array(STATE_1904); _sd = (_sc[-1] - _sc[-2]) / np.linalg.norm(_sc[-1] - _sc[-2])
STATE = LineString([tuple(q) for q in _sc] + [tuple(_sc[-1] + _sd * 80)])
def _to_state(l, deg):
    c = list(l.coords); q = l.intersection(G_INF); r = math.radians(deg)
    h = LineString([(q.x, q.y), (q.x - math.sin(r) * 1500, q.y - math.cos(r) * 1500)]).intersection(STATE)
    return LineString([(h.x, h.y), (q.x, q.y), c[-1]])
_w8 = dict((n, l) for n, l, w in THRU)['W 8th (viaduct line)']; _q8 = _w8.intersection(G_INF); _s8 = _w8.coords[0]
TH_W8_OWN = math.degrees(math.atan2(_q8.x - _s8[0], _q8.y - _s8[1])) % 360
TH_W8 = (TH_W8_OWN + TH_W) / 2
THRU = [(n, _to_state(l, TH_W8) if n.startswith('W 8th') else _to_state(l, TH_W) if n == 'Gest' else l, w) for n, l, w in THRU]
print('W 8th west of Garrard: own %.3f, grid %.3f, drawn %.3f' % (TH_W8_OWN, TH_W, TH_W8))

# ---------------------------------------------------------------- deck outline
corr = shape(json.load(open('corr.geojson'))['geometry'])
DECK = unary_union([corr, BLVD, RBC, SQ, PARK]).buffer(0)
DECK = DECK.difference(Point(RB).buffer(PAR['rb_r'] + 3).union(PALACE).union(FORECOURT)).union(RBC)
DECK = unary_union([g for g in getattr(DECK, 'geoms', [DECK]) if g.area > 3000])

# ---------------------------------------------------------------- precinct (CUT platforms and building, Hopkins to Kenner)
anc = {a['name']: a for a in anchors}
def street_N_at(nm, E):
    a = anc[nm]; t = (E - a['pt'][0]) / gdx; return a['pt'][1] + gdy * t
def hopkins_N(E):
    """Hopkins as the T-street loop draws it: on the basin street's line where the basin layer has it (2026-10-13)"""
    x, y = anc['Hopkins']['pt']
    ray0 = LineString([(x, y), (x + gdx * 400, y + gdy * 400)]).intersection(DECK)
    e0 = max(getattr(ray0, 'geoms', [ray0]), key=lambda g: g.length).coords if not ray0.is_empty else [(x, y)]
    be = basin_end('Hopkins', max(e0, key=lambda q: q[0]), 40)
    if be is None: return street_N_at('Hopkins', E)
    (bx, by), v = be; return by + (E - bx) * v[1] / v[0]
# the precinct starts 9 m north of Hopkins' centreline along its whole south edge (it had been measured at the platform
# edge only, and the sloping basin line then clipped the precinct's south-east corner and cut Hopkins short)
slope = gdy / gdx
pre_s = max(street_N_at('Hopkins', plat_w_edge), hopkins_N(plat_w_edge),
            hopkins_N(plat_w_edge - PAR['hh_d']) - (-PAR['hh_d']) * slope, hopkins_N(cut.bounds[2]) - (cut.bounds[2] - plat_w_edge) * slope) + 9
pre_n = street_N_at('Kenner', plat_w_edge) - 8
PRECINCT = Polygon([(plat_w_edge - PAR['hh_d'], pre_s), (cut.bounds[2], pre_s + (cut.bounds[2] - plat_w_edge) * gdy / gdx),
                    (cut.bounds[2], pre_n + (cut.bounds[2] - plat_w_edge) * gdy / gdx), (plat_w_edge - PAR['hh_d'], pre_n)])

# ---------------------------------------------------------------- T streets: from the anchor to the boulevard edge
T_ST = []
# new deck streets between Bank and the roundabout (no 1904 street there): every ~90 m on the grid bearing
# Realigned 2026-10-11 (Ben): the new streets now carry the basin streets that reach the deck edge north of Bank (Dolph,
# McRoberts, Western Avenue) west on the deck grid; Harrison has its radial; the old 90 m street beyond Harrison stays as New street E.
for nm, near in (('Dolph', (712777, 4333099)), ('McRoberts', (712777, 4333149)), ('Western', (712777, 4333255))):
    be = basin_end(nm, near, 30)
    if be: anchors.append(dict(name=nm, side='E', sheet='new', px=None, pt=be[0], w_ft=60, basin=True))
bank = [a for a in anchors if a['name'] == 'Bank'][0]['pt']
y = bank[1] + 90 * 5 + 0.0; x = ag + bg * (y - 4332000)
if y <= RB[1] - PAR['rb_r'] - 20: anchors.append(dict(name='New street E', side='E', sheet='new', px=None, pt=(x, y), w_ft=60))
for a in anchors:
    if a['side'] == 'N':
        x, y = a['pt']; ray = LineString([(x + gdx * 300, y + gdy * 300), (x - gdx * 600, y - gdy * 600)])
        g = ray.intersection(DECK).difference(PALACE.buffer(15)).difference(FORECOURT.buffer(5))
        parts = [p for p in getattr(g, 'geoms', [g]) if p.geom_type == 'LineString' and p.length > 40]
        for p in parts: T_ST.append(dict(name=a['name'], kind='T', side='N', w=a['w_ft'] * FT, line=p))
        continue
    x, y = a['pt']
    if a['side'] == 'E':
        d = (-gdx, -gdy)
        if a['name'] in ('Saratoga', 'Oscar'): d = (sar_d[0], sar_d[1])
    else:
        d = (sar_d[0], sar_d[1]) if a['name'] in ('Saratoga', 'Oscar') else (gdx, gdy)
    on_basin = False
    if a['side'] == 'E' and a['sheet'] != 'new':
        # where the basin layer has this street, start at its end on the deck edge and keep its line
        ray0 = LineString([(x, y), (x + gdx * 400, y + gdy * 400)]).intersection(DECK)
        e0 = max(getattr(ray0, 'geoms', [ray0]), key=lambda g: g.length).coords if not ray0.is_empty else [(x, y)]
        be = basin_end(a['name'], max(e0, key=lambda q: q[0]), 40)
        if be: (x, y), d = be[0], (be[1][0], be[1][1]); on_basin = True; a['basin_pt'] = [round(x, 1), round(y, 1)]
    if a.get('basin'): on_basin = True
    ray = LineString([(x, y), (x + d[0] * 1500, y + d[1] * 1500)])
    edge = EDGE_E if a['side'] == 'E' else EDGE_W
    hit = ray.intersection(edge)
    if hit.is_empty: continue
    seg = LineString([(x, y), (hit.x, hit.y)])
    if a['side'] == 'E' and not on_basin:   # extend east to the deck's east edge along the same line (rebuilt at deck level)
        east = LineString([(x, y), (x + gdx * 400, y + gdy * 400)]).intersection(DECK)
        pts = [(x, y)]
        if not east.is_empty:
            ge = max(getattr(east, 'geoms', [east]), key=lambda g: g.length)
            pts = [max(ge.coords, key=lambda q: q[0])]
        seg = LineString([pts[0], (hit.x, hit.y)])
    if a['side'] == 'E':
        seg = seam(seg, edge); hit = Point(seg.coords[-1])
    if a['sheet'] == 'new':
        hz = unary_union([r[1].buffer(r[2] / 2 + 15) for r in RADIALS] + [RBC.buffer(15)])
        g = seg.difference(hz); seg = min(getattr(g, 'geoms', [g]), key=lambda q: Point(q.coords[-1]).distance(Point(hit.x, hit.y)) if q.length > 40 else 1e9) if not g.is_empty else None
        if seg is None or seg.length < 100: continue
    if seg.intersects(PRECINCT) or seg.intersects(PARK.buffer(-2)):
        cutp = seg.difference(PRECINCT.buffer(1).union(PARK).union(HH))
        seg = max(getattr(cutp, 'geoms', [cutp]), key=lambda g: g.length) if not cutp.is_empty else None
        if seg is None or seg.length < 60: continue
    T_ST.append(dict(name=a['name'], kind='T', side=a['side'], w=a['w_ft'] * FT, line=seg))

# ---------------------------------------------------------------- the lower-pair dive (open between Bank and Findlay): streets that end at it
# 10l.30: Dayton, Exeter and York end at the dive; Bank and Findlay are re-graded and stay (Ben). The ramps run on both flanks
# of the APEx viaduct, so these streets stop at the outer wall on each side and nothing crosses between (Ben, 2026-10-11).
TRK = json.load(open('../deckpage/tracks.json'))
_dv = [LineString([q[:2] for q in f['geometry']['coordinates']]) for f in TRK['features']
       if f['properties'].get('layer') == 'lower' and f['properties'].get('state') == 'ramp']
DIVE = unary_union([g.buffer(3.5, cap_style=2) for g in _dv]).convex_hull if _dv else Polygon()   # track envelope 2.0 m + wall 1.5 m
DIVE_ENDS = ('Dayton', 'Exeter', 'York')
dive_cut = {}; _T2 = []
for t in T_ST:
    if t['name'] in DIVE_ENDS and t['line'].intersects(DIVE):
        dive_cut[t['name']] = [[round(q[0], 1), round(q[1], 1)] for q in t['line'].coords]
        g = t['line'].difference(DIVE)
        for part in getattr(g, 'geoms', [g]):
            if part.geom_type == 'LineString' and part.length > 6: _T2.append(dict(t, line=part, cut='dive'))
    else: _T2.append(t)
T_ST = _T2

W8L = [s_[1] for s_ in THRU if s_[0].startswith('W 8th')][0]
LPH_NSL = {}
for nm, pts in LPH_NS.items():
    ln = ax_line(pts); x = ln.intersection(W8L); LPH_NSL[nm] = LineString([(x.x, x.y), proj(ln, pts[-1])])
for t in T_ST:
    if t['name'] not in LPH_X: continue
    c = list(t['line'].coords); b = np.array(c[-1])     # c: basin end (east), Garrard, boulevard edge
    d = b - np.array(c[-2]); d = d / np.linalg.norm(d)
    tgt = LPH_NSL['Summer'] if t['name'] == 'Hopkins' else DEPOT
    hit = LineString([tuple(b), tuple(b + d * 900)]).intersection(tgt)
    if hit.is_empty: continue
    e = (hit.x + d[0] * 0.3, hit.y + d[1] * 0.3)   # 0.3 m past the centreline so the crossing nodes
    t['line'] = LineString(c[:-1] + [e]); t['kind'] = 'through'; t['side'] = 'LPH'
NS = [dict(name=nm, kind='NS', w=(50 * FT if nm != 'Evans' else 60 * FT), line=l, side='LPH') for nm, l in LPH_NSL.items()]
# the razed block north of W 8th: Depot, W 8th, the boulevard's west edge, Hopkins (to Summer), Summer, Clark (to Depot)
def _x(a, b):
    x = a.intersection(b); return (x.x, x.y) if x.geom_type == 'Point' else list(getattr(x, 'geoms', [x]))[0].coords[0]
_TL = {t['name']: t['line'] for t in T_ST if t['name'] in LPH_X}
RAZED = Polygon([_x(DEPOT, W8L), _x(W8L, EDGE_W), _x(_TL['Hopkins'], EDGE_W), _x(_TL['Hopkins'], LPH_NSL['Summer']),
                 _x(_TL['Clark'], LPH_NSL['Summer']), _x(_TL['Clark'], DEPOT)]).buffer(0)
for nm, ln, w in (('Garrard line', GARRARD, 60 * FT), ('Horne line', HORNE, 50 * FT)):
    g = ln.intersection(DECK).difference(PRECINCT.buffer(2)).difference(PARK.buffer(2)).difference(HH.buffer(2))
    for part in getattr(g, 'geoms', [g]):
        if part.geom_type == 'LineString' and part.length > 40: NS.append(dict(name=nm, kind='NS', w=w, line=part))

# ---------------------------------------------------------------- the west side of the valley (Ben, 2026-10-13): west_valley.py
import west_valley as _wv
WV = _wv.build(dict(ux=ux, uy=uy, TH_W=TH_W, DECK=DECK, EDGE_W=EDGE_W, EDGE_E=EDGE_E, T_ST=T_ST, NS=NS, THRU=THRU, RADIALS=RADIALS,
                    PALACE=PALACE, FORECOURT=FORECOURT, RBC=RBC, PRECINCT=PRECINCT, ag=ag, bg=bg))
STREETS = [dict(name=n, kind='through', w=w, line=l) for n, l, w in THRU] + \
          [dict(name=n, kind='radial', w=w, line=l) for n, l, w in RADIALS] + T_ST + NS + WV['new']

# ---------------------------------------------------------------- blocks
voids = [BLVD, RBC, SQ, PARK, HH, PRECINCT, PALACE, FORECOURT, DIVE, WV['VOIDS']]
street_polys = [s['line'].buffer(s['w'] / 2, cap_style=2) for s in STREETS]
street_polys.append(DEPOT.buffer(60 * FT / 2, cap_style=2))
street_polys += [l.buffer(w * FT / 2, cap_style=2) for n, l, w, src, note in WV['B1904']]
blocks_area = unary_union([DECK, RAZED, WV['WV_AREA']]).difference(unary_union(voids + street_polys))
blocks = [g for g in getattr(blocks_area, 'geoms', [blocks_area]) if g.area > 400]
def classify(g, i):
    if g.area < 2500: return 'planting'
    if g.intersection(DECK).area < 0.5 * g.area: return 'building'      # off the deck (west side of the valley): no vents
    if g.buffer(4).intersects(PARK) or g.buffer(4).intersects(SQ): return 'park'
    if g.buffer(6).intersects(PALACE) or g.buffer(6).intersects(FORECOURT): return 'park'
    if g.buffer(4).intersects(BLVD): return 'building'
    return 'square' if (i % 3 == 1 and g.area < 15000) else 'building'
order = sorted(range(len(blocks)), key=lambda k: (round((blocks[k].centroid.x - 712300) / 150), blocks[k].centroid.y))
BLK = []
rank = {k: r for r, k in enumerate(order)}
for k, g in enumerate(blocks):
    BLK.append(dict(id=f'B{k:03d}', type=classify(g, rank[k]), geom=g.simplify(0.5)))

# ---------------------------------------------------------------- write
def r1(g):
    m = mapping(g)
    def rr(c):
        if isinstance(c, (list, tuple)) and c and isinstance(c[0], (int, float)): return [round(c[0], 1), round(c[1], 1)]
        return [rr(x) for x in c]
    m['coordinates'] = rr(m['coordinates']); return m
F = []
F.append(dict(type='Feature', properties=dict(layer='deck', name='Deck outline'), geometry=r1(DECK)))
F.append(dict(type='Feature', properties=dict(layer='axis', name='Boulevard axis'), geometry=r1(AX)))
F.append(dict(type='Feature', properties=dict(layer='boulevard', name='Exposition Boulevard', width_m=BW), geometry=r1(BLVD)))
F.append(dict(type='Feature', properties=dict(layer='roundabout', name='Palace roundabout', radius_m=PAR['rb_r']), geometry=r1(RBC)))
F.append(dict(type='Feature', properties=dict(layer='palace', name='Cincinnati Palace (1913)'), geometry=r1(PALACE)))
F.append(dict(type='Feature', properties=dict(layer='forecourt', name='Palace forecourt'), geometry=r1(FORECOURT)))
F.append(dict(type='Feature', properties=dict(layer='cut_square', name='Terminal square'), geometry=r1(SQ)))
F.append(dict(type='Feature', properties=dict(layer='cut_park', name='CUT west park'), geometry=r1(PARK)))
F.append(dict(type='Feature', properties=dict(layer='cut_headhouse', name='CUT west headhouse'), geometry=r1(HH)))
F.append(dict(type='Feature', properties=dict(layer='cut_precinct', name='CUT platforms and terminal'), geometry=r1(PRECINCT)))
F.append(dict(type='Feature', properties=dict(layer='cut_building', name='Union Terminal'), geometry=r1(cut)))
if not DIVE.is_empty:
    F.append(dict(type='Feature', properties=dict(layer='dive_cut', name='Lower-pair dive, open cut (Bank to Findlay)', ends=list(dive_cut)), geometry=r1(DIVE)))
for i, s in enumerate(STREETS):
    F.append(dict(type='Feature', properties=dict(layer='street', id=f'S{i:03d}', name=s['name'], kind=s['kind'], width_m=round(s['w'], 1), side=s.get('side', ''), **({'cut': s['cut']} if s.get('cut') else {}),
                  **({'zone': s['zone']} if s.get('zone') else {}), **({'note': s['src']} if s.get('src') and s.get('src') != 'new' else {})), geometry=r1(s['line'])))
for b in BLK:
    F.append(dict(type='Feature', properties=dict(layer='block', id=b['id'], type=b['type'], area_m2=round(b['geom'].area), **({'side': 'WV'} if b['geom'].intersection(DECK).area < 0.5 * b['geom'].area else {})), geometry=r1(b['geom'])))
_seen = []
for c_ in WV['cuts']:
    if c_['p'] and any(n == c_['street'] and math.hypot(c_['p'][0] - q[0], c_['p'][1] - q[1]) < 25 for n, q in _seen): continue
    if c_['p']: _seen.append((c_['street'], c_['p']))
    if c_['p']: F.append(dict(type='Feature', properties=dict(layer='wv_cut', street=c_['street'], by=c_['bar'], rail=c_['rail'], street_z=c_['street_z'], diff=c_['diff'],
                              label=c_['street'].replace(' (carried west)', '').replace(' (carried south)', '').replace(' (carried east)', '') + ' cut'), geometry=dict(type='Point', coordinates=[round(c_['p'][0], 1), round(c_['p'][1], 1)])))
for g_ in WV.get('regrades', []):                 # 2026-10-14: streets re-graded over or under TRI B/D's dive (3 m or less)
    if any(n == g_['street'] and math.hypot(g_['p'][0] - q[0], g_['p'][1] - q[1]) < 25 for n, q in _seen): continue
    _seen.append((g_['street'], g_['p']))
    F.append(dict(type='Feature', properties=dict(layer='wv_regrade', street=g_['street'], by=g_['bar'], rail=g_['rail'], street_z=g_['street_z'], diff=g_['diff'], need=g_['need'], how=g_['how'],
                  label=g_['street'].replace(' (carried west)', '').replace(' (carried south)', '').replace(' (carried east)', '') + ' %s %.1f m' % (g_['how'], g_['need'])),
                  geometry=dict(type='Point', coordinates=[round(g_['p'][0], 1), round(g_['p'][1], 1)])))
if not WV['VOIDS'].is_empty:
    F.append(dict(type='Feature', properties=dict(layer='rail_open', name='Rail at or near street level (no blocks; streets end)'), geometry=r1(WV['VOIDS'])))
json.dump(dict(type='FeatureCollection', features=[dict(type='Feature', properties=dict(layer='street', id='SBW%03d' % i, name=n, kind='we_street', width_m=round(w * FT, 2), width_ft=float(w),
          width_src='default', side='', src=src, sheets='', geom_src='Sanborn crossings picked (lph/wb_picks.json)' if src.startswith('Sanborn') else 'OSM', note=note, set='wv'),
          geometry=dict(type='LineString', coordinates=[[round(x, 2), round(y, 2)] for x, y in l.coords])) for i, (n, l, w, src, note) in enumerate(WV['B1904'])]),
          open('../lph/wv_1904.json', 'w'))
out = dict(crs='EPSG:26916', params=PAR, axis=dict(S=S0, N=RB, bearing_deg=round(math.degrees(math.atan2(ux, uy)), 2), length_m=round(AX.length, 1)),
           cut=dict(axis_bearing_deg=93.5, square_centre=SQC, park_len_m=round(park_e - sq_e, 1), headhouse_centre=hh_c),
           garrard=dict(a=float(ag), b=float(bg)), anchors=anchors, dive_cut=dive_cut, features=F)
json.dump(out, open('deck.json', 'w'))
print('axis', [round(v, 1) for v in S0], '->', [round(v, 1) for v in RB], 'len', round(AX.length), 'bearing', out['axis']['bearing_deg'])
print('CUT square', [round(v) for v in SQC], 'park', round(park_e - sq_e), 'm; headhouse', [round(v) for v in hh_c])
print('streets', len(STREETS), 'T', len(T_ST), 'NS', len(NS), 'blocks', len(BLK), {t: sum(1 for b in BLK if b['type'] == t) for t in ('building', 'square', 'park', 'planting')})
print('deck area km2', round(DECK.area / 1e6, 3), 'blocks km2', round(sum(b['geom'].area for b in BLK) / 1e6, 3))
for s in T_ST: print('  T', s['name'], s['side'], round(s['line'].length), s.get('cut') or '')
for s in WV['new']: print('  WV', s['zone'], s['name'], round(s['line'].length), s.get('cut') or '')
for c_ in WV['cuts']: print('  cut', c_)
for g_ in WV.get('regrades', []): print('  regrade', g_)
print('notes', WV['notes'])
