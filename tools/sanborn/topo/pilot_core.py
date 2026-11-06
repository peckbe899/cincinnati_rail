"""1912 built-up core: density of black linework (streets, buildings, lettering) on the warped 1912 sheets."""
import numpy as np, cv2, rasterio, sys
from rasterio.windows import from_bounds
from scipy import ndimage as ndi
from pilot_common import load, hs, panel
name=sys.argv[1]; d=load(name); X0,Y1,n=d['X0'],d['Y1'],d['n']; W=n*2.0
with rasterio.open('warped/1912_Survey_Mosaic.vrt') as ds:
    w=from_bounds(X0,Y1-W,X0+W,Y1,ds.transform)
    img=ds.read([1,2,3],window=w,out_shape=(3,int(W),int(W)),boundless=True,fill_value=255).astype(np.int16)   # 1 m
mx=img.max(0); mn=img.min(0)
ink=(mx<120)&((mx-mn)<45)                       # dark and grey: black linework, not red contours / blue water / green parks
paper=(mx>150)
dens=ndi.gaussian_filter(ink.astype(np.float32),40)/np.maximum(ndi.gaussian_filter(paper.astype(np.float32)+ink,40),1e-3)
dens=cv2.resize(dens,(n,n),interpolation=cv2.INTER_AREA)
np.save(f'pilot_{name}_inkdens.npy',dens.astype(np.float32))
print(name,'ink density percentiles p10 %.3f p50 %.3f p90 %.3f p99 %.3f'%tuple(np.percentile(dens[d['cov']],[10,50,90,99])))
