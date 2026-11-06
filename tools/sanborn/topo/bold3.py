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
for name,sel in (('bold',V>=57),('thin',(V>0)&(V<57))):
    ys,xs=np.where(sel)
    E,N=px2utm('29',(xs+x0)/2.0,(ys+y0)/2.0); E=np.array(E);N=np.array(N)
    D=DemCrop(E,N); z,s=D.sample(E,N)
    for smin in (0.0,0.08,0.15):
        k=s>smin
        per=25 if name=='bold' else 5
        h,_=np.histogram(np.mod(z[k],per),bins=10,range=(0,per))
        print(name,smin,k.sum(),(h/h.mean()).round(2))
