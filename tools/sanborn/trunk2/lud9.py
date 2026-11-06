try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json,sys,numpy as np
SP=_ws.DATA
sys.path.insert(0,_ws.CODE+'nv'); import geom27 as G
from shapely.geometry import Point, LineString
def pt(s):
    if s<=5420: i=int(np.argmin(np.abs(G._S-s))); return np.array(G._P[i])
    return np.array(G.C.interpolate(s).coords[0])
Bd=np.load(SP+'trunk2/band.npy'); ss=Bd[:,0]; lo=Bd[:,1]+1.0; hi=Bd[:,2]-1.0
P0=np.array([pt(s) for s in ss]); t=np.gradient(P0,axis=0); t/=np.hypot(t[:,0],t[:,1])[:,None]; E=np.c_[t[:,1],-t[:,0]]
def U(b): r=np.radians(b); return np.array([np.sin(r),np.cos(r)])
def offsets(c):
    L=LineString(c); o=[]
    for p,e in zip(P0,E):
        seg=LineString([p-e*200,p+e*200]); x=seg.intersection(L)
        if x.is_empty: o.append(np.nan); continue
        q=x if x.geom_type=='Point' else min(x.geoms,key=lambda g:g.distance(Point(p)))
        o.append(float((np.array(q.coords[0])-p)@e))
    return np.array(o)
def route(dA,R,bB,dB):
    uA=U(34.2); eA=np.array([uA[1],-uA[0]]); a0=pt(5200)+eA*dA      # dA + east
    uB=U(bB); eB=np.array([uB[1],-uB[0]]); b0=pt(6800)+eB*dB
    t_,v_=np.linalg.solve(np.c_[uA,-uB],b0-a0); PI=a0+uA*t_
    D=np.arccos(np.clip(uA@uB,-1,1)); T=R*np.tan(D/2); TC=PI-uA*T; CT=PI+uB*T
    O=TC+eA*R; a=np.arctan2(*(TC-O)[::-1]); b=np.arctan2(*(CT-O)[::-1]); da=(b-a+np.pi)%(2*np.pi)-np.pi
    arc=np.array([O+R*np.array([np.cos(a+da*f),np.sin(a+da*f)]) for f in np.linspace(0,1,max(4,int(R*abs(da)/5)))])
    pre=np.array([a0+uA*x for x in np.arange(-600,(TC-a0)@uA,5)]); post=np.array([CT+uB*x for x in np.arange(5,900,5)])
    return np.vstack([pre,arc,post]),TC,CT
best=[]
win=(ss>=5300)&(ss<=7250)
for dA in (-8,-6,-4,-2,0):
  for bB in (61,62,63):
    for dB in (-6,-3,0,3,6):
      for R in (700,800,900,1000,1100,1200,1400,1600):
        c,TC,CT=route(dA,R,bB,dB); o=offsets(c)
        ok=np.all((o[win]>=lo[win])&(o[win]<=hi[win]))
        if ok: best.append((R,dA,bB,dB,round(float(np.nanmax(np.abs(o[win]))),1),round(G.C.project(Point(TC))),round(G.C.project(Point(CT)))))
best.sort(key=lambda r:(-r[0],r[4])); print(best[:10])
