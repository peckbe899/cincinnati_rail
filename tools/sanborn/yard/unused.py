try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys
sys.path.insert(0, (_ws.CODE + 'yard'))
from shapely.geometry import shape, LineString, mapping
from shapely.ops import unary_union
S = _ws.DATA
P = json.load(open(S + 'yard/part1.json')); d = json.load(open(S + 'yard/d3.json'))
lim = [shape(f['geometry']) for f in P['features'] if f['properties']['layer'] == 'yard_limit'][0]
B = unary_union([shape(f['geometry']) for f in P['features'] if f['properties']['layer'] == 'ud_box' and f['properties'].get('cls') == 'in'])
room = lim.buffer(-2.5).difference(B.buffer(2.5))
lines = [LineString(c) for y, k, c in d['SEG']] + [LineString(d[k]) for k in ('hump', 'ramp', 'zlead')]
fp = unary_union([l.buffer(3) for l in lines]).buffer(12).buffer(-12)
un = room.difference(fp.buffer(3))
print('room', round(room.area / 1e4, 1), 'footprint', round(fp.area / 1e4, 1), 'unused', round(un.area / 1e4, 1))
for g in sorted(getattr(un, 'geoms', [un]), key=lambda g: -g.area)[:12]:
    print(round(g.area / 1e4, 2), [round(v) for v in g.bounds])
