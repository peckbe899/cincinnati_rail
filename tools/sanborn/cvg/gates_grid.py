try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Trial terminal shifts (Ben, 18 October: terminals and taxiways may move). Scores each layout by stands placed, large stands,
# and stands whose taxilane would sit closer to a parallel taxiway than the taxiway-to-taxilane separation (they push back onto the parallel).
import json, sys, itertools, importlib.util, numpy as np
from shapely.geometry import Point
S = _ws.DATA
base = json.load(open(S + 'cvg/gates_params.json'))
res = []
for d1b, d2, d3 in itertools.product(*[list(map(float, a.split(','))) for a in sys.argv[1:4]]):
    P = dict(base); P['shift'] = {'Terminal 1B': [0, d1b], 'Terminal 4': [0, d1b], 'Terminal 2': [0, d2], 'Terminal 3': [0, d3]}
    json.dump(P, open(S + 'cvg/_gp.json', 'w'))
    sys.argv = ['g', 'LS', 'x', 'cvg/_gp.json']
    spec = importlib.util.spec_from_file_location('g', _ws.CODE + 'cvg/gates.py'); g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
    r = g.run(['Terminal 1A', 'Terminal 1B', 'Terminal 4', 'Terminal 2', 'Terminal 3'])
    pb = sum(1 for x in r if min(p.distance(x['tail'].centroid) for p in g.PAR) < P['sep_twy_tl'])
    res.append((d1b, d2, d3, len(r), sum(1 for x in r if x['cls'] == 'L'), pb)); print(res[-1], flush=True)
