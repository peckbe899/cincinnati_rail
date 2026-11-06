import numpy as np, cv2, time
from scipy import ndimage as ndi
from skimage.morphology import area_opening, area_closing, disk, reconstruction
from pilot_common import hs
G=np.load('map3_window_ground.npy')[1400:3000,2000:4400].astype(np.float64)
zi=np.round(G*100).astype(np.int32)
out={}
t=time.time()
A=area_closing(area_opening(zi,4000),4000)/100.0; out['area 1.6 ha']=A; print('area',time.time()-t)
A2=area_closing(area_opening(zi,12000),12000)/100.0; out['area 4.8 ha']=A2
M=ndi.median_filter(G,size=13); out['median 26 m']=M
# opening/closing by reconstruction, 15 m radius disk
se=disk(8)
er=ndi.grey_erosion(G,footprint=se); op=reconstruction(er,G,method='dilation')
di=ndi.grey_dilation(op,footprint=se); oc=reconstruction(di,op,method='erosion'); out['reconstruct 16 m']=oc
names=['LiDAR']+list(out); ims=[G]+list(out.values())
tiles=[]
for nm,im in zip(names,ims):
    t_=cv2.cvtColor(hs(ndi.gaussian_filter(im,0.7),6,2),cv2.COLOR_GRAY2BGR)[200:1000,600:1800]
    cv2.putText(t_,nm,(10,40),cv2.FONT_HERSHEY_SIMPLEX,1.2,(0,0,0),3); tiles.append(t_)
row1=np.hstack(tiles[:3]); row2=np.hstack(tiles[3:]+[np.full_like(tiles[0],255)]*(6-len(tiles)))
cv2.imwrite('m3/basin_variants.jpg',cv2.resize(np.vstack([row1,row2]),(1800,800),interpolation=cv2.INTER_AREA))
np.savez('m3/basin_variants.npz',**{k.replace(' ','_'):v.astype(np.float32) for k,v in out.items()})
