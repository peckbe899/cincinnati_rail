try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, glob, numpy as np, pickle, rasterio
from pyproj import Transformer
from shapely.ops import unary_union
from shapely import points, contains
T=Transformer.from_crs(4326,26916,always_xy=True)
O,Lk=pickle.load(open('topo/canon_river.pkl','rb')); U=unary_union([O,Lk])
src=rasterio.open(_ws.ext('/mnt/user-data/outputs/M3full/map3_profile_dem_dm.vrt'))
for f in sorted(glob.glob('handoff/out/lines/Line_*.json')):
    j=json.load(open(f)); p=np.array(j['path']); x,y=T.transform(p[:,1],p[:,2])
    c=np.arange(len(j['ground_dm']))*j['step_m']
    xs=np.interp(c,p[:,0],x); ys=np.interp(c,p[:,0],y)
    ins=contains(U,points(xs,ys))
    if not ins.any(): print(f.split('/')[-1],'no river'); continue
    v=np.array([s[0] for s in src.sample(list(zip(xs[ins],ys[ins])))])
    g=np.array(j['ground_dm']); old=g[ins].copy(); g[ins]=v; j['ground_dm']=g.tolist()
    j['ground_note']=(j.get('ground_note','')+'').strip()
    json.dump(j,open(f,'w'))
    print(f.split('/')[-1],'river samples',ins.sum(),'old min %.1f new min %.1f m'%(old.min()/10,v.min()/10))
