"""Lower Price Hill's own 1904 grid for the basin layer (Ben, 2026-10-13, option C): State Avenue to Evans Street south of
W 8th, and the strip between State and Depot north of it, from the vol. 5 picks (sheets 460-467) placed by lph/tf_all.json
with the Lower Price Hill spline (lph/tps.pkl). North of W 8th east of Depot the block is razed for the deck and the
Exposition, and the deck layer carries the new grid there (deck/deck_gen.py), so only Depot, Dutton and South's west piece
are drawn here north of W 8th. Streets are straight runs through their crossings and bends, at the printed width.
Combined grid (Ben, 2026-10-13): Hatmaker, Staebler, Storrs, St. Michael, Price, Dutton and South are drawn straight on the
boulevard's square (best fit through their 1904 crossings), Burns' run from W 6th to Hatmaker and the whole of Depot
parallel to the boulevard, so their crossings are right angles; moves stay inside the 1904 fit's residuals. State Avenue,
Neave, German, Evans, West 6th and Burns' kink to W 8th keep their surveyed lines; their crossings move along them.
Blocks: the faces between these streets, the deck's W 8th, Gest and W 6th, outside the deck. Writes lph/lph_streets.json
(features tagged set = 'lph'); lph/add22.py --install appends them to the basin layer."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, numpy as np
from shapely.geometry import LineString, Polygon, Point, mapping, shape
from shapely.ops import unary_union, polygonize
SP = _ws.DATA
FT = 0.3048
# world centres of the 1904 crossings, bends and ends (vol. 5 picks through tf_all + spline; sheet in brackets)
S04 = [
    ('State Avenue', 60, [(711500, 4330924), (711502, 4330981), (711506, 4331000), (711524, 4331085), (711537, 4331145), (711550, 4331211),
                          (711559, 4331258), (711570, 4331314), (711586, 4331391), (711601, 4331466), (711632.5, 4331606)], '461, 462, 466'),
    ('Depot Street', 60, [(711689, 4331251), (711690, 4331305), (711699, 4331460), (711708, 4331601), (711719, 4331777)], '462, 466, 467, 495, 496'),
    ('Burns Street', 45, [(711762, 4331300), (711769, 4331262), (711786, 4331218), (711786, 4331200), (711782, 4331129), (711779, 4331067),
                          (711773, 4330983), (711769, 4330921)], '462, 463'),
    ('Hatmaker Street', 60, [(711550, 4331211), (711786, 4331200)], '461, 462, 463'),
    ('Staebler Street', 40, [(711537, 4331145), (711592, 4331142), (711782, 4331129)], '461, 462, 463'),
    ('Storrs Street', 50, [(711524, 4331085), (711587, 4331081), (711779, 4331067)], '461, 462, 463'),
    ('St. Michael Street', 50, [(711506, 4331000), (711582, 4330996), (711705, 4330988), (711773, 4330983)], '461, 462, 463'),
    ('Neave Street', 50, [(711592, 4331142), (711587, 4331081), (711582, 4330996), (711554, 4330924)], '461, 462'),
    ('German Street', 50, [(711500, 4330924), (711554, 4330924)], '461'),
    ('Price', 20, [(711559, 4331258), (711689, 4331251), (711757, 4331248)], '462'),
    ('Dutton', 50, [(711586, 4331391), (711695, 4331382)], '466, 467'),
    ('South', 50, [(711601, 4331466), (711699, 4331460)], '466, 467'),
    ('Evans Street', 60, [(711988, 4331282), (711981, 4331175), (712024, 4331052), (712029, 4331038), (712024, 4330965), (712021, 4330923)], '463, 464, 460'),
    ('West 6th Street', 55, [(711769, 4330921), (712024, 4330965)], '460, 463'),
]
DK = json.load(open(SP + 'deckpage/deck.json'))['features']
deck = [shape(f['geometry']) for f in DK if f['properties']['layer'] == 'deck'][0]
dst = {f['properties']['name']: f for f in DK if f['properties']['layer'] == 'street'}

# ---------------------------------------------------------------- squaring (the combined grid)
bl = [f for f in DK if f['properties']['layer'] == 'boulevard'][0]['geometry']['coordinates'][0]
U = np.array(bl[3]) - np.array(bl[0]); U = U / np.linalg.norm(U)        # north along the boulevard
W = np.array([U[1], -U[0]])                                             # east on its square
P04 = {nm: pts for nm, ft, pts, sh in S04}
def fitl(pts, d): return (np.array(pts, float).mean(0), d)               # best fit at a fixed bearing: through the centroid
def big(L): c, d = L; return LineString([tuple(c - d * 3000), tuple(c + d * 3000)])
def xx(L1, L2):
    (c1, d1), (c2, d2) = L1, L2; t = np.linalg.solve(np.array([d1, -d2]).T, c2 - c1); return tuple(c1 + d1 * t[0])
def xp(L, line, near):
    g = big(L).intersection(line); g = min(getattr(g, 'geoms', [g]), key=lambda q: q.distance(Point(near))); return (g.x, g.y)
def pj(L, p): c, d = L; return tuple(c + d * float((np.array(p) - c) @ d))
SQ = ['Hatmaker Street', 'Staebler Street', 'Storrs Street', 'St. Michael Street', 'Price', 'Dutton', 'South']
LN = {nm: fitl(P04[nm], W) for nm in SQ}
BURNS = fitl(P04['Burns Street'][2:], U)                                 # W 6th to Hatmaker; the kink to W 8th stays
DEPOT = fitl(P04['Depot Street'], U)                                     # the same line as deck/deck_gen.py
STATE, NEAVE = LineString(P04['State Avenue']), LineString(P04['Neave Street'])
W8, GEST = (LineString(dst[n]['geometry']['coordinates']) for n in ('W 8th (viaduct line)', 'Gest'))
NEW = {}
for nm in SQ:
    p = P04[nm]; NEW[p[0]] = xp(LN[nm], STATE, p[0])                      # west ends on State
for nm in ('Staebler Street', 'Storrs Street', 'St. Michael Street'):
    NEW[P04[nm][1]] = xp(LN[nm], NEAVE, P04[nm][1])                      # Neave crossings
for nm in ('Hatmaker Street', 'Staebler Street', 'Storrs Street', 'St. Michael Street'):
    NEW[P04[nm][-1]] = xx(LN[nm], BURNS)                                 # Burns crossings
for p in (P04['Burns Street'][2], P04['Burns Street'][-1]): NEW[p] = pj(BURNS, p)
NEW[P04['Price'][1]] = xx(LN['Price'], DEPOT); NEW[P04['Price'][-1]] = pj(LN['Price'], P04['Price'][-1])
NEW[P04['Dutton'][-1]] = xx(LN['Dutton'], DEPOT); NEW[P04['South'][-1]] = xx(LN['South'], DEPOT)
dp = P04['Depot Street']
NEW[dp[1]] = xp(DEPOT, W8, dp[1]); NEW[dp[3]] = xp(DEPOT, GEST, dp[3]); NEW[dp[4]] = pj(DEPOT, dp[4])
NEW[P04['Evans Street'][0]] = tuple(np.array(dst['Evans']['geometry']['coordinates'][0]) + U * 0.3)   # the deck's straight Evans at W 8th (0.3 m past so it nodes)
# W 8th and Gest meet State where the deck layer has them (Gest on the grid, W 8th straightened; Ben, 2026-10-13)
NEW[(711570, 4331314)] = tuple(dst['W 8th (viaduct line)']['geometry']['coordinates'][0])
NEW[(711632.5, 4331606)] = tuple(dst['Gest']['geometry']['coordinates'][0])
DROP = {(711705, 4330988)}                                               # St. Michael: a bend, not a crossing
M = lambda p: NEW.get(tuple(p), tuple(p))
S = [(nm, ft, [M(p) for p in pts if tuple(p) not in DROP], sh) for nm, ft, pts, sh in S04]
MOVE = {nm: round(max(Point(p).distance(Point(M(p))) for p in pts if tuple(p) not in DROP), 1) for nm, ft, pts, sh in S04}
ctx = [LineString(dst[n]['geometry']['coordinates']) for n in ('W 8th (viaduct line)', 'Gest', 'W 6th')]
ctxw = {'W 8th (viaduct line)': 110, 'Gest': 60, 'W 6th': 60}
F = []
for i, (nm, ft, pts, sh) in enumerate(S):
    F.append(dict(type='Feature', properties=dict(layer='street', id=f'LPH{i:03d}', name=nm, kind='we_street', width_m=round(ft * FT, 2), width_ft=float(ft),
                  width_src='printed', side='', src='Sanborn 1904', sheets=sh, geom_src='Sanborn intersections (vol. 5, Lower Price Hill spline)' + (f'; straight on the boulevard grid (moved up to {MOVE[nm]} m)' if nm in SQ + ['Burns Street', 'Depot Street'] else (f'; crossings moved along it (up to {MOVE[nm]} m)' if MOVE[nm] > 0 else '')), set='lph'),
                  geometry=dict(type='LineString', coordinates=[[float(x), float(y)] for x, y in pts])))
lines = [LineString(p) for _, _, p, _ in S] + ctx
region = Polygon([M(p) for p in [(711500, 4330924), (711502, 4330981), (711506, 4331000), (711524, 4331085), (711537, 4331145), (711550, 4331211),
                  (711559, 4331258), (711570, 4331314), (711586, 4331391), (711601, 4331466), (711632.5, 4331606), (711708, 4331601),
                  (711699, 4331460), (711690, 4331305), (711988, 4331282), (711981, 4331175), (712024, 4331052), (712024, 4330965),
                  (711769, 4330921), (711554, 4330924)]]).buffer(2)
bands = unary_union([LineString(p).buffer(ft * FT / 2, cap_style=2, join_style=2, mitre_limit=3) for _, ft, p, _ in S] +
                    [g.buffer(ctxw[n] * FT / 2, cap_style=2) for g, n in zip(ctx, ctxw)])
nb = 0
for p in polygonize(unary_union(lines)):
    if p.area < 200 or not region.contains(p.representative_point()): continue
    b = p.difference(deck).difference(bands)
    for q in getattr(b, 'geoms', [b]):
        if q.geom_type != 'Polygon' or q.area < 300: continue
        nb += 1
        F.append(dict(type='Feature', properties=dict(layer='block', id=f'LPHB{nb:02d}', type='building', area_m2=int(q.area), name='', src='Sanborn 1904', set='lph'),
                      geometry=mapping(q.simplify(0.3))))
json.dump(dict(type='FeatureCollection', features=F), open(SP + 'lph/lph_streets.json', 'w'), separators=(',', ':'))
print('streets', len(S), 'blocks', nb, 'length', round(sum(LineString(p).length for _, _, p, _ in S)))
print('largest move per street (m):', MOVE)
