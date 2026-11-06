try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben (17 October): a layer showing the width of the rail viaducts and bridges in the valley and basin, above all the CUT approach viaduct
# (the buildings and lots either side will be redrawn by hand). Footprints are the track centre lines on structure, each widened by EDGE
# beyond the outer track (working value: overhead line masts on the deck edge, walkway and parapet), gaps under 2*CLOSE between tracks
# closed (island platforms, track pairs), and the platforms of stations on the structure added. Reads deckpage/tracks.json,
# context.json, deck.json, cut/trimet_bridges.json and the 2 m DEM; writes deckpage/structures.json. Run after tracks_gen4 + apex_region.
import json, math, numpy as np
from shapely.geometry import shape, mapping, LineString, Point, Polygon, MultiPolygon, box
from shapely.ops import unary_union, substring
S = _ws.DATA
EDGE = 4.2          # outer track centre to the deck's outer face (working value; e.g. a 13.4 m double-track deck with 5.0 m centres)
CLOSE = 3.0         # gaps narrower than 6 m between track footprints are decked over
T = json.load(open(S + 'deckpage/tracks.json')); C = json.load(open(S + 'deckpage/context.json')); D = json.load(open(S + 'deckpage/deck.json'))
TB = json.load(open(S + 'cut/trimet_bridges.json'))
DECKO = shape([f for f in D['features'] if f['properties'].get('layer') == 'deck'][0]['geometry']).buffer(0)
DECK = lambda N: 151.8 + (N - 4330700) / 4840 * 8.2
DMJ = json.load(open(S + 'topo/dem2m.json')); DEM = np.load(S + 'topo/dem2m.npy', mmap_mode='r')
def ground(p):
    if DECKO.contains(Point(p)): return DECK(p[1])
    r = int((DMJ['y1'] - p[1]) / 2); c = int((p[0] - DMJ['x0']) / 2)
    if not (0 <= r < DEM.shape[0] and 0 <= c < DEM.shape[1]): return None
    v = DEM[r, c]; return None if v == DMJ['nodata'] else float(v) / 10.0
FN0, FN1 = 4331646.0, 4332134.0
TL = [f for f in T['features'] if f['geometry']['type'] == 'LineString']
def lines(pred): return [LineString(f['geometry']['coordinates']) for f in TL if pred(f['properties'])]
nm = lambda p: p.get('name') or ''
BR = {nm(f['properties']): LineString(f['geometry']['coordinates']) for f in TL if f['properties'].get('layer') == 'bridge'}
def bridge(key): return next(v for k, v in BR.items() if k.startswith(key))
def north_of(N): return box(6e5, N, 8e5, 4.4e6)
def south_of(N): return box(6e5, 4.3e6, 8e5, N)
def deck(ls, clip=None):
    g = unary_union([l.buffer(EDGE, cap_style=2, join_style=2, mitre_limit=2.5) for l in ls])
    g = g.buffer(CLOSE, join_style=2, mitre_limit=2.5).buffer(-CLOSE, join_style=2, mitre_limit=2.5)
    return g.intersection(clip) if clip is not None else g
def cut_at_span(l, br, keep='before'):   # the part of a track before (north of) a bridge span starts
    s = l.project(Point(br.coords[0])); s2 = l.project(Point(br.coords[-1])); a = min(s, s2)
    return substring(l, 0, a) if keep == 'before' else substring(l, a, max(s, s2))
OUT = []; LAB = []
def widths(g, guide, step=120.0, name=''):
    """width across the footprint, perpendicular to the guide line, every step metres (labels where it changes)"""
    last = None; n = 0; ws = []
    for s in np.arange(step / 2, guide.length, step):
        p = guide.interpolate(s); a = guide.interpolate(max(0, s - 3)); b = guide.interpolate(min(guide.length, s + 3))
        dx, dy = b.x - a.x, b.y - a.y; L = math.hypot(dx, dy)
        if L == 0: continue
        nx, ny = -dy / L, dx / L; cut = LineString([(p.x - nx * 150, p.y - ny * 150), (p.x + nx * 150, p.y + ny * 150)]).intersection(g)
        segs = [q for q in getattr(cut, 'geoms', [cut]) if q.geom_type == 'LineString' and q.distance(p) < 0.5]
        if not segs: continue
        w = round(segs[0].length, 1); m = segs[0].interpolate(0.5, normalized=True); ws.append(w)
        if last is None or abs(w - last[0]) > 0.6 or s - last[1] > 450:
            LAB.append(dict(type='Feature', properties=dict(layer='struct_w', width_m=w, of=name), geometry=dict(type='Point', coordinates=[round(m.x, 1), round(m.y, 1)])))
            last = (w, s); n += 1
    return ws
def emit(g, name, kind, note, guide=None, **kw):
    g = g.buffer(0)
    if g.is_empty: return
    gg = g.simplify(0.1)
    ws = widths(g, guide, name=name) if guide is not None else []
    if ws: kw.update(w_min=min(ws), w_max=max(ws))
    OUT.append(dict(type='Feature', properties=dict(layer='struct', name=name, kind=kind, note=note, area_m2=round(g.area), **kw), geometry=json.loads(json.dumps(mapping(gg), default=float))))
# ---------------------------------------------------------------- 1. CUT approach viaduct (south): field to the bridges
APB = bridge('APEx bridge'); CVS = bridge('CVG Express span')
south = []
south += lines(lambda p: p.get('layer') == 'apex' and nm(p).startswith(('APEx south throat', 'CVG Express south throat', 'Cardinal branch')))
south += [l.intersection(south_of(FN0)) for l in lines(lambda p: p.get('kind') == 'transfer')]
south += [cut_at_span(l, APB) for l in lines(lambda p: nm(p).startswith('APEx Kentucky') and 'tunnel' not in nm(p))]
south += [cut_at_span(l, CVS) for l in lines(lambda p: nm(p).startswith('CVG Express (') and p.get('level') == '0, span')]
south += [l.intersection(south_of(FN0)) for l in lines(lambda p: p.get('layer') == 'passing')]
south = [l for l in south if not l.is_empty and l.length > 1]
g1 = deck(south, south_of(FN0 + 0.01))
guide1 = [l for l in lines(lambda p: nm(p).startswith('APEx Kentucky 2'))][0]
emit(g1, 'CUT approach viaduct (south)', 'viaduct', 'APEx Kentucky 4, Cardinal 2 and CVG Express 2 from the platform ends to the river; the arch viaduct over the deck streets (rail = deck + 6.5 m, then one grade to the bridge)',
     guide=cut_at_span(guide1, APB), tracks='4 APEx + 2 Cardinal + 2 CVG Express (+ freight passing track)')
# ---------------------------------------------------------------- 2. CUT platform deck
fld = lines(lambda p: p.get('layer') == 'apex' and p.get('kind') == 'platform') + [l.intersection(box(6e5, FN0, 8e5, FN1)) for l in lines(lambda p: p.get('layer') == 'passing')]
g2 = deck([l for l in fld if not l.is_empty], box(6e5, FN0, 8e5, FN1))
w_fld0 = g2.intersection(LineString([(712600, (FN0 + FN1) / 2), (713000, (FN0 + FN1) / 2)])).length
emit(g2, 'CUT platform deck', 'station', 'APEx platforms 1-7 and platform M (tracks 1-16) on the arch viaduct, level with the rotunda', guide=None,
     tracks='16 + freight passing track', w_min=round(w_fld0, 1), w_max=round(w_fld0, 1))
mid = (FN0 + FN1) / 2; w_fld = g2.intersection(LineString([(712600, mid), (713000, mid)])).length
LAB.append(dict(type='Feature', properties=dict(layer='struct_w', width_m=round(w_fld, 1), of='CUT platform deck'), geometry=dict(type='Point', coordinates=[round(g2.centroid.x, 1), round(mid, 1)])))
# ---------------------------------------------------------------- 3. North arch viaduct: field to Ludlow (APEx, lower pairs, RER on the viaduct)
north = lines(lambda p: p.get('layer') == 'apex' and nm(p).startswith(('APEx north throat', 'APEx north approach')))
north += lines(lambda p: p.get('layer') == 'lower' and (p.get('level') == '0' or p.get('state') == 'ramp'))
north += [l.intersection(north_of(FN1)) for l in lines(lambda p: p.get('layer') == 'passing')]
north += lines(lambda p: nm(p).startswith('R5 to the Cumminsville Spur'))      # 2026-10-22: R5 under the Indianapolis + D deck, and its 200 m curve onto RER A
trunk = unary_union([l for l in north if not l.is_empty])
rer_v = [LineString(r['c']) for r in C['rer_struct'] if r['state'] == 'viaduct' and r.get('note') != 'flyover']
rer_tr = []
for t in C['tracks']:
    if t['sys'] != 'rer': continue
    l = LineString(t['c'])
    for v in rer_v:
        part = l.intersection(v.buffer(9.0))
        for q in getattr(part, 'geoms', [part]):
            if q.geom_type == 'LineString' and q.length > 20: rer_tr.append(q)
g3 = deck([l for l in north if not l.is_empty] + rer_tr, north_of(FN1 - 0.01))
plats = [Polygon(pl['c']) for pl in C['plats'] if pl['sys'] == 'rer' and len(pl['c']) >= 3]
on = [q.buffer(1.0, join_style=2) for q in plats if q.buffer(0).intersects(g3) and q.buffer(0).intersection(g3).area > 0.3 * q.area]
g3 = unary_union([g3] + on)
guide3 = lines(lambda p: nm(p).startswith('APEx north approach 3'))[0]
emit(g3, 'North arch viaduct', 'viaduct', 'One level from the CUT platform ends to the Northside / Spring Grove (B) platform end: ORR / Transvalley 2, RER B/D 2, APEx 6 (then 4), ORR / Transvalley 2; the Indianapolis + D upper level west of it with R5 under it; RER stations on it (push of 26 October 2026)',
     guide=guide3, tracks='ORR/TV 4, RER B 2, APEx 6 then 4; Indianapolis + D upper level, R5 lower', rer_platforms=len(on))
# ---------------------------------------------------------------- 4-5. Intercity and C&O pairs: open from the portal (walls, then fill or viaduct)
PR = T['summary']['prof']
def climb(key, name, s_open, br, note):
    pts = PR[key]['c']; cl = LineString([q[:2] for q in pts]); zs = np.array([q[2] for q in pts]); ss = np.array([cl.project(Point(q[:2])) for q in pts])
    gr = np.array([ground(q[:2]) or np.nan for q in pts])
    if s_open is None:   # past the last street it passes under (W 6th), where the roof would show (rail within 7.5 m of the ground)
        w6 = next(f for f in T['features'] if f['properties'].get('name') == 'C&O pair under W 6th')['geometry']['coordinates']
        s6 = cl.project(Point(w6)) + 10.0
        ok = np.where((zs >= gr - 7.5) & (ss >= s6))[0]; s_open = float(ss[ok[0]]) if len(ok) else cl.length
    s_end = cl.project(Point(br.coords[0])) if br is not None else cl.length
    up = np.where((zs >= gr) & (ss >= s_open))[0]; s_up = float(ss[up[0]]) if len(up) else s_end
    for a, b, kind, txt in ((s_open, s_up, 'trough', 'open between retaining walls, rails below the ground'), (s_up, s_end, 'viaduct', 'on fill or viaduct, rails above the ground')):
        if b - a < 5: continue
        seg = substring(cl, a, b); g = unary_union([seg.parallel_offset(d, 'left') .buffer(EDGE, cap_style=2, join_style=2) for d in (-2.25, 2.25)])
        g = g.buffer(CLOSE, join_style=2).buffer(-CLOSE, join_style=2)
        za, zb = np.interp(a, ss, zs), np.interp(b, ss, zs)
        emit(g, f'{name}: {kind}', kind, f'{note}; {txt}; rail {za:.1f} to {zb:.1f} m', guide=seg, tracks='2', length_m=round(b - a))
    return s_open, s_up
CSB = bridge('Cincinnati Southern bridge')
ic = climb('intercity', 'Intercity pair', PR['intercity']['portal_s'], CSB, 'From the portal in the W 8th south wall to the CS bridge')
co = climb('co', 'C&O pair', None, None, 'From under W 6th to the TRIMET C&O viaduct')
# the TRIMET C&O viaduct on to the C&O bridge (an existing line: the same width rule, a working value)
COB = bridge('C&O bridge'); tco = [tuple(q) for q in TB['co']]
j = min(range(len(tco)), key=lambda i: math.dist(tco[i][:2], PR['co']['c'][-1][:2]))
cl = LineString([q[:2] for q in tco[j:]]); sb = cl.project(Point(COB.coords[0])); cl = substring(cl, 0, sb)
emit(deck([cl.parallel_offset(2.25, 'left'), cl.parallel_offset(2.25, 'right')]), 'C&O viaduct (TRIMET line, to the C&O bridge)', 'viaduct_existing',
     'the C&O pair on the TRIMET C&O approach viaduct to the river (double track, same width rule)', guide=cl, tracks='2')
# ---------------------------------------------------------------- 6. River bridges (tracks over the spans)
def span_deck(name, pred, br, tracks, note):
    ls = []
    for l in lines(pred):
        a, b = l.project(Point(br.coords[0])), l.project(Point(br.coords[-1]))
        if abs(b - a) > 20: ls.append(substring(l, min(a, b), max(a, b)))
    if ls: emit(deck(ls), name, 'bridge', note, guide=br, tracks=tracks)
span_deck('APEx bridge', lambda p: nm(p).startswith('APEx Kentucky') and 'tunnel' not in nm(p), APB, '4', 'four APEx tracks; span ends from Bridge Spans.kmz')
span_deck('CVG Express span', lambda p: nm(p).startswith('CVG Express (') and p.get('level') == '0, span', CVS, '2', 'double track beside the APEx bridge')
span_deck('Cincinnati Southern bridge (1922)', lambda p: nm(p).startswith('CS line ('), CSB, '2', 'the intercity pair; the real truss width is not set here, drawn by the same rule')
cob = LineString([q[:2] for q in tco]); a, b = cob.project(Point(COB.coords[0])), cob.project(Point(COB.coords[-1]))
emit(deck([substring(cob, min(a, b), max(a, b)).parallel_offset(d, 'left') for d in (-2.25, 2.25)]), 'C&O bridge (1929)', 'bridge', 'the C&O pair; the real truss width is not set here, drawn by the same rule', guide=COB, tracks='2')
# ---------------------------------------------------------------- 7. The trunk over Ludlow (2026-10-22, highway update): Ludlow stays at ground on its
# 1914 line, the viaduct spans it, and the tracks run on fill north of it, level through the RER B Northside / Spring Grove platforms, then down to ground
import sys as _sys; _sys.path.insert(0, _ws.CODE + 'nv'); import geom27 as G27
_sys.path.insert(0, _ws.CODE + 'trunk2'); import geo4 as _Q          # push of 26 October 2026: the new trunk frame north of Arlington
_FR = LineString(_Q.TR.P)
S_FILL1 = next(float(x) for x in np.arange(G27.S_NSP1, 7200, 5.0) if G27.north_z(x) <= (ground(_Q.TR.at(x)[0]) or 0))
def _cs(l, a, b):                                       # the part of a track between frame chainages a and b
    pts = [q for q in l.coords if a <= _Q.TR.proj(q) <= b and _FR.distance(Point(q)) < 60]
    return LineString(pts) if len(pts) >= 2 else None
fl = [_cs(l, G27.S_NSP1, S_FILL1) for l in lines(lambda p: nm(p).startswith(('APEx Dayton (Southwest Chief)', 'APEx Norwood (Transcontinental)')) or (p.get('layer') == 'lower' and nm(p).endswith('on the fill')))]
fl += [_cs(LineString(t['c']), G27.S_NSP1, S_FILL1) for t in C['tracks'] if t.get('pid') == 'R-B-715612-4338596']
fl = [l for l in fl if l is not None and l.length > 20]
g_fill = deck(fl)
_gd = LineString([_Q.TR.at(x)[0] for x in np.arange(G27.S_NSP1, S_FILL1, 5.0)])
emit(g_fill, 'North trunk fill (Northside / Spring Grove to ground)', 'embankment',
     f'the ORR / Transvalley pairs, RER B and the APEx Dayton and Norwood pairs on fill from the end of the north viaduct at the Northside / Spring Grove (B) platform end (s {G27.S_NSP1:,.0f}, {G27.Z_LUD:.1f} m), '
     f'{100 * G27.G_NFILL:.1f}% down to ground at about s {S_FILL1:,.0f}. Retaining walls or slopes not drawn',
     guide=_gd, tracks='ORR/TV 4, RER B 2, APEx 4')
_B22 = json.load(open(S + 'deckpage/basin.json'))
_lud = shape(next(f['geometry'] for f in _B22['features'] if f['properties'].get('id') == 'S22015'))
_ub = _lud.buffer(9.15 + 1.0, cap_style=2).intersection(unary_union([g3, g_fill]).buffer(0))
_ub = _ub.intersection(box(712650, 4336850, 712800, 4337000))
emit(_ub, 'Ludlow underbridge', 'bridge', f'the trunk over Ludlow Avenue at ground (155.4 m), rail {G27.Z_LUD:.1f} m, about 26 degrees of skew, so the span runs well over 100 m along the tracks; '
     'the RER B Northside / Spring Grove platforms start at its north edge', tracks='trunk')
# ---------------------------------------------------------------- 8. North of Mitchell (2026-10-26): the Transvalley crossing at Norwood and the RER B flyover near Paddock
_tv = lines(lambda p: nm(p).startswith('Transvalley, track'))
_low = lines(lambda p: nm(p).startswith(('APEx Norwood (Transcontinental)', 'Lower-level pair E')))
_lowU = unary_union([l.buffer(2.5, cap_style=2) for l in _low]).buffer(3.0).buffer(-3.0)
_part = []
for l in _tv:
    for x in np.arange(0.0, l.length, 2.0):
        q = l.interpolate(x)
        if _lowU.contains(q) and x > 260.0: _part.append(x)
    if _part:
        _part.sort(); _tvdeck = substring(l, _part[0], _part[-1]); _part = []
        OUT_TV = OUT_TV + [_tvdeck] if 'OUT_TV' in dir() else [_tvdeck]
emit(deck(OUT_TV), 'Transvalley over ORR and APEx (Norwood)', 'bridge', 'Transvalley at ground over ORR and APEx in the trench, between Reading Road and Section Avenue: 7.3 m or more rail to rail; a long skew span, so the deck runs some way along the tracks', tracks='Transvalley 2')
_fv = [LineString(r['c']) for r in C['rer_struct'] if r.get('note') == 'flyover']
_ftr = []
for t in C['tracks']:
    if t['sys'] != 'rer': continue
    l = LineString(t['c'])
    for v in _fv:
        pt_ = l.intersection(v.buffer(9.0))
        for q in getattr(pt_, 'geoms', [pt_]):
            if q.geom_type == 'LineString' and q.length > 20: _ftr.append(q)
if _ftr: emit(deck(_ftr), 'RER B over APEx Dayton (Paddock to Fairgrounds)', 'viaduct', 'RER B crosses over APEx, which takes the ORR alignment through Lockland while B keeps its own line; 7.3 m or more rail to rail', tracks='RER B 2')
out = dict(type='FeatureCollection', rule=dict(edge_m=EDGE, close_m=CLOSE, note='Footprints are drawing values: outer track centre + 4.2 m each side (overhead masts on the deck edge, walkway, parapet), gaps under 6 m between tracks decked over, platforms of stations on the structure added. Road bridges have no width set.'),
           features=OUT + LAB)
json.dump(out, open(S + 'deckpage/structures.json', 'w'))
for f in OUT: print(f['properties']['name'], f['properties']['kind'], f['properties']['area_m2'], f['properties'].get('length_m', ''))
print('labels', len(LAB), 'intercity open/up', [round(x) for x in ic], 'C&O open/up', [round(x) for x in co])
