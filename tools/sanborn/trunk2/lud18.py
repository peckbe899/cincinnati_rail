try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Trunk north of Arlington as straight - one curve - straight - one curve - straight (Ben, 25 October 2026: no S curves where avoidable).
# Arlington straight (today's bearing) -> curve 1 (right) -> straight A -> curve 2 (right) -> today's straight towards the Mill Creek bridge.
import sys, json, numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Point, LineString
SP=_ws.DATA
sys.path.insert(0,_ws.CODE+'nv'); sys.path.insert(0,_ws.CODE+'trunk2')
import geom27 as G
exec(open(_ws.CODE+'trunk2/lud6.py').read().split('def pt(s)')[0])           # PK
from creek_up import WAT_UP, DECKED_LINE
WATC = WAT_UP.union(DECKED_LINE.buffer(8))
_Sa,_ia=np.unique(G._S[::-1],return_index=True); _Pa=G._P[::-1][_ia]
def ref(s): return np.array([np.interp(s,_Sa,_Pa[:,0]),np.interp(s,_Sa,_Pa[:,1])]) if s<4950 else np.array(G.C.interpolate(s).coords[0])
RS=np.arange(4000.0,7800.0,1.0); RP=np.array([ref(s) for s in RS])
t=np.gradient(RP,axis=0); t/=np.hypot(t[:,0],t[:,1])[:,None]
for _ in range(20): t[1:-1]=(t[:-2]+2*t[1:-1]+t[2:])/4
t/=np.hypot(t[:,0],t[:,1])[:,None]; RE=np.c_[t[:,1],-t[:,0]]; KD=cKDTree(RP)
def tan_at(s): i=int(np.searchsorted(RS,s)); return t[i]
# band: deck edges 3 m + 1.5 m off the creek / culvert (west) and OH-75 (east); constant width W1 -30.15 to E2 20.25 after the shift
SB=np.arange(4300.0,7400.0,10.0)
def edge(p,e,geom,sign,maxd=150):
    for d in np.arange(0,maxd,0.5):
        if geom.contains(Point(p+e*sign*d)): return d
    return maxd
BP=np.array([ref(s) for s in SB]); BE=np.array([RE[int(np.searchsorted(RS,s))] for s in SB])
cw=np.array([edge(p,e,WATC,-1) for p,e in zip(BP,BE)]); ck=np.array([edge(p,e,PK,1) for p,e in zip(BP,BE)])
tt=np.clip((SB-5570)/400,0,1); west=24.45+9.9*(1-(1-np.cos(np.pi*tt))/2); east=24.45; CL=4.5
LO=-cw+CL+west; HI=ck-CL-east
LO[(SB>7250)]=-1e9; HI[(SB>7250)]=1e9                          # the bridge: on today's line by construction
def path(thA,dA,R1,R2):
    """returns polyline from s 4,000 to 7,700 or None"""
    pA0=ref(4200.0); uA0=tan_at(4200.0)                       # Arlington straight
    pB0=ref(6800.0); uB0=tan_at(6800.0)                       # straight towards the bridge
    r=np.radians(thA); uA=np.array([np.sin(r),np.cos(r)]); nA=np.array([uA[1],-uA[0]])
    pA=ref(5000.0)+RE[int(np.searchsorted(RS,5000.0))]*dA     # straight A passes dA m east of today's line at s 5,000
    def corner(p1,u1,p2,u2,R):
        tt_,v=np.linalg.solve(np.c_[u1,-u2],p2-p1); PI=p1+u1*tt_; th=np.arccos(np.clip(u1@u2,-1,1)); T=R*np.tan(th/2)
        a=PI-u1*T; b=PI+u2*T; cr=u1[0]*u2[1]-u1[1]*u2[0]; nr=np.array([u1[1],-u1[0]]) if cr<0 else np.array([-u1[1],u1[0]]); O=a+nr*R
        a0=np.arctan2(*(a-O)[::-1]); a1=np.arctan2(*(b-O)[::-1]); da=(a1-a0+np.pi)%(2*np.pi)-np.pi
        n=max(3,int(R*abs(da)/2)); f=np.linspace(0,1,n); arc=np.c_[O[0]+R*np.cos(a0+da*f),O[1]+R*np.sin(a0+da*f)]
        return a,b,arc,cr
    a1,b1,arc1,c1=corner(pA0,uA0,pA,uA,R1); a2,b2,arc2,c2=corner(pA,uA,pB0,uB0,R2)
    if c1>=0 or c2>=0: return None                           # both must be right-hand curves
    if (a1-pA0)@uA0 < 0: return None
    if (a2-b1)@uA < 0: return None                            # straight A must have positive length
    if (pB0-b2)@uB0 < -600: return None
    st0=np.array([pA0+uA0*x for x in np.arange(-200.0,(a1-pA0)@uA0,2.0)])
    stA=np.array([b1+uA*x for x in np.arange(2.0,(a2-b1)@uA,2.0)]) if (a2-b1)@uA>2 else np.zeros((0,2))
    stB=np.array([b2+uB0*x for x in np.arange(2.0,1300.0,2.0)])
    return np.vstack([st0,arc1,stA,arc2,stB]), (a1,b1,a2,b2)
def offsets(c):
    d,i=KD.query(c); s=RS[i]; o=np.einsum('ij,ij->i',c-RP[i],RE[i]); k=np.argsort(s); return s[k],o[k]
def ok(c, verbose=False):
    s,o=offsets(c); oo=np.interp(SB,s,o)
    bad=(oo<LO)|(oo>HI)
    if verbose and bad.any(): print('  fails at', SB[bad][:10])
    return not bad.any(), oo
if __name__=='__main__':
    best=None
    for thA in np.arange(30.0,37.01,0.5):
        for dA in np.arange(-14.0,6.01,1.0):
            # widest R1, R2 that pass
            for R1 in (2000,1600,1300,1100,950,850,780,720):
                for R2 in (2000,1600,1300,1100,950,850,780,720):
                    if best and min(R1,R2) < best[0]: continue
                    r=path(thA,dA,R1,R2)
                    if r is None: continue
                    g,_=ok(r[0])
                    if g:
                        sc=(min(R1,R2),R1+R2)
                        if best is None or sc>best[:2]: best=(sc[0],sc[1],thA,dA,R1,R2); print('candidate',best)
                        break
    print('best',best)
    json.dump(dict(best=best),open(SP+'trunk2/lud18_best.json','w'))
