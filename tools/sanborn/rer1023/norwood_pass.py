try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Norwood Central below ground, from the station sketch v10 (Ben, 23 October; norwood/sk9.py, frame norwood/frame.json):
#   Metro 4 terminus under Montgomery Road, its north end at frame offset -3 (level -2); the line's tail past it is cut (it crossed Line 3 at one level)
#   Metro 14 station about 100 m south along its line, beside Line 4 (level -3), centred at the point nearest frame (4499, -64)
#   TRI E platform between the main tunnel and TRI A: frame s 4,778-4,982, on its piece's east end (level -4)
#   Metro 3 is left as it is (Ben: its Norwood station is to be moved to a better location; not placed yet). TRI A as it was.
# Platforms keep their sideways extent; twin and RER tracks re-spread to the moved platforms (the build's 40 m tapers).
import json, numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import substring
import metro400 as M
SP = _ws.DATA
F = json.load(open(SP + 'norwood/frame.json')); O = np.array(F['o']); T_ = np.array(F['t']); N_ = np.array(F['n'])
def P(s, o): return O + T_ * (s - 4300) + N_ * o
def so(p): d = np.asarray(p) - O; return float(d @ T_) + 4300, float(d @ N_)
L4, L14, RE = 'M-L4-716800-4333419', 'M-L14-706647-4344031', 'R-E-720428-4337899'
def _ring(fr, a, b, lo, hi):
    g, ds, Pp, nr = fr; sel = (ds >= a - 1e-6) & (ds <= b + 1e-6); Q, Nn = Pp[sel], nr[sel]
    return M._r1(np.asarray(Polygon(np.r_[Q + Nn * hi, (Q + Nn * lo)[::-1]]).simplify(0.2).exterior.coords))
def _respread(C, m, cfg, sysname):
    fr = M.frame(m); g, ds, Pp, nr = fr
    spans = sorted(set((round(a, 1), round(b, 1)) for a, b, lo, hi in (M.measure(g, ds, Pp, nr, p['c']) for p in C['plats'] if p.get('pid') == m['id'])))
    C['tracks'] = [t for t in C['tracks'] if t.get('pid') != m['id']] + [dict(sys=sysname, line=m['name'], pid=m['id'], c=c) for c in M.twin_tracks(ds, Pp, nr, spans, cfg, C['meta'].get('taper_m', 40.0))]
def apply(C):
    rep = {}; NEW = C['meta']['metro_platform_m']; RPL = C['meta']['rer_platform_m']
    byid = {m['id']: m for m in C['metro'] + C['rer']}
    if L4 not in byid or L14 not in byid or RE not in byid: return {'skipped': 'pieces not found'}
    # ---- Metro 4: cut at frame offset -3, terminus platform on the new end
    m = byid[L4]; fr0 = M.frame(m); g0 = fr0[0]
    old = [p for p in C['plats'] if p.get('pid') == L4 and p['st'] == 'Norwood Central']
    if old and so(m['c'][-1])[1] > 0:                                  # not yet cut (the line still runs on north past the station)
        lat = M.measure(*fr0, old[0]['c'])[2:4]
        ds = np.linspace(0, g0.length, int(g0.length / 0.5)); oo = np.array([so(g0.interpolate(d).coords[0])[1] for d in ds])
        i = int(np.where((oo[:-1] < -3) & (oo[1:] >= -3))[0][-1]); cut = float(ds[i])
        m['c'] = M._r1(substring(g0, 0, cut).coords); fr = M.frame(m); L = fr[0].length
        old[0]['c'] = _ring(fr, L - NEW, L, *lat); C['plats'] = [p for p in C['plats'] if not (p.get('pid') == L4 and p['st'] == 'Norwood Central' and p is not old[0])]
        _respread(C, m, C['meta']['metro_twin'], 'metro')
        rep['L4'] = dict(cut_at_m=round(cut, 1), removed_tail_m=round(g0.length - cut, 1), end_so=[round(v, 1) for v in so(m['c'][-1])],
                         platform_so=[[round(v, 1) for v in so(fr[0].interpolate(L - NEW).coords[0])], [round(v, 1) for v in so(m['c'][-1])]])
    # ---- Metro 14: both side platforms to the point nearest frame (4499, -64)
    m = byid[L14]; fr = M.frame(m); g = fr[0]; c = g.project(Point(P(4499, -64)))
    for p in [p for p in C['plats'] if p.get('pid') == L14 and p['st'] == 'Norwood Central']:
        a, b, lo, hi = M.measure(*fr, p['c']); p['c'] = _ring(fr, c - NEW / 2, c + NEW / 2, lo, hi)
    rep['L14'] = dict(centre_so=[round(v, 1) for v in so(g.interpolate(c).coords[0])], arc=round(c, 1))
    # ---- TRI E: platform s 4,778-4,982 = the piece's first 204.2 m (the piece starts at frame s 4,981)
    m = byid[RE]; fr = M.frame(m); g = fr[0]
    for p in [p for p in C['plats'] if p.get('pid') == RE and p['st'] == 'Norwood Central']:
        a, b, lo, hi = M.measure(*fr, p['c']); p['c'] = _ring(fr, 0.0, RPL, lo, hi)
        rep['TRI_E'] = dict(old_s=[round(so(g.interpolate(a).coords[0])[0]), round(so(g.interpolate(b).coords[0])[0])],
                            new_s=[round(so(g.interpolate(0).coords[0])[0]), round(so(g.interpolate(RPL).coords[0])[0])])
    _respread(C, m, C['meta']['rer'], 'rer')
    # ---- station markers
    c4 = [p for p in C['plats'] if p.get('pid') == L4 and p['st'] == 'Norwood Central']; c14 = [p for p in C['plats'] if p.get('pid') == L14 and p['st'] == 'Norwood Central']
    cen = lambda ps: np.mean([Polygon(p['c']).centroid.coords[0] for p in ps], 0)
    for st in C['stations']:
        if st['name'] == 'Norwood Central' and 'Line 4' in st['line']: st['p'] = [round(float(v), 1) for v in (cen(c4) + cen(c14)) / 2]
    ce = [p for p in C['plats'] if p.get('pid') == RE and p['st'] == 'Norwood Central']
    for st in C['rer_stations']:
        if st['name'] == 'Norwood Central' and st['lines'] == ['E'] and ce: st['p'] = [round(float(v), 1) for v in cen(ce)]
    return rep

# ---- Metro 3 (Ben, 24 October): his line from St Bernard to Norwood Central (nw2/l3kml.py). It follows the page's line to within about 1 m as
# far as about 900 m short of Norwood; that piece (M-L3-720291-4337966, which starts at Norwood) takes his geometry, and the terminus platform sits
# at its new end (frame s 4,707, o +38), beside the north edge of the track field. Its level (at grade or -1, the concourse level) is still open.
L3 = 'M-L3-720291-4337966'
def apply_l3(C):
    import sys
    sys.path.insert(0, _ws.CODE + 'nw2'); from l3kml import L3NEW
    byid = {m['id']: m for m in C['metro']}
    if L3 not in byid: return {'skipped': 'piece not found'}
    m = byid[L3]; NEW = C['meta']['metro_platform_m']
    G = LineString(L3NEW); fr0 = M.frame(m); g0 = fr0[0]
    a = G.project(Point(m['c'][-1]))                                     # the piece's west end on Ben's line
    newc = [m['c'][-1]] + [list(q) for q in substring(G, a, G.length).coords][1:]
    newc = M._r1(newc[::-1])                                             # the piece runs from Norwood westward
    if np.allclose(np.asarray(newc[:3]), np.asarray(m['c'][:3]), atol=0.2): return {'L3': 'already applied'}
    pl = [p for p in C['plats'] if p.get('pid') == L3]
    meas = [(p, M.measure(*fr0, p['c'])) for p in pl]
    cen = {id(p): g0.interpolate((a_ + b_) / 2) for p, (a_, b_, lo, hi) in meas}
    m['c'] = newc; m.pop('k', None); fr = M.frame(m); g = fr[0]; rep = []
    for p, (a_, b_, lo, hi) in meas:
        if p['st'] == 'Norwood Central': s0, s1 = 0.0, NEW                  # terminus at the new end
        else: c = g.project(cen[id(p)]); s0, s1 = c - NEW / 2, c + NEW / 2
        p['c'] = _ring(fr, max(0.0, s0), min(g.length, s1), lo, hi); rep.append((p['st'], round(s0), round(s1)))
    _respread(C, m, C['meta']['metro_twin'], 'metro')
    nc = [p for p in C['plats'] if p.get('pid') == L3 and p['st'] == 'Norwood Central']
    for st in C['stations']:
        if st['name'] == 'Norwood Central' and st['line'] == 'Line 3' and nc: st['p'] = [round(float(v), 1) for v in Polygon(nc[0]['c']).centroid.coords[0]]
    return dict(L3_platforms=rep, end_so=[round(v, 1) for v in so(newc[0])], length=round(g.length), was=round(g0.length))

# ---- TRI A at Norwood Central (24 October): its line had a 130 m gap through the station (pieces ending at frame s 5,009 and starting at s 5,093,
# the station point between them) and a 60 m gap just north (s 5,158-5,178), so no platform was ever drawn. The south-west piece now runs on through
# the station and takes in the next piece's first curve; that piece runs on to the northern piece's end. Island platform 204.2 m centred on the station.
PA1, PA2, PA3 = 'R-A-718498-4336199', 'R-A-720547-4337903', 'R-A-720769-4338157'
def apply_tria(C):
    by = {m['id']: m for m in C['rer']}
    if not all(k in by for k in (PA1, PA2, PA3)): return {'skipped': 'pieces not found'}
    m1, m2, m3 = by[PA1], by[PA2], by[PA3]
    if any(p.get('pid') == PA1 and p['st'] == 'Norwood Central' for p in C['plats']): return {'TRI_A': 'already applied'}
    a, b = np.asarray(m2['c'][0], float), np.asarray(m2['c'][1], float); q = np.asarray(m2['k']['0'], float)
    curve = [((1 - u) ** 2 * a + 2 * (1 - u) * u * q + u * u * b).tolist() for u in np.linspace(0, 1, 13)]
    m1['c'] = M._r1(m1['c'] + curve)                                   # straight across the gap, then the curve (as polyline points)
    m1.setdefault('curves', []).extend(m2.get('curves', [])[:1])
    rest = [m2['c'][1], m2['c'][2]]                                    # drop the tiny back-step at the old end
    m2['c'] = M._r1(rest + [m3['c'][-1]]); m2['k'] = {'0': m2['k']['1']} if '1' in m2['k'] else {}; m2['curves'] = m2.get('curves', [])[1:]
    fr = M.frame(m1); g = fr[0]; RPL = C['meta']['rer_platform_m']; cfg = C['meta']['rer']
    stp = next(s for s in C['rer_stations'] if s['name'] == 'Norwood Central' and s['lines'] == ['A'])
    c = g.project(Point(stp['p'])); hw = cfg['island'] / 2
    C['plats'].append(dict(sys='rer', line='A', pid=PA1, c=_ring(fr, c - RPL / 2, c + RPL / 2, -hw, hw), st='Norwood Central', id='P-R-A-norwood-central'))
    for m in (m1, m2): _respread(C, m, cfg, 'rer')
    stp['p'] = [round(float(v), 1) for v in Polygon(C['plats'][-1]['c']).centroid.coords[0]]
    return dict(piece1_end=[round(v, 1) for v in so(m1['c'][-1])], piece2=[[round(v, 1) for v in so(p)] for p in m2['c']],
                platform_s=[round(so(g.interpolate(c - RPL / 2).coords[0])[0]), round(so(g.interpolate(c + RPL / 2).coords[0])[0])], station=[round(v, 1) for v in so(stp['p'])])
