try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import rasterio, numpy as np, cv2, json, sys
from pyproj import Transformer
from scipy.ndimage import map_coordinates, gaussian_filter
DM=json.load(open('dem2m.json')); DEM=np.load('dem2m.npy',mmap_mode='r'); FT=1200/3937
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/USGS_Historical/")
def overlay(fname,lon,lat,half,iv,out,shift=(0,0)):
    with rasterio.open(base+fname) as s:
        T=Transformer.from_crs('EPSG:4326',s.crs,always_xy=True); x,y=T.transform(lon,lat); r,c=s.index(x,y)
        w=rasterio.windows.Window(c-half,r-half,2*half,2*half)
        img=np.dstack([s.read(i,window=w,boundless=True) for i in (3,2,1)]).copy()
        tr=s.window_transform(w); H,W=img.shape[:2]
        yy,xx=np.mgrid[0:H,0:W]; X=tr.c+(xx+0.5)*tr.a; Y=tr.f+(yy+0.5)*tr.e
        U=Transformer.from_crs(s.crs,'EPSG:26916',always_xy=True); E,N=U.transform(X.ravel(),Y.ravel())
        E=np.asarray(E)+shift[0]; N=np.asarray(N)+shift[1]
    r=DM['res']; c0=int((E.min()-30-DM['x0'])/r); r0=int((DM['y1']-N.max()-30)/r)
    a=gaussian_filter(np.asarray(DEM[r0:r0+int((N.max()-N.min())/r)+60,c0:c0+int((E.max()-E.min())/r)+60]).astype(np.float32)/10/FT,1.0)
    z=map_coordinates(a,[(DM['y1']-N)/r-r0-0.5,(E-DM['x0'])/r-c0-0.5],order=1).reshape(H,W)
    q=np.floor(z/iv); e=np.zeros(z.shape,bool); e[:,1:]|=q[:,1:]!=q[:,:-1]; e[1:,:]|=q[1:,:]!=q[:-1,:]
    img[e]=(255,0,0)
    cv2.imwrite(out,img)
if __name__=='__main__':
    overlay("KY_Covington_708444_1950_24000_geo.tif",-84.525,39.075,350,10,'usgs/ov_cov50.png')
    overlay("OH_West Cincinnati_226552_1914_62500_geo.tif",-84.525,39.075,250,20,'usgs/ov_w14.png')
