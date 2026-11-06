try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, numpy as np, pickle
from shapely.geometry import shape, LineString, Polygon
from shapely.ops import unary_union, polygonize
from shapely.strtree import STRtree
S = _ws.DATA
D = json.load(open(S + 'deckpage/deck.json')); B = json.load(open(S + 'deckpage/basin.json'))
FE = D['features'] + B['features']
deck = shape([f for f in D['features'] if f['properties']['layer'] == 'deck'][0]['geometry']).buffer(0)
streets = [f for f in FE if f['properties'].get('layer') == 'street']
net = unary_union([LineString(f['geometry']['coordinates']) for f in streets])
faces = list(polygonize(net))
corrs = [LineString(f['geometry']['coordinates']).buffer((f['properties'].get('width_m') or 10) / 2, cap_style=2) for f in streets]
ct = STRtree(corrs)
blocks = [(f['properties']['id'], shape(f['geometry']).buffer(0), f['properties']) for f in FE if f['properties'].get('layer') == 'block']
bt = STRtree([b[1] for b in blocks])
OCC = {'rail_open', 'cut_precinct', 'palace', 'forecourt', 'boulevard', 'roundabout', 'cut_square', 'cut_park', 'cut_headhouse', 'cut_plaza', 'cut_lincoln', 'cut_building', 'cut_concourse', 'cut_terrace', 'cut_lawn', 'cut_road', 'cut_walk', 'dive_cut'}
occs = [shape(f['geometry']).buffer(0) for f in FE if f['properties'].get('layer') in OCC and f['geometry']['type'] in ('Polygon', 'MultiPolygon')]
ot = STRtree(occs)
out = []
for fi, fc in enumerate(faces):
    cs = [corrs[i] for i in ct.query(fc)]
    rest = fc.difference(unary_union(cs)) if cs else fc
    os_ = [occs[i] for i in ot.query(fc) if occs[i].intersects(fc)]
    if os_: rest = rest.difference(unary_union(os_).buffer(2.0))
    bi = [i for i in bt.query(fc) if blocks[i][1].intersection(fc).area > 0.5 * blocks[i][1].area]
    if bi: rest = rest.difference(unary_union([blocks[i][1] for i in bi]).buffer(2.0))
    pcs = []
    for g in getattr(rest, 'geoms', [rest]):
        if g.geom_type != 'Polygon' or g.area < 300: continue
        g2 = g.buffer(-1.5).buffer(1.5)
        for h in getattr(g2, 'geoms', [g2]):
            if h.geom_type == 'Polygon' and h.area >= 300: pcs.append(h)
    deck_split = len(bi) >= 2 and any(blocks[a][1].buffer(1).intersection(blocks[b][1].buffer(1)).intersection(deck.boundary.buffer(3)).length > 20 for a in bi for b in bi if a < b)
    if pcs or deck_split:
        out.append(dict(face=fi, blocks=[blocks[i][0] for i in bi], sides=[blocks[i][2].get('side') for i in bi], deck_split=bool(deck_split),
                        pieces=[dict(c=[list(q) for q in h.exterior.coords], area=round(h.area), touch=[blocks[i][0] for i in bi if blocks[i][1].distance(h) < 6], ondeck=round(h.intersection(deck).area / h.area, 2)) for h in pcs]))
pickle.dump(dict(faces=faces), open(S + 'fill/faces.pkl', 'wb'))
json.dump(out, open(S + 'fill/classes.json', 'w'))
na = sum(1 for o in out if not o['blocks'] and o['pieces']); nb = sum(1 for o in out if o['blocks'] and o['pieces']); nc = sum(1 for o in out if o['deck_split'])
print('faces with gaps', len(out), 'empty faces', na, 'partly filled', nb, 'split by the deck edge', nc)
print('pieces touching a block', sum(1 for o in out for p in o['pieces'] if p['touch']), 'free pieces', sum(1 for o in out for p in o['pieces'] if not p['touch']))
