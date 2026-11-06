try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Highway update on the Mill Creek Deck page (Ben, 2026-10-22). Reads the highway map's data (hwy/data.json, the "Cincinnati Interstate
# Types" artifact) for the pieces inside the page, but builds Millvale Boulevard on the page's own street lines (SMV streets from Ben's
# KMLs), because the map's lanes did not follow them closely. Writes deckpage/hwy.json (the Highways layer: cross-section strips, lane
# lines, signals, pieces for the inspector) and, with --install, changes deckpage/basin.json and deckpage/plots.json:
#   - new streets (set hwy): OH-75 parkway north-east of the page's Millvale Boulevard, OH-74's last stretch to Colerain, and the
#     Central Parkway leg, straight through the regraded hill, to OH-75 on Albone Street's axis (km 18.96, continuous T, angled)
#   - Colerain widened from OH-74 to Millvale Boulevard (33.2 m with the BRT to Blue Rock, 26.2 m on to Millvale; base widths set
#     between points, 'wv'), Blue Rock and Spring Grove (Blue Rock to Millvale) 21.6 m with centre BRT lanes
#   - Ludlow Avenue's first stretch at ground (no longer a viaduct): the trunk rises over it
#   - blocks and plots trimmed back from the widened corridors
# Idempotent: set hwy streets are removed first, widths are set (not added), and trimming an already trimmed block does nothing.
# Run after any street rebuild (cuf/rebuild_streets.sh, build_mv.py --install):  python3 hwy/build_hwy.py --install
import json, math, sys, numpy as np
from shapely.geometry import LineString, Point, Polygon, MultiPolygon, box, shape, mapping
from shapely.ops import substring, unary_union
SP = _ws.DATA
INSTALL = '--install' in sys.argv
B = json.load(open(SP + 'deckpage/basin.json'))
H = json.load(open(SP + 'hwy/data.json')); O = H['origin']
PAGE = box(711293, 4329989, 719869, 4338282)
FT = 0.3048
def r1(c): return [[round(float(x), 2), round(float(y), 2)] for x, y in c]
def seg(r, a, t): return LineString([(x + O[0], y + O[1]) for x, y in next(q for q in H['segs'] if q['r'] == r and q['a'] == a and q['t'] == t)['c']])
def segp(r, a, t): return next(q for q in H['segs'] if q['r'] == r and q['a'] == a and q['t'] == t)
ST = {f['properties']['id']: f for f in B['features'] if f['properties']['layer'] == 'street' and f['properties'].get('set') != 'hwy'}
def stl(i):
    return LineString(ST[i]['geometry']['coordinates'])
def first_pt(g): return g if g.geom_type == 'Point' else min(g.geoms, key=lambda q: q.y) if not g.is_empty else None

# ---------------------------------------------------------------- cross-section builder
def resample(L, step=2.0):
    n = max(2, int(math.ceil(L.length / step)) + 1); s = np.linspace(0, L.length, n)
    return np.array([L.interpolate(x).coords[0] for x in s]), s
def lnormals(P):
    t = np.gradient(P, axis=0); t /= np.hypot(*t.T)[:, None]; return np.c_[-t[:, 1], t[:, 0]]
OUT = []
def emit(layer, geom, **p):
    if geom is None or geom.is_empty: return
    if geom.geom_type in ('Polygon', 'MultiPolygon'):
        geom = geom.buffer(0)
        if geom.area < 0.5: return
    OUT.append(dict(type='Feature', properties=dict(layer=layer, **p), geometry=json.loads(json.dumps(mapping(geom.simplify(0.05)), default=float))))
def band(P, N, s, lo, hi, s0=None, s1=None):
    """strip between offsets lo(s) and hi(s) (left positive), optionally only s0..s1"""
    m = np.ones(len(s), bool)
    if s0 is not None: m &= s >= s0
    if s1 is not None: m &= s <= s1
    if m.sum() < 2: return None
    a = np.array([lo(x) for x in s[m]]); b = np.array([hi(x) for x in s[m]])
    if np.all(np.abs(b - a) < 0.05): return None
    L = P[m] + N[m] * a[:, None]; R = P[m] + N[m] * b[:, None]
    ring = np.r_[L, R[::-1], L[:1]]
    g = Polygon(ring).buffer(0)
    return g
def offl(P, N, s, o, s0=None, s1=None):
    m = np.ones(len(s), bool)
    if s0 is not None: m &= s >= s0
    if s1 is not None: m &= s <= s1
    if m.sum() < 2: return None
    oo = np.array([o(x) for x in s[m]]); return LineString(P[m] + N[m] * oo[:, None])
C = lambda v: (lambda s: v)
def ramp(pts):                                                   # piecewise-linear function of s from [(s, v), ...]
    xs, ys = zip(*pts); return lambda s: float(np.interp(s, xs, ys))

def section(name, L, side_l, side_r, centre=0.0, piece='', tunnel=False, mask=None, lane_kinds=('lanes', 'bus')):
    """standard section: centre strip of half width 'centre' (callable or float), then elements outward on each side.
    side_* = [(kind, width, nlanes), ...] from the centre out. Returns (P, N, s) for extra drawing."""
    P, s = resample(L); N = lnormals(P)
    cen = centre if callable(centre) else C(centre)
    for sgn, side in ((+1, side_l), (-1, side_r)):
        acc = [cen]
        for kind, w, n in side:
            a = acc[-1]; b = (lambda a, w: (lambda x: a(x) + (w(x) if callable(w) else w)))(a, w)
            lo, hi = ((lambda a: (lambda x: sgn * a(x)))(a), (lambda b: (lambda x: sgn * b(x)))(b))
            g = band(P, N, s, lambda x, lo=lo, hi=hi: min(lo(x), hi(x)), lambda x, lo=lo, hi=hi: max(lo(x), hi(x)))
            if g is not None and mask is not None and sgn > 0 and kind in mask[0]: g = g.difference(mask[1])
            emit('hw_strip', g, kind=kind, piece=piece, tunnel=tunnel)
            if kind in lane_kinds and n:
                lw = (lambda w, n: (lambda x: (w(x) if callable(w) else w) / n))(w, n)
                for j in range(1, n):
                    emit('hw_line', offl(P, N, s, (lambda a, j, lw: (lambda x: sgn * (a(x) + j * lw(x))))(a, j, lw)), style='dash', piece=piece, tunnel=tunnel)
                for e in (a, b):
                    emit('hw_line', offl(P, N, s, (lambda e: (lambda x: sgn * e(x)))(e)), style='edge', piece=piece, tunnel=tunnel)
            acc.append(b)
    return P, N, s
def piece(name, L, w, **p):
    emit('hw_piece', L, name=name, w=round(w, 2), **p)
def label(text, L, frac=0.5, dy=0, **p):
    q = L.interpolate(frac, normalized=True); a = L.interpolate(max(0, L.project(q) - 5)); b = L.interpolate(min(L.length, L.project(q) + 5))
    ang = math.degrees(math.atan2(b.y - a.y, b.x - a.x))
    if ang > 90: ang -= 180
    if ang < -90: ang += 180
    emit('hw_lab', Point(q.x, q.y), text=text, ang=round(ang, 1), **p)

# ---------------------------------------------------------------- sections (highway map 'side' lists)
PKW = [('brt', 3.5, 1), ('sep', 0.5, 0), ('shoulder', 0.6, 0), ('lanes', 7.0, 2), ('shoulder', 1.5, 0), ('verge', 2.5, 0), ('walk', 2.5, 0)]
BLV = [('brt', 3.5, 1), ('plat', 3.0, 0), ('lanes', 6.6, 2), ('load', 2.5, 0), ('walk', 6.26, 0)]
TUN = [('wall', 0.6, 0), ('brt', 3.5, 1), ('sep', 0.5, 0), ('shoulder', 0.5, 0), ('lanes', 7.0, 2), ('shoulder', 1.0, 0), ('wall', 0.6, 0)]
COL_BRT = [('brt', 3.5, 1), ('lanes', 6.6, 2), ('load', 2.5, 0), ('walk', 4.0, 0)]          # 33.2 m
COL = [('lanes', 6.6, 2), ('load', 2.5, 0), ('walk', 4.0, 0)]                             # 26.2 m
BRT_ST = [('brt', 3.5, 1), ('lanes', 3.3, 1), ('walk', 4.0, 0)]                          # 21.6 m
_LAY0 = json.load(open(SP + 'dbread7/deck/layout.json'))['streets']
W_CPWL_EDIT = (_LAY0.get('HW0003') or {}).get('w')                                          # Ben, 23 October: the leg at Central Parkway's 80 ft (24.4 m)
W_COL_BRT, W_COL, W_BRT_ST, W_CPWL = 33.2, 26.2, 21.6, (W_CPWL_EDIT or 27.2)

def cpw_side(w):
    rem = w / 2 - 3.5 - 6.6
    if rem < 6.5: return [('lanes', 6.6, 2), ('bus', 3.5, 1), ('walk', rem, 0)], 0.0           # 24.4 m: no median, 2.1 m walks
    # 45.72 m (Ben, 23 October): wide sidewalks lined with trees, parking, two lanes, a median and centre bus lanes. From the centre: 3.0 m median
    # (platform strip at stops), 3.5 m bus lane, two 3.3 m lanes, 2.5 m parking, 2.0 m tree strip, sidewalk (6.76 m at 150 ft)
    return [('brt', 3.5, 1), ('lanes', 6.6, 2), ('parking', 2.5, 0), ('trees', 2.0, 0), ('walk', w / 2 - 1.5 - 3.5 - 6.6 - 2.5 - 2.0, 0)], 1.5
# ---------------------------------------------------------------- OH-75 parkway (Broerman to Ludlow) and the CPW continuous T on Albone's axis
pkf = seg('OH-75', 14.54, 'Parkway hybrid'); KF = (19.4 - 14.54) / (pkf.length / 1000)
def km_of(p): return 14.54 + pkf.project(Point(p)) / 1000 * KF
def s_of_km(k): return (k - 14.54) / KF * 1000
pk = pkf.intersection(PAGE); pk = pk if pk.geom_type == 'LineString' else max(pk.geoms, key=lambda g: g.length)
s_pk0 = pkf.project(Point(pk.coords[0])); pk = substring(pkf, s_pk0, pkf.length)
K = lambda s: 14.54 + (s_pk0 + s) / 1000 * KF                                          # km along the drawn piece
# the T sits on Albone Street's axis (Ben, 22 October: Central Parkway square with Albone and angled to OH-75, hence the two banned movements)
_alb = LineString([(713018.6, 4337405.0), (713013.1, 4337258.2)]); _ad = np.subtract(_alb.coords[1], _alb.coords[0]); _ad = _ad / np.hypot(*_ad)
_ax = LineString([tuple(np.array(_alb.coords[0]) + _ad * 50), tuple(np.array(_alb.coords[0]) + _ad * 400)]).intersection(pkf)
K_T, K_LUD = km_of((_ax.x, _ax.y)), 19.4
T_pt = pkf.interpolate(s_of_km(K_T)); t_a, t_b = pkf.interpolate(s_of_km(K_T) - 5), pkf.interpolate(s_of_km(K_T) + 5)
t_u = np.array([t_b.x - t_a.x, t_b.y - t_a.y]); t_u /= np.hypot(*t_u); n_se = np.array([-t_u[1], t_u[0]])     # left of SW travel = the south-east (hill) side
if n_se[1] > 0: n_se = -n_se
E = np.array([T_pt.x, T_pt.y])
# the CPW leg (centre line T -> Ludlow). Ben (22 October): tangent at both ends. At the north end it runs on Albone Street's axis into the T
# (square with Albone across the parkway); at the south end it carries straight on from Central Parkway's own line, whose last straight
# (bearing 24.0 degrees) ends at his point 1, 18 m past Ludlow (his point 0 is a doubled-back vertex on Ludlow). Between them one circular
# curve of 1,000 m radius through the regraded hill.
LAYOUT = _LAY0                      # Ben's edits: Central Parkway is his
_cc = np.array(LAYOUT.get('SB0595', {}).get('c') or ST['SB0595']['geometry']['coordinates'], float)
_k = 1 if np.dot(_cc[1] - _cc[0], _cc[2] - _cc[1]) < 0 else 0                           # skip a doubled-back first vertex
CPW0 = tuple(_cc[_k]); _dc = _cc[_k] - _cc[_k + 6]; _dc = _dc / np.hypot(*_dc)           # Central Parkway's end and its heading (north-east)
_dn = -_ad                                                                                # Albone's axis, heading north
_t, _u = np.linalg.solve(np.array([_dc, -_dn]).T, E - np.array(CPW0)); _X = np.array(CPW0) + _t * _dc   # where the two tangents meet
R_LEG = 1000.0
_dl = math.acos(np.clip(np.dot(_dc, _dn), -1, 1)); _T = R_LEG * math.tan(_dl / 2)
assert _T < _t and _T < -_u, 'curve does not fit between the ends'
_A = _X - _dc * _T; _Bp = _X + _dn * _T                                                   # tangent points (south, north)
_nrm = np.array([-_dc[1], _dc[0]]); _side = 1 if np.dot(_dn - _dc, _nrm) > 0 else -1; _O = _A + _nrm * _side * R_LEG
_a0 = math.atan2(*(_A - _O)[::-1]); _a1 = math.atan2(*(_Bp - _O)[::-1])
if _side > 0:
    while _a1 < _a0: _a1 += 2 * math.pi
else:
    while _a1 > _a0: _a1 -= 2 * math.pi
_arc = [tuple(_O + R_LEG * np.array([math.cos(a), math.sin(a)])) for a in np.linspace(_a0, _a1, max(8, int(abs(_a1 - _a0) * R_LEG / 5)))]
LEG = LineString([tuple(E)] + _arc[::-1] + [CPW0])                                        # T -> north straight -> curve -> south straight -> Central Parkway
LEG_INFO = dict(R=R_LEG, defl=math.degrees(_dl), north_straight=float(-_u - _T), south_straight=float(_t - _T), arc=abs(_a1 - _a0) * R_LEG)
print('leg', {k: round(v, 1) for k, v in LEG_INFO.items()}, 'length', round(LEG.length, 1))
mouth = LEG.buffer(W_CPWL / 2 + 6, cap_style=2).intersection(Point(E).buffer(32))
# median: 4.0 m, widened to 7.5 m for 100 m before the T (two left lanes into Central Parkway between the bus lanes, Phase A), 4.6 m for the left to Ludlow
mh = lambda s: float(np.interp(K(s), [K_T - 0.14, K_T - 0.10, K_T, K_T + 0.05, 19.28, 19.32, 19.41], [2.0, 3.75, 3.75, 2.0, 2.0, 2.3, 2.3]))
# third northbound lane from the CPW free right, in the shoulder and verge, dropping north-east of the T (where is not set)
addw = lambda s: float(np.interp(K(s), [K_T - 0.34, K_T - 0.30, K_T, K_T + 0.0001], [0.0, 3.3, 3.3, 0.0]))
NB = [('brt', 3.5, 1), ('sep', 0.5, 0), ('shoulder', 0.6, 0), ('lanes', 7.0, 2), ('add_lane', addw, 0), ('shoulder_r', lambda s: 1.5 - addw(s) * 0.8 / 3.3, 0),
      ('verge', lambda s: 2.5 - addw(s) * 2.5 / 3.3, 0), ('walk', 2.5, 0)]
PKW = [('brt', 3.5, 1), ('sep', 0.5, 0), ('shoulder', 0.6, 0), ('lanes', 7.0, 2), ('shoulder_r', 1.5, 0), ('verge', 2.5, 0), ('walk', 2.5, 0)]
P1, N1, s1 = section('OH-75 parkway', pk, NB, PKW, centre=mh, piece='OH-75 parkway', mask=(('verge', 'walk', 'shoulder_r', 'add_lane'), mouth))
emit('hw_strip', band(P1, N1, s1, lambda x: -mh(x), lambda x: mh(x)), kind='median', piece='OH-75 parkway')
sT = s_of_km(K_T) - s_pk0
emit('hw_strip', band(P1, N1, s1, lambda x: -mh(x), lambda x: -mh(x) + 6.6, s_of_km(K_T - 0.10) - s_pk0, sT), kind='pocket', piece='OH-75 parkway', note='two left lanes into Central Parkway (Phase A)')
emit('hw_strip', band(P1, N1, s1, lambda x: -mh(x), lambda x: -mh(x) + 3.3, s_of_km(19.33) - s_pk0, s_of_km(19.40) - s_pk0), kind='pocket', piece='OH-75 parkway', note='left to Ludlow (Clifton)')
emit('hw_strip', band(P1, N1, s1, lambda x: -mh(x) - 3.5, lambda x: -mh(x), s_of_km(K_T - 0.14) - s_pk0, s_of_km(K_T - 0.10) - s_pk0), kind='brt_x', piece='OH-75 parkway', note='left-turners cross the southbound bus lane into the pocket')
for k in (K_T - 0.10,):
    emit('hw_line', offl(P1, N1, s1, lambda x: -mh(x) + 3.3, s_of_km(k) - s_pk0, sT), style='dash', piece='OH-75 parkway')
piece('OH-75 parkway (Broerman to Ludlow)', pk, 40.2, route='OH-75', type='Parkway hybrid', km=[round(K(0), 2), K_LUD],
      section='40.2 m: planted median 4.0, BRT 3.5 + 0.5 separator each way, two 3.5 m lanes each way with 0.6 and 1.5 m shoulders, 2.5 m verge and 2.5 m walk',
      note='Storrow/Jamaicaway parkway (highway map): compact ramps at the major crossings, signals at minor streets, local trucks only. At km %.2f, on Albone Street\'s axis, a continuous T with Central Parkway '
           '(Ben, 22 October: square with Albone and angled to OH-75, about 66 degrees): southbound through never stops; two protected left lanes into Central Parkway sit in the median, widened to 7.5 m for 100 m before the T (left-turners cross the '
           'southbound bus lane before the junction, so the southbound BRT runs straight through with the general lanes); northbound through and the northbound BRT stop for that phase; '
           'Central Parkway turns right from both lanes onto northbound OH-75, the outer lane becoming a third northbound lane in the shoulder and verge that drops north-east of the T '
           '(where is not set). Banned: Central Parkway to Millvale Boulevard south-west, and the northbound right into Central Parkway (those use Ludlow, Colerain or Spring Grove). '
           'The angle is why the two banned movements go: both would be turns of about 114 degrees. Signalled junction with Ludlow at km 19.4, coordinated with the T about %d m away' % (K_T, round((19.4 - K_T) * 1000)))
label('OH-75 parkway', pk, 0.35)
emit('hw_sig', Point(*(np.array(pkf.interpolate(s_of_km(K_T) - 12).coords[0]) + n_se * 9.5)), name='CPW T: northbound OH-75 (Phase B)')
emit('hw_sig', Point(*(np.array(pkf.interpolate(s_of_km(K_T) - 2).coords[0]) - n_se * 1.0)), name='CPW T: southbound left into Central Parkway (Phase A)')
emit('hw_lab', Point(*(np.array(pkf.interpolate(s_of_km(K_T) - 60).coords[0]) + n_se * 62)), text='continuous T: southbound never stops', ang=0, small=True)
emit('hw_lab', Point(*(np.array(pkf.interpolate(s_of_km(K_T - 0.32)).coords[0]) + n_se * 32)), text='third northbound lane drops (where not set)', ang=0, small=True)

# CPW leg strips (drawn after the parkway, from its outer edge)
s_out = 25.0
legd = substring(LEG, s_out, LEG.length)
_lside, _lmed = cpw_side(W_CPWL) if W_CPWL < 26 else ([('lanes', 6.6, 2), ('bus', 3.5, 1), ('walk', 2.5, 0)], 1.0)
P3, N3, s3 = section('Central Parkway leg', legd, _lside, _lside, centre=_lmed, piece='Central Parkway leg')
if _lmed > 0: emit('hw_strip', band(P3, N3, s3, C(-_lmed), C(_lmed)), kind='median', piece='Central Parkway leg')
emit('hw_strip', LEG.buffer(W_CPWL / 2, cap_style=2).intersection(Point(E).buffer(s_out + 1)).difference(pk.buffer(mh(sT) + 3.5 + 0.5 + 0.6 + 7.0 + 0.2, cap_style=2)), kind='junction', piece='Central Parkway leg')
piece('Central Parkway (to OH-75)', LEG, W_CPWL, route='Central Parkway', type='Avenue', section=('%.1f m (Ben, 23 October: Central Parkway\'s 80 ft): a 3.5 m kerbside bus lane, two 3.3 m lanes and a %.1f m walk each way, no median' % (W_CPWL, W_CPWL / 2 - 10.1)) if W_CPWL < 26 else '27.2 m: 2.0 m median, two 3.3 m lanes and a 3.5 m kerbside bus lane each way, 2.5 m walks',
      note='Central Parkway carried on north of Ludlow to a continuous T on OH-75 at km %.2f, tangent at both ends (Ben, 22 October): it carries straight on from '
           'Central Parkway\'s own line (bearing 24 degrees) for %d m, turns %.0f degrees on a %d m curve (%d m), and runs its last %d m on Albone Street\'s axis, so it lines '
           'up with Albone across the parkway and meets OH-75 at about 65 degrees. About %d m from Central Parkway\'s end. The hill between Millvale, Ludlow and Central '
           'Parkway is regraded for it: the road runs nearly level (about 168 m at Ludlow to 165 m at OH-75), so the hill is cut down by up to about 32 m (LiDAR), more than '
           '5 m over about 420 m. Kerbside bus lanes both ways (Ben: bus lanes, not necessarily BRT): northbound buses run in the bus lane straight into the right turn onto OH-75; '
           'southbound buses from the OH-75 BRT come over in the left-turn phase. Two general lanes in from the southbound left, two out turning right onto northbound OH-75. At Ludlow: no left turns from Central Parkway either '
           'way (two-phase signal); Clifton-bound traffic stays on Millvale and turns at the Ludlow signal' % (K_T, round(LEG_INFO['south_straight']), LEG_INFO['defl'], R_LEG, round(LEG_INFO['arc']), round(LEG_INFO['north_straight']), round(LEG.length)))
# (the street layer labels Central Parkway)
_lx = LineString([tuple(np.array(CPW0) + _dc * 5), tuple(np.array(CPW0) - _dc * 60)]).intersection(stl('S22016'))
emit('hw_sig', _lx if not _lx.is_empty else Point(*CPW0), name='Central Parkway / Ludlow (two phases, no lefts from Central Parkway)')

# ---------------------------------------------------------------- Central Parkway, Ludlow to Reading Road: kerbside bus lanes (Ben, 22 October)
# On Ben's own line and widths (his edit of SB0595: 24.4 m on almost all of it, 45.72 m on the last three pieces; East Central Parkway
# SB0675 to Reading Road 45.72 m). Each side from the kerb: walk, (loading lane), 3.5 m bus lane, two 3.3 m lanes, (median)
def qcurve(a, k, b, n=12): a, k, b = map(np.asarray, (a, k, b)); t = np.linspace(0, 1, n)[:, None]; return list((1 - t) ** 2 * a + 2 * (1 - t) * t * k + t * t * b)
_e = LAYOUT.get('SB0595', {}); _cv = _e.get('c') or ST['SB0595']['geometry']['coordinates']; _kv = _e.get('k') or {}; _wv = _e.get('wv') or [None] * (len(_cv) - 1)
_w0 = ST['SB0595']['properties']['width_m']; runs = []
for i in range(_k, len(_cv) - 1):
    _sg = qcurve(_cv[i], _kv[str(i)], _cv[i + 1]) if str(i) in _kv else [np.asarray(_cv[i]), np.asarray(_cv[i + 1])]
    w = _wv[i] or _w0
    if runs and abs(runs[-1][0] - w) < 0.01: runs[-1][1].extend(_sg[1:])
    else: runs.append([w, list(_sg)])
_ecp = ST['SB0675']; runs.append([_ecp['properties']['width_m'], [np.asarray(q) for q in _ecp['geometry']['coordinates']]])
_cpw_all = []
for w, pts in runs:
    Lr = LineString([tuple(q) for q in pts])
    if Lr.length < 2: continue
    side, med = cpw_side(w)
    Pc, Nc, sc = section('Central Parkway', Lr, side, side, centre=med, piece='Central Parkway')
    if med > 0: emit('hw_strip', band(Pc, Nc, sc, C(-med), C(med)), kind='median', piece='Central Parkway')
    _cpw_all += [tuple(q) for q in pts]
CPW_LINE = LineString(_cpw_all)
piece('Central Parkway (Ludlow to Reading Road)', CPW_LINE, 24.4, route='Central Parkway', type='Avenue',
      section='24.4 m (Ben\'s width, 80 ft): a 3.5 m kerbside bus lane, two 3.3 m lanes and a 2.1 m walk each way, no median (as the real Central Parkway has none). '
              '45.72 m (150 ft) at the south end and on East Central Parkway to Reading Road: 3.0 m median, centre bus lanes 3.5 m, two 3.3 m lanes, 2.5 m parking, 2.0 m tree strip and a 6.76 m sidewalk each way',
      note='Bus lanes the whole way from Millvale (OH-75) to Reading Road (Ben, 22 and 23 October: bus lanes, not necessarily BRT), on Ben\'s line and widths. On the 80 ft parkway they run at the '
           'kerb; on the 150 ft end (1,714 m, from the turn south near Liberty to Reading Road) they move to the centre, beside a 3.0 m median that can carry the stop platforms, with parking and '
           'tree-lined wide sidewalks at the sides. The buses cross between kerb and centre at the change of width (signal priority there not drawn)')
label('Central Parkway (bus lanes)', CPW_LINE, 0.45, small=True)
# ---------------------------------------------------------------- Millvale Boulevard on the page's own streets
lud_sig = Point(712716.4, 4336807.4)
mv0 = stl('SMV0033'); mv0 = substring(mv0, mv0.project(lud_sig), mv0.length)
mvp = []
for i, rev in (('SMV0034', False), ('SMV0035', False)): mvp.append(stl(i))
for L_, nm in ((mv0, 'Millvale Boulevard'), (mvp[0], 'Millvale Boulevard'), (mvp[1], 'Millvale Boulevard (to the English Woods tunnel)')):
    P2, N2, s2 = section(nm, L_, BLV, BLV, centre=1.0, piece='Millvale Boulevard')
    emit('hw_strip', band(P2, N2, s2, C(-1.0), C(1.0)), kind='median', piece='Millvale Boulevard')
ARM = [('median', 1.0, 0)] + BLV
for i, rev in (('SMV0037', False), ('SMV0038', True)):                                 # one-way arms round the confluence park, park on the left
    L_ = stl(i); L_ = LineString(L_.coords[::-1]) if rev else L_
    P2, s2 = resample(L_); N2 = lnormals(P2); acc = 22.86 / 2
    for kind, w, n in ARM:
        g = band(P2, N2, s2, C(acc - w), C(acc)); emit('hw_strip', g, kind=kind, piece='Millvale Boulevard')
        if kind == 'lanes':
            emit('hw_line', offl(P2, N2, s2, C(acc - w / 2)), style='dash', piece='Millvale Boulevard')
            for e in (acc, acc - w): emit('hw_line', offl(P2, N2, s2, C(e)), style='edge', piece='Millvale Boulevard')
        acc -= w
mvl = unary_union([mv0] + mvp)
piece('OH-75: Millvale Boulevard (Ludlow to the tunnel)', LineString(list(mv0.coords) + list(stl('SMV0037').coords) + list(mvp[0].coords) + list(mvp[1].coords)), 45.72, route='OH-75', type='Boulevard',
      km=[K_LUD, 21.4], section='45.72 m (150 ft, the page street): 2.0 m planted centre between the bus lanes, BRT 3.5, platform or planted strip 3.0, two 3.3 m lanes, 2.5 m loading lane, 6.26 m walk each way; '
      'one-way arms of 75 ft round the confluence park',
      note='Drawn on the page\'s Millvale Boulevard streets (Ben\'s KMLs), not the highway map\'s lanes, which did not follow them closely. Signals at every crossing street (highway map). '
           'Passes under the north trunk viaduct and RER B (km 19.6), the APEx Indianapolis + RER D deck (km 20.37, R5 below it) and the RER A trunk (km 21.31, 44 degrees, about 7.6 m '
           'down in the tunnel approach cut: piers in the centre BRT strip are the natural choice)')
label('Millvale Boulevard (OH-75)', mv0, 0.55)

# ---------------------------------------------------------------- English Woods tunnel (from the portal at Beekman), OH-74's end, the inner ring corner
tn = seg('OH-75', 21.4, 'Tunnel').intersection(PAGE); tn = tn if tn.geom_type == 'LineString' else max(tn.geoms, key=lambda g: g.length)
section('English Woods tunnel', tn, TUN, TUN, centre=6.0, piece='English Woods tunnel', tunnel=True)
piece('OH-75: English Woods tunnel', tn, 39.4, route='OH-75', type='Tunnel', km=[21.4, 23.5], section='two bores 12 m apart: each 0.6 m walls, BRT 3.5 + 0.5, two 3.5 m lanes, 0.5 and 1.0 m shoulders',
      note='Hazardous loads use the other ring (highway map). Metro Line 9 crosses over it at km 21.53 (ground 177 m, road about 147 m, roof about 154 m): its level is not set, so it has to pass above '
           'about 157 m or below about 140 m there; North Fairmount station is about 230 m away')
label('English Woods tunnel (OH-75)', tn, 0.5)
o74 = seg('OH-74', 18.67, 'Boulevard').intersection(PAGE); o74 = o74 if o74.geom_type == 'LineString' else max(o74.geoms, key=lambda g: g.length)
P4, N4, s4 = section('OH-74', o74, BLV, BLV, centre=1.0, piece='OH-74')
emit('hw_strip', band(P4, N4, s4, C(-1.0), C(1.0)), kind='median', piece='OH-74')
piece('OH-74 (boulevard, to Colerain)', o74, 45.72, route='OH-74', type='Boulevard', km=[round(20.31 - o74.length / 1000, 2), 20.31],
      section='45.72 m: as Millvale Boulevard',
      note='OH-74 ends at a signal on Colerain at Kirby. Through traffic goes down Colerain to Millvale Boulevard (path A, widened to 26.2 m); the BRT goes on along Colerain to Blue Rock, '
           'Blue Rock and Spring Grove to the Colerain stop on Millvale Boulevard. RER-1b crosses over it about 170 m short of Colerain and stays on viaduct (rail 160 m or more, road 153.5 m). '
           'West of the page OH-74 carries APEx in the centre and the RER D pair beside it in a 29.7 m median (section 73.42 m)')
label('OH-74', o74, 0.4)
# Inner Ring North, the OH-562 boulevard, whole length (Ben, 23 October: "put the 562 inner ring in"). The highway map's line, pushed north
# where it lay on the rail corridor west of Norwood Central and clipped the station's north tracks (nwring/ring.py -> nwring/ring_utm.json)
_RG = json.load(open(SP + 'nwring/ring_utm.json')); ir = LineString(_RG['coords'])
P5, N5, s5 = section('Inner ring', ir, BLV, BLV, centre=1.0, piece='Inner ring')
emit('hw_strip', band(P5, N5, s5, C(-1.0), C(1.0)), kind='median', piece='Inner ring')
piece('Inner Ring North (OH-562 boulevard)', ir, 45.72, route='Inner ring', type='Boulevard', km=[0, round(ir.length / 1000, 2)],
      section='45.72 m: from the centre a 1.0 m planted centre, 3.5 m bus lane, 3.0 m platform or planted strip, two 3.3 m lanes, 2.5 m loading lane, 6.26 m walk each way',
      note='OH-562 from Duck Creek (I-71, J8) west through Norwood to Broerman (OH-75, J7), highway map line. Pushed north (up to %.0f m) between Norwood Central frame s %.0f and %.0f, '
           'where the map line lay on the rail corridor west of the station and clipped its Transvalley tracks: its south edge now stays 3 m outside the six-track corridor and the '
           'station track area. Grade separations: the Waynesville pair (CL&N prong) just north-east of Norwood Central, the APEx Transcontinental at Ridge (km 2.13 from Duck Creek) '
           'and near Broerman (km 8.08); Metro Lines 2, 3, 4, 6, 7, 12 and 14 pass under it in tunnel' % (_RG['max_shift'], _RG['s_moved'][0], _RG['s_moved'][1]))
label('Inner Ring (OH-562)', ir, 0.42); label('Inner Ring (OH-562)', ir, 0.8)
PAGE_IR = ir.buffer(40)

# ---------------------------------------------------------------- Northside: Colerain, Blue Rock, Spring Grove (Ben: wider and the primary west-east street; BRT on Blue Rock)
col = stl('SB0612')
p74 = Point(711687.0, 4337699.0); s74 = col.project(p74)
sBR = col.project(first_pt(col.intersection(stl('SB0567'))))
sMV = col.project(first_pt(col.intersection(stl('SMV0033'))))
colA, colB = substring(col, s74, sBR), substring(col, sBR, sMV)
for L_, side, nm, w in ((colA, COL_BRT, 'Colerain Avenue (BRT)', W_COL_BRT), (colB, COL, 'Colerain Avenue', W_COL)):
    section(nm, L_, side, side, piece=nm)
br = stl('SB0567'); sg = stl('SB0935')
for L_, nm in ((br, 'Blue Rock Street (BRT)'), (sg, 'Spring Grove Avenue (BRT)')):
    section(nm, L_, BRT_ST, BRT_ST, piece=nm)
piece('Colerain Avenue (OH-74 to Blue Rock)', colA, W_COL_BRT, route='Colerain', type='Avenue', section='33.2 m: centre BRT 3.5 each way, two 3.3 m lanes, 2.5 m loading lane, 4.0 m walk each way',
      note='OH-74\'s through traffic and its BRT share this stretch (Ben, 22 October: path A for traffic, BRT on Blue Rock)')
piece('Colerain Avenue (Blue Rock to Millvale Boulevard)', colB, W_COL, route='Colerain', type='Avenue', section='26.2 m (86 ft): two 3.3 m lanes, 2.5 m loading lane, 4.0 m walk each way',
      note='the through route from OH-74 to Millvale Boulevard (path A); the Colerain, Spring Grove and Millvale junction stays busy by design, which keeps through drivers on the rings')
piece('Blue Rock Street', br, W_BRT_ST, route='BRT', type='BRT street', section='21.6 m (71 ft): centre BRT 3.5 each way, one 3.3 m lane, 4.0 m walk each way; 24.6 m at stops with a 3.0 m platform (stops not placed)',
      note='Northside\'s main street (Ben: Blue Rock as its 5th Street, Hoffner Park its Fountain Square); BRT from OH-74 to the Colerain stop on Millvale Boulevard')
piece('Spring Grove Avenue (Blue Rock to Millvale Boulevard)', sg, W_BRT_ST, route='BRT', type='BRT street', section='21.6 m: as Blue Rock', note='BRT to the Colerain stop (Metro Lines 5 and 13) on Millvale Boulevard')
label('BRT', br, 0.5, small=True); label('BRT', sg, 0.5, small=True)

# ---------------------------------------------------------------- signals from the highway map inside the page
for sgl in H['signals']:
    q = Point(sgl['p'][0] + O[0], sgl['p'][1] + O[1])
    if PAGE.contains(q) or PAGE_IR.contains(q): emit('hw_sig', q, name=sgl.get('n', '') + (' (' + sgl['j'] + ')' if sgl.get('j') else ''))
emit('hw_sig', p74, name='OH-74 / Colerain Avenue (OH-74 ends)')

# ---------------------------------------------------------------- Spring Grove Cemetery (Ben's GeoTIFF, 22 October: its alpha mask, sgc/cemetery_utm.json)
_cem = shape(json.load(open(SP + 'sgc/cemetery_utm.json')))
emit('hw_area', _cem, kind='cemetery', name='Spring Grove Cemetery')
emit('hw_lab', _cem.representative_point(), text='Spring Grove Cemetery', ang=0)
hw = dict(type='FeatureCollection', name='highways', note='Highway update 22 October 2026: the highway map\'s pieces inside the page, Millvale Boulevard on the page streets, the CPW continuous T, Northside widenings',
          features=OUT)
json.dump(hw, open(SP + 'deckpage/hwy.json', 'w'), separators=(',', ':'))
print('hwy.json', len(OUT), 'features; leg', round(LEG.length), 'm; Colerain s', round(s74), round(sBR), round(sMV))

if not INSTALL: sys.exit()
# ================================================================ basin.json and plots.json
B['features'] = [f for f in B['features'] if f['properties'].get('set') != 'hwy']
def newst(i, name, L, w, note):
    return dict(type='Feature', properties=dict(layer='street', id=i, name=name, kind='we_street', width_m=round(w, 2), width_ft=round(w / FT, 1), width_src='highway update (Ben 2026-10-22)', side='',
                src='Highway update 2026-10-22', note=note, set='hwy'), geometry=dict(type='LineString', coordinates=r1(L.coords)))
pk_st = substring(pkf, pkf.project(Point(pk.coords[0])), pkf.project(Point(stl('SMV0033').coords[0])))
B['features'] += [newst('HW0001', 'OH-75 (parkway)', pk_st, 40.2, 'OH-75 parkway from Broerman to Ludlow (highway map), north-east of the page\'s Millvale Boulevard street; lanes in the Highways layer'),
                  newst('HW0002', 'OH-74 (boulevard)', o74, 45.72, 'OH-74\'s last stretch, to its signal on Colerain at Kirby; lanes in the Highways layer'),
                  newst('HW0003', 'Central Parkway (to OH-75)', LEG, W_CPWL, 'Central Parkway carried on straight north of Ludlow through the regraded hill to a continuous T on OH-75 on Albone Street\'s axis, angled (Ben, 22 October)'),
                  newst('HW0004', 'Inner Ring (OH-562 boulevard)', ir, 45.72, 'Inner Ring North, Duck Creek (I-71) to Broerman (OH-75); lanes in the Highways layer (Ben, 23 October)')]
def setw(i, w, note):
    p = ST[i]['properties']; p['width_m'] = round(w, 2); p['width_ft'] = round(w / FT, 1); p['width_src'] = 'widened (highway update, Ben 2026-10-22)'
    base = (p.get('note') or ''); base = '' if base.startswith('widened 2026-10-22') else base.split(' | widened')[0]
    p['note'] = base + (' | ' if base else '') + 'widened ' + note
setw('SB0567', W_BRT_ST, '2026-10-22 to 21.6 m (71 ft) for centre BRT lanes, one lane each way (Ben: the primary west-east street, Hoffner Park its Fountain Square)')
setw('SB0935', W_BRT_ST, '2026-10-22 to 21.6 m (71 ft) for centre BRT lanes, Blue Rock to Millvale Boulevard')
# Colerain: widths between points (base 'wv'); vertices added at OH-74, Blue Rock and Millvale Boulevard
cf = ST['SB0612']; cc = [tuple(q) for q in cf['geometry']['coordinates']]
def insert(cc, s):
    L = LineString(cc); acc = 0.0
    for i in range(len(cc) - 1):
        d = math.dist(cc[i], cc[i + 1])
        if acc - 0.05 <= s <= acc + 0.05: return cc, i
        if acc + 0.05 < s < acc + d - 0.05:
            q = L.interpolate(s).coords[0]; return cc[:i + 1] + [(round(q[0], 2), round(q[1], 2))] + cc[i + 1:], i + 1
        acc += d
    return cc, len(cc) - 1
for s_ in sorted((s74, sBR, sMV)): cc, _ = insert(cc, s_)
Lc = LineString(cc); vs = [Lc.project(Point(q)) for q in cc]
wv = []
for i in range(len(cc) - 1):
    m = (vs[i] + vs[i + 1]) / 2
    wv.append(W_COL_BRT if s74 <= m <= sBR else W_COL if sBR <= m <= sMV else None)
cf['geometry']['coordinates'] = r1(cc); cf['properties']['wv'] = wv
cf['properties']['note'] = (cf['properties'].get('note') or '').split(' | widened')[0] + ' | widened 2026-10-22 from OH-74 (Kirby) to Millvale Boulevard: 33.2 m with the BRT to Blue Rock, 26.2 m (86 ft) on to Millvale (OH-74 through traffic, path A)'
# Ludlow at ground on its 1914 line
lf = ST['S22015']['properties']; lf.pop('structure', None)
lf['note'] = ('at ground on its 1914 line (Ben, 22 October): from Dodsworth Avenue (the 1904 name of its first block from Knowlton\'s Corner, 149.4 m) over Mill Creek and under the trunk, '
              'which rises on fill to a span over it (rail 162.5 m; Ludlow 155.4 m there), then about 2% up to the old canal bank (163-166 m). OH-75 / Millvale Boulevard meets it at a signal, '
              'at a skew of about 28 degrees')
# Norwood (Ben, 23 October): the station takes Harris Avenue and the side-street ends inside its track area (Montgomery, Smith Road and Forest
# cross it and stay through, on bridges); the Inner Ring replaces the stretches of Norwood Avenue and Sycamore Street it runs along.
_NW = json.load(open(SP + 'deckpage/norwood.json'))['features']
NW_AREA = shape(next(f for f in _NW if f['properties']['layer'] == 'nw_area')['geometry']); NW_BLDG = shape(next(f for f in _NW if f['properties']['layer'] == 'nw_bldg')['geometry'])
IR_BAND = ir.buffer(45.72 / 2, cap_style=2, join_style=2, mitre_limit=3)
THROUGH = {'Montgomery Avenue', 'Montgomery Pike', 'Smith Road', 'Forest Avenue'}
def _clip(f, poly, why):
    g = shape(f['geometry']); rest = g.difference(poly); parts = sorted([q for q in getattr(rest, 'geoms', [rest]) if q.geom_type == 'LineString' and q.length > 10], key=lambda q: -q.length)
    p = f['properties']; out = []
    for j, q in enumerate(parts):
        f2 = json.loads(json.dumps(f)); f2['geometry'] = dict(type='LineString', coordinates=r1(q.coords))
        if j: f2['properties']['id'] = p['id'] + 'abcdefgh'[j - 1]
        f2['properties']['note'] = ((p.get('note') or '') + ' | ' if p.get('note') else '') + why; out.append(f2)
    return out
newF, nclip = [], []
for f in B['features']:
    p = f['properties']
    if p['layer'] == 'street' and p.get('set') in ('c82A', 'c83A'):
        g = shape(f['geometry'])
        if p.get('name') not in THROUGH and g.intersection(NW_AREA).length > 5:
            newF += _clip(f, NW_AREA, 'cut back at Norwood Central\'s track area (Ben, 23 October)'); nclip.append(p['id']); continue
        if g.intersection(IR_BAND).length > 0.3 * g.length and g.intersection(IR_BAND).length > 30:
            newF += _clip(f, IR_BAND, 'the Inner Ring (OH-562) replaces the stretch along it'); nclip.append(p['id']); continue
    newF.append(f)
B['features'] = newF
print('Norwood streets cut back', nclip)
# corridors of the widened streets (mitred, as the page builds basin streets) and the new streets: trim blocks and plots
def corr(L, w): return L.buffer(w / 2, cap_style=2, join_style=2, mitre_limit=3)
cut = unary_union([corr(colA, W_COL_BRT), corr(colB, W_COL), corr(br, W_BRT_ST), corr(sg, W_BRT_ST), corr(LEG, W_CPWL), corr(pk_st, 40.2), corr(o74, 45.72), corr(ir, 45.72), NW_AREA, NW_BLDG]).buffer(0)
nb = 0; gone = []
for f in B['features']:
    p = f['properties']
    if p['layer'] != 'block': continue
    g = shape(f['geometry'])
    if not g.intersects(cut): continue
    h = g.difference(cut).buffer(0)
    if h.area < 0.98 * g.area - 0.5:
        if h.area < 20: gone.append(p.get('id')); f['_drop'] = True; continue
        h = h if h.geom_type == 'Polygon' else MultiPolygon([q for q in h.geoms if q.area > 2]) if h.geom_type == 'MultiPolygon' else h
        f['geometry'] = json.loads(json.dumps(mapping(h.simplify(0.02)), default=float)); p['area_m2'] = round(h.area) if 'area_m2' in p else p.get('area_m2'); nb += 1
B['features'] = [f for f in B['features'] if not f.get('_drop')]
json.dump(B, open(SP + 'deckpage/basin.json', 'w'), separators=(',', ':'))
print('basin: streets HW0001-4 added; blocks trimmed', nb, 'dropped', gone)
PL = json.load(open(SP + 'deckpage/plots.json')); E0, N0 = PL['o']
def dec(a):
    x, y = a[0], a[1]; pts = [[E0 + x / 10, N0 + y / 10]]
    for i in range(2, len(a), 2): x += a[i]; y += a[i + 1]; pts.append([E0 + x / 10, N0 + y / 10])
    return pts
def enc(pts):
    q = np.round((np.array(pts) - [E0, N0]) * 10).astype(int); e = [int(q[0, 0]), int(q[0, 1])]
    for i in range(1, len(q)): e += [int(q[i, 0] - q[i - 1, 0]), int(q[i, 1] - q[i - 1, 1])]
    return e
bbx = cut.bounds; newrows = []; npl = 0; nsplit = 0; ndrop = 0
for row in PL['plots']:
    rings = [dec(a) for a in row[6]]
    xs = [q[0] for q in rings[0]]; ys = [q[1] for q in rings[0]]
    if max(xs) < bbx[0] or min(xs) > bbx[2] or max(ys) < bbx[1] or min(ys) > bbx[3]: newrows.append(row); continue
    g = Polygon(rings[0], rings[1:]).buffer(0)
    if not g.intersects(cut): newrows.append(row); continue
    h = g.difference(cut).buffer(0)
    if h.area > g.area - max(1.0, 0.01 * g.area): newrows.append(row); continue
    parts = sorted([q for q in (h.geoms if h.geom_type == 'MultiPolygon' else [h]) if q.geom_type == 'Polygon' and q.area > 4], key=lambda q: -q.area)
    if not parts: ndrop += 1; continue
    for j, q in enumerate(parts):
        q = q.simplify(0.02); rr = [list(q.exterior.coords)] + [list(r.coords) for r in q.interiors]
        newrows.append([row[0] if j == 0 else row[0] + '~' + 'abcdefghijklmnopqrstuvwxyz'[j - 1], row[1], row[2], row[3], row[4], row[5], [enc(r) for r in rr]])
    npl += 1; nsplit += len(parts) > 1
PL['plots'] = newrows
json.dump(PL, open(SP + 'deckpage/plots.json', 'w'), separators=(',', ':'))
print('plots trimmed', npl, 'split', nsplit, 'dropped', ndrop)
