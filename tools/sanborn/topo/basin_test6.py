import numpy as np, cv2, rasterio, json
from scipy import ndimage as ndi
from skimage.morphology import area_opening, area_closing, disk
from pilot_common import hs
d=np.load('rw_setup.npz'); L=d['L']; x0=float(d['x0']); y1=float(d['y1']); H,W=d['L'].shape
DM=json.load(open('dem2m.json')); r0=int((DM['y1']-y1)/2); c0=int((x0-DM['x0'])/2)
with rasterio.open('map3_realonly_delta_dm.tif') as ds: dl=ds.read(1,window=rasterio.windows.Window(c0,r0,W,H)).astype(np.float32)/10
sl=(slice(1500,3100),slice(2100,3900)); G=(L+dl)[sl].astype(np.float64); S=np.load('m3/map3_smooth_base.npy')[sl]
Tr=ndi.gaussian_filter(G,40); R=G-Tr
gy,gx=np.gradient(ndi.gaussian_filter(G,8),2); w=np.clip((0.12-np.hypot(gx,gy))/0.06,0,1)
Rc=ndi.grey_closing(R,footprint=disk(6)); Rc=w*Rc+(1-w)*R
zi=np.round(Rc*100).astype(np.int32); D1=Tr+area_closing(area_opening(zi,12000),12000)/100.0
X=ndi.gaussian_filter(ndi.median_filter(D1,size=9),1.5)
np.save('m3/test_X.npy',X.astype(np.float32))
def tile(im,nm):
    t=cv2.cvtColor(hs(im,6,2,) if False else hs(im,6,2),cv2.COLOR_GRAY2BGR); cv2.putText(t,nm,(10,40),cv2.FONT_HERSHEY_SIMPLEX,1.2,(0,0,0),3); return t
cv2.imwrite('m3/basin_close.jpg',cv2.resize(np.hstack([tile(S[200:1200,0:1000],'current'),tile(X[200:1200,0:1000],'+ 24 m closing on flat ground')]),(1600,800),interpolation=cv2.INTER_AREA))
