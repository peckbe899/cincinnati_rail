try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json,sys,numpy as np
import sys; sys.path.insert(0,(_ws.CODE + 'trunk2'))
exec(open((_ws.CODE + 'trunk2/lud6.py')).read().split('res=[]')[0])
sys.path.insert(0,SP+'trunk'); from frames import chaikin, resample
from creek_up import WAT_UP as WAT
ss=np.arange(4950,7700,10.0); P0=np.array([pt(s) for s in ss])
t=np.gradient(P0,axis=0); t/=np.hypot(t[:,0],t[:,1])[:,None]; E=np.c_[t[:,1],-t[:,0]]
def edge(p,e,geom,sign,maxd=250):
    for d in np.arange(0,maxd,0.5):
        if geom.contains(Point(p+e*sign*d)): return d
    return maxd
cw=np.array([edge(p,e,WAT,-1) for p,e in zip(P0,E)]); ck=np.array([edge(p,e,PK,1) for p,e in zip(P0,E)])
isl=(ss>5266)&(ss<5670)
west=24.45+np.where(isl,10.0,0); east=24.45; CL=3.0
omin=-(cw-CL-west)   # offset (+east) lower bound: west edge must stay east of creek:  o - west >= -cw + CL
omin=-cw+CL+west; omax=ck-CL-east
for s,a,b,c1,c2 in zip(ss[::10],omin[::10],omax[::10],cw[::10],ck[::10]): print(int(s),'creek %.0f park %.0f  band %.1f..%.1f'%(c1,c2,a,b))
np.save(SP+'trunk2/band_up.npy',np.c_[ss,omin,omax])
