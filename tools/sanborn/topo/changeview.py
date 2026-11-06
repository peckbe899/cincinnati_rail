import numpy as np, json, cv2, sys
from pyproj import Transformer
DM=json.load(open('dem2m.json')); DEM=np.load('dem2m.npy',mmap_mode='r'); FT=1200/3937
C=np.load('C4m.npy'); cov=np.load('cov4m.npy')
thr=float(sys.argv[1]) if len(sys.argv)>1 else 2.5
Cs=np.sign(C)*np.maximum(0,np.abs(C)-thr)
chg=-Cs                       # modern minus 1912, ft (+ = fill)
# window (UTM) optional
E0,N1,E1,N0=(map(float,sys.argv[2:6]) if len(sys.argv)>5 else (DM['x0'],DM['y1'],DM['x0']+DM['w']*2,DM['y1']-DM['h']*2))
sc=float(sys.argv[6]) if len(sys.argv)>6 else 8.0; out=sys.argv[7] if len(sys.argv)>7 else 'change.png'
c0=int((E0-DM['x0'])/4); c1=int((E1-DM['x0'])/4); r0=int((DM['y1']-N1)/4); r1=int((DM['y1']-N0)/4)
f=int(sc/4)
ch=chg[r0:r1:f,c0:c1:f]; cv_=cov[r0:r1:f,c0:c1:f]
z=np.asarray(DEM[r0*2:r1*2:2*f,c0*2:c1*2:2*f]).astype(np.float32)/10; z[z<-1000]=np.nan
gy,gx=np.gradient(np.nan_to_num(z,nan=np.nanmean(z)),sc); hs=np.clip(0.6+(-gx*0.7+gy*0.7)/np.sqrt(1+gx**2+gy**2)*2.5,0,1)
img=np.dstack([hs*235]*3).astype(np.float32)
a=np.clip(np.abs(ch)/20,0,1)[...,None]; col=np.where(ch[...,None]>0,np.array([40,40,230.]),np.array([230,90,30.]))   # BGR: fill red, cut blue
img=img*(1-a*0.85)+col*a*0.85; img[~cv_]=img[~cv_]*0.6+100
img=img.astype(np.uint8)
T=Transformer.from_crs('EPSG:4326','EPSG:26916',always_xy=True); net=json.load(open('../editor/network.json'))['metro']
for k,pts in net.items():
    p=np.array(pts); e,n=T.transform(p[:,0],p[:,1]); xy=np.c_[(e-E0)/sc,(N1-n)/sc].astype(np.int32)
    cv2.polylines(img,[xy],False,(0,0,0),1,cv2.LINE_AA)
cv2.imwrite(out,img); print(img.shape)
