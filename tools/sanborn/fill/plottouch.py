try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json
from shapely.geometry import shape, Polygon
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
S = _ws.DATA
D = json.load(open(S + 'deckpage/deck.json')); B = json.load(open(S + 'deckpage/basin.json')); T = json.load(open(S + 'deckpage/tracks.json'))
deck = shape([f for f in D['features'] if f['properties']['layer'] == 'deck'][0]['geometry'])
blk = {f['properties']['id']: shape(f['geometry']) for f in D['features'] + B['features'] if f['properties']['layer'] == 'block'}
o = [x for x in json.load(open(S + 'fill/classes.json')) if x['blocks'] and any(p['touch'] for p in x['pieces'])]
print(len(o))
n = len(o); cols = 6; rows = (n + cols - 1) // cols
fig, axs = plt.subplots(rows, cols, figsize=(cols * 5, rows * 5)); axs = axs.ravel()
for ax, x in zip(axs, o):
    U = None
    for b in x['blocks']:
        g = blk[b]; U = g if U is None else U.union(g)
        for p in getattr(g, 'geoms', [g]): ax.fill(*p.exterior.xy, color='#888', alpha=0.5)
    for p in x['pieces']:
        P = Polygon(p['c']); U = U.union(P); ax.fill(*P.exterior.xy, color='r' if p['touch'] else 'orange', alpha=0.5)
    for dp in getattr(deck, 'geoms', [deck]): ax.plot(*dp.exterior.xy, 'b-', lw=1)
    for f in T['features']:
        if f['geometry']['type'] == 'LineString': c = f['geometry']['coordinates']; ax.plot([q[0] for q in c], [q[1] for q in c], 'm-', lw=0.4)
    bx = U.bounds; ax.set_xlim(bx[0] - 10, bx[2] + 10); ax.set_ylim(bx[1] - 10, bx[3] + 10); ax.set_aspect('equal')
    ax.set_title(f"{x['face']} {','.join(x['blocks'])} " + ' '.join(str(p['area']) for p in x['pieces']), fontsize=8); ax.tick_params(labelsize=5)
fig.savefig(S + 'fill/touch.png', dpi=45, bbox_inches='tight')
