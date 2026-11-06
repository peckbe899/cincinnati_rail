import numpy as np, cv2, rasterio
from scipy import ndimage as ndi
from pyproj import Transformer
from pilot_common import hs
d=np.load('rw_setup.npz'); L=d['L']; x0=float(d['x0']); y1=float(d['y1']); H,W=L.shape
KY=np.load('rw_KY.npy'); Z=np.load('rw_Zall.npy')&KY
G=np.load('ky1912_ground.npy')
with rasterio.open('I4_1912_ground_dm.tif') as ds:
    a=ds.read(1,window=rasterio.windows.from_bounds(x0,y1-2*H,x0+2*W,y1,ds.transform),boundless=True,fill_value=-32768)[:H,:W]
B=np.where(a>-30000,a/10.0,L).astype(np.float32)
G=np.where(np.isfinite(G),G,B)
T=Transformer.from_crs('EPSG:4326','EPSG:26916',always_xy=True)
def crop(lon,lat,half=1300):
    e,n=T.transform(lon,lat); c=int((e-x0)/2); r=int((y1-n)/2); h=half//2
    return slice(max(0,r-h),r+h), slice(max(0,c-h),c+h)
def panel(Zm,sl,zone):
    im=cv2.cvtColor(hs(Zm[sl],6,2),cv2.COLOR_GRAY2BGR)
    zb=zone[sl]; e=zb&~ndi.binary_erosion(zb,iterations=2); im[e]=(0,0,255)
    # 20 ft contours
    ft=Zm[sl]/(1200/3937); q=np.floor(ft/20)
    ce=(q!=np.roll(q,1,0))|(q!=np.roll(q,1,1)); im[ce]=(im[ce]*0.4+np.array([40,90,160])*0.6).astype(np.uint8)
    return im
rows=[]
for name,(lon,lat) in {'Covington cut':(-84.522,39.062),'Newport':(-84.488,39.085),'Bellevue/Dayton':(-84.468,39.100)}.items():
    sl=crop(lon,lat)
    p=np.hstack([panel(B,sl,Z),np.full((1300,10,3),255,np.uint8),panel(G,sl,Z)])
    cv2.putText(p,name+'  I4 base | 1912 rebuild',(10,40),cv2.FONT_HERSHEY_SIMPLEX,1.2,(0,0,0),3)
    rows.append(p)
out=np.vstack(rows); cv2.imwrite('ky_check.jpg',cv2.resize(out,(out.shape[1]//2,out.shape[0]//2),interpolation=cv2.INTER_AREA),[cv2.IMWRITE_JPEG_QUALITY,85])
