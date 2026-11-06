try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# shared crossings between 1922 plates (same name pair within 40 m): how far apart the fits put them
import json, sys, glob, itertools, numpy as np
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'cufp'); sys.path.insert(0, _ws.CODE + 'cuf38'); sys.path.insert(0, _ws.CODE + 'sbg')
import fwdlib, fwd38lib
from names import key
def pts(n, world):
    out = {}
    for fn in glob.glob(SP + f'sbg/picks22/s22-{n}_*.json'):
        for p in json.load(open(fn))['intersections']:
            if '?' in p['a'] + p['b']: continue
            out.setdefault(tuple(sorted((key(p['a']), key(p['b'])))), []).append(world(p['x'], p['y']))
    return {k: np.mean(v, 0) for k, v in out.items()}
P = {'38': pts('38', fwd38lib.world)}
for n in sys.argv[1:]: P[n] = pts(n, (lambda n: lambda x, y: fwdlib.world(n, x, y))(n))
for a, b in itertools.combinations(P, 2):
    d = [(float(np.hypot(*(P[a][k] - P[b][k]))), k) for k in P[a] if k in P[b] and np.hypot(*(P[a][k] - P[b][k])) < 40]
    if d: print(a, b, len(d), 'median', round(float(np.median([x for x, _ in d])), 1), 'max', round(max(d)[0], 1), max(d)[1])
