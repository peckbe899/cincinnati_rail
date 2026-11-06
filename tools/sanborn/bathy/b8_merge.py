try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, pickle, rasterio
from rasterio import features
from affine import Affine
from scipy.ndimage import map_coordinates
from shapely.ops import unary_union
bed=np.load('bathy/work/bed_canon4_s.npy')
O,Lk=pickle.load(open('topo/canon_river.pkl','rb')); U=unary_union([O,Lk])
src=_ws.ext('/mnt/user-data/outputs/M3full'); tot=0
import sys
for r in [int(v) for v in sys.argv[1:]] or (0,1):
    for c in (0,1):
        fn=f'{src}/map3_profile_dem_dm_r{r}c{c}.tif'
        with rasterio.open(fn) as s: a=s.read(1); prof=s.profile; tr=s.transform
        inside=features.rasterize([(U,1)],out_shape=a.shape,transform=tr).astype(bool)
        rr,cc=np.nonzero(inside&(a<=1460)&(a!=-32768))
        # 2 m pixel centre -> 4 m bed index
        X=tr.c+(cc+0.5)*2; Y=tr.f-(rr+0.5)*2
        bi=(4350000-Y)/4-0.5; bj=(X-695000)/4-0.5
        bf=np.nan_to_num(bed,nan=-999)
        v=map_coordinates(bf,[bi,bj],order=1,mode='nearest')
        ok=v>100
        newv=np.round(v[ok]*10).astype(np.int16)
        a[rr[ok],cc[ok]]=np.minimum(a[rr[ok],cc[ok]],newv)
        tot+=ok.sum()
        prof.update(compress="deflate",predictor=2,zlevel=9,tiled=True,blockxsize=512,blockysize=512)
        with rasterio.open(fn,'w',**prof) as d: d.write(a,1)
        print(fn.split('/')[-1],'bed px',ok.sum())
print('total km2',tot*4/1e6)
