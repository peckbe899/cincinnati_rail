try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben 2026-10-20: west of Hopson and north of Straight, the 1922 plate 35 (north) replaces the 1904 sheets: its streets are built from the
# crossings read on Ben's georeferenced copy (cuf/check_osm.py: within about 3 m of today's unchanged corners, so used as he made it), and
# the basin's earlier streets and blocks inside that area are taken out. The area: the plate's footprint, east of West McMicken Avenue
# (Ben's own line, kept), north of Straight Street (kept), west of Hopson Street / Woodside Place (kept).
#   python3 cuf/build22.py [--install]       (a reinstall first puts back what the last install took out)
import json, sys, os, collections, numpy as np
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'cuf'); sys.path.insert(0, _ws.CODE + 'sbg')
import common as C
from names import key2
from shapely.geometry import LineString, Point, Polygon, MultiPolygon, shape, mapping, box
from shapely.ops import unary_union, polygonize, nearest_points, linemerge
from scipy.sparse.csgraph import minimum_spanning_tree, shortest_path
import rasterio, rasterio.features
INSTALL = '--install' in sys.argv; SET = 'c22'; PREFIX = 'SC'; FT = 0.3048
BJ = json.load(open(SP + 'deckpage/basin.json'))
REM = SP + 'cuf/c22_removed.json'
if os.path.exists(REM):          # put back what the last install took out or clipped
    R0 = json.load(open(REM)); ids = {f['properties']['id'] for f in R0['features']}
    BJ['features'] = [f for f in BJ['features'] if f['properties'].get('set') != SET and f['properties'].get('id') not in ids] + R0['features']
ED = json.load(open(SP + 'dbread/deck/layout.json'))['streets']
EDITED = {k for k, v in ED.items() if 'c' in v or v.get('del')}
def geom_of(f): return LineString(ED[f['properties']['id']]['c']) if f['properties'].get('id') in ED and 'c' in ED[f['properties']['id']] else shape(f['geometry'])
# ---------------------------------------------------------------- area
r = rasterio.open(_ws.ext('/mnt/user-data/uploads/35_northern_CUF.tif')); al = r.read(4, out_shape=(r.height // 8, r.width // 8))
polys = [shape(g) for g, v in rasterio.features.shapes((al > 0).astype(np.uint8), mask=al > 0) if v == 1]
fp = max(polys, key=lambda p: p.area)
fp = Polygon([C.px2ben(x * 8, y * 8) for x, y in fp.exterior.coords]).buffer(-3)
ST = [f for f in BJ['features'] if f['properties']['layer'] == 'street']
def named(nm, ids=None): return [geom_of(f) for f in ST if f['properties'].get('name') == nm and (ids is None or f['properties']['id'] in ids)]
mcm = unary_union(named('West McMicken Avenue', {'SB1012', 'S22000'})); mcm = linemerge(mcm) if mcm.geom_type == 'MultiLineString' else mcm
mcm = max(getattr(mcm, 'geoms', [mcm]), key=lambda g: g.length)
c = list(mcm.coords); c = sorted(c, key=lambda q: -q[1])            # north to south
east_of_mcm = Polygon([(c[0][0], 4337000)] + c + [(c[-1][0], 4333000), (716000, 4333000), (716000, 4337000)]).buffer(0)
stt = (lambda u: linemerge(u) if u.geom_type == 'MultiLineString' else u)(unary_union(named('Straight Street', {'SB0944', 'S22002', 'SV0154'}) + [g for g in named('Straight Street') if g.bounds[0] > 713400 and g.bounds[1] > 4334000]))
sc = sorted([q for g in getattr(stt, 'geoms', [stt]) for q in g.coords], key=lambda q: q[0])
north_of_st = Polygon([(712500, sc[0][1])] + sc + [(716000, sc[-1][1]), (716000, 4337000), (712500, 4337000)]).buffer(0)
# east of Clifton Avenue Straight does not run: there the area reaches down to Calhoun Street (the University grounds; the 1904 sheets
# draw nothing there once 259's out-of-place University panel is left off)
cal = sorted([q for g in named('Calhoun Street') if g.bounds[0] > 714200 and g.bounds[1] > 4333850 and g.bounds[3] < 4334050 for q in g.coords], key=lambda q: q[0])
clf = max(sc, key=lambda q: q[0])[0]          # Straight's east end, at Clifton
if cal: north_of_st = north_of_st.union(Polygon([(clf, sc[-1][1])] + [q for q in cal if q[0] > clf] + [(716000, cal[-1][1]), (716000, sc[-1][1])]).buffer(0)).buffer(0)
hop = sorted([q for g in named('Hopson Street') for q in g.coords], key=lambda q: q[1])
hg = [h for h in hop if True]
west_of_hop = Polygon([(hg[0][0], 4333000)] + hg + [(hg[-1][0], 4337000), (712000, 4337000), (712000, 4333000)]).buffer(0)
AREA = fp.intersection(east_of_mcm).intersection(north_of_st).intersection(west_of_hop)
AREA = max(getattr(AREA, 'geoms', [AREA]), key=lambda p: p.area)
print('area', round(AREA.area / 1e4, 1), 'ha')
# ---------------------------------------------------------------- picks
P, O = [], []
for part in 'wme':
    d = json.load(open(SP + f'sbg/picks22/s22-35N_{part}.json'))
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
    E, N = C.px2ben(n['x'], n['y'])
    for k in n['pair']: V[k].append((float(E), float(N))); NAME.setdefault(k, n['names'][k])
for o in O:
    if o['typ'] == 'width': continue
    k = key2(o.get('street') or '')
    if not k: continue
    E, N = C.px2ben(o['x'], o['y']); V[k].append((float(E), float(N))); NAME.setdefault(k, o['street'])
WID = {}
for o in O:
    if o['typ'] == 'width' and key2(o['street']): WID[key2(o['street'])] = o['ft']
KEEP_EXISTING = {key2(n) for n in ('West McMicken Avenue', 'Straight Street', 'Hopson Street', 'Woodside Place', 'Woodside Place (south of University)', 'Calhoun Street', 'Hopple Street', 'Gilmore Street', 'Massachusetts Avenue', 'Bader Street', 'Township Street', 'Rachel Street', 'Cormany Avenue')}
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
for k, pts in V.items():
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
                    src='Sanborn 1922', sheets='22-35N', geom_src='1922 plate 35 (Ben’s georeference)', set=SET), geometry=dict(type='LineString', coordinates=[r1(c) for c in p['geom'].coords])))
for i, b in enumerate(blocks):
    out.append(dict(type='Feature', properties=dict(layer='block', id=f'{PREFIX}B{i + 1:04d}', type='building', area_m2=int(round(b.area)), name='', src='Sanborn 1922', set=SET),
                    geometry=dict(type='Polygon', coordinates=[[r1(c) for c in b.exterior.coords]] + [[r1(c) for c in h.coords] for h in b.interiors])))
json.dump(dict(type='FeatureCollection', features=out), open(SP + 'cuf/ext_c22.json', 'w'))
json.dump(mapping(AREA), open(SP + 'cuf/area_c22.json', 'w'))
print('named streets:', sorted({p['name'] for p in pieces}))
if INSTALL:
    json.dump(dict(type='FeatureCollection', features=removed), open(REM, 'w'))
    BJ['features'] = newf + out; json.dump(BJ, open(SP + 'deckpage/basin.json', 'w'), separators=(',', ':')); print('installed')
