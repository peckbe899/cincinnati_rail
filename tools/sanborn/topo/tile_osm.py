"""Cut OSM streets/buildings per tile (one pass over the big files)."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, numpy as np
from pyproj import Transformer
T=Transformer.from_crs('EPSG:4326','EPSG:26916',always_xy=True)
B=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/OSM/")
import sys
tiles=json.load(open('tiles.json')); names=sys.argv[1:] or sorted(tiles); C=np.array([[tiles[k]['cx'],tiles[k]['cy']] for k in names]); h=1750
out={k:{'streets':[],'buildings':[]} for k in names}
def assign(f,coords,kind):
    a=np.array(coords); e,n=T.transform(a[:,0],a[:,1]); e=np.asarray(e); n=np.asarray(n)
    lo=np.array([e.min(),n.min()]); hi=np.array([e.max(),n.max()])
    hit=np.nonzero((C[:,0]+h>lo[0])&(C[:,0]-h<hi[0])&(C[:,1]+h>lo[1])&(C[:,1]-h<hi[1]))[0]
    for i in hit: out[names[i]][kind].append(f)
for f in json.load(open(B+'streets_all.geojson'))['features']: assign(f,f['geometry']['coordinates'],'streets')
for f in json.load(open(B+'buildings.geojson'))['features']:
    g=f['geometry']; r=g['coordinates'][0] if g['type']=='Polygon' else g['coordinates'][0][0]; assign(f,r,'buildings')
for k in names: json.dump(out[k],open(f'pilot_{k}_osm.json','w'))
print('done',sum(len(v['buildings']) for v in out.values()))
