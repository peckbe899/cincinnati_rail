import numpy as np, cv2, pickle, rasterio
from scipy import ndimage as ndi
from rasterio.features import rasterize
from affine import Affine
from pyproj import Transformer
from pilot_common import hs
d=np.load('rw_setup.npz'); L=d['L']; x0=float(d['x0']); y1=float(d['y1']); H,W=L.shape; C=d['C']
KY=np.load('rw_KY.npy'); K12=np.load('ky1912_ground.npy')
O,Lk=pickle.load(open('canon_river.pkl','rb')); tr=Affine(2,0,x0,0,-2,y1)
CL=rasterize([(Lk,1)],out_shape=(H,W),transform=tr).astype(bool)
T=Transformer.from_crs('EPSG:4326','EPSG:26916',always_xy=True)
e,n=T.transform(-84.4941,39.0506); rT=int((y1-n)/2); print('Threemile mouth row',rT,'col',int((e-x0)/2))
WAL=151.8
Wt=C|CL; land=KY&~Wt
dW,ii=ndi.distance_transform_edt(~Wt,return_indices=True); dW*=2
# low land connected to the river below the wall height (1912 ground), within 1.5 km
g=np.where(np.isfinite(K12),K12,L)
low=land&(g<WAL)
lab,nl=ndi.label(low|Wt)
riv=np.unique(lab[Wt]); flood=np.isin(lab,riv)&land
print('KY land below 151.8 m connected to the river: %.2f km2'%(flood.sum()*4e-6))
s=4; im=cv2.cvtColor(hs(g[::s,::s],6,2*s),cv2.COLOR_GRAY2BGR)
f=flood[::s,::s]; im[f]=(im[f]*0.5+np.array([255,120,0])*0.5).astype(np.uint8)
im[Wt[::s,::s]]=(200,170,120); im[(~KY&~Wt)[::s,::s]]=(im[(~KY&~Wt)[::s,::s]]*0.4+150).astype(np.uint8)
cv2.line(im,(0,rT//s),(W//s,rT//s),(0,0,255),1)
for nm,(lo,la) in {'Bromley':(-84.565,39.083),'Ludlow':(-84.548,39.092),'Covington':(-84.51,39.088),'Newport':(-84.493,39.093),'Bellevue':(-84.478,39.105),'Dayton':(-84.462,39.106),'Fredericks Ldg':(-84.4925,39.0501)}.items():
    e,n=T.transform(lo,la); cv2.putText(im,nm,(int((e-x0)/2/s),int((y1-n)/2/s)),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,0,180),2)
cv2.imwrite('ky_flood.jpg',im[600:,:])
np.save('ky_flood.npy',flood); np.save('rw_CL.npy',CL)
