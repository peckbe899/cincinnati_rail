"""Basin streets and blocks from the georeferenced 1904 Sanborn picks (deck method).
Each named street: its intersections (clustered across sheets), bends and ends, ordered along the street,
split into straight runs (total-least-squares lines, 2 m tolerance), junctions at line intersections,
T and L ends snapped onto the centreline they meet. Width = printed width on the sheets of the run.
Blocks = faces of the street network minus the street bands, kept where the 1912 survey shows built blocks.
"""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import json, sys, os, collections, itertools, numpy as np
HERE = _ws.data_dir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, _ws.code_dir(HERE)); sys.path.insert(0, _ws.code_dir(os.path.dirname(HERE)))
from load import load, frame_of
from names import key, key2
from solve import apply
from shapely.geometry import LineString, Point, Polygon, MultiPolygon, shape, mapping
from shapely.ops import unary_union, polygonize, nearest_points, substring
from scipy.sparse.csgraph import minimum_spanning_tree, shortest_path
SP = _ws.DATA
FT = 0.3048
TOL = 2.0           # straight-run tolerance, m
MAXGAP = 450.0      # longest gap bridged between consecutive vertices of one street, m
TOL_MERGE, RMS_MERGE, MERGE_ANG = 3.0, 1.25, 8.0   # alignment pass: neighbouring runs merged into one straight line
JOG_MIN = 0.4       # offsets below this at a junction of near-parallel runs are drawn as a point, above as a step at the crossing
P = {k: np.array(v) for k, v in json.load(open(os.path.join(HERE, 'tf.json'))).items()}
R, O = load()
# ---------------------------------------------------------------- pick fixes from the OSM check (osmchk/pick_fix.json)
FIX = json.load(open(SP + 'sbg/osmchk/pick_fix.json'))
# one street read under two names on different sheets (alignment pass): fold the section name into the plain one
from names import key2 as _key2
ALIAS = {a['from']: a['to'] for a in FIX.get('alias', [])}
def key2(n):
    k = _key2(n); return ALIAS.get(k, k)
NOLINK_AT = [(f['street'], np.array(f['at'], float)) for f in FIX.get('nolink_at', [])]
def _near(r, f): return r['s'] == f['s'] and abs(r['x'] - f['x']) < 3 and abs(r['y'] - f['y']) < 3
for f in FIX['rename']:
    for r in R:
        if _near(r, f): r[f['side']] = f['to']; r['k' + f['side']] = key(f['to'])
R = [r for r in R if not any(_near(r, f) for f in FIX['drop'])]
for f in FIX.get('move', []):
    for r in R:
        if _near(r, f): r['x'], r['y'] = float(f['to'][0]), float(f['to'][1])
for f in FIX['add']:
    R.append(dict(s=f['s'], fr=frame_of(f['s'], None, f['y']), a=f['a'], b=f['b'], ka=key(f['a']), kb=key(f['b']), x=float(f['x']), y=float(f['y']), kind=f['kind']))
for f in FIX.get('add_bends', []): O.append(dict(street=f['street'], x=f['x'], y=f['y'], note=f['note'], s=f['s'], typ='bends'))
NOLINK = []
for f in FIX.get('nolink', []):
    NOLINK.append((key2(f['street']), tuple(sorted(f['between'][0])), tuple(sorted(f['between'][1]))))
R = [r for r in R if r['fr'] in P]
for r in R:
    r['E'], r['N'] = apply(P[r['fr']], r['x'], r['y'])
    r['k2a'], r['k2b'] = key2(r['a']), key2(r['b'])
    for side in 'ab':
        if r['k2' + side] is None and r[side] and r[side].strip() not in ('?',):
            r['k2' + side] = f"~{r['s']}~{r[side].strip().lower()}"      # unnamed, sheet-local
# ---------------------------------------------------------------- nodes
groups = collections.defaultdict(list)
for i, r in enumerate(R):
    if r['k2a'] and r['k2b'] and r['k2a'] != r['k2b']: groups[tuple(sorted((r['k2a'], r['k2b'])))].append(i)
nodes = []          # dict(pair, E, N, picks, kind)
for pk, idx in groups.items():
    cl = []
    for i in idx:
        r = R[i]; best = None
        for c in cl:
            if any(R[j]['fr'] == r['fr'] for j in c): continue
            m = np.median([[R[j]['E'], R[j]['N']] for j in c], axis=0)
            d = np.hypot(m[0] - r['E'], m[1] - r['N'])
            if d < 10 and (best is None or d < best[0]): best = (d, c)
        if best: best[1].append(i)
        else: cl.append([i])
    for c in cl:
        xy = np.array([[R[j]['E'], R[j]['N']] for j in c]); m = np.median(xy, axis=0)
        keep = [j for j, p in zip(c, xy) if np.hypot(*(p - m)) < 6] or c
        xy = np.array([[R[j]['E'], R[j]['N']] for j in keep]); m = xy.mean(axis=0)
        kinds = collections.Counter(R[j]['kind'] for j in keep)
        nodes.append(dict(pair=pk, E=float(m[0]), N=float(m[1]), picks=keep, kind=kinds.most_common(1)[0][0],
                          sheets=sorted({R[j]['s'] for j in keep}), spread=float(np.ptp(xy, axis=0).max()) if len(xy) > 1 else 0.0))
print('nodes', len(nodes), 'multi-sheet', sum(1 for n in nodes if len(n['sheets']) > 1))
# ---------------------------------------------------------------- corrections from the OSM check (osmchk/corrections.json)
from shapely.geometry import MultiPoint
COR = json.load(open(SP + 'sbg/osmchk/corrections.json'))
_need = {nm for c in COR for nm in c.get('osm', [])}
OSMG = collections.defaultdict(list)
for f in json.load(open(SP + 'basin/osm_basin.geojson'))['features']:
    nm = f['properties'].get('name')
    if nm in _need and f['properties'].get('highway') not in ('footway', 'steps', 'path', 'cycleway'): OSMG[nm].append(LineString(f['geometry']['coordinates']))
CARD = {'n': (0, 1), 's': (0, -1), 'e': (1, 0), 'w': (-1, 0)}
for c in COR:
    pp = np.array(c['pts']); c['_reg'] = MultiPoint([tuple(q) for q in pp]).buffer(22)
    cc = pp.mean(0); u, sv, vt = np.linalg.svd(pp - cc); d = vt[0]; nrm = np.array([-d[1], d[0]])
    if c['mode'] == 'shift':
        if nrm @ np.array(CARD[c['dir']]) < 0: nrm = -nrm
        c['_v'] = nrm * c['m']
    c['_lines'] = [g for nm in c.get('osm', []) for g in OSMG[nm] if g.distance(c['_reg']) < 1]
def cor_target(c, E, N):
    if c['mode'] == 'shift': return E + c['_v'][0], N + c['_v'][1]
    pt = Point(E, N); cand = []
    for g in c['_lines']:
        dd = g.distance(pt)
        if dd < 30: q = g.interpolate(g.project(pt)); cand.append((dd, np.array([q.x, q.y])))
    if not cand: return E, N
    cand.sort(key=lambda t: t[0]); best = cand[0][1]
    if c.get('dual'):
        v0 = best - np.array([E, N])
        for dd, q in cand[1:]:
            if np.hypot(*(q - best)) > 5 and (q - np.array([E, N])) @ v0 < 0: return tuple((best + q) / 2)
    return tuple(best)
ncor = 0
for n in nodes:
    for c in COR:
        if c['street'] in n['pair'] and c['_reg'].contains(Point(n['E'], n['N'])):
            n['E'], n['N'] = map(float, cor_target(c, n['E'], n['N'])); n['corrected'] = c['item']; ncor += 1
print('corrected nodes', ncor)
# ---------------------------------------------------------------- other picks to world
def frame_for(o, y):
    s = o['s']
    fr = ('17u' if y < 2200 else '17l') if s == 17 else frame_of(s, o.get('part'), y)
    if fr is None:      # sheet 17 bends without part: nearest pick's frame
        cand = [r for r in R if r['s'] == s]
        fr = min(cand, key=lambda r: np.hypot(r['x'] - o.get('x', o.get('x1')), r['y'] - y))['fr'] if cand else None
    return fr if fr in P else None
verts = collections.defaultdict(list)       # street key -> list of (E, N, tag, info)
for n in nodes:
    for k in n['pair']: verts[k].append((n['E'], n['N'], 'node', n))
nhalf = 0
for r in R:
    ka, kb = r['k2a'], r['k2b']
    if bool(ka) == bool(kb): continue           # both named (a node) or neither
    k = ka or kb
    if k.startswith('~'): continue
    verts[k].append((r['E'], r['N'], 'half', dict(s=r['s'], note='crossing with an unnamed way'))); nhalf += 1
print('half-named crossings added as vertices', nhalf)
for o in O:
    if o['typ'] not in ('bends', 'ends'): continue
    k = key2(o['street'])
    if k is None: k = f"~{o['s']}~{o['street'].strip().lower()}"
    fr = frame_for(o, o['y'])
    if not fr: continue
    E, N = apply(P[fr], o['x'], o['y'])
    for c in COR:
        if c['street'] == k and c['_reg'].contains(Point(E, N)): E, N = cor_target(c, E, N)
    verts[k].append((E, N, o['typ'][:-1], o))
for c in COR:
    if not c.get('shape'): continue
    for g in c['_lines']:
        for d in np.arange(0, g.length, 10.0):
            q = g.interpolate(d)
            if c['_reg'].contains(q):
                E, N = cor_target(c, q.x, q.y); verts[c['street']].append((E, N, 'shape', dict(s=-1, note=c['item'])))
# widths per (sheet, street key)
WID = collections.defaultdict(list)
# widths printed for one side of a crossing ("40' north of West 5th"): conditions on that crossing (widthnotes.py)
from widthnotes import parse as wparse
OVR = {key2(f['street']) for f in FIX.get('widths', [])}
WPOS = collections.defaultdict(list)       # street key -> [(sheet, ft, condition)]
for o in O:
    if o['typ'] == 'widths' and o.get('ft'):
        k = key2(o['street'])
        if not k: continue
        main, extra = (None, []) if k in OVR else wparse(o.get('note', ''), float(o['ft']))
        if main: WPOS[k].append((o['s'], float(o['ft']), main))
        else: WID[(o['s'], k)].append(float(o['ft']))
        for f_, cond in extra:
            if f_ and not (main and cond == main and abs(f_ - float(o['ft'])) < 0.01): WPOS[k].append((o['s'], float(f_), cond))
for f in FIX.get('widths', []): WID[(f['s'], key2(f['street']))] = [float(f['ft'])]
WALL = collections.defaultdict(list)
for (s, k), v in WID.items(): WALL[k] += v
for k, L in WPOS.items(): WALL[k] += [f_ for _, f_, _ in L] if not WALL[k] else []
import re as _re0
def kbase(kk): return _re0.sub(r'^(west|east|north|south) ', '', kk.split(' | ')[0])
def ckey(name): kk = key2(name); return kbase(kk) if kk else None
WCROSS = {k: {ckey(n) for _, _, c in L for n in c[1:]} for k, L in WPOS.items()}
def is_alley(k): return k.split(' | ')[0].endswith(' al') or ' al ' in k or k.endswith('~al') or 'alley' in k or k.endswith(' al)')
# display names
NAMES = collections.defaultdict(collections.Counter)
for r in R:
    for side in 'ab':
        if r['k2' + side]: NAMES[r['k2' + side]][r[side]] += 1
import re as _re
def disp(k):
    if k in NAMES and NAMES[k]: return _re.sub(r'\s*\(.*?\)', '', NAMES[k].most_common(1)[0][0]).strip()
    return k
# ---------------------------------------------------------------- order vertices along a street
def order(pts):
    """MST, split at long edges, longest path per component; leftover vertices inserted by projection"""
    n = len(pts)
    if n == 1: return [[0]]
    D = np.hypot(*(pts[:, None, :] - pts[None, :, :]).transpose(2, 0, 1))
    T = minimum_spanning_tree(D).toarray(); T = T + T.T
    T[T > MAXGAP] = 0
    from scipy.sparse.csgraph import connected_components
    nc, lab = connected_components(T > 0, directed=False)
    out = []
    for c in range(nc):
        idx = np.where(lab == c)[0]
        if len(idx) == 1: out.append([int(idx[0])]); continue
        sub = T[np.ix_(idx, idx)]
        dist, pred = shortest_path(sub, directed=False, return_predecessors=True)
        dd = np.where(np.isinf(dist), -1, dist); a, b = np.unravel_index(np.argmax(dd), dd.shape)
        path = [b]
        while path[-1] != a: path.append(pred[a, path[-1]])
        path = path[::-1]
        rest = [k for k in range(len(idx)) if k not in path]
        # insert leftovers by projection on the path polyline
        line = LineString(pts[idx[path]]) if len(path) > 1 else None
        if line is not None and rest:
            pos = {k: line.project(Point(pts[idx[k]])) for k in path}
            for k in rest: pos[k] = line.project(Point(pts[idx[k]]))
            allk = sorted(path + rest, key=lambda k: pos[k])
            path = allk
        out.append([int(idx[k]) for k in path])
    return out
def tls(seg):
    c = seg.mean(axis=0); u, s, vt = np.linalg.svd(seg - c); d = vt[0]; return c, d
def runs(pts, forced):
    def rec(i, j):
        if j - i < 2: return [(i, j)]
        seg = pts[i:j + 1]; c, d = tls(seg); nrm = np.array([-d[1], d[0]])
        dev = np.abs((seg - c) @ nrm)
        inner = [k for k in range(i + 1, j) if k in forced]
        if dev.max() <= TOL and not inner: return [(i, j)]
        if inner: k = min(inner, key=lambda k: abs(k - (i + j) / 2))
        else:
            a, b = pts[i], pts[j]; ab = b - a; L = np.hypot(*ab) + 1e-9; nn = np.array([-ab[1], ab[0]]) / L
            dv = np.abs((pts[i + 1:j] - a) @ nn); k = i + 1 + int(np.argmax(dv))
        return rec(i, k) + rec(k, j)
    rr = rec(0, len(pts) - 1)
    # straighten (2026-10-11 alignment pass): merge neighbouring runs that are one straight street within the fit noise
    while len(rr) > 1:
        best = None
        for a in range(len(rr) - 1):
            i, k = rr[a]; _, j = rr[a + 1]
            if k in forced: continue
            d1 = tls(pts[i:k + 1])[1]; d2 = tls(pts[k:j + 1])[1]
            if np.degrees(np.arccos(min(1, abs(d1 @ d2)))) > MERGE_ANG: continue
            seg = pts[i:j + 1]; c, d = tls(seg); dev = np.abs((seg - c) @ np.array([-d[1], d[0]]))
            if dev.max() <= TOL_MERGE and np.sqrt((dev ** 2).mean()) <= RMS_MERGE and (best is None or dev.max() < best[0]): best = (dev.max(), a)
        if best is None: break
        a = best[1]; rr = rr[:a] + [(rr[a][0], rr[a + 1][1])] + rr[a + 2:]
    return rr
def line_x(c1, d1, c2, d2):
    M = np.array([d1, -d2]).T
    if abs(np.linalg.det(M)) < 1e-9: return None
    t = np.linalg.solve(M, c2 - c1); return c1 + t[0] * d1
streets = []    # dict(key, coords, vtags, runs_w)
def base_of(k): return _re.sub(r'^(west|east|north|south) ', '', k.split(' | ')[0])
BASEV = collections.defaultdict(list)
for k_, V_ in verts.items():
    if not k_.startswith('~'):
        for v in V_: BASEV[base_of(k_)].append((v[0], v[1], k_))
def seg_dist(q, a, b):
    ab = b - a; t = np.clip((q - a) @ ab / (ab @ ab + 1e-9), 0, 1); return float(np.hypot(*(a + t * ab - q)))
def bridges_section(k, a, b):
    # a long link of one name that runs alongside a piece the sheets give under a section name of the same street
    if k.startswith('~') or np.hypot(*(b - a)) < 60: return False
    ab = b - a; L2 = ab @ ab; n_ = 0
    for E, N, k2 in BASEV[base_of(k)]:
        if k2 == k: continue
        q = np.array([E, N]); t = (q - a) @ ab / L2
        if 0.08 < t < 0.92 and seg_dist(q, a, b) < 15: n_ += 1
    return n_ >= 2
nsplit = collections.Counter()
for k, V in verts.items():
    if len(V) < 2: continue
    pts0 = np.array([(v[0], v[1]) for v in V])
    # merge vertices closer than 3 m (keep node info of all)
    used = [False] * len(V); merged = []
    for i in range(len(V)):
        if used[i]: continue
        grp = [i] + [j for j in range(i + 1, len(V)) if not used[j] and np.hypot(*(pts0[i] - pts0[j])) < 3.0]
        for j in grp: used[j] = True
        merged.append(grp)
    pts = np.array([pts0[g].mean(axis=0) for g in merged]); tags = [[V[j] for j in g] for g in merged]
    comps = []
    for comp in order(pts):
        cur = [comp[0]]
        for a_, b_ in zip(comp[:-1], comp[1:]):
            pa = {v[3]['pair'] for v in tags[a_] if v[2] == 'node'}; pb = {v[3]['pair'] for v in tags[b_] if v[2] == 'node'}
            if any(sk == k and ((p1 in pa and p2 in pb) or (p2 in pa and p1 in pb)) for sk, p1, p2 in NOLINK): comps.append(cur); cur = [b_]; nsplit['nolink'] += 1
            elif bridges_section(k, pts[a_], pts[b_]): comps.append(cur); cur = [b_]; nsplit['section'] += 1
            elif any(sk == k and seg_dist(q, pts[a_], pts[b_]) < 6 for sk, q in NOLINK_AT): comps.append(cur); cur = [b_]; nsplit['at'] += 1
            else: cur.append(b_)
        comps.append(cur)
    for comp in comps:
        # a dead end read on two sheets: drop the reading that turns the street back on itself
        for side in (0, 1):
            if len(comp) >= 3:
                e1, e0, e_1 = (comp[0], comp[1], comp[2]) if side == 0 else (comp[-1], comp[-2], comp[-3])
                pure = lambda i: all(v[2] == 'end' for v in tags[i])
                if pure(e1) and pure(e0) and np.hypot(*(pts[e1] - pts[e0])) < 30:
                    u = pts[e0] - pts[e_1]; w = pts[e1] - pts[e0]
                    if np.degrees(np.arccos(np.clip(u @ w / (np.hypot(*u) * np.hypot(*w) + 1e-9), -1, 1))) > 30:
                        comp = comp[1:] if side == 0 else comp[:-1]; nsplit['end'] += 1
        if len(comp) < 2: continue
        cp = pts[comp]; ct = [tags[i] for i in comp]
        if k.startswith('~'):
            c, d = tls(cp); dev = np.abs((cp - c) @ np.array([-d[1], d[0]]))
            if dev.max() > 3.0 or np.hypot(*(cp[0] - cp[-1])) > 220: continue
        forced = {i for i, t in enumerate(ct) if any(v[2] == 'bend' for v in t)}
        rr = runs(cp, forced)
        fits = [tls(cp[i:j + 1]) for i, j in rr]
        wb = {i for i, t in enumerate(ct) if any(v[2] == 'node' and any(kk != k and kbase(kk) in WCROSS.get(k, ()) for kk in v[3]['pair']) for v in t)}
        streets.append(dict(key=k, runs=rr, cp=cp, tags=ct, fits=fits, wbreak=wb))
# ---------------------------------------------------------------- one line through W/E halves of a street (alignment pass)
def base_key(k): return _re.sub(r'^(west|east|north|south) ', '', k)
njoint = 0
by_base = collections.defaultdict(list)
for si, st in enumerate(streets):
    if not st['key'].startswith('~'): by_base[base_key(st['key'])].append(si)
for b, idx in by_base.items():
    for a_, b_ in itertools.combinations(idx, 2):
        A, B = streets[a_], streets[b_]
        if A['key'] == B['key']: continue
        best = None
        for ea in (0, -1):
            for eb in (0, -1):
                pa = A['cp'][ea]; pb = B['cp'][eb]
                dd = np.hypot(*(pa - pb))
                if dd < 30 and (best is None or dd < best[0]): best = (dd, ea, eb)
        if not best: continue
        _, ea, eb = best
        ra = A['runs'][ea]; rb = B['runs'][eb]
        Pa = A['cp'][ra[0]:ra[1] + 1]; Pb = B['cp'][rb[0]:rb[1] + 1]
        da = A['fits'][ea][1]; db = B['fits'][eb][1]
        if np.degrees(np.arccos(min(1, abs(da @ db)))) > 3.0: continue
        seg = np.vstack([Pa, Pb]); c, d = tls(seg); dev = np.abs((seg - c) @ np.array([-d[1], d[0]]))
        if dev.max() > TOL_MERGE or np.sqrt((dev ** 2).mean()) > RMS_MERGE: continue
        A['fits'][ea] = (c, d); B['fits'][eb] = (c, d); njoint += 1
print('W/E halves put on one line', njoint)
def polyline(cp, rr, fits):
    """Coordinates of the runs; run ri covers out[bounds[ri][0]:bounds[ri][1] + 1]. Near-parallel runs that do not meet
    within 12 m of the junction vertex get a step at that vertex (the crossing) instead of a tilted link."""
    out = []; bounds = []; nxt = 0
    for ri, ((i, j), (c, d)) in enumerate(zip(rr, fits)):
        start = nxt
        if ri == 0: out.append(c + ((cp[i] - c) @ d) * d)
        if ri < len(rr) - 1:
            c2, d2 = fits[ri + 1]; ang = np.degrees(np.arccos(min(1, abs(d @ d2))))
            x = line_x(c, d, c2, d2) if ang > 3 else None
            if x is None or np.hypot(*(x - cp[j])) > 12:
                p1 = c + ((cp[j] - c) @ d) * d; p2 = c2 + ((cp[j] - c2) @ d2) * d2
                if np.hypot(*(p1 - p2)) < JOG_MIN: x = (p1 + p2) / 2
                else: out.append(p1); bounds.append((start, len(out) - 1)); nxt = len(out) - 1; out.append(p2); continue
            out.append(x)
        else: out.append(c + ((cp[j] - c) @ d) * d)
        bounds.append((start, len(out) - 1)); nxt = len(out) - 1
    # a run that starts after a step begins at the step's first point, so the step is drawn with the next run
    return out, bounds
nwb = 0
for st in streets:
    # split runs (not their lines) where a printed width changes at a crossing
    rr2, f2 = [], []
    for (i, j), f in zip(st['runs'], st['fits']):
        cuts_ = [i] + sorted(m for m in st['wbreak'] if i < m < j) + [j]
        for a_, b_ in zip(cuts_[:-1], cuts_[1:]): rr2.append((a_, b_)); f2.append(f)
        nwb += len(cuts_) - 2
    st['runs'], st['fits'] = rr2, f2
print('runs split at printed width changes', nwb)
for st in streets:
    out, bounds = polyline(st['cp'], st['runs'], st['fits'])
    st['coords'] = [list(map(float, p)) for p in out]; st['bounds'] = bounds
print('streets', len(streets), 'chain splits', dict(nsplit))
# ---------------------------------------------------------------- snap T and L ends onto the street they meet
SK = collections.defaultdict(list)
for si, s in enumerate(streets): SK[s['key']].append(si)
def end_nodes(s, end):
    t = s['tags'][0 if end == 0 else -1]
    return [v[3] for v in t if v[2] == 'node']
snapped = 0
for s in streets:
    for end in (0, -1):
        for n in end_nodes(s, end):
            other = [k for k in n['pair'] if k != s['key']]
            if not other: continue
            cand = [streets[i] for i in SK[other[0]]]
            if not cand: continue
            p = np.array(s['coords'][end]); q = np.array(s['coords'][1 if end == 0 else -2])
            best = None
            for o in cand:
                g = LineString(o['coords'])
                if g.distance(Point(p)) > 15: continue
                d = p - q; d /= np.hypot(*d) + 1e-9
                ray = LineString([q - d * 0.0, p + d * 40]); back = LineString([q, p])
                x = g.intersection(LineString([q, p + d * 40]))
                pts = [x] if x.geom_type == 'Point' else [gg for gg in getattr(x, 'geoms', []) if gg.geom_type == 'Point']
                for pt in pts:
                    dd = np.hypot(pt.x - p[0], pt.y - p[1])
                    if dd < 15 and (best is None or dd < best[0]): best = (dd, (pt.x, pt.y))
            if best:
                ex = np.array(best[1]); d = ex - q; d /= np.hypot(*d) + 1e-9
                s['coords'][end] = list(map(float, ex + d * 0.3)); snapped += 1; break
print('snapped ends', snapped)
# ---------------------------------------------------------------- widths per run
def run_width(s, ri):
    i, j = s['runs'][ri]; sheets = collections.Counter()
    for t in s['tags'][i:j + 1]:
        for v in t:
            if v[2] == 'node': sheets.update(v[3]['sheets'])
            elif v[3]['s'] >= 0: sheets[v[3]['s']] += 1
    # a width printed for this side of a crossing wins ('between' two crossings first)
    if WPOS.get(s['key']):
        mid = s['cp'][i:j + 1].mean(axis=0); hit = {'between': [], 'side': []}
        def at(name):
            ck = ckey(name); q = [s['cp'][m] for m, t in enumerate(s['tags']) for v in t if v[2] == 'node' and any(kk != s['key'] and kbase(kk) == ck for kk in v[3]['pair'])]
            return np.mean(q, axis=0) if q else None
        for sh, f_, c in WPOS[s['key']]:
            if c[0] == 'between':
                q1, q2 = at(c[1]), at(c[2])
                if q1 is not None and q2 is not None:
                    ab = q2 - q1; t_ = (mid - q1) @ ab / (ab @ ab + 1e-9)
                    if 0 < t_ < 1: hit['between'].append((0.0, f_))
                continue
            q = at(c[1])
            if q is None: continue
            ax, sg = {'north': (1, 1), 'south': (1, -1), 'east': (0, 1), 'west': (0, -1)}[c[0]]
            if sg * (mid[ax] - q[ax]) > 2: hit['side'].append((float(np.hypot(*(mid - q))), f_))
        for kind in ('between', 'side'):
            if hit[kind]: return min(hit[kind])[1], 'printed'      # the crossing nearest the run decides
    w = []
    for sh, _ in sheets.most_common(): w += WID.get((sh, s['key']), [])
    if not w: w = WALL.get(s['key'], [])
    if not w and ' | ' in s['key']: w = WALL.get(s['key'].split(' | ')[0], [])
    if w: return collections.Counter(w).most_common(1)[0][0], 'printed'
    return (10.0 if is_alley(s['key']) or s['key'].startswith('~') else 40.0), 'default'
feats = []
for s in streets:
    ws = [run_width(s, ri) for ri in range(len(s['runs']))]
    a = 0
    while a < len(ws):
        b = a
        while b + 1 < len(ws) and ws[b + 1] == ws[a]: b += 1
        coords = s['coords'][s['bounds'][a][0]:s['bounds'][b][1] + 1]
        ft, how = ws[a]
        sheets = sorted({sh for t in s['tags'] for v in t for sh in (v[3]['sheets'] if v[2] == 'node' else [v[3]['s']]) if sh >= 0})
        alley = is_alley(s['key']) or s['key'].startswith('~') or ft <= 20
        feats.append(dict(key=s['key'], name='' if s['key'].startswith('~') else disp(s['key']), coords=coords, ft=ft, how=how,
                          kind='we_alley' if alley else 'we_street', sheets=sheets))
        a = b + 1
# ---------------------------------------------------------------- alley segments
built = [LineString(f['coords']) for f in feats]
from shapely.strtree import STRtree
tree = STRtree(built)
nal = 0; ndup_named = 0
for o in O:
    if o['typ'] != 'alleys': continue
    fr = frame_for(o, (o['y1'] + o['y2']) / 2)
    if not fr: continue
    p1 = np.array(apply(P[fr], o['x1'], o['y1'])); p2 = np.array(apply(P[fr], o['x2'], o['y2']))
    if np.hypot(*(p2 - p1)) < 8: continue
    g = LineString([p1, p2]); k = key2(o['name']) if o.get('name') else None
    dup = False
    for j in tree.query(g.buffer(5)):
        b = built[int(j)]
        if b.buffer(5).intersection(g).length > 0.6 * g.length: dup = True; break
    if not dup and k:
        for j in tree.query(g.buffer(20)):
            if feats[int(j)]['key'] is None or base_of(feats[int(j)]['key']) != base_of(k): continue
            b = built[int(j)]; part = b.intersection(g.buffer(20, cap_style=2))
            if part.is_empty or part.length < 0.6 * g.length: continue
            c_ = np.array(b.coords); db_ = c_[-1] - c_[0]; dg_ = p2 - p1
            if abs(db_ @ dg_) / (np.hypot(*db_) * np.hypot(*dg_) + 1e-9) > 0.985: dup = True; ndup_named += 1; break
    if dup: continue
    d = (p2 - p1) / np.hypot(*(p2 - p1))
    for e, (p, sgn) in enumerate(((p1, -1), (p2, 1))):
        best = None
        for j in tree.query(Point(p).buffer(10)):
            b = built[int(j)]
            if b.distance(Point(p)) > 10: continue
            x = b.intersection(LineString([p - sgn * d * 12, p + sgn * d * 12]))
            pts = [x] if x.geom_type == 'Point' else [gg for gg in getattr(x, 'geoms', []) if gg.geom_type == 'Point']
            for pt in pts:
                dd = np.hypot(pt.x - p[0], pt.y - p[1])
                if best is None or dd < best[0]: best = (dd, np.array([pt.x, pt.y]))
        if best is not None:
            if e == 0: p1 = best[1] - d * 0.3
            else: p2 = best[1] + d * 0.3
    ft = float(o['ft']) if o.get('ft') else 10.0
    feats.append(dict(key=k or f"~{o['s']}~alley", name=o.get('name') or '', coords=[list(p1), list(p2)], ft=ft, how='printed' if o.get('ft') else 'default',
                      kind='we_alley', sheets=[o['s']])); nal += 1
print('alley segments added', nal, 'features', len(feats), '| named duplicates of a built street skipped', ndup_named)
# ---------------------------------------------------------------- streets the OSM check found on the 1904 sheets but missing here (osmchk/additions.json)
import pickle
from shapely.ops import linemerge
COV = pickle.load(open(SP + 'sbg/osmchk/cov.pkl', 'rb'))
ADD = json.load(open(SP + 'sbg/osmchk/additions.json'))
_an = {a['osm'] for a in ADD}; OL = collections.defaultdict(list)
for f in json.load(open(SP + 'basin/osm_basin.geojson'))['features']:
    nm = f['properties'].get('name')
    if nm in _an: OL[nm].append(LineString(f['geometry']['coordinates']))
built = [LineString(f['coords']) for f in feats]; tree = STRtree(built)
def snap_end(p, q):
    # extend the end p (coming from q) up to 15 m onto the nearest built street ahead of it
    d = (p - q) / (np.hypot(*(p - q)) + 1e-9); ray = LineString([p - d * 3, p + d * 15]); best = None
    for j in tree.query(ray):
        x = built[int(j)].intersection(ray)
        for pt in ([x] if x.geom_type == 'Point' else [g for g in getattr(x, 'geoms', []) if g.geom_type == 'Point']):
            dd = np.hypot(pt.x - p[0], pt.y - p[1])
            if best is None or dd < best[0]: best = (dd, np.array([pt.x, pt.y]))
    return best[1] + d * 0.3 if best is not None else p
nadd = 0
for a in ADD:
    reg = MultiPoint([tuple(q) for q in a['pts']]).buffer(10)
    g = unary_union([l.intersection(reg) for l in OL[a['osm']]])
    if not a['opt'].get('nocov'): g = g.intersection(COV)
    g = linemerge(g) if g.geom_type == 'MultiLineString' else g
    for part in getattr(g, 'geoms', [g]):
        if part.geom_type != 'LineString' or part.length < 8: continue
        c = np.array(part.simplify(1.0).coords)
        if a['opt'].get('keep') == 'south':
            if c[0][1] > c[-1][1]: c = c[::-1]
            ln = LineString(c); c = np.array(substring(ln, 0, min(ln.length, a['opt']['m'])).coords) if ln.length > a['opt']['m'] else c
        c[0] = snap_end(c[0], c[1]); c[-1] = snap_end(c[-1], c[-2])
        ft = a['ft']
        if ft is None:
            ws = [f['ft'] for f in feats if f['name'] == a['name'] and f['how'] == 'printed']; ft = collections.Counter(ws).most_common(1)[0][0] if ws else 40.0
        feats.append(dict(key=key2(a['name']) if a['name'] else f"~add~{a['id']}", name=a['name'], coords=[list(map(float, q)) for q in c], ft=float(ft),
                          how={'street': 'printed'}.get(a['src'], a['src']), kind='we_alley' if ft <= 20 else 'we_street', sheets=[], geom_src='OSM, checked on the 1904 sheet', check=a['id']))
        nadd += 1
print('streets added from the OSM check', nadd)
json.dump(dict(feats=feats, nodes=[{k: v for k, v in n.items() if k != 'picks'} for n in nodes]), open(os.path.join(HERE, 'streets_raw.json'), 'w'))
