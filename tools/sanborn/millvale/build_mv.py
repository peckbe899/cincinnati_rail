try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben 2026-10-20: Millvale grid (option 1, Manhattan as built) between Dreman, Geringer, the rail trunk, Hopple and Beekman, with the
# Broadway-style boulevard over the culverted Mill Creek (Ben's straightened KML, 150 ft like Central Parkway in the basin): through traffic
# leaves at the split for the English Woods tunnel portal at Beekman (Richardson Ave analog), the straight piece runs on to Hopple (Lombard to
# Lyon). Avenues on the Borden and Follett lines at 3 deg (100 ft), cross streets at 93 deg (60 ft): Dreman-Ralston 2 blocks, Ralston-Hopple
# 20 blocks of about 78.8 m; trunk frontage 60 ft. Blocks are the faces left after the street bands and the viaduct footprints (the West Fork
# culvert lies under the APEx Indianapolis + RER D deck, so nothing is built there). Set 'mv', ids SMV####.
#   python3 millvale/build_mv.py [--install]      (reinstall replaces the set)
import json, sys, numpy as np
from shapely.geometry import shape, Polygon, LineString, Point, MultiLineString, mapping
from shapely.ops import unary_union, polygonize, linemerge, substring, nearest_points
SP = _ws.DATA
FT = 0.3048; SET = 'mv'
BJ = json.load(open(SP + 'deckpage/basin.json'))
BJ['features'] = [f for f in BJ['features'] if f['properties'].get('set') != SET]
ST = {f['properties']['id']: shape(f['geometry']) for f in BJ['features'] if f['properties']['layer'] == 'street'}
P = Polygon(json.load(open(SP + 'millvale/grid_area.json')))
TR = json.load(open(SP + 'deckpage/tracks.json')); CX = json.load(open(SP + 'deckpage/context.json'))
trk = lambda nm: [shape(f['geometry']) for f in TR['features'] if f['properties'].get('name') == nm][0]
K = json.load(open(SP + 'millvale/blvd2.json'))
blvd = LineString(K['blvd']); lomb = LineString(K['old'])
s_split = blvd.project(Point(K['old'][0]))
hop = linemerge([ST['S22014'], ST['SB0779']]) if linemerge([ST['S22014'], ST['SB0779']]).geom_type == 'LineString' else ST['S22014']
beek = linemerge([ST['SBW002'], ST['SBW001']])
th = np.radians(3.0); U_ = np.array([np.sin(th), np.cos(th)]); V_ = np.array([np.cos(th), -np.sin(th)])
def ray(p, d, a=-2500, b=2500): p = np.asarray(p, float); return LineString([p + d * a, p + d * b])
def cut_between(line, a, b):
    """piece of line between its crossings with a and b (or the nearest approach)"""
    pa = line.intersection(a); pb = line.intersection(b)
    pa = pa if not pa.is_empty else nearest_points(line, a)[0]; pb = pb if not pb.is_empty else nearest_points(line, b)[0]
    sa, sb = line.project(pa if pa.geom_type == 'Point' else pa.centroid), line.project(pb if pb.geom_type == 'Point' else pb.centroid)
    return substring(line, min(sa, sb), max(sa, sb))
# ---- trunk frontage: 18 m west of the westmost trunk track, from Geringer to Hopple
w1 = trk('Lower-level pair W, track 1, on the viaduct')
fr = w1.parallel_offset(18, 'left') if w1.coords[0][1] < w1.coords[-1][1] else w1.parallel_offset(18, 'right')
if fr.distance(Point(712200, 4335600)) > w1.distance(Point(712200, 4335600)): fr = w1.parallel_offset(18, 'right' if fr == w1.parallel_offset(18, 'left') else 'left')
fr = linemerge(fr) if fr.geom_type == 'MultiLineString' else fr
frontage = cut_between(fr, ST['SB0736'], hop)
# ---- avenues
bor0 = np.array(ST['SB0571'].coords[0]); fol0 = np.array(ST['SB0721'].coords[-1])          # existing south ends (Borden 4,336,370; Follett at Ralston)
borden = LineString([bor0, bor0 - U_ * 2500]); borden = substring(borden, 0, borden.project(borden.intersection(beek)))
follett = LineString([fol0, fol0 - U_ * 2500]); xh = follett.intersection(hop); follett = substring(follett, 0, follett.project(xh))
# ---- cross streets: points on the Follett line
fol_full = LineString([fol0 + U_ * 400, fol0 - U_ * 2500])
s_dre = fol_full.project(fol_full.intersection(ST['SB0650'])); s_ral = fol_full.project(Point(fol0)); s_hop = fol_full.project(xh)
pos = [(s_dre + s_ral) / 2] + [s_ral + (s_hop - s_ral) * k / 20 for k in range(1, 20)]
print('block spacing Dreman-Ralston %.1f m, Ralston-Hopple %.1f m' % ((s_ral - s_dre) / 2, (s_hop - s_ral) / 20))
west_edge = beek; east_edge = unary_union([frontage, ST['SB0736']])
pieces = []
def add(g, name, ft, note=''):
    for q in getattr(g, 'geoms', [g]):
        if q.geom_type == 'LineString' and q.length > 5: pieces.append(dict(g=q, name=name, ft=ft, note=note))
for k, s in enumerate(pos):
    p = np.array(fol_full.interpolate(s).coords[0]); L = ray(p, V_, -1500, 1500)
    seg = L.intersection(P.buffer(0.5))
    seg = max(getattr(seg, 'geoms', [seg]), key=lambda g: g.length)
    # east end at the frontage (or Geringer), west end on Beekman
    xe = seg.intersection(east_edge); xw = seg.intersection(west_edge)
    a = seg.project(xw if not xw.is_empty and xw.geom_type == 'Point' else Point(seg.coords[0])) if not xw.is_empty else 0
    b = seg.project(xe if xe.geom_type == 'Point' else (xe.geoms[0] if not xe.is_empty else Point(seg.coords[-1]))) if not xe.is_empty else seg.length
    add(substring(seg, min(a, b), max(a, b)), f'New street M{k + 1}', 60)
# Ralston carried west to Beekman and east to the frontage
ral = ST['SB0905']; rp = np.array(ral.coords[0]); rq = np.array(ral.coords[-1])        # (east end, west end)
Lw = LineString([rq, rq - V_ * 600]); add(substring(Lw, 0, Lw.project(Lw.intersection(beek))), 'Ralston Avenue (carried west)', 60)
Le = LineString([rp, rp + V_ * 600]); xe_ = Le.intersection(east_edge); add(substring(Le, 0, Le.project(xe_ if xe_.geom_type == 'Point' else xe_.geoms[0])), 'Ralston Avenue (carried east)', 60)
add(borden, 'Borden Street (carried south)', 100); add(follett, 'Follett Avenue (carried south)', 100)
add(frontage, 'New street MT (trunk frontage)', 60)
# boulevard: whole KML, split into the run to the split, the tunnel branch, and the Lombard piece to Hopple (ends snapped onto Hopple / Follett)
add(substring(blvd, 0, s_split), 'Millvale Boulevard', 150, 'Broadway-style boulevard over the culverted Mill Creek (Ben 2026-10-20); one-way arms around the diamond park between M3 and M6')
add(substring(blvd, s_split, blvd.length), 'Millvale Boulevard (to the English Woods tunnel)', 150, 'through route to the tunnel portal at Beekman (Richardson Ave analog)')
lc = list(lomb.coords); lc[0] = blvd.interpolate(s_split).coords[0]; lc[-1] = xh.coords[0]
add(LineString(lc), 'Millvale Boulevard (to Hopple)', 150, 'the street carries on over the culvert to Hopple (Lombard St to Lyon analog); meets Follett Avenue at Hopple')
# ---- Follett crossing (Ben, 20 October): the boulevard forks round a diamond park from between M2 and M3 to between M6 and M7, each
# one-way arm half the boulevard (75 ft); M3 to M6 end at the arms; Follett meets them at the M3 (west) and M6 (east) corners, one way
# toward the boulevard and 60 ft on its last block (drivers leaving the boulevard for Follett use M2 or M7); the 150 ft band stays park or road.
def piece(name): return next(p for p in pieces if p['name'] == name)
Bp = piece('Millvale Boulevard'); B_ = Bp['g']; HALF = 150 * FT / 2; CW = HALF
S_F, S_R = 1150.0, 1510.0
Fp = piece('Follett Avenue (carried south)'); M = {k: piece(f'New street M{k}')['g'] for k in (2, 3, 6, 7)}
pF3, pF6 = Fp['g'].intersection(M[3]), Fp['g'].intersection(M[6])
def frame(s):
    a = np.array(B_.interpolate(s).coords[0]); b = np.array(B_.interpolate(s + 1).coords[0]); t = (b - a) / np.linalg.norm(b - a); return a, np.array([-t[1], t[0]])
def arm(sign, knots):
    ss = np.linspace(S_F, S_R, 300); ks, ko = zip(*knots); off = np.interp(ss, ks, ko)
    off = np.convolve(np.r_[[off[0]] * 6, off, [off[-1]] * 6], np.ones(13) / 13, 'valid')
    return LineString([frame(s_)[0] + sign * frame(s_)[1] * o for s_, o in zip(ss, off)])
D0 = HALF - CW / 2
west = arm(-1, [(S_F, D0), (B_.project(pF3), pF3.distance(B_.interpolate(B_.project(pF3)))), (S_R, D0)])
east = arm(+1, [(S_F, D0), (B_.project(pF6), pF6.distance(B_.interpolate(B_.project(pF6)))), (S_R, D0)])
west = LineString([c if Point(c).distance(pF3) > 6 else pF3.coords[0] for c in west.coords]); east = LineString([c if Point(c).distance(pF6) > 6 else pF6.coords[0] for c in east.coords])
face = Polygon(list(west.coords) + list(east.coords)[::-1]).buffer(0)
new = []
for p in pieces:
    g = p['g']
    if p is Bp:
        new += [dict(p, g=substring(g, 0, S_F + 25)), dict(p, g=substring(g, S_R - 25, g.length))]; continue      # overlaps the arms' first 25 m: no notch at the fork
    if p['name'] in ('Follett Avenue (carried south)', 'New street M3', 'New street M4', 'New street M5', 'New street M6'):
        g = g.difference(face)
        parts = [q for q in getattr(g, 'geoms', [g]) if q.geom_type == 'LineString' and q.length > 3]
        if p is Fp:
            for q in parts:
                end = M[2] if q.distance(pF3) < 1 else M[7]; x = q.intersection(end); sx = q.project(x if x.geom_type == 'Point' else x.centroid)
                a, b = substring(q, 0, sx), substring(q, sx, q.length)
                near, far = (a, b) if a.distance(pF3 if end is M[2] else pF6) < b.distance(pF3 if end is M[2] else pF6) else (b, a)
                new.append(dict(p, g=far))
                new.append(dict(p, g=near, ft=60, note='one way toward the boulevard (Ben, 20 October): ' + ('southbound, joins the south-west-bound arm at M3' if end is M[2] else 'northbound, joins the north-east-bound arm at M6')))
            continue
        for q in parts: new.append(dict(p, g=q))
        continue
    new.append(p)
new += [dict(g=west, name='Millvale Boulevard (south-west-bound)', ft=75, note='one-way arm round the confluence park (Fell and Oak along the Panhandle)'),
        dict(g=east, name='Millvale Boulevard (north-east-bound)', ft=75, note='one-way arm round the confluence park (Fell and Oak along the Panhandle)')]
pieces = new
PARK_FACE = face
print('street pieces', len(pieces), 'km', round(sum(p['g'].length for p in pieces) / 1000, 2))
# ---- blocks
OLD = [(g, f) for f in BJ['features'] if f['properties']['layer'] == 'street' for g in [shape(f['geometry'])] if g.intersects(P.buffer(60))]
net = unary_union([p['g'] for p in pieces] + [g for g, f in OLD] + [P.exterior])
bands = unary_union([p['g'].buffer(p['ft'] * FT / 2, cap_style=2, join_style=2) for p in pieces] +
                    [g.buffer((f['properties'].get('width_m') or 12) / 2, cap_style=2, join_style=2) for g, f in OLD])
via = [trk(f'APEx north approach {i} of 6') for i in (5, 6)] + [LineString(f['c']) for f in CX['tracks'] if f.get('sys') == 'rer' and f.get('line') == 'D']
viaR5 = [trk('R5 to the Cumminsville Spur (west track)'), trk('R5 to the Cumminsville Spur (east track)')]
viaA = [LineString(f['c']) for f in CX['tracks'] if f.get('sys') == 'rer' and f.get('line') == 'A']
keepout = unary_union([g.buffer(4.2) for g in via + viaR5 + viaA] + [w1.buffer(14)]).buffer(3).buffer(-3)      # 2026-10-22: the structure footprint (outer track + 4.2 m, gaps under 6 m decked over, cut/structures.py rule), not 6 m and 20 m
blocks = []; parks = []
arm_bands = unary_union([p['g'].buffer(p['ft'] * FT / 2, cap_style=2) for p in pieces if 'bound)' in p['name']])
for q in polygonize(net):
    if not P.contains(q.representative_point()): continue
    r = q.intersection(P).difference(bands).difference(keepout).difference(PARK_FACE)
    for part in getattr(r, 'geoms', [r]):
        if part.geom_type == 'Polygon' and part.area > 300 and not part.buffer(-6).is_empty: blocks.append(part.buffer(-1.0, join_style=2).buffer(1.0, join_style=2).simplify(0.25, preserve_topology=True))
small = [b for b in blocks if b.area < 1500 and b.distance(arm_bands) < 1]                 # the wedges the arms leave go to the park
blocks = [b for b in blocks if b not in small]
def clean(g):                                                                            # no slivers at the tips
    g = g.buffer(-2.0, join_style=2).buffer(2.0, join_style=2)
    return [q for q in getattr(g, 'geoms', [g]) if q.geom_type == 'Polygon' and q.area > 150]
parks = clean(PARK_FACE.difference(bands)) + [q for b in small for q in clean(b)]
print('blocks', len(blocks), 'ha', round(sum(b.area for b in blocks) / 1e4, 1), 'park ha', round(sum(g.area for g in parks) / 1e4, 2))
r1 = lambda c: [round(c[0], 1), round(c[1], 1)]
out = []
for i, p in enumerate(pieces):
    out.append(dict(type='Feature', properties=dict(layer='street', id=f'SMV{i + 1:04d}', name=p['name'], kind='we_street', width_m=round(p['ft'] * FT, 2), width_ft=p['ft'],
                    width_src='Ben 2026-10-20' , side='', src='Millvale grid (Ben 2026-10-20)', note=p['note'], set=SET), geometry=dict(type='LineString', coordinates=[r1(c) for c in p['g'].coords])))
for i, b in enumerate(blocks):
    out.append(dict(type='Feature', properties=dict(layer='block', id=f'SMVB{i + 1:04d}', type='building', area_m2=int(round(b.area)), name='', src='Millvale grid (Ben 2026-10-20)', set=SET),
                    geometry=dict(type='Polygon', coordinates=[[r1(c) for c in b.exterior.coords]] + [[r1(c) for c in h.coords] for h in b.interiors])))
for i, g in enumerate(parks):
    for pg in getattr(g, 'geoms', [g]):
        if pg.geom_type != 'Polygon' or pg.area < 50: continue
        out.append(dict(type='Feature', properties=dict(layer='block', id=f'SMVP{i + 1:03d}', type='park', area_m2=int(round(pg.area)), name='Confluence park (working name)' if i == 0 else '',
                        src='Millvale grid (Ben 2026-10-20)', set=SET), geometry=dict(type='Polygon', coordinates=[[r1(c) for c in pg.exterior.coords]] + [[r1(c) for c in h.coords] for h in pg.interiors])))
json.dump(dict(type='FeatureCollection', features=out), open(SP + 'millvale/ext_mv.json', 'w'))
if '--install' in sys.argv:
    BJ['features'] += out; json.dump(BJ, open(SP + 'deckpage/basin.json', 'w'), separators=(',', ':')); print('installed')
