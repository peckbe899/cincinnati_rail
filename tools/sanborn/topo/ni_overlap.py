try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, numpy as np
from pyproj import Transformer
from shapely.geometry import LineString
from shapely.strtree import STRtree
T=Transformer.from_crs('EPSG:4326','EPSG:26916',always_xy=True)
NI=json.load(open('../kmz_ni/new_interstates.json'))
roads=json.load(open(_ws.ext('/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/OSM/roads.geojson')))['features']
mot=[f for f in roads if f['properties'].get('highway') in ('motorway','trunk','motorway_link','trunk_link','primary')]
L=[];lab=[]
for f in mot:
    a=np.array(f['geometry']['coordinates']); e,n=T.transform(a[:,0],a[:,1]); L.append(LineString(np.c_[e,n]))
    p=f['properties']; lab.append((p.get('highway'),p.get('ref') or '',p.get('name') or ''))
tree=STRtree(L)
res={}
for nm,pts in NI.items():
    a=np.array(pts); e,n=T.transform(a[:,0],a[:,1]); line=LineString(np.c_[e,n])
    s=np.arange(0,line.length,20.0); P=[line.interpolate(x) for x in s]
    near=[]; 
    for p in P:
        i=tree.nearest(p); d=p.distance(L[i]); near.append((d,lab[i]))
    d=np.array([x[0] for x in near])
    follows=d<45
    # runs
    runs=[]; cur=None
    for k,(dd,lb) in enumerate(near):
        key=(lb[0] if dd<45 else 'NEW', lb[1] if dd<45 else '', lb[2] if dd<45 else '')
        if cur and cur[0]==key: cur[2]=k
        else:
            if cur: runs.append(cur)
            cur=[key,k,k]
    runs.append(cur)
    # merge tiny runs
    print(f'\n== {nm}: {line.length/1000:.1f} km, follows an existing road {follows.mean()*100:.0f}%, new {100-follows.mean()*100:.0f}%')
    for key,k0,k1 in runs:
        km=(k1-k0+1)*0.02
        if km<0.6: continue
        lon,lat=np.array(T.transform(P[k0].x,P[k0].y,direction='INVERSE'))
        print(f'   {k0*0.02:5.1f}-{k1*0.02:5.1f} km  {km:4.1f} km  {key[0]:13s} {key[1]:14s} {key[2][:30]:30s} start {lat:.4f},{lon:.4f}')
    res[nm]={'s':s.tolist(),'d':d.tolist(),'lab':[x[1] for x in near]}
json.dump(res,open('ni_overlap.json','w'))
