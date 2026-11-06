try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import shape, LineString
S = _ws.DATA
RAW = json.load(open(S + 'cvg/_taxi_raw.json')); AP = json.load(open(S + 'deckpage/airport.json'))
x0, y0, x1, y1 = map(float, sys.argv[1].split(','))
fig, ax = plt.subplots(figsize=(16, 16 * (y1 - y0) / (x1 - x0)))
for f in AP['features']:
    p = f['properties']
    if p['layer'] in ('cvg_runway', 'cvg_building', 'cvg_stand'):
        g = shape(f['geometry'])
        for q in getattr(g, 'geoms', [g]): ax.fill(*q.exterior.xy, color={'cvg_runway': '0.6', 'cvg_building': '#7a5c99', 'cvg_stand': '0.88'}[p['layer']], lw=0)
col = lambda n: 'red' if 'rapid' in n else 'blue' if 'connector' in n or 'crossing' in n else 'green' if 'entry' in n else 'orange' if 'Apron' in n else 'magenta' if 'link' in n else 'black'
for r in RAW:
    l = LineString(r['c']); ax.plot(*l.xy, color=col(r['name']), lw=1.4)
    m = l.interpolate(0.5, normalized=True)
    if x0 < m.x < x1 and y0 < m.y < y1 and 'Apron' not in r['name']: ax.annotate(r['name'].replace('Taxiway ', '').split(' (')[0], (m.x, m.y), fontsize=6)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); plt.tight_layout(); plt.savefig(S + sys.argv[2], dpi=60)
