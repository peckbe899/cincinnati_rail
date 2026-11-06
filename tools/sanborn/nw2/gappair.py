try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, math
import numpy as np
from shapely.geometry import LineString, Point
SP=_ws.DATA
src=open(_ws.CODE+'nw2/gapcheck2.py').read().split("ST=[")[0]
exec(src)
def tang(g,e):
    c=np.array(g.coords); 
    if e==0: a=c[0]; 
    else: a=c[-1]
    # outward tangent from 15 m in
    L=g.length; p=g.interpolate(min(15,L/2) if e==0 else max(L-15,L/2))
    v=a-np.array(p.coords[0]); return v/np.linalg.norm(v)
ENDS=[]
for ln,ps in G.items():
    for pid,g,ed in ps:
        for e in (0,-1):
            q=Point(g.coords[e])
            touch=[oid for oid,o,_ in ps if oid!=pid and o.distance(q)<0.5]
            ENDS.append(dict(ln=ln,pid=pid,e=e,q=q,t=tang(g,e),touch=touch,ed=ed,g=g))
loose=[x for x in ENDS if not x['touch']]
out=[];used=set()
for x in loose:
    best=None
    for y in loose:
        if y['ln']!=x['ln'] or y['pid']==x['pid']: continue
        v=np.array(y['q'].coords[0])-np.array(x['q'].coords[0]); d=np.linalg.norm(v)
        if d<0.3 or d>500: continue
        u=v/d
        if np.dot(u,x['t'])>0.8 and np.dot(-u,y['t'])>0.8 and (best is None or d<best[0]): best=(d,y)
    if best:
        k=tuple(sorted([(x['pid'],x['e']),(best[1]['pid'],best[1]['e'])]))+(x['ln'],)
        if k in used: continue
        used.add(k); out.append(('PAIR',x['ln'],round(best[0],1),x['pid'],x['e'],best[1]['pid'],best[1]['e'],x['ed'] or best[1]['ed']))
    else:
        ps=G[x['ln']]; c=[(o.distance(x['q']),oid) for oid,o,_ in ps if oid!=x['pid']]
        d,oid=min(c) if c else (None,None)
        out.append(('LOOSE',x['ln'],round(d,1) if d else None,x['pid'],x['e'],oid,None,x['ed'],[round(v) for v in x['q'].coords[0]]))
for r in sorted(out,key=lambda r:(r[0],r[1],r[2] or 0)): print(r)
