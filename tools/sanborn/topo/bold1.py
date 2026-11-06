try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import cv2, numpy as np
from skimage.morphology import skeletonize, remove_small_objects
im=cv2.imread(_ws.ext('/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/Sheet_29_Mt._Auburn.jpg'))
y0,y1,x0,x1=2300,3800,4000,5800
c=im[y0:y1,x0:x1]
lab=cv2.cvtColor(c,cv2.COLOR_BGR2LAB).astype(np.float32); L,a,b=lab[...,0],lab[...,1]-128,lab[...,2]-128
bga=cv2.medianBlur((a+128).astype(np.uint8),31).astype(np.float32)-128
bgL=cv2.medianBlur(L.astype(np.uint8),31).astype(np.float32)
r=np.clip(a-bga,0,None); d=np.clip(bgL-L,0,None)
black=(L<100); blackd=cv2.dilate(black.astype(np.uint8),np.ones((7,7),np.uint8)).astype(bool)
m=(r>6)&~blackd
m=remove_small_objects(m,40)
sk=skeletonize(m); sk=remove_small_objects(sk,20,connectivity=2)
dt=cv2.distanceTransform(m.astype(np.uint8),cv2.DIST_L2,5)
# smoothed darkness along skeleton
rs=cv2.GaussianBlur(r,(0,0),1.0)
ys,xs=np.where(sk)
w=dt[ys,xs]*2; pk=rs[ys,xs]; dk=d[ys,xs]
print('width pct',np.percentile(w,[10,25,50,75,90,97]).round(2))
print('peak r pct',np.percentile(pk,[10,25,50,75,90,97]).round(1))
h,e=np.histogram(w,bins=20,range=(0,10)); print(h)
h,e=np.histogram(pk,bins=20,range=(0,40)); print(h)
# visualize: color skeleton by width
vis=c.copy()//2+127
col=np.zeros_like(c); 
vis[sk&(dt*2<3.5)]=(255,150,0); vis[sk&(dt*2>=3.5)]=(0,0,255)
cv2.imwrite('bold1.png',vis)
np.save('bold1_r.npy',r)
