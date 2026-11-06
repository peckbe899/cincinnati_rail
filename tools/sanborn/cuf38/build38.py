try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben 2026-10-20: the streets of 1922 plate 38 (Clifton: Ludlow, Clifton Avenue, Jefferson, Vine, Dixmyth to Woolper) on the map, built
# from the crossings read on Ben's scan and placed with our fit (cuf38/fit38.py, 4 m leave-one-out), as plate 35's were (cuf/build22.py).
# Area: the plate's footprint (3 m in), east of West McMicken Avenue (Ben's line, kept), less plate 35's area (Dixmyth is plate 35's).
# Earlier streets and blocks inside are taken out (Ben's edited ones kept), those crossing the edge are cut there.
#   python3 cuf38/build38.py [--install]       (a reinstall first puts back what the last install took out)
import json, sys, os, collections, numpy as np
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'cuf'); sys.path.insert(0, _ws.CODE + 'sbg'); sys.path.insert(0, _ws.CODE + 'cuf38')
import fwd38lib
def W38(x, y): return fwd38lib.world(float(x), float(y))
import common as C
from names import key2
from shapely.geometry import LineString, Point, Polygon, MultiPolygon, shape, mapping, box
from shapely.ops import unary_union, polygonize, nearest_points, linemerge
from scipy.sparse.csgraph import minimum_spanning_tree, shortest_path
import rasterio, rasterio.features
INSTALL = '--install' in sys.argv; SET = 'c38'; PREFIX = 'SK'; FT = 0.3048
BJ = json.load(open(SP + 'deckpage/basin.json'))
REM = SP + 'cuf38/c38_removed.json'
if os.path.exists(REM):          # put back what the last install took out or clipped
    R0 = json.load(open(REM)); ids = {f['properties']['id'] for f in R0['features']}
    BJ['features'] = [f for f in BJ['features'] if f['properties'].get('set') != SET and f['properties'].get('id') not in ids] + R0['features']
ED = json.load(open(SP + 'dbread/deck/layout.json'))['streets']
EDITED = {k for k, v in ED.items() if 'c' in v or v.get('del')}
def geom_of(f): return LineString(ED[f['properties']['id']]['c']) if f['properties'].get('id') in ED and 'c' in ED[f['properties']['id']] else shape(f['geometry'])
# ---------------------------------------------------------------- area
from PIL import Image; Image.MAX_IMAGE_PIXELS = None
al = np.load(SP + 'cuf38/png_alpha_s4.npy')[::2, ::2]                     # png alpha every 8 px
polys = [shape(g) for g, v in rasterio.features.shapes((al > 0).astype(np.uint8), mask=al > 0) if v == 1]
fp = max(polys, key=lambda p: p.area)
fp = Polygon(fwd38lib.world_many([(x * 8, y * 8) for x, y in fp.exterior.coords])).buffer(0).buffer(-3)
ST = [f for f in BJ['features'] if f['properties']['layer'] == 'street']
def named(nm, ids=None): return [geom_of(f) for f in ST if f['properties'].get('name') == nm and (ids is None or f['properties']['id'] in ids)]
mcm = unary_union(named('West McMicken Avenue', {'SB1012', 'S22000'})); mcm = linemerge(mcm) if mcm.geom_type == 'MultiLineString' else mcm
mcm = max(getattr(mcm, 'geoms', [mcm]), key=lambda g: g.length)
c = list(mcm.coords); c = sorted(c, key=lambda q: -q[1])
east_of_mcm = Polygon([(c[0][0], 4338000)] + c + [(c[-1][0], 4333000), (717000, 4333000), (717000, 4338000)]).buffer(0)
A22 = shape(json.load(open(SP + 'cuf/area_c22.json'))).buffer(3)
AREA = fp.intersection(east_of_mcm).difference(A22)
AREA = max(getattr(AREA, 'geoms', [AREA]), key=lambda p: p.area)
print('area', round(AREA.area / 1e4, 1), 'ha')
# ---------------------------------------------------------------- picks
P, O = [], []
import glob
for fn_ in sorted(glob.glob(SP + 'sbg/picks22/s22-38_*.json')):
    d = json.load(open(fn_))
    P += d.get('intersections', []); O += [dict(o, typ=t) for t in ('bends', 'ends') for o in d.get(t, [])]
    for w in d.get('widths', []): O.append(dict(w, typ='width'))
nodes = []
for p in P:
    ka, kb = key2(p['a']), key2(p['b'])
    if not ka or not kb or ka == kb: continue
    k = tuple(sorted((ka, kb)))
    q = next((n for n in nodes if n['pair'] == k and np.hypot(n['x'] - p['x'], n['y'] - p['y']) < 60), None)
    if q: q['xs'].append(p['x']); q['ys'].append(p['y']); q['x'] = float(np.mean(q['xs'])); q['y'] = float(np.mean(q['ys']))
    else: nodes.append(dict(pair=k, names={ka: p['a'], kb: p['b']}, x=p['x'], y=p['y'], xs=[p['x']], ys=[p['y']]))
V = collections.defaultdict(list); NAME = {}
for n in nodes:
    E, N = W38(n['x'], n['y'])
    for k in n['pair']: V[k].append((float(E), float(N))); NAME.setdefault(k, n['names'][k])
for o in O:
    if o['typ'] == 'width': continue
    k = key2(o.get('street') or '')
    if not k: continue
    E, N = W38(o['x'], o['y']); V[k].append((float(E), float(N))); NAME.setdefault(k, o['street'])
WID = {}
for o in O:
    if o['typ'] == 'width' and key2(o['street']): WID[key2(o['street'])] = o['ft']
KEEP_EXISTING = {key2(n) for n in ('West McMicken Avenue', 'Dixmyth Avenue')}
def order(pts):
    pts = np.array(pts); n = len(pts)
    if n < 2: return []
    D = np.hypot(*(pts[:, None, :] - pts[None, :, :]).transpose(2, 0, 1)); T = minimum_spanning_tree(D).toarray(); T = T + T.T; T[T > 450] = 0
    dist, pred = shortest_path(T, directed=False, return_predecessors=True); dd = np.where(np.isinf(dist), -1, dist)
    a, b = np.unravel_index(np.argmax(dd), dd.shape); path = [b]
    while path[-1] != a and pred[a, path[-1]] >= 0: path.append(pred[a, path[-1]])
    line = LineString(pts[path[::-1]]) if len(path) > 1 else None
    if line is None: return []
    rest = [i for i in range(n) if i not in path]
    cs = np.array(line.coords); L = line.length
    def tpos(i):                       # position along the path, extended past both ends (points beyond a >450 m gap)
        t = line.project(Point(pts[i]))
        if t <= 1e-6:
            d = cs[1] - cs[0]; return float(np.dot(pts[i] - cs[0], d / np.linalg.norm(d)))
        if t >= L - 1e-6:
            d = cs[-1] - cs[-2]; return L + float(np.dot(pts[i] - cs[-1], d / np.linalg.norm(d)))
        return t
    allp = sorted(path + rest, key=tpos)
    out = [tuple(pts[allp[0]])]
    for i in allp[1:]:
        if np.hypot(*(pts[i] - np.array(out[-1]))) > 2.0: out.append(tuple(pts[i]))
    return out
def heads_to(inner, q, t):            # the gap q->t continues the street's own direction (within 45 degrees)
    a = np.array(q.coords[0]) - np.array(inner.coords[0]); b = np.array(t.coords[0]) - np.array(q.coords[0])
    return float(np.dot(a, b)) > np.cos(np.radians(45)) * np.linalg.norm(a) * np.linalg.norm(b)
pieces = []
OLDKEEP = collections.defaultdict(list)
for f in BJ['features']:
    if f['properties']['layer'] == 'street' and key2(f['properties'].get('name') or '') in KEEP_EXISTING: OLDKEEP[key2(f['properties']['name'])].append(geom_of(f))
for k in (key2('Woodside Place'), key2('Woodside Place (south of University)')): OLDKEEP[k] += OLDKEEP[key2('Hopson Street')]   # the plate's Woodside Place is the kept Hopson
def clusters(pts, gap=450.0):        # same name, separate streets (plate 38 has two Terrace Avenues): points more than 450 m from the rest form their own street
    pts = [tuple(p) for p in pts]; left = set(range(len(pts))); out = []
    while left:
        stack = [left.pop()]; grp = []
        while stack:
            i = stack.pop(); grp.append(i)
            near = [j for j in left if np.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1]) < gap]
            for j in near: left.discard(j); stack.append(j)
        out.append([pts[i] for i in grp])
    return out
def axis(grp):
    a = np.array(grp)
    if len(a) < 2 or np.ptp(a, 0).max() < 60: return None
    u, sv, vt = np.linalg.svd(a - a.mean(0)); return vt[0]
def merge_clusters(cl):          # rejoin pieces of one street a long block apart (McAlpin, Woolper): the gap must run along the street
    changed = True
    while changed and len(cl) > 1:
        changed = False
        for i in range(len(cl)):
            for j in range(i + 1, len(cl)):
                A, B = np.array(cl[i]), np.array(cl[j]); d = np.hypot(*(A[:, None, :] - B[None, :, :]).transpose(2, 0, 1))
                ia, ib = np.unravel_index(np.argmin(d), d.shape); br = B[ib] - A[ia]
                if np.linalg.norm(br) > 1200: continue
                br = br / np.linalg.norm(br); ok = True
                for g in (cl[i], cl[j]):
                    ax = axis(g)
                    if ax is not None and abs(float(np.dot(ax, br))) < np.cos(np.radians(25)): ok = False
                if ok: cl[i] = cl[i] + cl[j]; cl.pop(j); changed = True; break
            if changed: break
    return cl
VV = []
for k, pts in V.items():
    for grp in merge_clusters(clusters(pts)): VV.append((k, grp))
for k, pts in VV:
    o = order(pts)
    if len(o) < 2: continue
    if k in KEEP_EXISTING:            # an edge street stays as it is; only a stretch the kept streets lack is added (Straight from Fairview to Clifton)
        g = LineString(o).intersection(AREA.buffer(30))
        if OLDKEEP[k]: g = g.difference(unary_union(OLDKEEP[k]).buffer(25))
        g = [q for q in getattr(g, 'geoms', [g]) if q.geom_type == 'LineString' and q.length > 40]
        if not g: continue
        g = linemerge(g) if len(g) > 1 else g[0]
    else: g = LineString(o).intersection(AREA.buffer(3))
    for part in getattr(g, 'geoms', [g]):
        if part.geom_type == 'LineString' and part.length > 8:
            ft = WID.get(k, 15 if ('alley' in k or k.endswith(' al')) else 50)
            pieces.append(dict(name=NAME[k], k=k, geom=part, ft=ft, kind='we_alley' if ft < 20 else 'we_street'))
print('new street pieces', len(pieces))
# ---------------------------------------------------------------- earlier streets and blocks in the area
removed, kept_edited, clipped, dup_dropped = [], [], [], []
newf = []
for f in BJ['features']:
    p = f['properties']; lay = p['layer']
    if lay == 'street':
        g = geom_of(f); kk = key2(p.get('name') or '')
        if kk in KEEP_EXISTING and not (p.get('set') == 'v3' and kk == key2('West McMicken Avenue') and g.distance(mcm) < 25 and p['id'] not in ('SB1012', 'S22000')):
            newf.append(f); continue
        inside = g.intersection(AREA).length / max(g.length, 1e-6)
        if inside < 0.02: newf.append(f); continue
        if p['id'] in EDITED: kept_edited.append(p['id']); newf.append(f); continue
        removed.append(json.loads(json.dumps(f)))
        rest = g.difference(AREA)
        parts = [q for q in getattr(rest, 'geoms', [rest]) if q.geom_type == 'LineString' and q.length > 10]
        if parts and inside < 0.98:      # crossing the edge: the part outside stays (one piece; the longest if it splits)
            q = max(parts, key=lambda q: q.length)
            twin = [pc['geom'] for pc in pieces if pc['k'] == kk]
            if twin and q.intersection(unary_union(twin).buffer(45)).length > 0.8 * q.length:
                dup_dropped.append(p['id']); continue          # the outside part only doubles the plate's own line for the same street
            f2 = json.loads(json.dumps(f)); f2['geometry'] = mapping(q); f2['properties']['clip_by'] = SET; newf.append(f2); clipped.append(p['id'])
    elif lay == 'block':
        g = shape(f['geometry'])
        if AREA.contains(g.representative_point()): removed.append(json.loads(json.dumps(f))); continue
        newf.append(f)
    else: newf.append(f)
print('earlier streets removed', sum(1 for f in removed if f['properties']['layer'] == 'street') - len(clipped), 'clipped at the edge', len(clipped), 'blocks removed', sum(1 for f in removed if f['properties']['layer'] == 'block'), 'kept (edited by Ben)', kept_edited, 'outside part dropped as a duplicate', dup_dropped)
# ---------------------------------------------------------------- join to the streets kept around the area
OLD = [f for f in newf if f['properties']['layer'] == 'street']; OG = [geom_of(f) for f in OLD]; OK = [key2(f['properties'].get('name') or '') for f in OLD]
nj = nt = 0
for p in pieces:
    cs = list(p['geom'].coords)
    for e in (0, -1):
        q = Point(cs[e]); inner = Point(cs[1 if e == 0 else -2])
        same = [(g.distance(q), g) for g, kk in zip(OG, OK) if kk == p['k'] and g.distance(q) < 25]
        if same:
            g = min(same, key=lambda t: t[0])[1]; ends = [Point(g.coords[0]), Point(g.coords[-1])]; de = [q.distance(t) for t in ends]
            t = ends[int(np.argmin(de))] if min(de) < 25 else nearest_points(g, q)[0]; cs[e] = (t.x, t.y); nj += 1; continue
        cand = [(g.distance(q), g) for g in OG if g.distance(q) < 30]
        if cand:
            g = min(cand, key=lambda t: t[0])[1]; t = nearest_points(g, q)[0]
            if t.distance(inner) > 2 and (q.distance(t) < 15 or heads_to(inner, q, t)): cs[e] = (t.x, t.y); nt += 1
    p['geom'] = LineString(cs)
print('joined to the same street', nj, 'snapped onto a crossing street', nt)
# loose ends of the kept streets at the edge: carry them onto the plate's streets (Whitfield and Morrison onto Dixmyth, Guy onto Stratford)
NG = [p['geom'] for p in pieces]; no = 0
for f, g in zip(OLD, OG):
    if f['properties']['id'] in EDITED: continue
    cs = list(g.coords); moved = False
    for e in (0, -1):
        q = Point(cs[e]); inner = Point(cs[1 if e == 0 else -2])
        if q.distance(AREA.boundary) > 60 or min([h.distance(q) for h in OG if h is not g] + [h.distance(q) for h in NG]) < 1: continue
        cand = [(h.distance(q), h) for h in NG if h.distance(q) < 30]
        if not cand: continue
        t = nearest_points(min(cand, key=lambda c: c[0])[1], q)[0]
        if q.distance(t) < 15 or heads_to(inner, q, t): cs[e] = (t.x, t.y); moved = True
    if moved:
        if f['properties']['id'] not in {r['properties']['id'] for r in removed}: removed.append(json.loads(json.dumps(f)))   # original kept for a reinstall
        f['geometry'] = mapping(LineString(cs)); f['properties']['ext_by'] = SET; no += 1
print('kept streets carried onto the plate streets', no)
# loose ends found on the first install (2026-10-20): each closed onto the street it plainly meets
def _end_near(nm, pt, maxd):
    best = None
    for p in pieces:
        if p['name'] != nm: continue
        for e in (0, -1):
            d = Point(p['geom'].coords[e]).distance(Point(pt))
            if d < maxd and (best is None or d < best[0]): best = (d, p, e)
    return best
def _move(b, xy):
    d, p, e = b; cs = list(p['geom'].coords); cs[e] = (float(xy[0]), float(xy[1])); p['geom'] = LineString(cs)
oldby = {f['properties']['id']: g for f, g in zip(OLD, OG)}
fixes = 0
b = _end_near('Lafayette Avenue', (713191, 4336374), 80)           # Lafayette meets Ludlow where the plate-37 Ludlow (S22016) ends, the 1912 survey corner
if b and 'S22016' in oldby: _move(b, oldby['S22016'].coords[-1] if Point(oldby['S22016'].coords[-1]).distance(Point(713170, 4336348)) < 5 else oldby['S22016'].coords[0]); fixes += 1
b = _end_near('Gazley Street', (713337, 4335462), 30)               # Gazley (1922) is the 1904 Herbert Street: joined end to end
herb = [g for f, g in zip(OLD, OG) if f['properties'].get('name') == 'Herbert Street' and g.distance(Point(713337, 4335465)) < 30]
if b and herb:
    h = herb[0]; t = min((h.coords[0], h.coords[-1]), key=lambda c: Point(c).distance(Point(b[1]['geom'].coords[b[2]]))); _move(b, t); fixes += 1
b = _end_near('Ludlow Avenue', (713191, 4336297), 80)              # the plate's Ludlow runs on to the same corner with Lafayette
if b and 'S22016' in oldby: _move(b, oldby['S22016'].coords[-1] if Point(oldby['S22016'].coords[-1]).distance(Point(713170, 4336348)) < 5 else oldby['S22016'].coords[0]); fixes += 1
bv = _end_near('Vine Street', (715106, 4336338), 40); bw = _end_near('Woolper Street', (715108, 4336315), 40)    # Vine and Woolper meet at the plate's north-east corner
if bv and bw:
    m = np.mean([bv[1]['geom'].coords[bv[2]], bw[1]['geom'].coords[bw[2]]], 0); _move(bv, m); _move(bw, m); fixes += 1
vine = unary_union([p['geom'] for p in pieces if p['name'] == 'Vine Street'])
for nm, pt in (('East Nixon Street', (715278, 4335020)), ('Shields Street', (715276, 4335325))):   # the stubs east of Vine start at Vine
    b = _end_near(nm, pt, 40)
    if b and not vine.is_empty:
        t = nearest_points(vine, Point(b[1]['geom'].coords[b[2]]))[0].coords[0]; o = b[1]['geom'].coords[-1 - b[2] if b[2] in (0, -1) else 0]
        if Point(t).distance(Point(o)) > 5: _move(b, t); fixes += 1   # a stub that already starts at Vine keeps its far end (20 October: East Nixon had collapsed to a point)
dix = unary_union([g for f, g in zip(OLD, OG) if f['properties'].get('name') == 'Dixmyth Avenue'])
b = _end_near('Whitfield Avenue', (713975, 4335238), 45)            # Whitfield runs on to Dixmyth
if b and not dix.is_empty: _move(b, nearest_points(dix, Point(b[1]['geom'].coords[b[2]]))[0].coords[0]); fixes += 1
mc = [(f, g) for f, g in zip(OLD, OG) if f['properties'].get('name') == 'West McMicken Avenue' and f['properties'].get('set') == 'v3' and g.distance(Point(713335, 4335430)) < 120]
ben = oldby.get('SB1012')
for f, g in mc:
    cs = list(g.coords); moved = False
    for e in (0, -1):
        q = Point(cs[e]); others = [h for ff, h in mc if ff is not f]
        near = [(h.distance(q), h) for h in others if 0.5 < h.distance(q) < 12]
        if near: t = nearest_points(min(near, key=lambda t: t[0])[1], q)[0]; cs[e] = (t.x, t.y); moved = True
        elif ben is not None and 0.5 < ben.distance(q) < 25: t = nearest_points(ben, q)[0]; cs[e] = (t.x, t.y); moved = True
    if moved:
        if f['properties']['id'] not in {r['properties']['id'] for r in removed}: removed.append(json.loads(json.dumps(f)))
        f['geometry'] = mapping(LineString(cs)); f['properties']['ext_by'] = SET; fixes += 1
print('loose ends closed', fixes)

# ---------------------------------------------------------------- blocks: faces of the new network in the area
net = unary_union([p['geom'] for p in pieces if p['kind'] == 'we_street'] + [g for g, f in zip(OG, OLD) if g.intersects(AREA.buffer(300)) and 'alley' not in (f['properties'].get('kind') or '')] + [AREA.exterior])
bands = unary_union([p['geom'].buffer(max(p['ft'] * FT, 2.5) / 2, cap_style=2, join_style=2, mitre_limit=3) for p in pieces] +
                    [g.buffer(max(f['properties'].get('width_m') or 10, 2.5) / 2, cap_style=2, join_style=2, mitre_limit=3) for g, f in zip(OG, OLD) if g.intersects(AREA.buffer(300))])
blocks = []
for q in polygonize(net):
    if q.area < 80 or not AREA.contains(q.representative_point()) or q.area > 60000: continue
    rr = q.intersection(AREA).difference(bands)
    for part in getattr(rr, 'geoms', [rr]):
        if part.geom_type == 'Polygon' and part.area > 120 and not part.buffer(-2).is_empty: blocks.append(part.simplify(0.25, preserve_topology=True))
print('new blocks', len(blocks))
def r1(c): return [round(c[0], 1), round(c[1], 1)]
out = []
for i, p in enumerate(sorted(pieces, key=lambda p: (p['kind'], p['name']))):
    out.append(dict(type='Feature', properties=dict(layer='street', id=f'{PREFIX}{i + 1:04d}', name=p['name'], kind=p['kind'], width_m=round(p['ft'] * FT, 2), width_ft=p['ft'], width_src='printed' if p['k'] in WID else 'default', side='',
                    src='Sanborn 1922', sheets='22-38', geom_src='1922 plate 38 (fitted to unchanged streets)', set=SET), geometry=dict(type='LineString', coordinates=[r1(c) for c in p['geom'].coords])))
for i, b in enumerate(blocks):
    out.append(dict(type='Feature', properties=dict(layer='block', id=f'{PREFIX}B{i + 1:04d}', type='building', area_m2=int(round(b.area)), name='', src='Sanborn 1922', set=SET),
                    geometry=dict(type='Polygon', coordinates=[[r1(c) for c in b.exterior.coords]] + [[r1(c) for c in h.coords] for h in b.interiors])))
json.dump(dict(type='FeatureCollection', features=out), open(SP + 'cuf38/ext_c38.json', 'w'))
json.dump(mapping(AREA), open(SP + 'cuf38/area_c38.json', 'w'))
print('named streets:', sorted({p['name'] for p in pieces}))
if INSTALL:
    json.dump(dict(type='FeatureCollection', features=removed), open(REM, 'w'))
    BJ['features'] = newf + out; json.dump(BJ, open(SP + 'deckpage/basin.json', 'w'), separators=(',', ':')); print('installed')
