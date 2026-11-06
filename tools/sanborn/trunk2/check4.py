try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import sys, numpy as np
SP=_ws.DATA
sys.path.insert(0,_ws.CODE+'trunk2')
exec(open(_ws.CODE+'trunk2/lud6.py').read().split('def pt(s)')[0])
from creek_up import WAT_UP as WAT
import geo4 as Q
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Point
def resamp(c, step):
    c=np.asarray(c); d=np.r_[0,np.cumsum(np.hypot(*np.diff(c,axis=0).T))]; keep=np.r_[True,np.diff(d)>1e-6]; c=c[keep]; d=d[keep]
    t=np.arange(0,d[-1],step); return np.c_[np.interp(t,d,c[:,0]),np.interp(t,d,c[:,1])]
def radii(c, chord=30.0):
    p=resamp(c,chord/2); a,b,cc=p[:-2],p[1:-1],p[2:]
    ab=np.hypot(*(b-a).T); bc=np.hypot(*(cc-b).T); ac=np.hypot(*(cc-a).T)
    cr=np.abs((b-a)[:,0]*(cc-a)[:,1]-(b-a)[:,1]*(cc-a)[:,0]); return b, ab*bc*ac/(2*cr+1e-12)
def zfun(kind, s, deck):
    if kind in ('orr','apex','r5'): return G.band(s)
    if kind=='rer': return G.band(s) if s>=G.S_SEP else G.band(s)-12
    if kind=='indy': return G.Z_TOP if deck else G.sh_z(s)
    if kind=='rerd': return G.Z_TOP if deck else min(G.Z_TOP, G.band(3250)+0.025*max(0,s-3250))
L=Q.build()
if __name__=='__main__':
    print('== radii (30 m chord), every stretch under 1,500 m')
    for k,v in L.items():
        b,R=radii(v['c']); s=np.array([Q.TR.proj(q) for q in b]); low=R<1500; segs=[]; j=0
        while j<len(R):
            if low[j]:
                j0=j
                while j<len(R) and low[j]: j+=1
                m=j0+np.argmin(R[j0:j]); segs.append('%.0f@%.0f'%(R[m],s[m]))
            j+=1
        print('%-16s min %5.0f at s %5.0f | %s'%(k,R.min(),s[np.argmin(R)],' '.join(segs)))
    print('== same-level spacing under 4.3 m (excluding the turnouts)')
    pts={}
    for k,v in L.items():
        p=resamp(v['c'],2.0); s=np.array([Q.TR.proj(q) for q in p]); dist=np.array([LineString(Q.TR.P).distance(Point(q)) for q in p])
        deck=(s>Q.S_TC)&(dist>3)&(v['kind'] in ('indy','rerd'))
        z=np.array([zfun(v['kind'],a,dk) for a,dk in zip(s,deck)]); pts[k]=(p,s,z)
    names=list(pts); TOL=4.3
    for i in range(len(names)):
        for j in range(i+1,len(names)):
            a,b=pts[names[i]],pts[names[j]]; T=cKDTree(b[0]); dd,ii=T.query(a[0],distance_upper_bound=TOL)
            ok=np.isfinite(dd)
            if not ok.any(): continue
            dz=np.abs(a[2][ok]-b[2][ii[ok]]); sv=a[1][ok][dz<6.5]
            if len(sv): print('  %s / %s : s %.0f-%.0f (%d pts, min gap %.1f)'%(names[i],names[j],sv.min(),sv.max(),len(sv),dd[ok][dz<6.5].min()))
    print('== creek / parkway clearance of the deck edges (4.2 m out from the outer tracks)')
    for s in np.arange(4700,7700,10.0):
        lo=Q.o_w(0)(s)-4.2; hi=Q.o_e(1)(s)+4.2
        pw_=Q.TR.at(s,lo)[0]; pe=Q.TR.at(s,hi)[0]; seg=LineString([pw_,pe])
        dw=WAT.distance(Point(pw_)); de=PK.distance(Point(pe))
        if seg.intersects(WAT) or seg.intersects(PK) or dw<3 or de<3: print('  s %.0f  west edge to creek %.1f, east edge to parkway %.1f %s'%(s,dw,de,'(bridge)' if 7265<=s<=7400 else ''))
