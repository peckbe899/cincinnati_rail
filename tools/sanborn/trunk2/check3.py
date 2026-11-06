try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import sys, numpy as np
SP=_ws.DATA
sys.path.insert(0,_ws.CODE+'trunk2')
exec(open(_ws.CODE+'trunk2/lud6.py').read().split('def pt(s)')[0])
import geo3 as Q
from shapely.geometry import LineString, Point
def resamp(c, step):
    d=np.r_[0,np.cumsum(np.hypot(*np.diff(c,axis=0).T))]; keep=np.r_[True,np.diff(d)>1e-6]; c=c[keep]; d=d[keep]
    t=np.arange(0,d[-1],step); return np.c_[np.interp(t,d,c[:,0]),np.interp(t,d,c[:,1])]
def radii(c, chord=20.0):
    p=resamp(c,chord/2); a,b,cc=p[:-2],p[1:-1],p[2:]
    ab=np.hypot(*(b-a).T); bc=np.hypot(*(cc-b).T); ac=np.hypot(*(cc-a).T)
    cr=np.abs((b-a)[:,0]*(cc-a)[:,1]-(b-a)[:,1]*(cc-a)[:,0])
    R=np.where(cr>1e-9, ab*bc*ac/(2*cr+1e-12), np.inf); return b, R
if __name__!="__main__": raise SystemExit
L=Q.build()
print('trunk frame'); b,R=radii(Q.TR.P); i=np.argmin(R); print('  min R %.0f at s %.0f'%(R[i],Q.TR.proj(b[i])))
for k,v in L.items():
    b,R=radii(v['c']); i=np.argmin(R)
    # list every local stretch under 1500 m
    s=np.array([Q.TR.proj(q) for q in b]); low=R<1500
    segs=[];
    j=0
    while j<len(R):
        if low[j]:
            j0=j
            while j<len(R) and low[j]: j+=1
            m=j0+np.argmin(R[j0:j]); segs.append('%.0f@%.0f'%(R[m],s[m]))
        j+=1
    print(k, ' min R %.0f at s %.0f'%(R[i],s[i]), ' bends<1500:', ' '.join(segs[:12]), v.get('r_bore',''))
# creek / parkway clearance of deck edges, s 4,900-8,000
outer={}
for s in np.arange(4900,8000,10.0):
    lo=min(f(s) for f in [Q.o_w(0)]) - 4.2; hi=Q.o_e(1)(s)+4.2
    pw_=Q.TR.at(s,lo)[0]; pe=Q.TR.at(s,hi)[0]
    dw=WAT.distance(Point(pw_)) if not WAT.contains(Point(pw_)) else -1; de=PK.distance(Point(pe)) if not PK.contains(Point(pe)) else -1
    seg=LineString([pw_,pe]); hitw=seg.intersects(WAT); hitp=seg.intersects(PK)
    if hitw or hitp or dw<3 or de<3: print('  clearance s %.0f  west-edge to creek %.1f  east-edge to parkway %.1f  %s%s'%(s,dw,de,'CREEK ' if hitw else '','PARKWAY' if hitp else ''))
