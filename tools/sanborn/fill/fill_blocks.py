try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# 17 October (Ben): fill the street faces that have no block with editable blocks (not divided); the deck outline is no longer a boundary
# for blocks or lots: blocks cut by it are joined across it (and the lots it cut), and land a block stopped short of at the deck edge
# (or any other non-street line) joins that block. Hand-edited or locked blocks (from the saved layout) are left as they are.
# Reads and rewrites deckpage/deck.json, basin.json, plots.json (keeps *_pre copies in fill/). Run after cut1931.py and build_plots.py.
import json, sys, math, numpy as np
from shapely.geometry import shape, mapping, LineString, Polygon, MultiPolygon
from shapely.ops import unary_union, polygonize
from shapely.strtree import STRtree
S = _ws.DATA
D = json.load(open(S + 'deckpage/deck.json')); B = json.load(open(S + 'deckpage/basin.json')); P = json.load(open(S + 'deckpage/plots.json'))
if D.get('fill17'): sys.exit('already filled')
LAY = json.load(open(S + 'plots/live/deck/layout.json'))
held = set(k for k, v in LAY.get('blocks', {}).items())              # any block edit (type, name, use, lock)
txt = json.dumps(LAY.get('plotOps', [])) + json.dumps(list(LAY.get('plots', {}).keys()))
FE = D['features'] + B['features']
for f in FE:
    p = f['properties']
    if p.get('layer') == 'block' and ('"' + p['id'] + '-' in txt or '"' + p['id'] + '.' in txt): held.add(p['id'])
deck = shape([f for f in D['features'] if f['properties']['layer'] == 'deck'][0]['geometry']).buffer(0)
streets = [f for f in FE if f['properties'].get('layer') == 'street']
def ext_line(c, d):                                                  # street ends run on half a width and 3 m, so a street that stops at another closes the face
    c = [tuple(q) for q in c]
    def far(a, b): L = math.dist(a, b); return (b[0] + (b[0] - a[0]) / L * d, b[1] + (b[1] - a[1]) / L * d) if L > 0 else b
    return LineString([far(c[1], c[0])] + c[1:-1] + [far(c[-2], c[-1])]) if len(c) >= 2 else LineString(c)
faces = list(polygonize(unary_union([ext_line(f['geometry']['coordinates'], (f['properties'].get('width_m') or 10) / 2 + 3) for f in streets])))
corrs = [LineString(f['geometry']['coordinates']).buffer((f['properties'].get('width_m') or 10) / 2, cap_style=2) for f in streets]; ct = STRtree(corrs)
BF = {f['properties']['id']: f for f in FE if f['properties'].get('layer') == 'block'}
BG = {k: shape(f['geometry']).buffer(0) for k, f in BF.items()}
bids = list(BG); bt = STRtree([BG[k] for k in bids])
OCC = {'rail_open', 'cut_precinct', 'palace', 'forecourt', 'boulevard', 'roundabout', 'cut_square', 'cut_park', 'cut_headhouse', 'cut_plaza', 'cut_lincoln', 'cut_building', 'cut_concourse', 'cut_terrace', 'cut_lawn', 'cut_road', 'cut_walk', 'dive_cut'}
occs = [shape(f['geometry']).buffer(0) for f in FE if f['properties'].get('layer') in OCC and f['geometry']['type'] in ('Polygon', 'MultiPolygon')]; ot = STRtree(occs)
E0, N0 = P['o']
def dec(a):
    x, y = a[0], a[1]; pts = [(E0 + x / 10, N0 + y / 10)]
    for i in range(2, len(a), 2): x += a[i]; y += a[i + 1]; pts.append((E0 + x / 10, N0 + y / 10))
    return pts
def enc(poly):
    out = []
    for g in getattr(poly, 'geoms', [poly]):
        c = list(g.exterior.coords)[:-1]; q = [(round((x - E0) * 10), round((y - N0) * 10)) for x, y in c]
        a = [q[0][0], q[0][1]]
        for i in range(1, len(q)): a += [q[i][0] - q[i - 1][0], q[i][1] - q[i - 1][1]]
        out.append(a)
    return out
def clean(g):
    g = g.buffer(0.05, join_style=2).buffer(-0.05, join_style=2)
    if g.geom_type == 'MultiPolygon': g = MultiPolygon([p for p in g.geoms if p.area > 5])
    return g
def ring_coords(g):
    if g.geom_type == 'Polygon': return dict(type='Polygon', coordinates=[[[round(x, 2), round(y, 2)] for x, y in g.exterior.coords]])
    return dict(type='MultiPolygon', coordinates=[[[[round(x, 2), round(y, 2)] for x, y in p.exterior.coords]] for p in g.geoms])
PL = {p[0]: p for p in P['plots']}
plots_by_block = {}
for p in P['plots']: plots_by_block.setdefault(p[1], []).append(p[0])
LABI = {l: i for i, l in enumerate(P['labels'])}
log = dict(joined=[], lots_joined=[], extended=[], new=[], skipped_held=[])
# ---- 1. blocks split by the deck edge: join (union-find over pairs sharing 20 m or more of the deck edge)
edge = deck.boundary.buffer(3)
par = {}
def find(a):
    while par.get(a, a) != a: a = par[a]
    return a
removed = set()
for fc in faces:
    inside = [bids[i] for i in bt.query(fc) if BG[bids[i]].intersection(fc).area > 0.5 * BG[bids[i]].area]
    for a in inside:
        for b in inside:
            if a < b and BG[a].buffer(1).intersection(BG[b].buffer(1)).intersection(edge).length > 20:
                if a in held or b in held: log['skipped_held'].append([a, b]); continue
                par[find(a)] = find(b)
groups = {}
for k in list(par):
    groups.setdefault(find(k), set()).add(k)
for r, mem in groups.items():
    mem = sorted(mem | {r}, key=lambda k: -BG[k].area); keep = mem[0]
    U = clean(unary_union([BG[k] for k in mem]))
    for k in mem[1:]:
        removed.add(k)
        for pid in plots_by_block.get(k, []): PL[pid][1] = keep
        plots_by_block.setdefault(keep, []).extend(plots_by_block.pop(k, []))
    BG[keep] = U; BF[keep]['geometry'] = ring_coords(U); BF[keep]['properties']['area_m2'] = round(U.area); BF[keep]['properties']['joined17'] = mem[1:]
    log['joined'].append(mem)
    # lots the deck edge cut: join the pair on each frontage (both lots, under 1,500 m2 each, sharing 5 m or more of the edge)
    lots = [PL[pid] for pid in plots_by_block[keep]]
    geo = {p[0]: unary_union([Polygon(dec(r)) for r in p[6]]).buffer(0) for p in lots}
    used = set()
    for p in lots:
        for q in lots:
            if p[0] >= q[0] or p[0] in used or q[0] in used or p[2] != 'l' or q[2] != 'l': continue
            if p[0].split('-')[0] == q[0].split('-')[0]: continue           # from the same original block: not cut by the edge
            gp, gq = geo[p[0]], geo[q[0]]
            if gp.area > 1500 or gq.area > 1500: continue
            if gp.buffer(0.3).intersection(gq.buffer(0.3)).intersection(edge).length < 5: continue
            u = clean(gp.union(gq))
            if u.geom_type != 'Polygon': continue
            big, small = (p, q) if gp.area >= gq.area else (q, p)
            big[6] = enc(u); big[5] = sorted(set(big[5]) | set(small[5])); used |= {p[0], q[0]}; PL.pop(small[0])
            log['lots_joined'].append([big[0], small[0]])
for k in removed: BF.pop(k)
# ---- 2. land no block covers: join the block it touches (unless held), or a new block; one lot each, not divided
BG = {k: shape(f['geometry']).buffer(0) for k, f in BF.items()}; bids = list(BG); bt = STRtree([BG[k] for k in bids])
nnew = 0
for fc in faces:
    cs = [corrs[i] for i in ct.query(fc)]
    free = fc.difference(unary_union(cs)) if cs else fc
    os_ = [occs[i] for i in ot.query(fc) if occs[i].intersects(fc)]
    if os_: free = free.difference(unary_union(os_).buffer(1.0))
    inside = [bids[i] for i in bt.query(fc) if BG[bids[i]].intersection(fc).area > 0.5 * BG[bids[i]].area]
    rest = free.difference(unary_union([BG[k] for k in inside]).buffer(2.0)) if inside else free
    for g in getattr(rest, 'geoms', [rest]):
        if g.geom_type != 'Polygon' or g.area < 300: continue
        g2 = g.buffer(-1.5).buffer(1.5)
        for h in getattr(g2, 'geoms', [g2]):
            if h.geom_type != 'Polygon' or h.area < 300 or h.buffer(-3).is_empty: continue
            near = sorted(((BG[k].buffer(2.5).intersection(h.buffer(2.5)).length if False else BG[k].distance(h), k) for k in inside), key=lambda t: t[0])
            tgt = next((k for d, k in near if d < 6 and k not in held), None)
            if tgt:
                others = unary_union([BG[k] for k in inside if k != tgt]) if len(inside) > 1 else None
                ext = h.buffer(2.2, join_style=2).intersection(free)
                if others is not None: ext = ext.difference(others.buffer(0.5))
                ext = ext.difference(BG[tgt])
                ext = clean(ext) if not ext.is_empty else ext
                if ext.is_empty or ext.area < 300: continue
                U = clean(BG[tgt].union(ext)); BG[tgt] = U; BF[tgt]['geometry'] = ring_coords(U); BF[tgt]['properties']['area_m2'] = round(U.area)
                BF[tgt]['properties'].setdefault('extended17', 0); BF[tgt]['properties']['extended17'] += round(ext.area)
                n = sum(1 for pid in PL if pid.startswith(tgt + '-F')) + 1; pid = f'{tgt}-F{n:02d}'
                PL[pid] = [pid, tgt, 'l', None, None, [], enc(ext)]; log['extended'].append([tgt, round(ext.area)])
            else:
                nnew += 1; bid = f'FB{nnew:03d}'; hh = clean(h)
                f = dict(type='Feature', properties=dict(layer='block', id=bid, type='building', area_m2=round(hh.area), side='fill', name=''), geometry=ring_coords(hh))
                BF[bid] = f; BG[bid] = hh; PL[bid + '-001'] = [bid + '-001', bid, 'l', None, None, [], enc(hh)]
                log['new'].append([bid, round(hh.area), 'on the deck' if hh.centroid.within(deck) else 'off the deck'])
# ---- write: deck blocks and new blocks to deck.json, basin blocks stay in basin.json
deck_ids = set(f['properties']['id'] for f in D['features'] if f['properties'].get('layer') == 'block')
D['features'] = [f for f in D['features'] if f['properties'].get('layer') != 'block' or f['properties']['id'] in BF] + [BF[k] for k in BF if k.startswith('FB')]
D['features'] = [BF.get(f['properties']['id'], f) if f['properties'].get('layer') == 'block' else f for f in D['features']]
B['features'] = [(BF[f['properties']['id']] if f['properties'].get('layer') == 'block' else f) for f in B['features'] if f['properties'].get('layer') != 'block' or f['properties']['id'] in BF]
P['plots'] = list(PL.values())
D['fill17'] = dict(joined=len(log['joined']), lots_joined=len(log['lots_joined']), extended=len(log['extended']), new=len(log['new']))
json.dump(D, open(S + 'deckpage/deck.json', 'w')); json.dump(B, open(S + 'deckpage/basin.json', 'w')); json.dump(P, open(S + 'deckpage/plots.json', 'w'))
json.dump(log, open(S + 'fill/fill_log.json', 'w'), indent=0)
print(D['fill17'], 'skipped (hand-edited)', log['skipped_held'], 'new area', sum(x[1] for x in log['new']), 'extended area', sum(x[1] for x in log['extended']))
