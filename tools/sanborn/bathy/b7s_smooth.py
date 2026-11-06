try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, rasterio
from affine import Affine
from scipy import ndimage as ndi
tr=Affine(4,0,695000,0,-4,4350000)
for f in ['bed_real4f','bed_canon4']:
    a=np.load(f'bathy/work/{f}.npy'); m=np.isfinite(a)
    s=ndi.gaussian_filter(np.where(m,a,0),3)/np.maximum(ndi.gaussian_filter(m.astype(float),3),1e-6)
    np.save(f'bathy/work/{f}_s.npy',np.where(m,s,np.nan).astype(np.float32))
def out(name,arr):
    o=np.where(np.isfinite(arr),np.round(arr*10),-32768).astype(np.int16)
    with rasterio.open(_ws.ext(f'/mnt/user-data/outputs/Bathy/{name}_dm.tif'),'w',driver='GTiff',height=o.shape[0],width=o.shape[1],count=1,dtype='int16',crs='EPSG:26916',transform=tr,nodata=-32768,compress='deflate',predictor=2,tiled=True) as d: d.write(o,1)
import sys
if len(sys.argv)>1:
    out('ohio_bed_real_2022',np.load('bathy/work/bed_real4f_s.npy')); out('ohio_bed_canon_map3',np.load('bathy/work/bed_canon4_r.npy'))
