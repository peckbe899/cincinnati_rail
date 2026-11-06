# ---------------------------------------------------------------- CVG Express: platform M, its own span beside the APEx bridge, with the APEx through the hills, its own line to CVG
# Ben (16 October): option A with a separate span; CVG Express New.kmz: from CUT with the APEx across the river and through the hills to Erlanger,
# then its own line west to CVG (the last part on the TRIMET CVG line); the path to the terminals is not set (it is an airside train).
# The CVG pair stays east of the APEx (no crossing at CUT but the Cardinal pair, none in Ludlow), runs in its own bores beside the APEx tunnel, and
# crosses over the APEx before Erlanger, where it turns west.
TCS = smooth([tuple(p[:2]) for p in TB['cs']], it=4)
MERGE = (712600.0, 4330705.0)
BANK_N = 4330684.0
def tcs_z(p):                                                       # TRIMET CS viaduct rail level nearest p
    pts = TB['cs']; g = LineString([q[:2] for q in pts]); s = g.project(Point(p)); acc = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        L = math.dist(a[:2], b[:2])
        if acc + L >= s: f = (s - acc) / max(L, 1e-9); return a[2] + f * (b[2] - a[2])
        acc += L
    return pts[-1][2]
z_merge = tcs_z(MERGE)                                              # the intercity pair's target where it meets the TRIMET CS viaduct
_KN = json.load(open(S + 'cvgkmz/cvg_kmz.json'))['CVG_Express_New.kml']
_P2 = [tuple(c) for c in _KN[1]['c']][::-1]; _P3 = [tuple(c) for c in _KN[2]['c']]; _P4 = [tuple(c) for c in _KN[3]['c']]
CV3_ = [tuple(c) for c in [r for r in json.load(open(S + 'ludlow/kmz_south.json'))['TRIMET_Lines.kmz'] if r['name'] == 'CVG Express 3D'][0]['c']]
def z_on3(L3, p):
    g = LineString([c[:2] for c in L3]); s = g.project(Point(p)); acc = 0.0
    for a, b in zip(L3[:-1], L3[1:]):
        Lg = math.dist(a[:2], b[:2])
        if acc + Lg >= s: f = (s - acc) / max(Lg, 1e-9); return a[2] + f * (b[2] - a[2])
        acc += Lg
    return L3[-1][2]
_AK = [r for r in json.load(open(S + 'ludlow/kmz_south.json'))['APEx Routes.kmz'] if r['kind'] == 'line' and r['name'] == 'Cincinnati-Lexington 1' and r['n'] == 9][0]['c']
_AK = [tuple(c[:2]) for c in _AK]; _AK = _AK if _AK[0][1] > _AK[-1][1] else _AK[::-1]      # the APEx KMZ line, Ludlow -> south past Erlanger
CORR = resample(KC + [q for q in _AK if q[1] < KC[-1][1] - 30], 5.0)  # the APEx Kentucky centre line: approach, bridge, Ludlow, the KMZ line through the hills
_CORRL = LineString(CORR); s_kb_c = _CORRL.project(Point(APB[1]))
CVG_OFF = 24.75                                                     # CVG centre east of the APEx centre (tracks +22.5 / +27.0): own span, own bores
N_JOIN = 4331300.0
N_DIV0 = 4326050.0                                                  # the CVG leaves the side of the APEx here and crosses over it to the west
_par = from_N([q for q in offs(CORR, CVG_OFF)], N_JOIN)
_par = cut_at_N(_par, N_DIV0)
_d3 = np.subtract(_P3[5], _P3[4]); _d3 = _d3 / np.linalg.norm(_d3)
_P2pt = tuple(np.array(_P3[4]) + _d3 * 250.0)                        # on the KMZ line west of the APEx, 250 m past where it leaves it
_xo = bezt(tuple(_par[-1]), tuple(tangent(_par, 'end')), _P2pt, tuple(_d3), k=0.42, n=120)
_tail = [_P2pt] + [_P3[5]] + _P4[1:]
_tail = smooth(thin(_tail, 25.0), it=5, step=5.0)
CVGC = resample(_par + _xo[1:] + _tail[1:], 5.0)
CVGC = smooth(thin(CVGC, 12.0), it=3, step=5.0)
for n, d in (('15', -2.25), ('16', 2.25)):
    tgt = offs(CVGC, d)
    add('apex', bezt(TRK[n][1], tuple(F_DIR), tgt[0], tangent(tgt, 'start'), k=0.42, n=60), name=f'CVG Express south throat, track {n}', level='0', kind='throat')
_CVL = LineString(CVGC)
s_cv_bank = _CVL.project(Point(tuple(np.array(APB[1]) + _n * CVG_OFF)))
def apex_zN(N):                                                     # APEx rail on the approach (CUT to the Ohio bank) by northing
    if N >= STREETS['W 8th']: return APEX(N)
    s8_ = s_at_N(CSL, STREETS['W 8th']); sbk = s_at_N(CSL, float(APB[0][1]))
    s_ = LineString(CSL).project(Point(min(CSL, key=lambda q: abs(q[1] - N))))
    return min(164.0, APEX(STREETS['W 8th']) + (164.0 - APEX(STREETS['W 8th'])) / (sbk - s8_) * (s_ - s8_))
def apex_at(p):                                                     # APEx rail level nearest p (by corridor chainage)
    sc = _CORRL.project(Point(p))
    return apex_zN(p[1]) if sc < s_kb_c else apex_kz(sc - s_kb_c)
_J = (707194.0, 4323703.0); s_J = _CVL.project(Point(_J)); z_J = z_on3(CV3_, _J)   # where the line meets the TRIMET CVG line
s_X0 = _CVL.project(Point(_par[-1]))
def cvg_profile(s_c0):
    z0 = apex_at(_CVL.interpolate(s_c0).coords[0]); g = (z_J - z0) / (s_J - s_c0)
    def z(s):
        q = _CVL.interpolate(s).coords[0]
        if s <= s_cv_bank: return apex_zN(q[1])
        if s <= s_c0: return apex_at(q)
        if s <= s_J: return z0 + g * (s - s_c0)
        return z_on3(CV3_, q)
    return g, z
# choose where the CVG starts to climb away from the APEx: as late as possible with the climb at 2.5% or less and 15 m over the APEx where it crosses (working value for bore over bore)
_best = None
for s_c0 in np.arange(s_cv_bank + 1000, s_X0 + 1, 50.0):
    g, zf = cvg_profile(s_c0)
    if g > 0.025: continue
    clr = min((zf(s) - apex_at(_CVL.interpolate(s).coords[0]), s) for s in np.arange(s_X0, s_X0 + 1600, 5.0) if _CORRL.distance(_CVL.interpolate(s)) < 6.75 + 2.25 + 2.0) if True else None
    if clr[0] >= 15.0: _best = (s_c0, g, clr)
S_C0, G_CV, CLR_X = _best
_, cvz = cvg_profile(S_C0)
# the CS line crossing near Erlanger, ground cover, portals
_csx = _CVL.intersection(LineString(LWS))
_csx = [p for p in getattr(_csx, 'geoms', [_csx]) if p.geom_type == 'Point' and p.y < 4325000]
_csxi = [dict(at=[round(p.x), round(p.y)], z_cvg=round(cvz(_CVL.project(p)), 1), z_cs=round(cs_z((p.x, p.y)), 1)) for p in _csx]
_DMJ2 = json.load(open(S + 'topo/dem2m.json')); _DEM2 = np.load(S + 'topo/dem2m.npy', mmap_mode='r')
def ground2(p):
    r = int((_DMJ2['y1'] - p[1]) / 2); c = int((p[0] - _DMJ2['x0']) / 2)
    if not (0 <= r < _DEM2.shape[0] and 0 <= c < _DEM2.shape[1]): return None
    v = _DEM2[r, c]; return None if v == _DMJ2['nodata'] else float(v) / 10.0
SS = np.arange(s_cv_bank, _CVL.length, 10.0)
_state = []
for s in SS:
    gz = ground2(_CVL.interpolate(s).coords[0]); z = cvz(s)
    _state.append('tunnel' if (gz is not None and gz - z >= COVER) else 'open')
_runs = []                                                          # [(state, s0, s1)]
for s, st in zip(SS, _state):
    if _runs and _runs[-1][0] == st: _runs[-1][2] = s
    else: _runs.append([st, s, s])
_runs = [r for r in _runs if r[2] - r[1] >= 60 or r[0] == 'open']
CVG_INFO = dict(z_m=round(APEX(FN0), 1), offset=CVG_OFF, span_gap=round(CVG_OFF - 2.25 - 4.75 - (6.75 + 4.75), 2),
                climb_from=round(S_C0 - s_cv_bank), g=round(100 * G_CV, 2), over_apex=dict(clear=round(CLR_X[0], 1), at=[round(_CVL.interpolate(CLR_X[1]).x), round(_CVL.interpolate(CLR_X[1]).y)]),
                cs_crossing=_csxi, z_J=round(z_J, 1), end=[round(CVGC[-1][0]), round(CVGC[-1][1])], z_end=round(cvz(_CVL.length), 1),
                length_km=round((_CVL.length - s_cv_bank) / 1000, 1), runs=[(r[0], round(r[1] - s_cv_bank), round(r[2] - s_cv_bank)) for r in _runs],
                r_min_throat=round(min(min_radius(f['geometry']['coordinates'], win=20.0) for f in F if f['properties'].get('name', '').startswith('CVG Express south throat'))),
                r_min=round(min_radius(CVGC, win=30.0)))
# the Cardinal pair crosses the CVG pair (at grade, south of W 8th)
_car = [LineString(f['geometry']['coordinates']) for f in F if f['properties'].get('name', '').startswith('Cardinal branch')]
_xc = []
for a in _car:
    for d in (-2.25, 2.25):
        x = a.intersection(LineString(offs(CVGC, d))); _xc += [p for p in getattr(x, 'geoms', [x]) if p.geom_type == 'Point' and p.y > 4330800]
_xcN = sorted(p.y for p in _xc)
CVG_INFO.update(cardinal_x=len(_xc), cardinal_N=[round(_xcN[-1]), round(_xcN[0])] if _xcN else None)
# draw: tunnel runs dashed
_cuts = [(r[0], r[1], r[2]) for r in _runs]
def piece(c, s0, s1):
    g = LineString(c); return list(substring(g, max(0, s0), min(g.length, s1)).coords)
from shapely.ops import substring
for d, nm in ((-2.25, 'west'), (2.25, 'east')):
    c = offs(CVGC, d)
    add('apex', piece(c, 0, s_cv_bank), name=f'CVG Express ({nm} track): platform M to the Ohio, on its own span', level='0, span', kind='cvg',
        note='east of the APEx approach from platform M (at grade across the Cardinal pair south of W 8th), then its own double-track span beside the APEx bridge')
    for st, s0, s1 in _cuts:
        add('apex', piece(c, s0, s1 + 10), name=f'CVG Express ({nm} track), ' + ('tunnel' if st == 'tunnel' else 'open'), level=st, kind='cvg', **({'state': 'tunnel'} if st == 'tunnel' else {}),
            note=f'CVG Express New.kmz: beside the APEx (own bores, {CVG_OFF:.2f} m east of its centre) through Ludlow and the hills, {100*G_CV:.2f}% up from {S_C0 - s_cv_bank:,.0f} m past the bank, '
                 f'over the APEx ({CLR_X[0]:.1f} m) before Erlanger, under the CS line, then on to CVG (the last part on the TRIMET CVG line); the path to the terminals is not set (airside)')
add('bridge', [tuple(np.array(APB[0]) + _n * CVG_OFF), tuple(np.array(APB[1]) + _n * CVG_OFF)], name='CVG Express span (double track), beside the APEx bridge',
    rail_m='about 164', note=f'its own structure, {CVG_INFO["span_gap"]:.1f} m clear of the APEx bridge (drawing values: 4.75 m from outer track to deck edge)')
if _xc: addpt('marker', (np.mean([p.x for p in _xc]), np.mean([p.y for p in _xc])), kind='level', name='Cardinal crosses the CVG Express', label='Cardinal crosses the CVG Express at grade', anchor='left')
_qx = _CVL.interpolate(CLR_X[1])
addpt('marker', (_qx.x, _qx.y), kind='level', name='CVG Express over the APEx', label=f'CVG Express {cvz(CLR_X[1]):.0f} m over the APEx tunnel ({CLR_X[0]:.0f} m clear)', anchor='left')
for x in _csxi: addpt('marker', tuple(x['at']), kind='level', name='CVG Express under the CS line', label=f'CVG Express {x["z_cvg"]:.0f} m, under the CS line ({x["z_cs"]:.0f} m)', anchor='left')
addpt('marker', tuple(CVGC[-1]), kind='flag', name='CVG Express: end of the KMZ line', label='CVG Express: on to the terminals (airside), not set', anchor='left')
