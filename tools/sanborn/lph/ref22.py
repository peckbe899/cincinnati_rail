"""World positions of named intersections from the georeferenced 1922 halves (cluster per name pair)."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, collections, numpy as np
SP=_ws.DATA
sys.path.insert(0,_ws.CODE+'lph')
from fit22 import load22, pair, ap
def ref(tf='tf22_aff.json'):
    TF=json.load(open(SP+'lph/'+tf)); G=collections.defaultdict(list)
    for r in load22():
        if r['fr'] in TF: G[r['k']].append(np.array(ap(TF[r['fr']],r['x'],r['y'])))
    out={}
    for k,v in G.items():
        cl=[]
        for q in v:
            for c in cl:
                if np.hypot(*(q-np.mean(c,0)))<6: c.append(q); break
            else: cl.append([q])
        out[k]=[np.mean(c,0) for c in cl]
    return out
