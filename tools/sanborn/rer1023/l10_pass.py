try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Line 10 on its new right of way (Ben, 24 October: rer1023/line10_1024.kml, "new Line 10"; west of it unchanged).
# The KML runs from a point on the old line just west of Wilstach (713,187 / 4,332,333) to Ft Thomas. The inner piece keeps the old
# line up to that point and takes the KML to the plan window edge (x 716,800); the outer piece is the KML from there on.
# Platforms from Wilstach east are rebuilt on the new line, centred where the old ones were, at 121.92 m (bore: two side platforms).
# Baines: the Line 10 platform is centred on Ben's point (KML "Bains", 24 October), 61 m west of the shared Line 5/10 station mark.
import json, numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import substring
import metro400 as M
SP = _ws.DATA
IN, OUT = 'M-L10-710747-4329650', 'M-L10-716800-4331840'
EDGE_X = 716800.0
BAINS = (716983.2, 4332077.5)
def _new():
    N = json.load(open(SP + 'rer1023/l10_new_utm.json'))
    return N[1] + N[0][1:]                                              # "Metro Line 10" (west part) then "Line 10" (east part)
def _ring(g, ds, Pp, nr, a, b, lo, hi):
    sel = (ds >= a - 1e-6) & (ds <= b + 1e-6); Q, Nn = Pp[sel], nr[sel]
    return M._r1(np.asarray(Polygon(np.r_[Q + Nn * hi, (Q + Nn * lo)[::-1]]).simplify(0.2).exterior.coords))
def apply(C):
    from gaps_pass import respread
    byid = {m['id']: m for m in C['metro']}
    if IN not in byid or OUT not in byid: return {'skipped': 'pieces not found'}
    mi, mo = byid[IN], byid[OUT]
    new = _new(); gnew = LineString(new)
    g0 = M.frame(mi)[0]
    s_cut = g0.project(Point(new[0]))
    if g0.distance(Point(new[0])) > 2: return {'skipped': 'KML start is not on the old line'}
    # old platforms to rebuild: those on the inner piece east of the cut, and all on the outer piece
    oldp = [p for p in C['plats'] if p['sys'] == 'metro' and p.get('pid') in (IN, OUT)
            and (p['pid'] == OUT or M.measure(*M.frame(mi), p['c'])[0] > s_cut)]
    stations = {}
    for p in oldp: stations.setdefault(p['st'], []).append(Polygon(p['c']).centroid)
    # inner piece: old vertices before the cut (with their curves), the old curve up to the cut, then the KML to the window edge
    vs = np.array([g0.project(Point(v)) for v in mi['c']]); keep = int(np.searchsorted(vs, s_cut - 1.0))   # vertices 0..keep-1
    k = {i: v for i, v in (mi.get('k') or {}).items() if int(i) < keep - 1}
    part = list(substring(g0, vs[keep - 1], s_cut).coords)[1:]
    part = list(LineString([mi['c'][keep - 1]] + part).simplify(0.1).coords)[1:-1] if len(part) > 1 else []
    edge = gnew.intersection(LineString([(EDGE_X, 4300000), (EDGE_X, 4360000)]))
    s_edge = gnew.project(edge)
    west = list(substring(gnew, 0, s_edge).coords); east = list(substring(gnew, s_edge, gnew.length).coords)
    mi['c'] = mi['c'][:keep] + M._r1(part) + M._r1(west); mi['k'] = k
    mo['c'] = M._r1(east); mo.pop('k', None)
    # platforms
    C['plats'] = [p for p in C['plats'] if not any(p is q for q in oldp)]
    NEW = C['meta']['metro_platform_m']; MB = C['meta']['metro_bore']; i0 = MB['h0'] + MB['edge']
    bands = [(i0, i0 + MB['side']), (-i0 - MB['side'], -i0)]
    frs = {IN: M.frame(mi), OUT: M.frame(mo)}; rep = []
    for st, cens in stations.items():
        c = BAINS if st == 'Baines' else tuple(np.mean([[q.x, q.y] for q in cens], axis=0))
        pid = min(frs, key=lambda kk: frs[kk][0].distance(Point(c))); g, ds, Pp, nr = frs[pid]
        sc = g.project(Point(c)); a, b = sc - NEW / 2, sc + NEW / 2
        if a < 0: a, b = 0.0, NEW
        if b > g.length: a, b = g.length - NEW, g.length
        for lo, hi in bands:
            ring = _ring(g, ds, Pp, nr, a, b, lo, hi); cen = np.mean(ring[:-1], axis=0)
            C['plats'].append(dict(sys='metro', line='Line 10', pid=pid, st=st, id=f'P-M-L10-{int(cen[0])}-{int(cen[1])}', c=ring))
        rep.append((st, pid[-7:], round(a), round(b), round(g.distance(Point(c)), 1)))
    respread(C, mi, 'metro'); respread(C, mo, 'metro')
    return dict(cut_at_old_m=round(s_cut, 1), inner_len=round(frs[IN][0].length), outer_len=round(frs[OUT][0].length), edge=M._r1([edge.coords[0]])[0], platforms=rep)
# Ben's live edit of the inner piece (made before the KML) is what the page draws, so it gets the same change: his edit up to the
# KML's start, then the KML to the window edge (Ben, 24 October: "previous edits overwriting it").
def edit_fix(e):
    new = _new(); gnew = LineString(new)
    g0 = LineString(M._dense(e['c'], e.get('k') or {})) if e.get('k') else LineString(e['c'])
    if g0.distance(Point(new[0])) > 3: return None
    s_cut = g0.project(Point(new[0]))
    vs = np.array([g0.project(Point(v)) for v in e['c']]); keep = int(np.searchsorted(vs, s_cut - 1.0))
    k = {i: v for i, v in (e.get('k') or {}).items() if int(i) < keep - 1}
    part = list(substring(g0, vs[keep - 1], s_cut).coords)[1:]
    part = list(LineString([e['c'][keep - 1]] + part).simplify(0.1).coords)[1:-1] if len(part) > 1 else []
    edge = gnew.intersection(LineString([(EDGE_X, 4300000), (EDGE_X, 4360000)]))
    west = list(substring(gnew, 0, gnew.project(edge)).coords)
    return dict(e, c=e['c'][:keep] + M._r1(part) + M._r1(west), k=k)
