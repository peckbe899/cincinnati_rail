try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys
from shapely.geometry import shape, LineString
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
S = _ws.DATA
x0, y0, x1, y1 = map(float, sys.argv[1:5]); out = sys.argv[5]
PRE = sys.argv[6] if len(sys.argv) > 6 else 'deckpage/'
D = json.load(open(S + PRE + 'deck.json')); B = json.load(open(S + PRE + 'basin.json')); P = json.load(open(S + PRE + 'plots.json'))
fig, ax = plt.subplots(figsize=(12, 12 * (y1 - y0) / (x1 - x0)))
inb = lambda b: not (b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1)
for f in D['features'] + B['features']:
    p = f['properties']; L = p.get('layer')
    if not f['geometry'] or L in ('street',): continue
    g = shape(f['geometry'])
    if not inb(g.bounds): continue
    for q in getattr(g, 'geoms', [g]):
        if q.geom_type != 'Polygon' or q.is_empty: continue
        if L == 'deck': ax.plot(*q.exterior.xy, color='m', lw=1.5, ls='--'); [ax.plot(*i.xy, color='m', lw=1.5, ls='--') for i in q.interiors]
        elif L == 'block': ax.fill(*q.exterior.xy, color='#f2d4c4', ec='k', lw=0.8, alpha=0.8); c = q.representative_point(); ax.text(c.x, c.y, p['id'], fontsize=7, color='#a33', clip_on=True)
        else: ax.fill(*q.exterior.xy, color='#9cf', ec='b', lw=0.6, alpha=0.4); c = q.representative_point(); ax.text(c.x, c.y, L, fontsize=6, color='b', clip_on=True)
E0, N0 = P['o']
def dec(a):
    x, y = a[0], a[1]; pts = [(E0 + x / 10, N0 + y / 10)]
    for i in range(2, len(a), 2): x += a[i]; y += a[i + 1]; pts.append((E0 + x / 10, N0 + y / 10))
    return pts
for pl in P['plots']:
    for a in pl[6]:
        pts = dec(a); xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
        if max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1: continue
        ax.plot(xs + xs[:1], ys + ys[:1], color='#844', lw=0.4)
for f in D['features'] + B['features']:
    p = f['properties']
    if p.get('layer') != 'street': continue
    l = LineString(f['geometry']['coordinates'])
    if not inb(l.bounds): continue
    c = l.buffer((p.get('width_m') or 10) / 2, cap_style=2)
    for q in getattr(c, 'geoms', [c]): ax.fill(*q.exterior.xy, color='#4a7ab0', alpha=0.3, ec='#2a4a80', lw=0.6)
    m = l.interpolate(0.5, normalized=True); ax.text(m.x, m.y, p['id'], fontsize=6, clip_on=True)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.grid(alpha=0.2)
fig.savefig(S + 'cut/' + out, dpi=70, bbox_inches='tight')
