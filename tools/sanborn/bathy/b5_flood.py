try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, pickle, rasterio
from rasterio.enums import Resampling
from scipy import ndimage as ndi
from rasterio import features
from affine import Affine
FS=146.3
D=np.load('topo/dem2m.npy',mmap_mode='r')
H8,W8=4375,5000
real=np.empty((H8,W8),np.float32)
for i in range(0,17500,500):
    blk=D[i:i+500].astype(np.float32)/10; real[i//4:i//4+125]=blk.reshape(125,4,W8,4).mean((1,3))
with rasterio.open(_ws.ext('/mnt/user-data/outputs/M3full/map3_profile_dem_dm.vrt')) as s:
    can=s.read(1,out_shape=(H8,W8),resampling=Resampling.average).astype(np.float32)/10
    print('vrt shape',s.shape, s.transform)
O,Lk=pickle.load(open('topo/canon_river.pkl','rb'))
tr=Affine(8,0,695000,0,-8,4350000)
riv=features.rasterize([(O,1)],out_shape=(H8,W8),transform=tr).astype(bool)
near=ndi.distance_transform_edt(~riv)*8<=600
def flood(Z):
    low=(Z<=FS)&near
    lab,n=ndi.label(low); keep=np.unique(lab[riv&low]); keep=keep[keep>0]
    return np.isin(lab,keep)|riv
FR=flood(real); FC=flood(can)
np.save('bathy/work/flood_real8.npy',FR); np.save('bathy/work/flood_canon8.npy',FC)
print('real flood km2',FR.sum()*64/1e6,'canon flood km2',FC.sum()*64/1e6,'river km2',riv.sum()*64/1e6)
