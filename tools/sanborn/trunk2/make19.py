try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# write the chosen straight/curve trunk (lud19_best.json) as lud19.npy: s, x, y, offset from today's line (5 m grid, 4,200-7,650)
import json, numpy as np
from shapely.geometry import LineString
exec(open((_ws.CODE + 'trunk2/lud19.py')).read().split("if __name__=='__main__':")[0])
b=json.load(open(SP+'trunk2/lud19_best.json'))['best']
_,_,_,thA,dA,thC,dC,R2,R3=b
A=mkA(thA,dA); C1=curve1(*A); c,tp=build(A,C1,thC,dC,int(R2),int(R3))
print('curve 1 R %.0f; tangent points s'%C1[0],[round(sof(p)) for p in tp])
g=LineString(c); ss=np.arange(4200.0,7650.1,5.0); out=[]
for s in ss:
    i=int(np.searchsorted(RS,s)); p=RP[i]; e=RE[i]; X=g.intersection(LineString([p-e*80,p+e*80]))
    q=np.array(X.coords[0]) if X.geom_type=='Point' else np.array(list(X.geoms)[0].coords[0]); out.append([s,q[0],q[1],(q-p)@e])
out=np.array(out); np.save(SP+'trunk2/lud19.npy',out)
json.dump(dict(R1=C1[0],R2=R2,R3=R3,thA=thA,thC=thC,tangents=[float(sof(p)) for p in tp]),open(SP+'trunk2/lud19_geom.json','w'))
print('max shift %.1f m at s %.0f'%(np.abs(out[:,3]).max(),out[np.argmax(np.abs(out[:,3])),0]))
