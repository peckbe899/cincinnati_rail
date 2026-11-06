try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json,sys,numpy as np
exec(open((_ws.CODE + 'trunk2/lud6.py')).read().split('res=[]')[0])
sys.path.insert(0,SP+'trunk'); from frames import chaikin, resample
import sys, os; sys.path.insert(0,SP+'trunk2')
from creek_up import WAT_UP, DECKED_LINE
MODE=os.environ.get('MODE','open')
WAT = WAT_UP if MODE=='open' else WAT_UP.union(DECKED_LINE.buffer(8))
ss=np.arange(4950,7700,10.0); P0=np.array([pt(s) for s in ss])
t=np.gradient(P0,axis=0); t/=np.hypot(t[:,0],t[:,1])[:,None]; E=np.c_[t[:,1],-t[:,0]]
def edge(p,e,geom,sign,maxd=250):
    for d in np.arange(0,maxd,0.5):
        if geom.contains(Point(p+e*sign*d)): return d
    return maxd
cw=np.array([edge(p,e,WAT,-1) for p,e in zip(P0,E)]); ck=np.array([edge(p,e,PK,1) for p,e in zip(P0,E)])
t_=np.clip((ss-5570)/400,0,1); west=24.45+9.9*(1-(1-np.cos(np.pi*t_))/2); east=24.45; CL=3.0   # constant width (W at -30.15) to the viaduct end, then W steps in on the fill
omin=-(cw-CL-west)   # offset (+east) lower bound: west edge must stay east of creek:  o - west >= -cw + CL
omin=-cw+CL+west; omax=ck-CL-east
for s,a,b,c1,c2 in zip(ss[::10],omin[::10],omax[::10],cw[::10],ck[::10]): print(int(s),'creek %.0f park %.0f  band %.1f..%.1f'%(c1,c2,a,b))
np.save(SP+'trunk2/band_%s.npy'%MODE,np.c_[ss,omin,omax])
