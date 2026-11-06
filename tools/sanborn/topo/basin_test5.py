import numpy as np, cv2, rasterio, json
from scipy import ndimage as ndi
from skimage.morphology import area_opening, area_closing
from pilot_common import hs
d=np.load('rw_setup.npz'); L=d['L']; x0=float(d['x0']); y1=float(d['y1']); H,W=d['L'].shape
DM=json.load(open('dem2m.json')); r0=int((DM['y1']-y1)/2); c0=int((x0-DM['x0'])/2)
with rasterio.open('map3_realonly_delta_dm.tif') as ds: dl=ds.read(1,window=rasterio.windows.Window(c0,r0,W,H)).astype(np.float32)/10
G0=L+dl
def detr(G, sig=40, area=12000):
    Tr=ndi.gaussian_filter(G,sig); zi=np.round((G-Tr)*100).astype(np.int32)
    return Tr+area_closing(area_opening(zi,area),area)/100.0
rows=[]
for (a,b,c,e,nm) in ((1700,2500,3100,4100,'hillside'),(900,1700,5600,6600,'East Walnut Hills'),(2300,3100,300,1300,'west')):
    G=G0[a-200:b+200,c-200:e+200].astype(np.float64); D1=detr(G)
    gy,gx=np.gradient(ndi.gaussian_filter(G,8),2); w=np.clip((0.22-np.hypot(gx,gy))/0.10,0,1)
    A=w*ndi.gaussian_filter(ndi.median_filter(D1,size=9),1.5)+(1-w)*ndi.gaussian_filter(ndi.median_filter(G,size=9),1.0)
    B=ndi.gaussian_filter(ndi.median_filter(D1,size=9),1.5)
    ims=[G,A,B]; nms=[nm+' LiDAR','detrended on gentle ground only','detrended everywhere']
    t=[]
    for im,n_ in zip(ims,nms):
        x=cv2.cvtColor(hs(im[200:-200,200:-200],6,2),cv2.COLOR_GRAY2BGR); cv2.putText(x,n_,(10,40),cv2.FONT_HERSHEY_SIMPLEX,1.1,(0,0,0),3); t.append(x)
    rows.append(np.hstack(t))
cv2.imwrite('m3/basin_detr2.jpg',cv2.resize(np.vstack(rows),(1800,1440),interpolation=cv2.INTER_AREA))
