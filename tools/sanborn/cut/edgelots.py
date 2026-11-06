try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben (17 October): along the former deck edge the lots were jagged and left gaps (the lot lines had followed the traced zigzag, and the
# block clean-up did not reach every block). For every block within 7 m of the traced edge: each lot keeps its shape away from the
# zigzag band; inside the band, and in any gap of the block, land goes to the lot beside it, carried straight on, first on its own side of
# the smoothed edge, then across it. Reads and writes deckpage/plots.json (pre copy fill/plots_preedgelots.json). Marks plots 'edgelots17'.
import json, math, sys, shutil
from shapely.geometry import shape, mapping, LineString, Polygon, MultiPolygon, Point
from shapely.ops import unary_union
S = _ws.DATA
DRY = '--dry' in sys.argv
D = json.load(open(S + 'deckpage/deck.json')); B = json.load(open(S + 'deckpage/basin.json')); P = json.load(open(S + 'deckpage/plots.json'))
if P.get('edgelots17') and not DRY: sys.exit('already done')
LAY = json.load(open(S + 'plots/live/deck/layout.json')); held = set(LAY.get('blocks', {}))
RAW = shape(json.load(open(S + 'fill/deck_outline_raw.json'))['geometry']).buffer(0)
NEW = shape([f for f in D['features'] if f['properties'].get('layer') == 'deck'][0]['geometry']).buffer(0)
EB = RAW.boundary.buffer(7.0); EB2 = RAW.boundary.buffer(3.5)
def clean(g, a=3):
    g = g.buffer(0.05, join_style=2).buffer(-0.05, join_style=2)
    ps = [q for q in getattr(g, 'geoms', [g]) if q.geom_type == 'Polygon' and q.area > a]
    return MultiPolygon(ps) if len(ps) > 1 else (ps[0] if ps else Polygon())
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
PL = {p[0]: p for p in P['plots']}; byb = {}
for p in P['plots']: byb.setdefault(p[1], []).append(p[0])
SIDE = NEW
NB = {}; BFm = {}
for f in D['features'] + B['features']:
    p = f['properties']
    if p.get('layer') != 'block' or not f.get('geometry'): continue
    g = shape(f['geometry']).buffer(0)
    if g.intersects(EB) and g.intersection(EB).area > 5: NB[p['id']] = g; BFm[p['id']] = f
# notches the traced zigzag left in the block outlines (at the street ends of the old edge): closed, within the band, short of the streets
from shapely.geometry import box as _box
ed = LAY.get('streets', {})
def scoords(f): e = ed.get(f['properties']['id'], {}); return e.get('c') or f['geometry']['coordinates']
def swidth(f): e = ed.get(f['properties']['id'], {}); return e.get('w') or f['properties'].get('width_m') or 10
FE = D['features'] + B['features']
corr = unary_union([LineString(scoords(f)).buffer(swidth(f) / 2, cap_style=2) for f in FE if f['properties'].get('layer') == 'street' and not ed.get(f['properties']['id'], {}).get('del') and LineString(scoords(f)).intersects(EB.envelope)])
OCCL = {'rail_open', 'cut_precinct', 'palace', 'forecourt', 'boulevard', 'roundabout', 'cut_square', 'cut_park', 'cut_headhouse', 'cut_plaza', 'cut_lincoln', 'cut_building', 'cut_concourse', 'cut_terrace', 'cut_lawn', 'cut_road', 'dive_cut'}
occ = unary_union([shape(f['geometry']).buffer(0) for f in FE if f['properties'].get('layer') in OCCL and f.get('geometry') and f['geometry']['type'] in ('Polygon', 'MultiPolygon')])
allb = unary_union([shape(f['geometry']).buffer(0) for f in FE if f['properties'].get('layer') == 'block' and f.get('geometry')])
nfill = 0
for k, g in list(NB.items()):
    cand = g.buffer(6, join_style=2, mitre_limit=3).difference(g).intersection(EB).difference(corr.buffer(0.05)).difference(occ).difference(allb.difference(g).buffer(0.1))
    add = unary_union([q for q in getattr(cand, 'geoms', [cand]) if q.geom_type == 'Polygon' and 1 < q.area < 80 and q.distance(g) < 0.3])
    add = clean(add, 1) if not add.is_empty else add
    if add.is_empty: continue
    g2 = clean(g.union(add.buffer(0.05, join_style=2)))
    NB[k] = g2; nfill += add.area
    BFm[k]['geometry'] = json.loads(json.dumps(mapping(g2.simplify(0.02)), default=float)); BFm[k]['properties']['area_m2'] = round(g2.area)
plog = dict(lots=0, lost=[], gap0=0.0, gap1=0.0, held=[])
for keep, nb in NB.items():
    pids = list(byb.get(keep, []))
    before = [(pid, unary_union([dec(a) for a in PL[pid][6]])) for pid in pids]
    gap0 = nb.difference(unary_union([g for _, g in before])).area if before else nb.area
    G = {}
    for pid in pids:
        p = PL[pid]; g = unary_union([dec(a) for a in p[6]])
        core = clean(g.intersection(nb).difference(EB), 1)
        if core.area < 0.25 * g.area: core = clean(g.intersection(nb).difference(EB2), 1)
        if core.area < 0.25 * g.area: core = clean(g.intersection(nb), 1)
        if core.is_empty: PL.pop(pid); plog['lost'].append(pid); continue
        G[pid] = core
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
            pid = f'{keep}-E{sum(1 for x in PL if x.startswith(keep + "-E")) + 1:02d}'; PL[pid] = [pid, keep, 'l', None, None, [], enc(q)]; G[pid] = q
    for pid, g in G.items(): PL[pid][6] = enc(g); plog['lots'] += 1
    gap1 = nb.difference(unary_union(list(G.values()))).area if G else nb.area
    plog['gap0'] += gap0; plog['gap1'] += gap1
    if keep in held: plog['held'].append(keep)
P['plots'] = list(PL.values())
P['edgelots17'] = dict(blocks=len(NB), lots=plog['lots'], lost=plog['lost'], gaps_before_m2=round(plog['gap0']), gaps_after_m2=round(plog['gap1']), held=plog['held'])
P['edgelots17']['notches_m2'] = round(nfill)
if DRY: json.dump(P, open(S + 'cut/prev_plots.json', 'w'))
else:
    for n in ('deck', 'basin'): shutil.copy(S + f'deckpage/{n}.json', S + f'fill/{n}_preedgelots.json')
    json.dump(P, open(S + 'deckpage/plots.json', 'w')); json.dump(D, open(S + 'deckpage/deck.json', 'w')); json.dump(B, open(S + 'deckpage/basin.json', 'w'))
print(json.dumps(P['edgelots17']))
