try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json,sys
import numpy as np
from shapely.geometry import shape, LineString, Point
SP=_ws.DATA
C=json.load(open(SP+'deckpage/context.json')); T=json.load(open(SP+'deckpage/tracks.json'))
L=[]; ref=None
for f in T['features']:
    n=f['properties'].get('name') or ''
    g=shape(f['geometry'])
    if g.geom_type!='LineString': continue
    if n.startswith('APEx north approach 3'): ref=g
    if g.bounds[3]>4333500 and g.bounds[1]<4339500 and g.bounds[0]<716500: L.append((n[:30],g))
ext=[f for f in T['features'] if (f['properties'].get('name') or '').startswith('APEx Southwest Chief, Transcontinental Limited (2')]
ref=LineString(list(ref.coords)+list(shape(ext[0]['geometry']).coords)[1:])
for t in C['tracks']:
    if t['sys']=='rer' and t.get('pid','')[:4] in ('R-BD','R-B-','R-D-'):
        L.append(('RER '+t['line']+' '+t['pid'][2:9],LineString(t['c'])))
for s in [float(v) for v in sys.argv[1:]]:
    p=np.array(ref.interpolate(s).coords[0]); q=np.array(ref.interpolate(s+5).coords[0]); u=(q-p)/np.linalg.norm(q-p); nrm=np.array([u[1],-u[0]])
    cut=LineString([p-nrm*200,p+nrm*200]); row=[]
    for n,g in L:
        X=g.intersection(cut)
        if X.is_empty: continue
        for pt in getattr(X,'geoms',[X]):
            if pt.geom_type=='Point': row.append((round(float((np.array(pt.coords[0])-p)@nrm),1),n))
    print(int(s),[round(v) for v in p],sorted(row))
