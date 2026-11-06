try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys
from shapely.geometry import shape, LineString
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
S = _ws.DATA
DK = sys.argv[6] if len(sys.argv) > 6 else 'deckpage/deck.json'; BK = sys.argv[7] if len(sys.argv) > 7 else 'deckpage/basin.json'
D = json.load(open(S + DK)); B = json.load(open(S + BK))
x0, y0, x1, y1 = map(float, sys.argv[1:5])
fig, ax = plt.subplots(figsize=(18, 18 * (y1 - y0) / (x1 - x0)))
COL = {'cut_building': '#7a4a9a', 'cut_headhouse': '#7a4a9a', 'cut_concourse': '#b090c0', 'cut_precinct': '#ccc', 'cut_park': '#5a9a5a', 'cut_square': '#e8dcb0', 'cut_plaza': '#efe6c8', 'cut_lincoln': '#9fd09f',
       'cut_lawn': '#6fb06f', 'cut_road': '#999', 'cut_terrace': '#d8c890', 'cut_walk': '#eee', 'block': '#f2d4c4', 'forecourt': '#ddd'}
order = ['block', 'cut_precinct', 'cut_square', 'cut_park', 'cut_plaza', 'cut_lincoln', 'cut_lawn', 'cut_terrace', 'cut_road', 'cut_walk', 'cut_concourse', 'cut_building', 'cut_headhouse']
F = D['features'] + B['features']
for L in order:
    for f in F:
        p = f['properties']
        if p.get('layer') != L: continue
        g = shape(f['geometry'])
        if g.bounds[2] < x0 or g.bounds[0] > x1 or g.bounds[3] < y0 or g.bounds[1] > y1: continue
        for q in getattr(g, 'geoms', [g]):
            if q.geom_type == 'Polygon': ax.fill(*q.exterior.xy, color=COL[L], ec='k', lw=0.4, alpha=0.9)
            else: ax.plot(*q.xy, color='k', lw=0.6)
for f in F:
    p = f['properties']
    if p.get('layer') != 'street': continue
    l = LineString(f['geometry']['coordinates'])
    if l.bounds[2] < x0 or l.bounds[0] > x1 or l.bounds[3] < y0 or l.bounds[1] > y1: continue
    c = l.buffer((p.get('width_m') or 10) / 2, cap_style=2)
    for q in getattr(c, 'geoms', [c]): ax.fill(*q.exterior.xy, color='#4a7ab0', alpha=0.25, ec='#2a4a80', lw=0.6)
    ax.plot(*l.xy, color='#2a4a80', lw=0.8); m = l.interpolate(0.5, normalized=True); (ax.text(m.x, m.y, p['id'], fontsize=7, color='#123', clip_on=True) if x0 < m.x < x1 and y0 < m.y < y1 else None)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.grid(alpha=0.2)
fig.savefig(S + 'cut/' + sys.argv[5], dpi=60, bbox_inches='tight')
