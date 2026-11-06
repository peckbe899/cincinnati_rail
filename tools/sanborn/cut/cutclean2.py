try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Second half of cutclean (17 October): recut blocks and lots wherever a street or a CUT shape moved. Blocks lose what the new streets and
# CUT shapes cover and take the land the old ones left (to the block it borders most); lots are clipped, and new land joins the lot beside
# it, its side lines carried straight across. Held blocks (saved edits or locks) are only clipped by streets. Writes the data files.
import json, math, sys, shutil
sys.path.insert(0, (_ws.CODE + 'cut'))
import cutclean as C
from shapely.geometry import shape, LineString, Polygon, MultiPolygon, Point, box
from shapely.ops import unary_union, nearest_points
from shapely.strtree import STRtree
S = C.S; D, B, P, LAY, SF, log = C.D, C.B, C.P, C.LAY, C.SF, C.log
DRY = '--dry' in sys.argv
held = set(LAY.get('blocks', {}))
txt = json.dumps(LAY.get('plotOps', [])) + json.dumps(list(LAY.get('plots', {}).keys()))
live_st = {i: f for i, f in SF.items() if not f.get('_drop')}
NEWC = {i: C.corr(f['geometry']['coordinates'], f['properties']['width_m']) for i, f in live_st.items()}
changed = set(C.OLD_ST)
pre = json.load(open(S + 'fill/basin_preez.json'))
laurel = [C.corr(f['geometry']['coordinates'], f['properties']['width_m']) for f in pre['features'] if f['properties'].get('id') in ('SB0817', 'SB0818', 'SB0819')]
CH = unary_union([C.OLD_ST[i].symmetric_difference(NEWC[i]).buffer(-0.25, join_style=2).buffer(0.3, join_style=2) if i in NEWC else C.OLD_ST[i] for i in changed] + laurel + [C.OLD_OCC.symmetric_difference(C.NEW_OCC)]).buffer(0.3, join_style=2)
from shapely.affinity import translate as _tr
sqb = C.to_uv(shape([f for f in D['features'] if f['properties'].get('layer') == 'cut_square'][0]['geometry'])).bounds
ZONE = C.uvpoly([(sqb[0] - 5, -C.HW - 1), (0, -C.HW - 1), (0, C.HW + 1), (sqb[0] - 5, C.HW + 1)])   # the whole CUT strip, square to Freeman
CH = CH.union(ZONE)
reg = CH.envelope.buffer(60)
ALLC = unary_union([g for g in NEWC.values() if g.intersects(reg)])
OCCL = {'rail_open', 'cut_precinct', 'palace', 'forecourt', 'boulevard', 'roundabout', 'cut_square', 'cut_park', 'cut_headhouse', 'cut_plaza', 'cut_lincoln', 'cut_building', 'cut_concourse', 'cut_terrace', 'cut_lawn', 'cut_road', 'dive_cut'}
OCC = unary_union([shape(f['geometry']).buffer(0) for f in D['features'] + B['features'] if not f.get('_drop') and f['properties'].get('layer') in OCCL and f['geometry']['type'] in ('Polygon', 'MultiPolygon') and shape(f['geometry']).intersects(reg)])
BLK = ALLC.intersection(CH).union(OCC)
STB = ALLC.intersection(CH)
BF = {f['properties']['id']: f for f in D['features'] + B['features'] if f['properties'].get('layer') == 'block'}
BG = {k: shape(f['geometry']).buffer(0) for k, f in BF.items()}
hit = [k for k, g in BG.items() if g.intersects(CH)]
def clean(g, a=2):
    g = g.buffer(0.05, join_style=2).buffer(-0.05, join_style=2)
    ps = [q for q in getattr(g, 'geoms', [g]) if q.geom_type == 'Polygon' and q.area > a]
    return MultiPolygon(ps) if len(ps) > 1 else (ps[0] if ps else Polygon())
NB = {}
for k in hit:
    NB[k] = clean(BG[k].difference(ALLC if k in held else BLK))
others = unary_union([g for k, g in BG.items() if k not in NB and g.intersects(reg)] + [g for g in NB.values()])
free = CH.difference(BLK).difference(others.buffer(0.05))
free = clean(free.buffer(-0.4, join_style=2).buffer(0.4, join_style=2), 3)
glog = dict(given=[], new=[], dropped=[])
nfb = max([int(k[2:]) for k in BF if k.startswith('FB')] + [0])
for g in getattr(free, 'geoms', [free]):
    if g.is_empty: continue
    cand = []
    for k in list(NB) + [k for k, h in BG.items() if k not in NB and h.distance(g) < 1]:
        if k in held: continue
        h = NB.get(k, BG[k]); L = h.buffer(0.7).intersection(g).area / 0.7 if h.distance(g) < 0.6 else 0
        if L > 1: cand.append((L, k))
    if cand:
        k = max(cand)[1]
        if k not in NB: NB[k] = BG[k]; hit.append(k)
        NB[k] = clean(NB[k].union(g.buffer(0.08, join_style=2))); glog['given'].append([k, round(g.area)])
    elif g.area > 300 and not g.buffer(-4).is_empty:
        nfb += 1; k = f'FB{nfb:03d}'
        BF[k] = dict(type='Feature', properties=dict(layer='block', id=k, type='building', area_m2=round(g.area), side='fill', name=''), geometry=None); D['features'].append(BF[k])
        NB[k] = clean(g); BG[k] = Polygon(); glog['new'].append([k, round(g.area)])
    else: glog['dropped'].append(round(g.area))
log['blocks'] = dict(changed=len(NB), given=len(glog['given']), given_m2=sum(x[1] for x in glog['given']), new=glog['new'], dropped_m2=round(sum(glog['dropped'])), held_clipped=[k for k in NB if k in held])
# ---------------------------------------------------------------- lots
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
def sweep(p, d):   # p swept along vector d
    parts = [p, Polygon([(x + d[0], y + d[1]) for x, y in p.exterior.coords])]
    c = list(p.exterior.coords)
    for a, b in zip(c, c[1:]): parts.append(Polygon([a, b, (b[0] + d[0], b[1] + d[1]), (a[0] + d[0], a[1] + d[1])]).buffer(0))
    return unary_union(parts)
def into(p, g):   # unit vector from lot p into piece g, across their shared edge
    sh = p.boundary.intersection(g.buffer(0.3))
    segs = [s for s in getattr(sh, 'geoms', [sh]) if s.geom_type == 'LineString' and s.length > 0.3]
    if not segs: return None
    s = max(segs, key=lambda s: s.length); (x0, y0), (x1, y1) = s.coords[0], s.coords[-1]; L = math.hypot(x1 - x0, y1 - y0)
    if L < 0.3: return None
    n = (-(y1 - y0) / L, (x1 - x0) / L); m = s.interpolate(0.5, normalized=True)
    if not g.buffer(0.3).contains(Point(m.x + n[0] * 0.5, m.y + n[1] * 0.5)): n = (-n[0], -n[1])
    return n
PL = {p[0]: p for p in P['plots']}; byb = {}
for p in P['plots']: byb.setdefault(p[1], []).append(p[0])
plog = dict(clipped=0, grown=0, lost=[], lost_in_edits=[], new=[], locked_kept=[])
for k, nb in NB.items():
    if BF[k]['properties'].get('id') in held and LAY['blocks'].get(k, {}).get('lk'): plog['locked_kept'].append(k)
    ids = byb.get(k, []); G = {}
    for pid in ids:
        g = unary_union([dec(a) for a in PL[pid][6]]); g2 = clean(g.intersection(nb), 10)
        if g2.is_empty:
            plog['lost'].append([pid, round(g.area), [round(v) for v in g.centroid.coords[0]]])
            if pid in txt: plog['lost_in_edits'].append(pid)
            PL.pop(pid); continue
        if abs(g2.area - g.area) > 0.5: plog['clipped'] += 1
        G[pid] = g2
    if k in held:
        for pid, g in G.items(): PL[pid][6] = enc(g)
        continue
    rest = nb.difference(unary_union(list(G.values())).buffer(0.05)) if G else nb
    rest = clean(rest.buffer(-0.3, join_style=2).buffer(0.3, join_style=2), 4)
    for piece in getattr(rest, 'geoms', [rest]):
        if piece.is_empty: continue
        nbrs = sorted(((G[pid].distance(piece), pid) for pid in G), key=lambda t: t[0])
        nbrs = [pid for d, pid in nbrs if d < 0.6]
        left = piece
        for pid in sorted(nbrs, key=lambda q: -G[q].buffer(0.4).intersection(piece).area):
            n = into(G[pid], piece)
            if not n: continue
            gain = sweep(G[pid], (n[0] * 80, n[1] * 80)).intersection(left)
            gain = clean(gain, 1)
            if gain.is_empty: continue
            G[pid] = clean(G[pid].union(gain.buffer(0.06, join_style=2)).intersection(nb.buffer(0.01)), 1); left = clean(left.difference(gain.buffer(0.05)), 1)
            plog['grown'] += 1
            if left.is_empty: break
        for q in getattr(left, 'geoms', [left]):
            if q.is_empty or q.area < 1: continue
            best = max(G, key=lambda pid: G[pid].buffer(0.6).intersection(q).area) if G else None
            if best and G[best].buffer(0.6).intersection(q).area > 0.2:
                G[best] = clean(G[best].union(q.buffer(0.06, join_style=2)).intersection(nb.buffer(0.01)), 1)
            elif q.area > 40:
                n = 1
                while f'{k}-C{n:02d}' in PL: n += 1
                pid = f'{k}-C{n:02d}'; PL[pid] = [pid, k, 'l', None, None, [], enc(q)]; G[pid] = q; plog['new'].append(pid)
    for pid, g in G.items(): PL[pid][6] = enc(g)
for k, nb in NB.items():
    BF[k]['geometry'] = C.rg(nb) if not nb.is_empty else None; BF[k]['properties']['area_m2'] = round(nb.area); BF[k]['properties']['clean17'] = True
gone = [k for k, nb in NB.items() if nb.is_empty]
plog['lost_n'] = len(plog['lost'])
log['lots'] = {k: v for k, v in plog.items() if k != 'lost'}; log['blocks']['emptied'] = gone
# ---------------------------------------------------------------- write
def keep(f): return not f.get('_drop') and not (f['properties'].get('layer') == 'block' and f['properties']['id'] in gone)
D['features'] = [f for f in D['features'] if keep(f)]; B['features'] = [f for f in B['features'] if keep(f)]
P['plots'] = [p for p in PL.values() if p[1] not in gone]
D['clean17'] = log
if DRY:
    json.dump(D, open(S + 'cut/prev_deck.json', 'w')); json.dump(B, open(S + 'cut/prev_basin.json', 'w')); json.dump(P, open(S + 'cut/prev_plots.json', 'w'))
else:
    for n in ('deck', 'basin', 'plots'): shutil.copy(S + f'deckpage/{n}.json', S + f'fill/{n}_preclean.json')
    json.dump(D, open(S + 'deckpage/deck.json', 'w')); json.dump(B, open(S + 'deckpage/basin.json', 'w')); json.dump(P, open(S + 'deckpage/plots.json', 'w'))
print(json.dumps({k: log[k] for k in ('blocks', 'lots')}, indent=0)); print(plog['lost'])
