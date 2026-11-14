try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Step 6 for a 1922 plate N (generalised from cuf38/build38.py, 2026-10-21): the plate's streets on the map, built from the crossings
# read on Ben's scan (sbg/picks22/s22-N_*.json) and placed with our fit (cufp/fit.py -> cufp/N/fwd.pkl).
# Area: the plate's footprint (3 m in), less the areas of the plates built before it (c22, c38, then cufp plates in PLATE_ORDER).
# Earlier streets and blocks inside are taken out (Ben's edited ones kept), those crossing the edge are cut there. Per-plate settings
# (keep-lines, loose-end fixes) in cufp/config.json.
#   python3 cufp/build.py N [--install]       (a reinstall first puts back what the last install took out)
import json, sys, os, collections, numpy as np
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'cuf'); sys.path.insert(0, _ws.CODE + 'sbg'); sys.path.insert(0, _ws.CODE + 'cufp')
NP_ = sys.argv[1]
import fwdlib
def W38(x, y): return fwdlib.world(NP_, float(x), float(y))
import common as C
from names import key2
from shapely.geometry import LineString, Point, Polygon, MultiPolygon, shape, mapping, box
from shapely.ops import unary_union, polygonize, nearest_points, linemerge
from scipy.sparse.csgraph import minimum_spanning_tree, shortest_path
import rasterio, rasterio.features
CFG = json.load(open(SP + 'cufp/config.json')).get(NP_, {}) if os.path.exists(SP + 'cufp/config.json') else {}
PLATE_ORDER = ['66', '68', '67', '69', '70', '82A', '83A', '75', '76', '29', '26A', '26B', '31', '33', '25', '28', '39', '40', '45', '43', '44', '80']   # 31, 33 Fairmount (2026-10-25); 82A, 83A Norwood (2026-10-23); 75, 76 (2026-10-24); 29, 26A, 26B Price Hill (2026-10-25)
INSTALL = '--install' in sys.argv; SET = 'c' + NP_; PREFIX = 'S' + {'66': 'P', '67': 'Q', '68': 'R', '69': 'T', '70': 'U', '82A': 'N', '83A': 'O', '75': 'X', '76': 'Y', '26A': 'D', '26B': 'F', '29': 'G', '31': 'H', '33': 'L', '25': 'A', '28': 'I', '39': 'J', '40': 'S', '45': '4', '43': '3', '44': '5', '80': '6'}[NP_]; FT = 0.3048
BJ = json.load(open(SP + 'deckpage/basin.json'))
REM = SP + f'cufp/{NP_}/removed.json'
if os.path.exists(REM):          # put back what the last install took out or clipped
    R0 = json.load(open(REM)); ids = {f['properties']['id'] for f in R0['features']}
    BJ['features'] = [f for f in BJ['features'] if f['properties'].get('set') != SET and f['properties'].get('id') not in ids] + R0['features']
ED = json.load(open(SP + 'dbread/deck/layout.json'))['streets']
EDITED = {k for k, v in ED.items() if 'c' in v or v.get('del')}
def geom_of(f): return LineString(ED[f['properties']['id']]['c']) if f['properties'].get('id') in ED and 'c' in ED[f['properties']['id']] else shape(f['geometry'])
# ---------------------------------------------------------------- area
al = np.load(SP + f'cufp/{NP_}/png_alpha_s4.npy')[::2, ::2]                     # png alpha every 8 px
polys = [shape(g) for g, v in rasterio.features.shapes((al > 0).astype(np.uint8), mask=al > 0) if v == 1]
fp = max(polys, key=lambda p: p.area)
fp = Polygon(fwdlib.world_many(NP_, [(x * 8, y * 8) for x, y in fp.exterior.coords])).buffer(0).buffer(-3)
ST = [f for f in BJ['features'] if f['properties']['layer'] == 'street']
def named(nm, ids=None): return [geom_of(f) for f in ST if f['properties'].get('name') == nm and (ids is None or f['properties']['id'] in ids)]
PRIOR = [SP + 'cuf/area_c22.json', SP + 'cuf38/area_c38.json'] + [SP + f'cufp/{q}/area.json' for q in PLATE_ORDER[:PLATE_ORDER.index(NP_)]]
PRIOR = [shape(json.load(open(fn))).buffer(3) for fn in PRIOR if os.path.exists(fn)]
AREA = fp.difference(unary_union(PRIOR)) if PRIOR else fp
AREA = max(getattr(AREA, 'geoms', [AREA]), key=lambda p: p.area)
KEEP_SETS = set(CFG.get('keep_sets', []))          # 2026-10-25 (Price Hill): the OSM major streets (set w1) stay; the plate fills in around them
if CFG.get('avoid_existing'):                       # ... and the plate takes only ground the page has not drawn yet (Lower Price Hill and the deck stay as they are)
    _cov = []
    for f in BJ['features']:
        p_ = f['properties']
        if p_.get('set') in KEEP_SETS or p_.get('set') == SET: continue
        if p_['layer'] == 'street' and f['geometry']['type'] == 'LineString': _cov.append(geom_of(f).buffer(p_.get('width_m', 12) / 2 + 6, cap_style=2))
        elif p_['layer'] in ('block',) and f['geometry']['type'] in ('Polygon', 'MultiPolygon'): _cov.append(shape(f['geometry']).buffer(3))
    _cov = unary_union(_cov).buffer(90).buffer(-60)       # closed: the ground between the page's own streets (up to about 180 m apart) counts as theirs
    AREA = fp.difference(unary_union(PRIOR + [_cov])) if PRIOR else fp.difference(_cov)
    if CFG.get('clip_to'): AREA = AREA.intersection(Polygon(json.load(open(SP + CFG['clip_to']))))   # Ben's Western Hills line (25 Oct): plates fill only inside it
    AREA = unary_union([q for q in getattr(AREA, 'geoms', [AREA]) if q.area > 20000])
KEPT_G = [geom_of(f) for f in BJ['features'] if f['properties'].get('set') in KEEP_SETS and f['properties']['layer'] == 'street']
mcm = LineString([(0, 0), (1, 1)])
print('area', round(AREA.area / 1e4, 1), 'ha')
# ---------------------------------------------------------------- picks
P, O = [], []
import glob
for fn_ in sorted(glob.glob(SP + 'sbg/picks22/s22-' + NP_ + '_*.json')):
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
# per-plate name settings (2026-10-23, Norwood): merge keys printed two ways for one street; best printed name per street
MERGE = CFG.get('merge', {})
if MERGE:
    for a_, b_ in MERGE.items():
        if a_ in V: V[b_] += V.pop(a_); NAME.setdefault(b_, NAME.get(a_)); NAME.pop(a_, None)
if CFG.get('best_names'):
    VAR = collections.defaultdict(collections.Counter)
    for p in P:
        for nm in (p['a'], p['b']): VAR[MERGE.get(key2(nm), key2(nm))][nm] += 1
    for o in O:
        if o['typ'] != 'width' and o.get('street'): VAR[MERGE.get(key2(o['street']), key2(o['street']))][o['street']] += 1
    SUF = (' Avenue', ' Street', ' Road', ' Boulevard', ' Place', ' Pike', ' Lane', ' Park')
    for k, c in VAR.items():
        if k not in NAME: continue
        cand = [n for n in c if n.endswith(SUF)] or list(c)
        NAME[k] = CFG.get('names', {}).get(k) or max(cand, key=lambda n: (c[n], len(n)))
WID = {}
for o in O:
    if o['typ'] == 'width' and key2(o['street']): WID[key2(o['street'])] = o['ft']
KEEP_EXISTING = {key2(n) for n in CFG.get('keep', [])}
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
_DROP = {key2(n) for n in CFG.get('drop', [])}       # estate roads read off a plate that are not streets (Brestel Road on 33, 25 Oct)
pieces = [pc for pc in pieces if pc['k'] not in _DROP]
for k_, pxy, nm_n, nm_s in CFG.get('split', []):     # one street printed under two names (Montgomery Pike north of the railroads, Avenue south)
    sx, sy = W38(*pxy); out_ = []
    for pc in pieces:
        if pc['k'] != k_: out_.append(pc); continue
        g = pc['geom']; t = g.project(Point(sx, sy)); parts = []
        if 1 < t < g.length - 1:
            cs = list(g.coords); acc = 0; a_, b_ = [cs[0]], []
            for i in range(1, len(cs)):
                seg = LineString([cs[i - 1], cs[i]]); 
                if not b_ and acc + seg.length >= t: q = g.interpolate(t); a_.append((q.x, q.y)); b_ = [(q.x, q.y), cs[i]]
                elif b_: b_.append(cs[i])
                else: a_.append(cs[i])
                acc += seg.length
            parts = [LineString(a_), LineString(b_)]
        else: parts = [g]
        for gg in parts:
            if gg.length < 8: continue
            out_.append(dict(pc, geom=gg, name=nm_n if gg.centroid.y > sy else nm_s))
    pieces = out_
if KEEP_SETS and KEPT_G:
    _kb = unary_union(KEPT_G).buffer(18); _out = []
    for pc in pieces:
        g = pc['geom'].difference(_kb)
        for q in getattr(g, 'geoms', [g]):
            if q.geom_type == 'LineString' and q.length > 40: _out.append(dict(pc, geom=q))
    print('plate pieces cut back from the kept OSM streets', len(pieces), '->', len(_out)); pieces = _out
print('new street pieces', len(pieces))
# ---------------------------------------------------------------- earlier streets and blocks in the area
removed, kept_edited, clipped, dup_dropped = [], [], [], []
newf = []
for f in BJ['features']:
    p = f['properties']; lay = p['layer']
    if lay == 'street':
        g = geom_of(f); kk = key2(p.get('name') or '')
        if kk in KEEP_EXISTING or p.get('set') in KEEP_SETS:
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
    if f['properties']['id'] in EDITED or f['properties'].get('set') in KEEP_SETS: continue
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
# loose ends: per-plate fixes from cufp/config.json, each [street, [x, y] of the loose end, max distance, target]
# target: {"street": name} -> nearest point of that street (kept or new); {"xy": [E, N]} -> that point. A snap that would leave a piece under 5 m is skipped.
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
fixes = 0
for nm, pt, maxd, tgt in CFG.get('fixes', []):
    b = _end_near(nm, pt, maxd)
    if not b: print('fix not found', nm, pt); continue
    q = Point(b[1]['geom'].coords[b[2]]); o = Point(b[1]['geom'].coords[-1 - b[2] if b[2] in (0, -1) else 0])
    if 'xy' in tgt: t = tuple(tgt['xy'])
    else:
        g = unary_union([pp['geom'] for pp in pieces if pp['name'] == tgt['street'] and pp is not b[1]] + [g for f, g in zip(OLD, OG) if f['properties'].get('name') == tgt['street']])
        if g.is_empty: print('fix target missing', tgt); continue
        t = nearest_points(g, q)[0].coords[0]
    if Point(t).distance(o) > 5: _move(b, t); fixes += 1
print('loose ends closed', fixes)
# second pass (2026-10-21): a plate street end left 1-30 m short of another street (new or kept) is carried onto it when it heads there
# (or is within 15 m); two pieces of the same street with a gap under 30 m are joined end to end
def _touch(q, me):
    return min([pp['geom'].distance(q) for pp in pieces if pp is not me] + [g.distance(q) for g in OG]) < 1.0
n2 = 0; trim = []
for p in pieces:
    cs = list(p['geom'].coords)
    for e in (0, -1):
        q = Point(cs[e]); inner = Point(cs[1 if e == 0 else -2])
        if _touch(q, p): continue
        same = [pp for pp in pieces if pp is not p and pp['k'] == p['k'] and pp['geom'].distance(q) < 30]
        if same:
            g = min(same, key=lambda pp: pp['geom'].distance(q))['geom']; ends = [Point(g.coords[0]), Point(g.coords[-1])]
            t = min(ends, key=lambda t: t.distance(q)) if min(t.distance(q) for t in ends) < 30 else nearest_points(g, q)[0]
            cs[e] = (t.x, t.y); n2 += 1; continue
        cand = [(pp['geom'].distance(q), pp['geom']) for pp in pieces if pp is not p and pp['geom'].distance(q) < 30] + [(g.distance(q), g) for g in OG if g.distance(q) < 30]
        if not cand: continue
        g = min(cand, key=lambda c: c[0])[1]; t = nearest_points(g, q)[0]
        if t.distance(inner) > 2 and (q.distance(t) < 15 or heads_to(inner, q, t)): cs[e] = (t.x, t.y); n2 += 1
        elif t.distance(inner) <= 2 and q.distance(t) < 15: cs[e] = (t.x, t.y); n2 += 1; trim.append((p, e))     # overshoot past the street it ends at (Eden past East Auburn): cut back to it
    p['geom'] = LineString(cs)
for p, e in trim:                      # drop the now near-duplicate vertex next to the cut-back end
    cs = list(p['geom'].coords)
    if len(cs) > 2 and Point(cs[e]).distance(Point(cs[1 if e == 0 else -2])) <= 2: cs.pop(1 if e == 0 else -2); p['geom'] = LineString(cs)
print('loose ends closed (second pass)', n2)


# ---------------------------------------------------------------- blocks: faces of the new network in the area
net = unary_union([p['geom'] for p in pieces if p['kind'] == 'we_street'] + [g for g, f in zip(OG, OLD) if g.intersects(AREA.buffer(300)) and 'alley' not in (f['properties'].get('kind') or '')] + [AREA.boundary])
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
                    src='Sanborn 1922', sheets='22-' + NP_, geom_src='1922 plate ' + NP_ + ' (fitted to unchanged streets)', set=SET), geometry=dict(type='LineString', coordinates=[r1(c) for c in p['geom'].coords])))
for i, b in enumerate(blocks):
    out.append(dict(type='Feature', properties=dict(layer='block', id=f'{PREFIX}B{i + 1:04d}', type='building', area_m2=int(round(b.area)), name='', src='Sanborn 1922', set=SET),
                    geometry=dict(type='Polygon', coordinates=[[r1(c) for c in b.exterior.coords]] + [[r1(c) for c in h.coords] for h in b.interiors])))
json.dump(dict(type='FeatureCollection', features=out), open(SP + f'cufp/{NP_}/ext.json', 'w'))
json.dump(mapping(AREA), open(SP + f'cufp/{NP_}/area.json', 'w'))
print('named streets:', sorted({p['name'] for p in pieces}))
if INSTALL:
    json.dump(dict(type='FeatureCollection', features=removed), open(REM, 'w'))
    BJ['features'] = newf + out; json.dump(BJ, open(SP + 'deckpage/basin.json', 'w'), separators=(',', ':')); print('installed')
