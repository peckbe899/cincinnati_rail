import numpy as np, json, cv2, sys
from pyproj import Transformer
DM=json.load(open('dem2m.json')); R=4.0
zA=np.load('zoneA4m.npy'); zB=np.load('zoneB4m.npy'); zone=np.load('zone4m.npy'); sl=np.load('slope4m.npy')
E0,N1,E1,N0,f,out=float(sys.argv[1]),float(sys.argv[2]),float(sys.argv[3]),float(sys.argv[4]),int(sys.argv[5]),sys.argv[6]
c0=int((E0-DM['x0'])/R); c1=int((E1-DM['x0'])/R); r0=int((DM['y1']-N1)/R); r1=int((DM['y1']-N0)/R)
DEM=np.load('dem2m.npy',mmap_mode='r'); z=np.asarray(DEM[r0*2:r1*2:2*f,c0*2:c1*2:2*f]).astype(np.float32)/10
gy,gx=np.gradient(z,R*f); hs=np.clip(0.55+(-gx+gy)*0.7/np.sqrt(1+gx**2+gy**2)*1.6,0,1)
img=(np.dstack([hs]*3)*230).astype(np.float32)
for m,col,al in ((zB[r0:r1:f,c0:c1:f],(200,0,200),0.55),(zA[r0:r1:f,c0:c1:f],(0,140,255),0.55)):
    img[m]=img[m]*(1-al)+np.array(col)*al
img=img.astype(np.uint8)
zz=zone[r0:r1:f,c0:c1:f].astype(np.uint8); cs,_=cv2.findContours(zz,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE); cv2.drawContours(img,cs,-1,(0,0,200),1)
T=Transformer.from_crs('EPSG:4326','EPSG:26916',always_xy=True)
for k,pts in json.load(open('../editor/network.json'))['metro'].items():
    p=np.array(pts); e,n=T.transform(p[:,0],p[:,1]); cv2.polylines(img,[np.c_[(e-E0)/(R*f),(N1-n)/(R*f)].astype(np.int32)],False,(30,30,30),2,cv2.LINE_AA)
cv2.imwrite(out,img); print(img.shape)
