import numpy as np, cv2
from mlib import *
sid='29'; u0,u1,v0,v1=2100,2850,1250,1850
# z-field at every half-res px in window
uu,vv=np.meshgrid(np.arange(u0,u1,dtype=float),np.arange(v0,v1,dtype=float))
E,N=px2utm(sid,uu.ravel(),vv.ravel()); E=np.array(E);N=np.array(N)
D=DemCrop(E,N,smooth=1.0); z,s=D.sample(E,N); z=z.reshape(uu.shape); s=s.reshape(uu.shape)
np.save('win29_z.npy',z); np.save('win29_s.npy',s)
sk=cv2.imread('contours/29_contours.png',0)[v0:v1,u0:u1]>0
print('px',sk.sum(),'z',z.min(),z.max())
for smin in (0,0.05,0.10,0.15):
    m=sk&(s>smin); r=np.mod(z[m],5)
    h,_=np.histogram(r,bins=10,range=(0,5)); print(smin,m.sum(),(h/h.mean()).round(2))
# chamfer: distance from 1912 px to LiDAR iso-lines at levels where (z+d)%5==0
def iso(z,d,iv=5):
    k=np.floor((z+d)/iv)
    e=np.zeros(z.shape,bool)
    e[:,1:]|=k[:,1:]!=k[:,:-1]; e[1:,:]|=k[1:,:]!=k[:-1,:]
    return e
pts=np.argwhere(sk&(s>0.05))
for d in np.arange(0,5,0.25):
    e=iso(z,d); dt=cv2.distanceTransform((~e).astype(np.uint8),cv2.DIST_L2,5)
    c=np.minimum(dt[pts[:,0],pts[:,1]],8).mean()
    print(f'{d:5.2f} {c:.3f}')
