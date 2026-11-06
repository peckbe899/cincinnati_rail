try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben (18 October, option A): Camp Washington west of the viaduct on a near-Manhattan grid, blocks longer W-E than N-S. N-S avenues: Ben's
# J1-J3 (100 m apart, 3.36 deg east of north) kept, then every 200 m west to Beekman; the 1922 Follett, Roll, Dawson and Borden lines
# carried south (slanting the other way) removed. E-W streets: the carried-west Camp Washington streets kept, new ones added (15.2 m)
# wherever the gap was over 115 m, so they run about 70-90 m apart, square to the avenues. Blocks between Hopple, Ralston, Beekman and the
# viaduct rebuilt from the street faces; each block divided into lots square to its long side (10 m frontage, two rows back to back when
# deeper than 55 m). Reads deckpage/deck.json, basin.json, plots.json, structures.json and the saved layout; writes them (pre copies
# fill/*_precampw.json). Marks deck.json 'campw18'.
import json, math, sys, shutil, numpy as np
from shapely.geometry import shape, mapping, LineString, Polygon, MultiPolygon, Point, box
from shapely.ops import unary_union, polygonize
from shapely.affinity import rotate
S = _ws.DATA
D = json.load(open(S + 'deckpage/deck.json')); B = json.load(open(S + 'deckpage/basin.json')); P = json.load(open(S + 'deckpage/plots.json'))
if D.get('campw18'): sys.exit('already done')
LAY = json.load(open(S + 'plots/live/deck/layout.json')); ED = LAY['streets']
FE = D['features'] + B['features']
SF = {f['properties']['id']: f for f in FE if f['properties'].get('layer') == 'street'}
SC = lambda i: [tuple(q) for q in (ED.get(i, {}).get('c') or SF[i]['geometry']['coordinates'])]
gone = {'S074', 'S075', 'S076', 'S077'}
assert not gone & set(ED), 'saved edits on a removed street'
# ---------------------------------------------------------------- frame
TH = math.radians(3.36)                                   # J bearing, east of north
NV = np.array([math.sin(TH), math.cos(TH)]); EV = np.array([NV[1], -NV[0]])     # along the avenues (north), across them (east)
J3 = np.array(SC('S058')); O = J3[0]
xu = lambda p: (np.array(p) - O) @ EV; yu = lambda p: (np.array(p) - O) @ NV
XY = lambda x, y: tuple(O + EV * x + NV * y)
beek = LineString(SC('SBW002')); hop = LineString(SC('S22014')); ral = LineString(SC('SB0905'))
via = [shape(f['geometry']) for f in json.load(open(S + 'deckpage/structures.json'))['features'] if f['properties'].get('name') == 'North arch viaduct'][0]
y_h = yu((711950, 4334915)); y_r = yu((711900, 4336478))
region = Polygon([XY(-600, y_h - 5), XY(400, y_h - 5), XY(400, y_r + 5), XY(-600, y_r + 5)])
west = Polygon(list(beek.coords) + [(711000, 4336552), (711000, 4334900)]).buffer(0)
trunk = via.intersection(Polygon([XY(150, y_h - 400), XY(900, y_h - 400), XY(900, y_r + 400), XY(150, y_r + 400)]))   # the trunk only (east of J2): the RER A Westwood viaduct crossing the lobe stands over the blocks
region = region.difference(west.buffer(9.2)).difference(trunk.buffer(1))
region = max(getattr(region, 'geoms', [region]), key=lambda g: g.area)
# ---------------------------------------------------------------- streets
new = []
def street(i, name, c, w, note):
    f = dict(type='Feature', properties=dict(layer='street', id=i, name=name, kind='WV', width_m=w, side='WV', zone='3', note=note, campw18=True), geometry=dict(type='LineString', coordinates=[[round(x, 2), round(y, 2)] for x, y in c]))
    new.append(f)
# avenues every 200 m west of J3, Hopple to Ralston, cut at Beekman
k = 0
for x in (-200.0, -400.0):
    l = LineString([XY(x, y_h - 20), XY(x, y_r + 20)]).intersection(region.buffer(8))
    if l.is_empty or l.length < 150: continue
    l = max(getattr(l, 'geoms', [l]), key=lambda g: g.length); k += 1
    street(f'S090{k}', f'New avenue J{3 + 2 * k}', list(l.coords), 18.3, 'Camp Washington grid (option A, 18 October): avenue 200 m west of the last, parallel to J1-J3')
# E-W streets: existing ones by their y on the frame, gaps over 115 m filled
EW = {}
for f in FE:
    p = f['properties']
    if p.get('layer') != 'street' or p['id'] in gone or ED.get(p['id'], {}).get('del'): continue
    l = LineString(SC(p['id'])); c = l.intersection(region)
    if c.is_empty or c.length < 120: continue
    a, b = np.array(l.coords[0]), np.array(l.coords[-1]); d = (b - a) / np.linalg.norm(b - a)
    if abs(d @ EV) > 0.97: EW[p['id']] = yu(c.centroid.coords[0])
ys = sorted([y_h] + list(EW.values()) + [y_r]); add_y = []
for a, b in zip(ys, ys[1:]):
    n = int(math.ceil((b - a) / 95.0)) - 1 if b - a > 115 else 0
    for j in range(1, n + 1): add_y.append(a + (b - a) * j / (n + 1))
for j, y in enumerate(add_y):
    l = LineString([XY(-700, y), XY(500, y)]).intersection(region.buffer(8))
    if l.is_empty: continue
    l = max(getattr(l, 'geoms', [l]), key=lambda g: g.length)
    street(f'S091{j:02d}', f'New street {chr(65 + j)} (Camp Washington)', list(l.coords), 15.2, 'Camp Washington grid (option A, 18 October): E-W street square to the avenues, filling a gap over 115 m')
# ---------------------------------------------------------------- blocks: faces of the street net inside the region
D['features'] = [f for f in D['features'] if f['properties'].get('id') not in gone] + new
FE = D['features'] + B['features']
streets = [f for f in FE if f['properties'].get('layer') == 'street' and not ED.get(f['properties']['id'], {}).get('del')]
def coords(f): return [tuple(q) for q in (ED.get(f['properties']['id'], {}).get('c') or f['geometry']['coordinates'])]
def wid(f): return ED.get(f['properties']['id'], {}).get('w') or f['properties'].get('width_m') or 10
def ext(c, d):
    def far(a, b): L = math.dist(a, b); return (b[0] + (b[0] - a[0]) / L * d, b[1] + (b[1] - a[1]) / L * d) if L > 0 else b
    return LineString([far(c[1], c[0])] + c[1:-1] + [far(c[-2], c[-1])])
near = [f for f in streets if LineString(coords(f)).intersects(region.buffer(60))]
corr = unary_union([LineString(coords(f)).buffer(wid(f) / 2, cap_style=2) for f in near])
faces = [g for g in polygonize(unary_union([ext(coords(f), wid(f) / 2 + 3) for f in near] + [region.boundary])) if g.representative_point().within(region)]
held = set(LAY.get('blocks', {}))
old_ids = [f['properties']['id'] for f in FE if f['properties'].get('layer') == 'block' and f.get('geometry') and shape(f['geometry']).representative_point().within(region)]
assert not set(old_ids) & held, 'held block in the region'
txt = json.dumps(LAY.get('plotOps', [])) + json.dumps(list(LAY.get('plots', {})))
assert not any('"' + b + '-' in txt for b in old_ids), 'saved lot edits in the region'
D['features'] = [f for f in D['features'] if f['properties'].get('id') not in old_ids]
B['features'] = [f for f in B['features'] if f['properties'].get('id') not in old_ids]
E0, N0 = P['o']
def enc(poly):
    c = list(poly.exterior.coords)[:-1]; q = [(round((x - E0) * 10), round((y - N0) * 10)) for x, y in c]; a = [q[0][0], q[0][1]]
    for i in range(1, len(q)): a += [q[i][0] - q[i - 1][0], q[i][1] - q[i - 1][1]]
    return a
plots = [p for p in P['plots'] if p[1] not in old_ids]
nb = 0; nl = 0
for fc in sorted(faces, key=lambda g: (-g.centroid.y, g.centroid.x)):
    g = fc.difference(corr).buffer(-0.3, join_style=2).buffer(0.3, join_style=2)
    g = max(getattr(g, 'geoms', [g]), key=lambda q: q.area) if not g.is_empty else g
    if g.is_empty or g.area < 400: continue
    nb += 1; bid = f'CW{nb:03d}'
    D['features'].append(dict(type='Feature', properties=dict(layer='block', id=bid, type='building', area_m2=round(g.area), side='WV', zone='3', name='', campw18=True), geometry=json.loads(json.dumps(mapping(g.simplify(0.05)), default=float))))
    # lots: strips square to the long side (along EV), 10 m frontage, two rows when deeper than 55 m
    gu = rotate(g, -math.degrees(math.atan2(EV[1], EV[0])), origin=(0, 0), use_radians=False); x0, y0, x1, y1 = gu.bounds
    rows = 2 if (y1 - y0) > 55 else 1; n = max(1, round((x1 - x0) / 10.0)); k = 0
    for r in range(rows):
        for i in range(n):
            cell = box(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * r / rows - (0.1 if r == 0 else 0), x0 + (x1 - x0) * (i + 1) / n, y0 + (y1 - y0) * (r + 1) / rows + (0.1 if r == rows - 1 else 0))
            q = gu.intersection(cell)
            for qq in getattr(q, 'geoms', [q]):
                if qq.geom_type != 'Polygon' or qq.area < 25: continue
                qq = rotate(qq, math.degrees(math.atan2(EV[1], EV[0])), origin=(0, 0), use_radians=False); k += 1
                plots.append([f'{bid}-{k:03d}', bid, 'l', None, None, [], [enc(qq.simplify(0.05))]]); nl += 1
P['plots'] = plots
D['campw18'] = dict(avenues_added=[f['properties']['name'] for f in new if 'avenue' in f['properties']['name']], ew_added=len(add_y), removed=sorted(gone), blocks_removed=len(old_ids), blocks=nb, lots=nl)
for n_ in ('deck', 'basin', 'plots'): shutil.copy(S + f'deckpage/{n_}.json', S + f'fill/{n_}_precampw.json')
json.dump(D, open(S + 'deckpage/deck.json', 'w')); json.dump(B, open(S + 'deckpage/basin.json', 'w')); json.dump(P, open(S + 'deckpage/plots.json', 'w'))
print(json.dumps(D['campw18']))
