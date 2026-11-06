try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys
from shapely.geometry import shape, LineString, Polygon
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
S = _ws.DATA
D = json.load(open(S + 'deckpage/deck.json')); B = json.load(open(S + 'deckpage/basin.json')); T = json.load(open(S + 'deckpage/tracks.json')); C = json.load(open(S + 'deckpage/context.json'))
cand = json.load(open(S + 'fill/cand.json'))
x0, y0, x1, y1 = map(float, sys.argv[1:5])
fig, ax = plt.subplots(figsize=(15, 15))
for f in D['features'] + B['features']:
    L = f['properties'].get('layer')
    if f['geometry']['type'] in ('Polygon', 'MultiPolygon'):
        g = shape(f['geometry'])
        for p in getattr(g, 'geoms', [g]):
            if p.bounds[2] < x0 or p.bounds[0] > x1 or p.bounds[3] < y0 or p.bounds[1] > y1: continue
            ax.fill(*p.exterior.xy, color='#ccc' if L == 'block' else '#bde', lw=0.3, ec='w')
    elif L == 'street':
        c = f['geometry']['coordinates']; ax.plot([q[0] for q in c], [q[1] for q in c], color='k', lw=0.4)
for i, c in enumerate(cand):
    p = Polygon(c['c'])
    if p.bounds[2] < x0 or p.bounds[0] > x1 or p.bounds[3] < y0 or p.bounds[1] > y1: continue
    ax.fill(*p.exterior.xy, color='r', alpha=0.45); ax.text(p.centroid.x, p.centroid.y, str(i), fontsize=8)
for f in T['features']:
    if f['geometry']['type'] == 'LineString':
        c = f['geometry']['coordinates']; ax.plot([q[0] for q in c], [q[1] for q in c], color='m', lw=0.6)
for r in C['rer']:
    c = r['c']; ax.plot([q[0] for q in c], [q[1] for q in c], color='orange', lw=0.8)
for t in C['tracks']:
    if t['sys'] == 'rer': c = t['c']; ax.plot([q[0] for q in c], [q[1] for q in c], color='orange', lw=0.4)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
fig.savefig(S + 'fill/' + sys.argv[5], dpi=70, bbox_inches='tight')
