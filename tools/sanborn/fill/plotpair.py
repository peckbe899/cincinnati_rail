try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, pickle
from shapely.geometry import shape, Polygon
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
S = _ws.DATA
D = json.load(open(S + 'deckpage/deck.json')); B = json.load(open(S + 'deckpage/basin.json')); P = json.load(open(S + 'deckpage/plots.json'))
deck = shape([f for f in D['features'] if f['properties']['layer'] == 'deck'][0]['geometry'])
o = json.load(open(S + 'fill/classes.json'))
faces = [x for x in o if x['deck_split']]
E0, N0 = P['o']
def ring(a):
    x, y = a[0], a[1]; pts = [(E0 + x / 10, N0 + y / 10)]
    for i in range(2, len(a), 2): x += a[i]; y += a[i + 1]; pts.append((E0 + x / 10, N0 + y / 10))
    return pts
fig, axs = plt.subplots(3, 4, figsize=(24, 18)); axs = axs.ravel()
blk = {f['properties']['id']: shape(f['geometry']) for f in D['features'] + B['features'] if f['properties']['layer'] == 'block'}
for ax, x in zip(axs, [f for f in faces if 'B026' not in f['blocks']]):
    U = None
    for i, b in enumerate(x['blocks']):
        g = blk[b]; U = g if U is None else U.union(g)
        for p in getattr(g, 'geoms', [g]): ax.fill(*p.exterior.xy, color='C%d' % i, alpha=0.25)
    for pl in P['plots']:
        if pl[1] in x['blocks']:
            for r in pl[6]: q = ring(r); ax.plot([a[0] for a in q] + [q[0][0]], [a[1] for a in q] + [q[0][1]], 'k-', lw=0.5)
    bx = U.bounds; [ax.plot(*dp.exterior.xy, 'r-', lw=1.5) for dp in getattr(deck, 'geoms', [deck])]; ax.set_xlim(bx[0] - 10, bx[2] + 10); ax.set_ylim(bx[1] - 10, bx[3] + 10); ax.set_aspect('equal'); ax.set_title(str(x['face']) + ' ' + ','.join(x['blocks']), fontsize=9)
fig.savefig(S + 'fill/pairs.png', dpi=60, bbox_inches='tight')
