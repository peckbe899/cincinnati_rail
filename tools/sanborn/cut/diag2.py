try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys
from shapely.geometry import shape, LineString, Polygon
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
S = _ws.DATA
x0, y0, x1, y1 = map(float, sys.argv[1:5]); out = sys.argv[5]; pre = sys.argv[6] if len(sys.argv) > 6 else 'cut/prev_'
D = json.load(open(S + pre + 'deck.json')); B = json.load(open(S + pre + 'basin.json')); P = json.load(open(S + pre + 'plots.json'))
fig, ax = plt.subplots(figsize=(18, 18 * (y1 - y0) / (x1 - x0)))
COL = {'cut_building': '#7a4a9a', 'cut_headhouse': '#7a4a9a', 'cut_concourse': '#b090c0', 'cut_precinct': '#ccc', 'cut_park': '#5a9a5a', 'cut_square': '#e8dcb0', 'cut_plaza': '#efe6c8', 'cut_lincoln': '#9fd09f',
       'cut_lawn': '#6fb06f', 'cut_road': '#999', 'cut_terrace': '#d8c890', 'cut_walk': '#eee', 'block': '#f2d4c4', 'boulevard': '#dde'}
order = ['boulevard', 'block', 'cut_precinct', 'cut_square', 'cut_park', 'cut_plaza', 'cut_lincoln', 'cut_lawn', 'cut_terrace', 'cut_road', 'cut_walk', 'cut_concourse', 'cut_building', 'cut_headhouse']
F = D['features'] + B['features']
inb = lambda b: not (b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1)
for L in order:
    for f in F:
        p = f['properties']
        if p.get('layer') != L or not f['geometry']: continue
        g = shape(f['geometry'])
        if not inb(g.bounds): continue
        for q in getattr(g, 'geoms', [g]):
            if q.geom_type == 'Polygon': ax.fill(*q.exterior.xy, color=COL[L], ec='k', lw=0.5, alpha=0.9)
            else: ax.plot(*q.xy, color='k', lw=0.6)
        if L == 'block': c = g.representative_point(); ax.text(c.x, c.y, p['id'], fontsize=6, color='#a33', clip_on=True)
E0, N0 = P['o']
def dec(a):
    x, y = a[0], a[1]; pts = [(E0 + x / 10, N0 + y / 10)]
    for i in range(2, len(a), 2): x += a[i]; y += a[i + 1]; pts.append((E0 + x / 10, N0 + y / 10))
    return pts
for pl in P['plots']:
    for a in pl[6]:
        pts = dec(a); xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
        if max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1: continue
        ax.plot(xs + xs[:1], ys + ys[:1], color='#844', lw=0.35)
for f in F:
    p = f['properties']
    if p.get('layer') != 'street': continue
    l = LineString(f['geometry']['coordinates'])
    if not inb(l.bounds): continue
    c = l.buffer((p.get('width_m') or 10) / 2, cap_style=2)
    for q in getattr(c, 'geoms', [c]): ax.fill(*q.exterior.xy, color='#4a7ab0', alpha=0.3, ec='#2a4a80', lw=0.6)
    ax.plot(*l.xy, color='#2a4a80', lw=0.6)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.grid(alpha=0.2)
fig.savefig(S + 'cut/' + out, dpi=60, bbox_inches='tight')
