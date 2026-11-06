try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, numpy as np
from shapely.geometry import shape, LineString, Polygon, MultiPolygon
from shapely.ops import unary_union, polygonize
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
S = _ws.DATA
D = json.load(open(S + 'deckpage/deck.json')); B = json.load(open(S + 'deckpage/basin.json'))
FE = D['features'] + B['features']
streets = [f for f in FE if f['properties'].get('layer') == 'street']
lines = [LineString(f['geometry']['coordinates']) for f in streets]
corr = unary_union([LineString(f['geometry']['coordinates']).buffer((f['properties'].get('width_m') or 10) / 2, cap_style=2) for f in streets])
net = unary_union(lines)
faces = list(polygonize(net))
OCC = {'block', 'rail_open', 'cut_precinct', 'palace', 'forecourt', 'boulevard', 'roundabout', 'cut_square', 'cut_park', 'cut_headhouse', 'cut_plaza', 'cut_lincoln', 'cut_building', 'cut_concourse', 'cut_terrace', 'cut_lawn', 'cut_road', 'cut_walk', 'dive_cut'}
occ = unary_union([shape(f['geometry']).buffer(0) for f in FE if f['properties'].get('layer') in OCC and f['geometry']['type'] in ('Polygon', 'MultiPolygon')])
print('faces', len(faces))
cand = []
for i, fc in enumerate(faces):
    rest = fc.difference(corr).difference(occ.buffer(2.0))
    for g in getattr(rest, 'geoms', [rest]):
        if g.geom_type != 'Polygon' or g.area < 300: continue
        g = g.buffer(-1.5).buffer(1.5)
        if g.is_empty or g.area < 300: continue
        for h in getattr(g, 'geoms', [g]):
            if h.area < 300: continue
            comp = 4 * np.pi * h.area / h.length ** 2
            cand.append((h, fc.area, comp))
print('candidates', len(cand), 'area', round(sum(c[0].area for c in cand)))
json.dump([dict(c=list(map(list, h.exterior.coords)), area=round(h.area), face=round(fa), comp=round(cp, 3)) for h, fa, cp in cand], open(S + 'fill/cand.json', 'w'))
fig, ax = plt.subplots(figsize=(16, 16))
for f in FE:
    if f['properties'].get('layer') == 'block':
        for p in getattr(shape(f['geometry']), 'geoms', [shape(f['geometry'])]): ax.fill(*p.exterior.xy, color='#ccc', lw=0)
for l in lines: ax.plot(*l.xy, color='k', lw=0.3)
for h, fa, cp in cand: ax.fill(*h.exterior.xy, color='r' if cp > 0.15 else 'orange', alpha=0.7, lw=0)
ax.set_aspect('equal'); fig.savefig(S + 'fill/cand_all.png', dpi=80, bbox_inches='tight')
ax.set_xlim(711600, 713600); ax.set_ylim(4332600, 4334600); fig.savefig(S + 'fill/cand_qc.png', dpi=80, bbox_inches='tight')
