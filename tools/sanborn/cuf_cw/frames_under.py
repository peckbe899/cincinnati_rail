try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, pickle, os, collections, numpy as np
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'sbg'); sys.path.insert(0, _ws.CODE + 'cuf'); sys.path.insert(0, _ws.CODE + 'lph'); sys.path.insert(0, _ws.CODE + 'cufp')
import mosn, fwdlib
from plates import POLY22
from shapely.geometry import Polygon, Point
TF = {}
for fn in ('lph/tf_all.json', 'lph/tf_ext.json', 'lph/tf_ext2.json', 'lph/tf_ext3.json'): TF.update(json.load(open(SP + fn)))
FP = {k: Polygon(fwdlib.world_many(k[3:], np.array(POLY22[k], float))).buffer(0) for k in ('22-34L', '22-34R', '22-37L', '22-37R', '22-16R')}
hits = collections.defaultdict(dict)
for fr in TF:
    sh = ''.join(ch for ch in fr if ch.isdigit()); fn = SP + f'sbg/picks/s{sh}.json'
    if not os.path.exists(fn): continue
    P = json.load(open(fn))['intersections']
    if not P: continue
    E, N = mosn.ap(TF[fr], np.array([p['x'] for p in P], float), np.array([p['y'] for p in P], float))
    for n, F in FP.items():
        k = sum(F.contains(Point(e, nn)) for e, nn in zip(E, N))
        if k: hits[fr][n] = k
for fr in sorted(hits, key=lambda s: (int(''.join(ch for ch in s if ch.isdigit())), s)): print(fr, hits[fr])
json.dump(hits, open(SP + 'cuf_cw/frames_under.json', 'w'))
print(','.join(sorted(hits, key=lambda s: (int(''.join(ch for ch in s if ch.isdigit())), s))))
