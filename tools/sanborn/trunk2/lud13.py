try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import sys,numpy as np
exec(open((_ws.CODE + 'trunk2/lud9.py')).read().split('def route')[0])
def U2(b): r=np.radians(b); return np.array([np.sin(r),np.cos(r)])
def build(dA,s_tc,R,bE,sj0,sj1):
    uA=U2(34.2); eA=np.array([uA[1],-uA[0]])
    a0=pt(5200)+eA*dA; TC=a0+uA*(s_tc-5200)
    # right turn: centre to the right (east)
    O=TC+eA*R; a=np.arctan2(*(TC-O)[::-1]); D=np.radians(bE-34.2)
    arc=np.array([O+R*np.array([np.cos(a-D*f),np.sin(a-D*f)]) for f in np.linspace(0,1,max(4,int(R*D/4)))])
    CT=arc[-1]; uE=U2(bE)
    st=np.array([CT+uE*x for x in np.arange(4,1500,4)])
    pre=np.array([a0+uA*x for x in np.arange(-500,s_tc-5200,4)])
    c=np.vstack([pre,arc,st])
    # offsets vs the current line, then an S back onto the current line between sj0 and sj1
    o=offsets(c)
    return c,o
win=(ss>=5300)&(ss<=7250)
res=[]
for dA in (-5,-6,-8):
  for s_tc in (5400,5450,5500):
    for R in (700,800,900,1000,1200,1400,1700,2000):
      for bE in (60,62,64,66):
        c,o=build(dA,s_tc,R,bE,0,0)
        # S back: where o is defined; final target 0 by 7200; we accept o up to band (S handled later)
        m=win&(ss<=6400)&~np.isnan(o)
        if not m.any(): continue
        ok=np.all((o[m]>=lo[m])&(o[m]<=hi[m]))
        o64=o[np.argmin(np.abs(ss-6400))]
        if ok: res.append((R,dA,s_tc,bE,round(float(o64),1)))
res.sort(key=lambda r:(-r[0],abs(r[4]))); print(res[:15])
for args in ((-5,5450,1000,62),(-5,5450,700,66)):
    c,o=build(*args,0,0); print(args)
    for s,oo,a,b in zip(ss,o,lo,hi):
        if 5300<=s<=6450 and int(s)%50==0: print('  ',int(s),round(oo,1),round(a,1),round(b,1),'X' if not(a<=oo<=b) else '')
