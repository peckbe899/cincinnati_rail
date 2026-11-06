try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np
sys.path.insert(0,(_ws.CODE + 'nv')); import geom27 as G
from shapely.geometry import LineString, Point, shape
SP=_ws.DATA
H=json.load(open(SP+'deckpage/hwy.json'))
pk=[shape(f['geometry']).buffer(f['properties']['w']/2,cap_style=2) for f in H['features'] if f['properties'].get('layer')=='hw_piece' and f['properties']['name'].startswith('OH-75 parkway')]
from shapely.ops import unary_union
PK=unary_union(pk)
def pt(s):
    if s<=5420: i=int(np.argmin(np.abs(G._S-s))); return np.array(G._P[i])
    return np.array(G.C.interpolate(s).coords[0])
def tan(s):
    a=pt(s-10); b=pt(s+10); v=b-a; return v/np.hypot(*v)
def bez(p0,t0,p3,t3,a,b,n=600):
    q1,q2=p0+t0*a,p3-t3*b; u=np.linspace(0,1,n)[:,None]; return (1-u)**3*p0+3*(1-u)**2*u*q1+3*(1-u)*u**2*q2+u**3*p3
def minr(c):
    d1=np.gradient(c,axis=0); d2=np.gradient(d1,axis=0); k=np.abs(d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0])/np.hypot(d1[:,0],d1[:,1])**3; return 1/k.max()
def east_clear(c, edge=26.7):
    t=np.gradient(c,axis=0); t/=np.hypot(t[:,0],t[:,1])[:,None]; e=np.c_[t[:,1],-t[:,0]]
    worst=1e9
    for p,ee in zip(c[::5],e[::5]):
        if G.C.project(Point(p))<5330: continue
        seg=LineString([p,p+ee*80]); x=seg.intersection(PK)
        if not x.is_empty: d=Point(p).distance(x); worst=min(worst,d-edge)
    return worst
best=None
for s0 in (4950,5000,5100):
  for s1 in (6200,6400,6600,6800):
    p0,t0,p3,t3=pt(s0),tan(s0),pt(s1),tan(s1); L=np.hypot(*(p3-p0))
    for fa in np.linspace(0.2,0.6,9):
      for fb in np.linspace(0.2,0.6,9):
        c=bez(p0,t0,p3,t3,fa*L,fb*L); r=minr(c); cl=east_clear(c)
        if cl>=3.0 and (best is None or r>best[0]): best=(r,s0,s1,fa,fb,cl)
print('best', best)
# current
c0=np.array([pt(s) for s in np.arange(4950,6600,2.0)]); print('current minR',round(minr(c0)),'east clearance',round(east_clear(c0),1))
res=[]
for s0 in (4500,4650,4800,4950):
  for s1 in (6000,6300,6600,7000,7400):
    p0,t0,p3,t3=pt(s0),tan(s0),pt(s1),tan(s1); L=np.hypot(*(p3-p0))
    for fa in np.linspace(0.15,0.7,12):
      for fb in np.linspace(0.15,0.7,12):
        c=bez(p0,t0,p3,t3,fa*L,fb*L); res.append((round(east_clear(c),1),round(minr(c)),s0,s1,round(fa,2),round(fb,2)))
res.sort(reverse=True); print(res[:10])
print(sorted([r for r in res if r[0]>=3],key=lambda r:-r[1])[:5])
