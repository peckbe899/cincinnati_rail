try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben (17 October): Ezzard Charles Drive replaces Laurel, widened in place on its modern line (OSM), Freeman to Music Hall (Central Parkway).
# Widths are drawing values from the modern road: divided boulevard Freeman to Baymiller, four to five lanes to Central Avenue, two to three
# lanes on to Music Hall. Blocks and lots along it lose the land the wider street takes. Marks basin.json 'ezzard17'; will not run twice.
import json, sys
from shapely.geometry import shape, mapping, LineString, Polygon, MultiPolygon
from shapely.ops import unary_union
S = _ws.DATA
B = json.load(open(S + 'deckpage/basin.json')); P = json.load(open(S + 'deckpage/plots.json'))
if B.get('ezzard17'): sys.exit('already done')
LAY = json.load(open(S + 'plots/live/deck/layout.json'))
held = set(LAY.get('blocks', {}))
SEG = [('EZ1', 'Ezzard Charles Drive (Freeman to Baymiller)', 45.72, [(713375, 4331838), (713455, 4331835), (713530, 4331830)]),
       ('EZ2', 'Ezzard Charles Drive (Baymiller to Central Avenue)', 24.38, [(713530, 4331830), (713581, 4331825), (713761, 4331815), (713948, 4331807), (714153, 4331796)]),
       ('EZ3', 'Ezzard Charles Drive (Central Avenue to Music Hall)', 18.29, [(714153, 4331796), (714211, 4331798), (714296, 4331801), (714373, 4331818), (714416, 4331828), (714435, 4331839)])]
GONE = {'SB0817', 'SB0818', 'SB0819'}
assert not GONE & set(LAY.get('streets', {})), 'Laurel has saved edits'
corr = unary_union([LineString(c).buffer(w / 2, cap_style=2, join_style=1) for _, _, w, c in SEG] + [LineString(c[:1] + c[:1]).buffer(0) for _, _, _, c in SEG])
B['features'] = [f for f in B['features'] if f['properties'].get('id') not in GONE]
for sid, nm, w, c in SEG:
    B['features'].append(dict(type='Feature', properties=dict(layer='street', id=sid, name=nm, kind='we_street', width_m=w, width_ft=round(w / 0.3048), width_src='drawing value, modern Ezzard Charles Drive (17 October)',
                                                           src='OSM (modern Ezzard Charles Drive)', geom_src='OSM centre line, replacing Laurel (SB0817-SB0819)'), geometry=dict(type='LineString', coordinates=[list(q) for q in c])))
E0, N0 = P['o']
def dec(a):
    x, y = a[0], a[1]; pts = [(E0 + x / 10, N0 + y / 10)]
    for i in range(2, len(a), 2): x += a[i]; y += a[i + 1]; pts.append((E0 + x / 10, N0 + y / 10))
    return Polygon(pts).buffer(0)
def enc(poly):
    c = list(poly.exterior.coords)[:-1]; q = [(round((x - E0) * 10), round((y - N0) * 10)) for x, y in c]; a = [q[0][0], q[0][1]]
    for i in range(1, len(q)): a += [q[i][0] - q[i - 1][0], q[i][1] - q[i - 1][1]]
    return a
r = lambda g: json.loads(json.dumps(mapping(g.simplify(0.05)), default=float))
hit_blocks, held_hit = [], []
for f in B['features']:
    p = f['properties']
    if p.get('layer') != 'block': continue
    g = shape(f['geometry']).buffer(0)
    if not g.intersects(corr) or g.intersection(corr).area < 1: continue
    if p['id'] in held: held_hit.append(p['id'])
    g2 = g.difference(corr).buffer(0)
    g2 = MultiPolygon([q for q in getattr(g2, 'geoms', [g2]) if q.area > 20]) if g2.geom_type == 'MultiPolygon' else g2
    if g2.is_empty: continue
    if g2.geom_type == 'MultiPolygon' and len(g2.geoms) == 1: g2 = g2.geoms[0]
    f['geometry'] = r(g2); p['area_m2'] = round(g2.area); p['ezzard17'] = round(g.area - g2.area); hit_blocks.append(p['id'])
lost, cut, keep = [], 0, []
for pl in P['plots']:
    if pl[1] not in hit_blocks: keep.append(pl); continue
    g = unary_union([dec(a) for a in pl[6]])
    if not g.intersects(corr): keep.append(pl); continue
    g2 = g.difference(corr).buffer(0)
    parts = [q for q in getattr(g2, 'geoms', [g2]) if q.geom_type == 'Polygon' and q.area > 15]
    if not parts: lost.append(pl[0]); continue
    pl[6] = [enc(max(parts, key=lambda q: q.area))]; cut += 1; keep.append(pl)
txt = json.dumps(LAY.get('plotOps', [])) + json.dumps(list(LAY.get('plots', {})))
P['plots'] = keep
B['ezzard17'] = dict(blocks=len(hit_blocks), lots_lost=len(lost), lots_cut=cut, held_touched=held_hit, lost_in_edits=[x for x in lost if x in txt], area=round(sum(1 for _ in [])))
json.dump(B, open(S + 'deckpage/basin.json', 'w')); json.dump(P, open(S + 'deckpage/plots.json', 'w'))
print(B['ezzard17'], 'taken m2', sum(f['properties'].get('ezzard17', 0) for f in B['features'] if f['properties'].get('layer') == 'block'))
