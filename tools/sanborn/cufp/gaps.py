try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# loose ends: endpoints of plate streets that stop 1-60 m short of another street
import json, sys
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
SP = _ws.DATA
SETS = set(sys.argv[1].split(','))
B = json.load(open(SP + 'deckpage/basin.json'))
S = [f for f in B['features'] if f['properties']['layer'] == 'street']
G = [shape(f['geometry']) for f in S]; T = STRtree(G)
out = []
for f, g in zip(S, G):
    if f['properties'].get('set') not in SETS: continue
    for e in (0, -1):
        q = Point(g.coords[e]); near = [int(j) for j in T.query(q.buffer(60))]
        d = min([G[j].distance(q) for j in near if G[j] is not g] or [999])
        if 1.0 < d < 60: out.append((f['properties']['set'], f['properties']['id'], f['properties']['name'], [round(c) for c in g.coords[e]], round(d, 1)))
for o in sorted(out): print(*o)
print(len(out))
