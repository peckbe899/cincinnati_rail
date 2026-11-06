try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Clean the generated plots (clip to their block, fix invalid rings, explode), read the Sanborn use labels onto them,
# and write the page file deckpage/plots.json.
#   plots.json = {o: [E0, N0], labels: [text...], plots: [[id, block, kind, street, u0, [label idx...], [ring, ...]], ...]}
#   ring = delta-encoded integer decimetres from o: [x0, y0, dx1, dy1, ...]
import sys, json, glob, re, collections
sys.path.insert(0, (_ws.CODE + 'plots'))
from common import load_layers, SP
from shapely.geometry import Polygon, Point
from shapely.strtree import STRtree
from shapely.ops import unary_union

blocks = load_layers()[0]
BG = {b['id']: b['g'].buffer(0) for b in blocks}
P = json.load(open(SP + 'plots/plots_all.json'))['plots']

def parts(g):
    if g.is_empty: return []
    if g.geom_type == 'Polygon': return [g]
    if g.geom_type in ('MultiPolygon', 'GeometryCollection'): return [q for x in g.geoms for q in parts(x)]
    return []

clean = []; nfix = 0; nsplit = 0
for p in P:
    g = Polygon(p['c'])
    if not g.is_valid: g = g.buffer(0); nfix += 1
    g = g.intersection(BG[p['block']])
    ps = [q for q in parts(g) if q.area >= 2.0]
    if not ps: continue
    ps.sort(key=lambda q: -q.area)
    if len(ps) > 1: nsplit += 1
    for k, q in enumerate(ps):
        q = q.simplify(0.05)
        if q.is_empty or not q.is_valid: q = q.buffer(0)
        for qq in parts(q):
            clean.append(dict(id=p['id'] + ('' if k == 0 else '~' + 'abcdefghijklmnop'[k - 1]), block=p['block'], kind=p['kind'], street=p['street'], g=qq))
            break
print('plots', len(P), '->', len(clean), 'fixed', nfix, 'split', nsplit)

# ---------------------------------------------------------------- labels
man = {m['id']: m for m in json.load(open(SP + 'plots/crops/manifest.json'))}
L = []
for f in sorted(glob.glob(SP + 'plots/labels/agent_*.json')): L += json.load(open(f))
DROP = re.compile(r'^(autos?\.?|auto ho\.?|auto house|private garage|pvt\.? garage|garage \(private\)|shed|coal|stable|privy)$', re.I)
PARK = re.compile(r'(auto|car|motor)s? park', re.I)
USE = {'religious': 'w', 'civic': 'v', 'industrial': 'i', 'commercial': 'c'}
pts = []
for e in L:
    t = re.sub(r'\s+', ' ', str(e.get('text', '')).strip())
    if not t or DROP.match(t) or e.get('use') not in USE: continue
    m = man[e['crop']]; X = m['X0'] + float(e['x']); Y = m['Y1'] - float(e['y'])
    u = 'p' if PARK.search(t) else USE[e['use']]
    pts.append((X, Y, t, u))
# de-duplicate labels read twice from neighbouring crops
norm = lambda t: re.sub(r'[^a-z0-9]', '', t.lower())
keep = []; grid = collections.defaultdict(list)
for X, Y, t, u in pts:
    k = (int(X // 10), int(Y // 10)); dup = False
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for j in grid[(k[0] + dx, k[1] + dy)]:
                q = keep[j]
                if norm(q[2]) == norm(t) and (q[0] - X) ** 2 + (q[1] - Y) ** 2 < 64: dup = True
    if not dup: grid[k].append(len(keep)); keep.append((X, Y, t, u))
print('labels', len(L), 'kept', len(pts), 'after de-dup', len(keep))

tree = STRtree([c['g'] for c in clean])
hits = collections.defaultdict(list); nin = nnear = nmiss = 0
for X, Y, t, u in keep:
    pt = Point(X, Y); best = None
    for i in tree.query(pt):
        if clean[i]['g'].contains(pt): best = i; break
    if best is None:
        bd = 5.0
        for i in tree.query(pt.buffer(5.0)):
            d = clean[i]['g'].distance(pt)
            if d < bd: bd = d; best = i
        if best is None: nmiss += 1; continue
        nnear += 1
    else: nin += 1
    hits[best].append((t, u))
print('labels in a plot', nin, 'within 5 m', nnear, 'off any plot', nmiss)

PRI = {'w': 4, 'v': 3, 'i': 2, 'c': 1, 'p': 0}
texts = []; tix = {}
def ti(t):
    if t not in tix: tix[t] = len(texts); texts.append(t)
    return tix[t]
nset = collections.Counter()
for i, c in enumerate(clean):
    h = hits.get(i)
    if not h: c['u0'] = None; c['lab'] = []; continue
    cnt = collections.Counter(u for _, u in h)
    c['u0'] = max(cnt, key=lambda u: (cnt[u], PRI[u])); nset[c['u0']] += 1
    c['lab'] = [ti(t) for t in dict.fromkeys(t for t, _ in h)][:6]
print('plots prefilled', sum(nset.values()), dict(nset))

# ---------------------------------------------------------------- write
E0 = int(min(c['g'].bounds[0] for c in clean)) // 100 * 100; N0 = int(min(c['g'].bounds[1] for c in clean)) // 100 * 100
def enc(ring):
    xs = [(round((x - E0) * 10), round((y - N0) * 10)) for x, y in ring.coords[:-1]]
    out = [xs[0][0], xs[0][1]]
    for a, b in zip(xs, xs[1:]):
        if b == a: continue
        out += [b[0] - a[0], b[1] - a[1]]
    return out
rows = []
for c in clean:
    g = c['g']
    if not g.exterior.is_ccw: g = Polygon(g.exterior.coords[::-1], [r.coords for r in g.interiors])
    rings = [enc(g.exterior)] + [enc(r) for r in g.interiors]
    rows.append([c['id'], c['block'], c['kind'][0], c['street'], c['u0'], c['lab'], rings])
json.dump(dict(o=[E0, N0], labels=texts, plots=rows), open(SP + 'deckpage/plots.json', 'w'), separators=(',', ':'))
import os; print('plots.json', os.path.getsize(SP + 'deckpage/plots.json') // 1024, 'KB')
