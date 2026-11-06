import numpy as np, cv2, rasterio, json
from scipy import ndimage as ndi
from skimage.morphology import area_opening, area_closing
from pilot_common import hs
d=np.load('rw_setup.npz'); L=d['L']; x0=float(d['x0']); y1=float(d['y1']); H,W=d['L'].shape
DM=json.load(open('dem2m.json')); r0=int((DM['y1']-y1)/2); c0=int((x0-DM['x0'])/2)
with rasterio.open('map3_realonly_delta_dm.tif') as ds: dl=ds.read(1,window=rasterio.windows.Window(c0,r0,W,H)).astype(np.float32)/10
sl=(slice(1700,2900),slice(2300,3900))
G=(L+dl)[sl].astype(np.float64); S1=np.load('m3/map3_smooth_base.npy')[sl]
def detr(G, sig, area):
    Tr=ndi.gaussian_filter(G,sig); R=G-Tr
    zi=np.round(R*100).astype(np.int32)
    Rf=area_closing(area_opening(zi,area),area)/100.0
    return Tr+Rf
out=[]
for sig,area in ((25,6000),(40,12000)):
    D1=detr(G,sig,area)
    gy,gx=np.gradient(ndi.gaussian_filter(G,8),2); w=np.clip((0.22-np.hypot(gx,gy))/0.10,0,1)
    D2=w*ndi.gaussian_filter(ndi.median_filter(D1,size=9),1.5)+(1-w)*ndi.gaussian_filter(ndi.median_filter(G,size=9),1.0)
    out.append((f'detrended {sig*2} m, {area*4/1e4:.1f} ha',D2))
tiles=[]
for nm,im in [('LiDAR',G),('current',S1)]+out:
    t=cv2.cvtColor(hs(im,6,2),cv2.COLOR_GRAY2BGR); cv2.putText(t,nm,(10,40),cv2.FONT_HERSHEY_SIMPLEX,1.2,(0,0,0),3); tiles.append(t)
img=np.vstack([np.hstack(tiles[:2]),np.hstack(tiles[2:])])
cv2.imwrite('m3/basin_detr.jpg',cv2.resize(img,(1800,1350),interpolation=cv2.INTER_AREA))
