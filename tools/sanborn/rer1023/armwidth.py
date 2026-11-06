try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np
from shapely.geometry import shape, LineString, Point
SP=_ws.DATA
S=json.load(open(SP+'deckpage/structures.json')); C={f['id']:f for f in json.load(open(SP+'deckpage/context.json'))['rer']}
G=[shape(f['geometry']) for f in S['features'] if f['properties'].get('layer')=='struct']
D=LineString(C['R-D-710306-4337028']['c'])
for s in range(1350, 2500, 50):
    p=np.array(D.interpolate(s).coords[0]); q=np.array(D.interpolate(s+1).coords[0]); t=(q-p)/np.linalg.norm(q-p); n=np.array([-t[1],t[0]])
    ln=LineString([p-n*60,p+n*60]); w=sum(g.intersection(ln).length for g in G)
    print(s, [round(v) for v in p], 'structure width across the arm', round(w,1))
