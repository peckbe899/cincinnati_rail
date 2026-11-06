try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys
from shapely.geometry import shape
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
S = _ws.DATA
D = json.load(open(S + 'deckpage/deck.json')); B = json.load(open(S + 'deckpage/basin.json'))
D0 = json.load(open(S + 'fill/deck_pre.json')); B0 = json.load(open(S + 'fill/basin_pre.json'))
old = {f['properties']['id']: shape(f['geometry']) for f in D0['features'] + B0['features'] if f['properties'].get('layer') == 'block'}
deck = shape([f for f in D['features'] if f['properties']['layer'] == 'deck'][0]['geometry'])
x0, y0, x1, y1 = map(float, sys.argv[1:5])
fig, ax = plt.subplots(figsize=(14, 14 * (y1 - y0) / (x1 - x0)))
for f in D['features'] + B['features']:
    p = f['properties']
    if p.get('layer') == 'street':
        c = f['geometry']['coordinates']; ax.plot([q[0] for q in c], [q[1] for q in c], color='k', lw=0.3)
    if p.get('layer') != 'block': continue
    g = shape(f['geometry'])
    if g.bounds[2] < x0 or g.bounds[0] > x1 or g.bounds[3] < y0 or g.bounds[1] > y1: continue
    col = '#e05050' if p.get('side') == 'fill' else '#8a5aa8' if p.get('joined17') else '#bbb'
    for q in getattr(g, 'geoms', [g]): ax.fill(*q.exterior.xy, color=col, lw=0.3, ec='w')
    if p.get('extended17') and p['id'] in old:
        ex = g.difference(old[p['id']])
        for q in getattr(ex, 'geoms', [ex]):
            if q.geom_type == 'Polygon' and q.area > 50: ax.fill(*q.exterior.xy, color='#3a9a5a', lw=0)
for dp in getattr(deck, 'geoms', [deck]): ax.plot(*dp.exterior.xy, 'b--', lw=1)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
ax.set_title('grey: blocks as before; purple: joined across the deck edge; green: land added to a block; red: new filled blocks; blue dashes: deck')
fig.savefig(S + 'fill/' + sys.argv[5], dpi=60, bbox_inches='tight')
