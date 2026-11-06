try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json,sys,numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from pyproj import Transformer
from shapely.geometry import shape, box, LineString
from shapely.ops import transform, unary_union
SP=_ws.DATA
TR=Transformer.from_crs(4326,26916,always_xy=True)
W=json.load(open(_ws.ext('/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/OSM/water.geojson')))
B=box(711000,4334000,717000,4340500)
creek=[];polys=[]
for f in W['features']:
    g=transform(TR.transform,shape(f['geometry']))
    if not g.intersects(B): continue
    if f['properties'].get('name')=='Mill Creek' and 'Line' in g.geom_type: creek.append(g)
    elif g.geom_type in ('Polygon','MultiPolygon') and g.area>1500: polys.append(g)
json.dump({'creek':[list(map(list,c.coords)) for c in creek]},open(SP+'trunk2/millcreek.json','w'))
if __name__=='__main__':
    sys.path.insert(0,_ws.CODE+'nv'); import geom27 as G
    H=json.load(open(SP+'deckpage/hwy.json'))
    fig,ax=plt.subplots(figsize=(14,10))
    for g in polys:
        for q in getattr(g,'geoms',[g]): ax.fill(*q.exterior.xy,color='#90caf9')
    for c in creek: ax.plot(*c.xy,color='b',lw=2)
    for f in H['features']:
        if f['properties'].get('layer')=='hw_piece':
            g=shape(f['geometry']).buffer(f['properties']['w']/2,cap_style=2)
            for q in getattr(g,'geoms',[g]): ax.fill(*q.exterior.xy,color='m',alpha=.2)
    cur=np.array([G.C.interpolate(s).coords[0] for s in np.arange(4500,8600,4)])
    ax.plot(cur[:,0],cur[:,1],'k',lw=1.5,label='trunk now (KMZ)')
    L=np.load(SP+'trunk2/lud_100.npy'); ax.plot(L[:,1],L[:,2],'r',lw=1.2,label='my smoothed line')
    T=json.load(open(SP+'deckpage/tracks.json'))
    for f in T['features']:
        if f['geometry']['type']=='LineString' and (f['properties'].get('name') or '').startswith(('APEx north approach','Lower-level','APEx Southwest Chief, Trans')):
            c=np.array(f['geometry']['coordinates']); ax.plot(c[:,0],c[:,1],color='0.5',lw=0.5)
    ax.set_xlim(712200,714600); ax.set_ylim(4336300,4338000); ax.set_aspect('equal'); ax.legend(); ax.grid(alpha=.3)
    plt.savefig(SP+'trunk2/creek.png',dpi=80)
