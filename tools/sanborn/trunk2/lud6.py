try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json,sys,numpy as np
from pyproj import Transformer
from shapely.geometry import shape, box, LineString, Point, Polygon
from shapely.ops import transform, unary_union
SP=_ws.DATA
sys.path.insert(0,_ws.CODE+'nv'); import geom27 as G
TR=Transformer.from_crs(4326,26916,always_xy=True)
W=json.load(open(_ws.ext('/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/OSM/water.geojson')))
B=box(711800,4335800,716500,4339500); wat=[]
for f in W['features']:
    g=transform(TR.transform,shape(f['geometry']))
    if not g.intersects(B): continue
    if f['properties'].get('name')=='Mill Creek': wat.append(g.buffer(8))
    elif g.geom_type in ('Polygon','MultiPolygon') and g.area>1500: wat.append(g)
WAT=unary_union(wat)
H=json.load(open(SP+'deckpage/hwy.json'))
PK=unary_union([shape(f['geometry']).buffer(f['properties']['w']/2,cap_style=2) for f in H['features'] if f['properties'].get('layer')=='hw_piece' and f['properties']['name'].startswith('OH-75 parkway')])
def pt(s):
    if s<=5420: i=int(np.argmin(np.abs(G._S-s))); return np.array(G._P[i])
    return np.array(G.C.interpolate(s).coords[0])
def U(b): r=np.radians(b); return np.array([np.sin(r),np.cos(r)])
def bear(s): v=pt(s+10)-pt(s-10); return np.degrees(np.arctan2(v[0],v[1]))
A0=pt(5200); uA=U(34.2)
def route(se,R):
    uB=U(bear(se)); B0=pt(se)
    t,v=np.linalg.solve(np.c_[uA,-uB],B0-A0); PI=A0+uA*t
    D=np.arccos(np.clip(uA@uB,-1,1)); T=R*np.tan(D/2); TC=PI-uA*T; CT=PI+uB*T
    if (TC-A0)@uA<0 or (B0-CT)@uB<0: return None
    e=np.array([uA[1],-uA[0]]); O=TC+e*R
    a0=np.arctan2(*(TC-O)[::-1]); a1=np.arctan2(*(CT-O)[::-1]); da=(a1-a0+np.pi)%(2*np.pi)-np.pi
    arc=np.array([O+R*np.array([np.cos(a0+da*f),np.sin(a0+da*f)]) for f in np.linspace(0,1,max(4,int(R*abs(da)/4)))])
    pre=np.array([A0+uA*x for x in np.arange(-250,(TC-A0)@uA,4)]); post=np.array([CT+uB*x for x in np.arange(4,(B0-CT)@uB,4)])
    return np.vstack([pre,arc,post]) if len(post) else np.vstack([pre,arc])
def footprint(c, west=24.45, east=24.45, isl=(5266,5670,10.0)):
    t=np.gradient(c,axis=0); t/=np.hypot(t[:,0],t[:,1])[:,None]; e=np.c_[t[:,1],-t[:,0]]
    s=np.array([G.C.project(Point(q)) for q in c]); w=west+np.where((s>isl[0])&(s<isl[1]),isl[2],0)
    return Polygon(np.vstack([c-e*w[:,None],(c+e*east)[::-1]])).buffer(0)
res=[]
for se in range(6600,7801,100):
    for R in (800,1000,1200,1500,1800,2200,2600,3000):
        c=route(se,R)
        if c is None: continue
        fp=footprint(c)
        dw=fp.distance(WAT); dk=fp.distance(PK); hitw=fp.intersection(WAT).area; hitk=fp.intersection(PK).area
        res.append((R,se,round(hitw),round(hitk),round(dw,1),round(dk,1)))
ok=[r for r in res if r[2]==0 and r[3]==0]
ok.sort(key=lambda r:(-r[0],-min(r[4],r[5])))
print('clear options:',ok[:12])
print('all R>=1500:',[r for r in res if r[0]>=1500][:20])
print(len(res)); print(sorted(res,key=lambda r:r[2]+r[3])[:15])
for se in (6600,7000,7400):
    print(se, bear(se))
