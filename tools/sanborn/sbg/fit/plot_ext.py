try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import json, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import shape, Polygon
SP = _ws.DATA
X = json.load(open(SP + f'sbg/fit/ext_{sys.argv[1]}.json'))['features']; B = json.load(open(SP + 'deckpage/basin.json'))['features']; SH = json.load(open(SP + 'deckpage/sheets.json'))
x0, y0, x1, y1 = map(float, sys.argv[2].split(','))
fig, ax = plt.subplots(figsize=(16, 16 * (y1 - y0) / (x1 - x0)))
for e in SH:
    p = Polygon(e['poly'])
    if p.intersects(Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])): ax.plot(*p.exterior.xy, color='c', lw=0.6); ax.annotate(e['sheet'], (p.centroid.x, p.centroid.y), color='c', fontsize=8)
for f in B:
    if f['properties'].get('set') == sys.argv[1]: continue
    g = shape(f['geometry'])
    if f['properties']['layer'] == 'block':
        for q in getattr(g, 'geoms', [g]): ax.fill(*q.exterior.xy, color='0.85', lw=0)
    elif f['properties']['layer'] == 'street' and g.geom_type == 'LineString': ax.plot(*g.xy, color='0.4', lw=f['properties']['width_m'] / 6)
for f in X:
    g = shape(f['geometry'])
    if f['properties']['layer'] == 'block': ax.fill(*g.exterior.xy, color='#f6c', alpha=0.4, lw=0)
    else:
        ax.plot(*g.xy, color='r', lw=max(1, f['properties']['width_m'] / 6)); m = g.interpolate(0.5, normalized=True)
        if x0 < m.x < x1 and y0 < m.y < y1: ax.annotate(f['properties']['name'][:18], (m.x, m.y), fontsize=7, color='darkred')
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); plt.tight_layout(); plt.savefig(SP + sys.argv[3], dpi=60)
