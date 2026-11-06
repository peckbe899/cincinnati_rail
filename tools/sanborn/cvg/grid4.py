try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, itertools, importlib.util
S = _ws.DATA
base = json.load(open(S + sys.argv[1]))
for d2, d3 in itertools.product(*[list(map(float, a.split(','))) for a in sys.argv[2:4]]):
    P = json.loads(json.dumps(base)); P['shift'] = {'Terminal 2': [0, d2], 'Terminal 3': [0, d3]}
    json.dump(P, open(S + 'cvg/_gp.json', 'w'))
    sys.argv = ['g', 'LS', 'x', 'cvg/_gp.json']
    spec = importlib.util.spec_from_file_location('g', _ws.CODE + 'cvg/gates.py'); g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
    best = None
    for order in (['Terminal 1A', 'Terminal 1B', 'Terminal 4', 'Terminal 2', 'Terminal 3'], ['Terminal 2', 'Terminal 3', 'Terminal 1A', 'Terminal 1B', 'Terminal 4'], ['Terminal 3', 'Terminal 2', 'Terminal 1A', 'Terminal 1B', 'Terminal 4']):
        r = g.run(order); t = {}
        for x in r: t[x['term']] = t.get(x['term'], 0) + 1
        if best is None or len(r) > best[0]: best = (len(r), t, order[0])
    print(d2, d3, best, flush=True)
