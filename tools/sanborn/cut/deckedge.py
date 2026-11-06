try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben (17 October): problems at the former deck edge. The deck outline was traced off the Sanborn sheets' zigzag edge symbol on a 2 m grid,
# so it zigzags (about 7 m steps, 2-6 m either side of the real line), and blocks still followed it: held blocks the fill step could not
# join (B026/SBB1037, B027 with the sliver FB005 beside it) and slivers it left. Here: the outline is smoothed onto the middle of the
# zigzag; in each street face, blocks that meet across the old edge are joined and the slivers along it go to the block beside them;
# lots keep their shape away from the edge and are carried straight across the zigzag band (an empty fill lot is shared out the same way).
# Reads and writes deckpage/deck.json, basin.json, plots.json (pre copies fill/*_predeckedge.json). Marks deck.json 'edge17'.
import json, math, sys, shutil, numpy as np
from shapely.geometry import shape, mapping, LineString, Polygon, MultiPolygon, Point
from shapely.ops import unary_union, polygonize
from shapely.strtree import STRtree
S = _ws.DATA
DRY = '--dry' in sys.argv
D = json.load(open(S + 'deckpage/deck.json')); B = json.load(open(S + 'deckpage/basin.json')); P = json.load(open(S + 'deckpage/plots.json'))
if D.get('edge17'): sys.exit('already done')
LAY = json.load(open(S + 'plots/live/deck/layout.json')); held = set(LAY.get('blocks', {})); txt = json.dumps(LAY.get('plotOps', [])) + json.dumps(list(LAY.get('plots', {}).keys()))
DF = [f for f in D['features'] if f['properties'].get('layer') == 'deck'][0]
OLD = shape(DF['geometry']).buffer(0)
# ---------------------------------------------------------------- 1. smooth the outline (Gaussian along each ring, sigma 6 m)
def smooth_ring(coords, sig=6.0):
    r = LineString(coords); n = max(int(r.length), 8); pts = np.array([r.interpolate(i * r.length / n).coords[0] for i in range(n)])
    k = int(3 * sig); w = np.exp(-0.5 * (np.arange(-k, k + 1) / sig) ** 2); w /= w.sum()
    ext = np.vstack([pts[-k:], pts, pts[:k]]); sm = np.column_stack([np.convolve(ext[:, j], w, mode='valid') for j in (0, 1)])
    return Polygon(sm).simplify(0.25)
polys = []
for g in OLD.geoms:
    ext = smooth_ring(list(g.exterior.coords)[:-1]); holes = [smooth_ring(list(i.coords)[:-1]) for i in g.interiors]
    polys.append(Polygon(ext.exterior.coords, [h.exterior.coords for h in holes]).buffer(0))
NEW = MultiPolygon(polys)
dev = max(Point(p).distance(NEW.boundary) for g in OLD.geoms for p in g.exterior.coords)
DF['geometry'] = json.loads(json.dumps(mapping(NEW), default=float)); DF['properties']['note'] = 'smoothed onto the middle of the traced zigzag (17 October)'
json.dump(dict(type='Feature', properties=dict(layer='deck_raw'), geometry=mapping(OLD)), open(S + 'fill/deck_outline_raw.json', 'w'), default=float)
EB = OLD.boundary.buffer(7.0)                      # the zigzag band
# ---------------------------------------------------------------- 2. faces, corridors, occupied land
FE = D['features'] + B['features']
ed = LAY.get('streets', {})
def scoords(f):
    e = ed.get(f['properties']['id'], {}); return e.get('c') or f['geometry']['coordinates']
def swidth(f):
    e = ed.get(f['properties']['id'], {}); return e.get('w') or f['properties'].get('width_m') or 10
streets = [f for f in FE if f['properties'].get('layer') == 'street' and not ed.get(f['properties']['id'], {}).get('del')]
def ext_line(c, d):
    c = [tuple(q) for q in c]
    def far(a, b): L = math.dist(a, b); return (b[0] + (b[0] - a[0]) / L * d, b[1] + (b[1] - a[1]) / L * d) if L > 0 else b
    return LineString([far(c[1], c[0])] + c[1:-1] + [far(c[-2], c[-1])])
faces = list(polygonize(unary_union([ext_line(scoords(f), swidth(f) / 2 + 3) for f in streets])))
corr = unary_union([LineString(scoords(f)).buffer(swidth(f) / 2, cap_style=2) for f in streets if LineString(scoords(f)).intersects(EB.envelope)])
OCCL = {'rail_open', 'cut_precinct', 'palace', 'forecourt', 'boulevard', 'roundabout', 'cut_square', 'cut_park', 'cut_headhouse', 'cut_plaza', 'cut_lincoln', 'cut_building', 'cut_concourse', 'cut_terrace', 'cut_lawn', 'cut_road', 'dive_cut'}
occ = unary_union([shape(f['geometry']).buffer(0) for f in FE if f['properties'].get('layer') in OCCL and f.get('geometry') and f['geometry']['type'] in ('Polygon', 'MultiPolygon')])
BF = {f['properties']['id']: f for f in FE if f['properties'].get('layer') == 'block' and f.get('geometry')}
BG = {k: shape(f['geometry']).buffer(0) for k, f in BF.items()}
ids = list(BG); bt = STRtree([BG[k] for k in ids])
def clean(g, a=3):
    g = g.buffer(0.05, join_style=2).buffer(-0.05, join_style=2)
    ps = [q for q in getattr(g, 'geoms', [g]) if q.geom_type == 'Polygon' and q.area > a]
    return MultiPolygon(ps) if len(ps) > 1 else (ps[0] if ps else Polygon())
# ---------------------------------------------------------------- 3. per face: join across the old edge, take the slivers
par = {}
def find(a):
    while par.get(a, a) != a: a = par[a]
    return a
grow = {}; TR = []; SPL = []; log = dict(joined=[], slivers=[], held_touched=set(), moved=[])
for fc in faces:
    if not fc.intersects(EB): continue
    inside = [ids[i] for i in bt.query(fc) if BG[ids[i]].intersection(fc).area > 0.5 * BG[ids[i]].area]
    touch = [k for k in inside if BG[k].boundary.intersection(EB).length > 5]
    if not touch: continue
    for a in touch:
        for b in touch:
            if a < b and BG[a].geom_type == BG[b].geom_type == 'Polygon' and min(BG[a].intersection(fc).area / BG[a].area, BG[b].intersection(fc).area / BG[b].area) > 0.8 and BG[a].distance(BG[b]) < 3 and BG[a].buffer(2).intersection(BG[b].buffer(2)).intersection(EB).area > 15:
                par[find(a)] = find(b)
    anyb = [ids[i] for i in bt.query(fc) if BG[ids[i]].intersection(fc).area > 20 and BG[ids[i]].intersection(fc).boundary.intersection(EB).length > 5]
    for a in touch:      # a block reaching into this face across the old edge: the piece here goes to the block that holds the face
        for b in anyb:
            if a == b or BG[a].geom_type != 'Polygon': continue
            fa, fb = BG[a].intersection(fc).area / BG[a].area, BG[b].intersection(fc).area / max(BG[b].area, 1)
            if fa > 0.8 and fb < 0.5:
                pc = BG[b].intersection(fc)
                if b in held or ('"' + b + '-') in txt:   # held or with saved lot edits: both blocks stay, the line between them is set on the smoothed edge
                    if not any(x[0] == b and x[1] == a for x in log.setdefault('left_held', [])): log['left_held'].append([b, a, round(pc.area)]); SPL.append((b, a, fc))
                    continue
                if pc.area > 20 and (pc.area < 3500 or pc.intersection(EB).area > 0.5 * pc.area) and BG[a].distance(pc) < 3 and BG[a].buffer(2).intersection(pc.buffer(2)).intersection(EB).area > 15:
                    TR.append((b, a, pc))
    free = fc.difference(corr).difference(occ.buffer(0.5)).difference(unary_union([BG[k] for k in inside]))
    for q in getattr(free, 'geoms', [free]):
        if q.geom_type != 'Polygon' or q.area < 2 or not q.intersects(EB): continue
        if q.area > 400 and q.intersection(EB).area < 0.6 * q.area: continue          # real open land, not a sliver of the zigzag
        near = sorted((BG[k].distance(q), -BG[k].buffer(1.5).intersection(q).area, k) for k in touch)
        if near and near[0][0] < 2.5: grow.setdefault(near[0][2], []).append(q); log['slivers'].append([near[0][2], round(q.area)])
for b, a, fc in SPL:   # straighten the shared line inside the zigzag band
    U = unary_union([BG[a].intersection(fc), BG[b].intersection(fc)]).buffer(1.6, join_style=2).buffer(-1.6, join_style=2)
    band = U.intersection(EB); sa = BG[a].intersection(fc).difference(EB).representative_point().within(NEW)
    sideA = band.intersection(NEW) if sa else band.difference(NEW); sideB = band.difference(sideA)
    na = unary_union([BG[a].intersection(fc).difference(EB), sideA]); nb_ = unary_union([BG[b].intersection(fc).difference(EB), sideB])
    BG[a] = clean(unary_union([BG[a].difference(fc), na])); BG[b] = clean(unary_union([BG[b].difference(fc), nb_]))
MOVED = {}                                                       # lot id -> new block
for b, a, pc in TR:
    BG[b] = clean(BG[b].difference(pc.buffer(0.05))); grow.setdefault(a, []).append(pc); log['moved'].append([b, a, round(pc.area)])
groups = {}
for k in list(par): groups.setdefault(find(k), set()).add(k)
for r in list(groups): groups[r].add(r)
merged = {}                                                     # kept id -> member ids
for r, mem in groups.items():
    mem = sorted(mem, key=lambda k: (k.startswith('FB'), k not in held, -BG[k].area)); merged[mem[0]] = mem
for k in grow:
    r = find(k); keep = next((kk for kk, m in merged.items() if r in m or k in m), None)
    if keep is None: merged[k] = [k]
for b, a, pc in TR:
    if not any(b in m for m in merged.values()): merged[b] = [b]
for b, a, fc in SPL:
    for k in (a, b):
        if not any(k in m for m in merged.values()): merged[k] = [k]
NB = {}
for keep, mem in merged.items():
    extra = [q for k in mem for q in grow.get(k, [])]
    U = unary_union([BG[k] for k in mem] + [q.buffer(0.05) for q in extra])
    U = U.buffer(1.6, join_style=2).buffer(-1.6, join_style=2)          # closes the zigzag gaps between the joined pieces
    U = clean(U.difference(corr.union(occ).intersection(EB.buffer(3))))       # only along the old edge; elsewhere the block keeps its shape
    U = clean(unary_union([U.intersection(EB.buffer(3))] + [BG[k].difference(EB.buffer(3)) for k in mem] + [q.difference(EB.buffer(3)) for q in extra]))
    NB[keep] = U; log['joined'].append(mem) if len(mem) > 1 else None
    log['held_touched'] |= {k for k in mem if k in held}
# ---------------------------------------------------------------- 4. lots: away from the band unchanged, carried straight across it
E0, N0 = P['o']
def dec(a):
    x, y = a[0], a[1]; pts = [(E0 + x / 10, N0 + y / 10)]
    for i in range(2, len(a), 2): x += a[i]; y += a[i + 1]; pts.append((E0 + x / 10, N0 + y / 10))
    return Polygon(pts).buffer(0)
def enc(poly):
    out = []
    for g in getattr(poly, 'geoms', [poly]):
        c = list(g.exterior.coords)[:-1]; q = [(round((x - E0) * 10), round((y - N0) * 10)) for x, y in c]; a = [q[0][0], q[0][1]]
        for i in range(1, len(q)): a += [q[i][0] - q[i - 1][0], q[i][1] - q[i - 1][1]]
        out.append(a)
    return out
def sweep(p, d):
    parts = [p]
    for g in getattr(p, 'geoms', [p]):
        c = list(g.exterior.coords); parts.append(Polygon([(x + d[0], y + d[1]) for x, y in c]))
        for a, b in zip(c, c[1:]): parts.append(Polygon([a, b, (b[0] + d[0], b[1] + d[1]), (a[0] + d[0], a[1] + d[1])]).buffer(0))
    return unary_union(parts)
def into(p, g):
    sh = p.boundary.intersection(g.buffer(0.3)); segs = [s for s in getattr(sh, 'geoms', [sh]) if s.geom_type == 'LineString' and s.length > 0.3]
    if not segs: return None
    s = max(segs, key=lambda s: s.length); (x0, y0), (x1, y1) = s.coords[0], s.coords[-1]; L = math.hypot(x1 - x0, y1 - y0)
    if L < 0.3: return None
    n = (-(y1 - y0) / L, (x1 - x0) / L); m = s.interpolate(0.5, normalized=True)
    if not g.buffer(0.3).contains(Point(m.x + n[0] * 0.5, m.y + n[1] * 0.5)): n = (-n[0], -n[1])
    return n
txt = json.dumps(LAY.get('plotOps', [])) + json.dumps(list(LAY.get('plots', {}).keys()))
PL = {p[0]: p for p in P['plots']}; byb = {}
for p in P['plots']: byb.setdefault(p[1], []).append(p[0])
SIDE = NEW.buffer(0)
for b_, a_, pc in TR:
    kk = next(k for k, m in merged.items() if a_ in m)
    for pid in byb.get(b_, []):
        if unary_union([dec(x) for x in PL[pid][6]]).representative_point().within(pc.buffer(0.5)): MOVED[pid] = kk
plog = dict(dropped_fill_lots=[], lots=0, lost=[])
for keep, nb in NB.items():
    mem = merged[keep]; pids = [pid for k in mem for pid in byb.get(k, []) if MOVED.get(pid, keep) == keep] + [pid for pid, kk in MOVED.items() if kk == keep]
    pids = list(dict.fromkeys(pids))
    G = {}
    for pid in pids:
        p = PL[pid]; g = unary_union([dec(a) for a in p[6]])
        if p[1].startswith('FB') and len(byb.get(p[1], [])) == 1 and not p[5] and pid not in txt: plog['dropped_fill_lots'].append(pid); PL.pop(pid); continue
        core = clean(g.intersection(nb).difference(EB), 1)
        if core.is_empty: core = clean(g.intersection(nb), 1)
        if core.is_empty: PL.pop(pid); plog['lost'].append(pid); continue
        G[pid] = core; p[1] = keep
    rest = clean(nb.difference(unary_union(list(G.values())).buffer(0.05)) if G else nb, 1)
    for pass_ in (0, 1):
        pieces = []
        for piece in getattr(rest, 'geoms', [rest]):
            if piece.is_empty: continue
            pieces += [piece.intersection(SIDE), piece.difference(SIDE)] if pass_ == 0 else [piece]
        left_all = []
        for piece in pieces:
            piece = clean(piece, 0.5)
            if piece.is_empty: continue
            for pc in getattr(piece, 'geoms', [piece]):
                side_in = pc.representative_point().within(SIDE)
                nbrs = [pid for pid in G if G[pid].distance(pc) < 0.6 and (pass_ == 1 or (G[pid].representative_point().within(SIDE) == side_in))]
                left = pc
                for pid in sorted(nbrs, key=lambda q: -G[q].buffer(0.4).intersection(pc).area):
                    n = into(G[pid], left)
                    if not n: continue
                    gain = clean(sweep(G[pid], (n[0] * 60, n[1] * 60)).intersection(left), 0.5)
                    if gain.is_empty: continue
                    G[pid] = clean(G[pid].union(gain.buffer(0.06, join_style=2)).intersection(nb.buffer(0.01)), 1); left = clean(left.difference(gain.buffer(0.05)), 0.5)
                    if left.is_empty: break
                if not left.is_empty: left_all.append(left)
        rest = unary_union(left_all) if left_all else Polygon()
    for q in getattr(rest, 'geoms', [rest]):
        if q.is_empty or q.area < 0.5: continue
        best = max(G, key=lambda pid: G[pid].buffer(0.6).intersection(q).area) if G else None
        if best: G[best] = clean(G[best].union(q.buffer(0.06, join_style=2)).intersection(nb.buffer(0.01)), 1)
        elif q.area > 40:
            pid = f'{keep}-E01'; PL[pid] = [pid, keep, 'l', None, None, [], enc(q)]; G[pid] = q
    for pid, g in G.items(): PL[pid][6] = enc(g); plog['lots'] += 1
# ---------------------------------------------------------------- write
gone = {k for mem in merged.values() for k in mem[1:]}
def rg(g): return json.loads(json.dumps(mapping(g.simplify(0.02)), default=float))
for keep, nb in NB.items():
    BF[keep]['geometry'] = rg(nb); BF[keep]['properties']['area_m2'] = round(nb.area); BF[keep]['properties']['edge17'] = merged[keep][1:]
keepf = lambda f: not (f['properties'].get('layer') == 'block' and f['properties'].get('id') in gone)
D['features'] = [f for f in D['features'] if keepf(f)]; B['features'] = [f for f in B['features'] if keepf(f)]
P['plots'] = [p for p in PL.values() if p[1] not in gone]
log = dict(outline_shift_max=round(dev, 1), blocks_changed=len(NB), joined=log['joined'], moved=log['moved'], left_held=log.get('left_held', []), slivers=len(log['slivers']), sliver_m2=round(sum(x[1] for x in log['slivers'])),
           held_touched=sorted(log['held_touched']), fill_lots_shared=len(plog['dropped_fill_lots']), lots_redrawn=plog['lots'], lots_lost=plog['lost'], lost_in_edits=[x for x in plog['lost'] if x in txt])
D['edge17'] = log
pre = 'cut/prev_' if DRY else 'deckpage/'
if not DRY:
    for n in ('deck', 'basin', 'plots'): shutil.copy(S + f'deckpage/{n}.json', S + f'fill/{n}_predeckedge.json')
json.dump(D, open(S + pre + 'deck.json', 'w')); json.dump(B, open(S + pre + 'basin.json', 'w')); json.dump(P, open(S + pre + 'plots.json', 'w'))
print(json.dumps(log))
