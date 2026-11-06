try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import linemerge
SP=_ws.DATA
L=json.load(open(SP+'nv/lines.json')); R=json.load(open(SP+'nv/orr_near.json'))['lines']
def get(src,name,folder=None):
    for o in L:
        if o['src']==src and o['name']==name and (folder is None or folder in o['folder']): return LineString(o['c'])
a=get('APEx','Cincinnati-Camp Washington'); b=get('APEx','Camp Washington-St Bernard')
ca=list(a.coords); cb=list(b.coords)
if Point(ca[0]).distance(Point(712700,4331900))>Point(ca[-1]).distance(Point(712700,4331900)): ca=ca[::-1]
if Point(cb[0]).distance(Point(ca[-1]))>Point(cb[-1]).distance(Point(ca[-1])): cb=cb[::-1]
pts=[ca[0]]
for q in ca[1:]+cb[1:]:
    if (q[0]-pts[-1][0])**2+(q[1]-pts[-1][1])**2>1: pts.append(q)
C=LineString(pts)
print('C len',C.length, 'start',C.coords[0])
def off(g, s):
    p=C.interpolate(s); q=C.interpolate(s+1); t=np.array([q.x-p.x,q.y-p.y]); t/=np.linalg.norm(t); n=np.array([t[1],-t[0]])  # right normal
    # intersect normal line with g
    from shapely.geometry import LineString as LS
    nl=LS([(p.x-n[0]*400,p.y-n[1]*400),(p.x+n[0]*400,p.y+n[1]*400)])
    try: x=nl.intersection(g)
    except Exception: return None
    if x.is_empty: return None
    pts=[x] if x.geom_type=='Point' else list(getattr(x,'geoms',[x]))
    vals=[ (pp.x-p.x)*n[0]+(pp.y-p.y)*n[1] for pp in pts if pp.geom_type=='Point']
    return min(vals,key=abs) if vals else None
lines={
 'TRI Dayton-Ind 3D':get('TRIMET3D','Dayton-Independence 3D'),
 'TRI Greensburg 3D':get('TRIMET3D','Greensburg-California 3D'),
 'TRI Oxford 3D':get('TRIMET3D','Oxford-Aurora 3D'),
 'TRI Lebanon 3D':get('TRIMET3D','Lebanon-Walton 3D'),
 'CR RER-2 MCT':get('CR','RER Mill Creek Trunk','RER-2'),
 'CR RER-2 Cin-Day':get('CR','Cincinnati-Dayton','RER-2'),
 'CR RER-4 Gr':get('CR','Greensburg-CUT TRIMET','RER-4'),
 'APEx Indy':get('APEx','Greensburg-CUT TRIMET'),
 'APEx Vandalia':get('APEx','Vandalia-Cincinnati'),
 'APEx Norwood':get('APEx','Cincinnati-Norwood'),
}
for o in R:
    lines['ORR '+o['path'][-1]+' '+o['name'][:14]]=LineString(o['pts'])
ss=list(range(2500,9700,200))+[4135,4146,4555,5560,5725,7938,8927]
ss=sorted(set(ss))
names=[k for k in lines if lines[k] is not None]
for s in ss:
    row=[]
    for k in names:
        v=off(lines[k],s)
        if v is not None and abs(v)<300: row.append('%s=%.0f'%(k,v))
    print(s, '; '.join(r for r in row if not r.endswith('=0') and not r.endswith('=-0') and not r.endswith('=1') and not r.endswith('=-1')))
