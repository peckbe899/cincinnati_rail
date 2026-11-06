try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import cv2, numpy as np, warnings; warnings.filterwarnings('ignore')
from skimage.morphology import skeletonize, remove_small_objects
from scipy import ndimage as ndi
from mlib import *
im=cv2.imread(_ws.ext('/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/Sheet_29_Mt._Auburn.jpg'))
y0,y1,x0,x1=2300,3800,4000,5800
c=im[y0:y1,x0:x1]
lab=cv2.cvtColor(c,cv2.COLOR_BGR2LAB).astype(np.float32); L,a=lab[...,0],lab[...,1]-128
bga=cv2.medianBlur((a+128).astype(np.uint8),31).astype(np.float32)-128
r=np.clip(a-bga,0,None)
black=(L<100); blackd=cv2.dilate(black.astype(np.uint8),np.ones((7,7),np.uint8)).astype(bool)
m=(r>6)&~blackd; m=remove_small_objects(m,40)
sk=skeletonize(m); sk=remove_small_objects(sk,20,connectivity=2)
ink=cv2.boxFilter(r,-1,(7,7),normalize=False)/7.0
nb=ndi.convolve(sk.astype(int),np.ones((3,3)),mode='constant')-1
seg=sk&(nb<=2); lab_,n=ndi.label(seg,np.ones((3,3)))
idx=np.arange(1,n+1); med=ndi.median(ink,lab_,idx); size=ndi.sum(seg,lab_,idx)
M=np.zeros(n+1); M[1:]=np.where(size>=15,med,0); V=M[lab_]
ys,xs=np.where(V>=57)
# z field over the full window at full-res px (step 1) in local sheet coordinates
H=homog('29'); Hi=np.linalg.inv(H)
gy,gx=np.mgrid[y0:y1,x0:x1].astype(np.float64)
p=cv2.perspectiveTransform(np.c_[gx.ravel(),gy.ravel()][None],Hi)[0]
E,N=loc2utm.transform(p[:,0]*FT,p[:,1]*FT); E=np.array(E);N=np.array(N)
D=DemCrop(E,N); z,s=D.sample(E,N); z=z.reshape(gx.shape); s=s.reshape(gx.shape)
np.save('w29z.npy',z); np.save('w29s.npy',s)
k=s[ys,xs]>0.08
ph=np.mod(z[ys,xs][k],25)/25*2*np.pi
cm=np.angle(np.mean(np.exp(1j*ph)))/2/np.pi*25; R=np.abs(np.mean(np.exp(1j*ph)))
print('circ mean z mod 25 =',round(cm,2),'R',round(R,3),'n',k.sum())
# chamfer vs delta and shift (px, 1 px = 1.0997 ft = 0.335 m)
def iso(z,d,iv):
    q=np.floor((z+d)/iv); e=np.zeros(z.shape,bool)
    e[:,1:]|=q[:,1:]!=q[:,:-1]; e[1:,:]|=q[1:,:]!=q[:-1,:]; return e
pts=np.c_[ys,xs][k]
best=[]
for d in np.arange(-5,5.01,1.0):
    dt=cv2.distanceTransform((~iso(z,d,25)).astype(np.uint8),cv2.DIST_L2,5)
    for dy in range(-30,31,3):
        for dx in range(-30,31,3):
            yy=np.clip(pts[:,0]+dy,0,z.shape[0]-1); xx=np.clip(pts[:,1]+dx,0,z.shape[1]-1)
            best.append((np.minimum(dt[yy,xx],40).mean(),d,dx,dy))
best.sort(); print(best[:8]); 
c0=[b for b in best if b[2]==0 and b[3]==0]; c0.sort(); print('no shift:',[(round(b[0],2),b[1]) for b in c0])
