try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, cv2, json, rasterio
from scipy import ndimage as ndi
from shapely.geometry import shape
from shapely.ops import transform
from pyproj import Transformer
from rasterio.features import rasterize
from affine import Affine
from pilot_common import hs
d=np.load('rw_setup.npz'); L=d['L']; x0=float(d['x0']); y1=float(d['y1']); H,W=L.shape
KY=np.load('rw_KY.npy'); Z=np.load('rw_Zall.npy')&KY
G=np.load('ky1912_ground.npy')
with rasterio.open('I4_1912_ground_dm.tif') as ds:
    a=ds.read(1,window=rasterio.windows.from_bounds(x0,y1-2*H,x0+2*W,y1,ds.transform),boundless=True,fill_value=-32768)[:H,:W]
B=np.where(a>-30000,a/10.0,L).astype(np.float32); G=np.where(np.isfinite(G),G,B)
T=Transformer.from_crs('EPSG:4326','EPSG:26916',always_xy=True).transform
rf=json.load(open(_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/OSM/roads.geojson")))['features']
mw=[transform(T,shape(f['geometry'])) for f in rf if f['properties'].get('highway') in ('motorway','trunk')]
tr=Affine(2,0,x0,0,-2,y1)
M=rasterize([(g,1) for g in mw],out_shape=(H,W),transform=tr,all_touched=True).astype(bool)
print('motorway px',M.sum(), 'B-L in KY p5/p95', np.percentile((B-L)[KY],[1,99]))
s=4; im=cv2.cvtColor(hs(B[::s,::s],6,2*s),cv2.COLOR_GRAY2BGR)
dz=(G-B)[::s,::s]; pos=dz>1; neg=dz<-1
im[pos]=(im[pos]*0.4+np.array([0,140,0])*0.6).astype(np.uint8); im[neg]=(im[neg]*0.4+np.array([200,0,200])*0.6).astype(np.uint8)
z=Z[::s,::s]; im[z&~ndi.binary_erosion(z)]=(0,0,255)
im[ndi.binary_dilation(M[::s,::s])]=(255,120,0)
im[~KY[::s,::s]]=(im[~KY[::s,::s]]*0.6+90).astype(np.uint8)
cv2.imwrite('ky_over.jpg',im,[cv2.IMWRITE_JPEG_QUALITY,85]); print(im.shape)
