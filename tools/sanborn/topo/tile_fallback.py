"""No usable 1912 contours in this tile: write a stand-in S1912 (smoothed LiDAR, no cover) so I4 runs as cleaned LiDAR."""
import numpy as np, json, sys
from scipy import ndimage as ndi
name=sys.argv[1]; t=json.load(open('tiles.json'))[name]; DM=json.load(open('dem2m.json'))
X0=t['cx']-1700; Y1=t['cy']+1700; n=850
DEM=np.load('dem2m.npy',mmap_mode='r'); c0=int((X0-DM['x0'])/2); r0=int((DM['y1']-Y1)/2)
L=np.asarray(DEM[r0:r0+2*n:2,c0:c0+2*n:2]).astype(np.float32)/10; S=ndi.gaussian_filter(L,3)
np.savez_compressed(f'pilot_{name}_S1912.npz',cov=np.zeros((n,n),bool),S=S,lo=S-1e3,hi=S+1e3,X0=X0,Y1=Y1,R=4.0)
z=np.zeros((1,),float); np.savez_compressed(f'pilot_{name}_labels2.npz',E=z,N=z,inv=np.zeros(1,int),lab=np.full(1,np.nan),isb=np.zeros(1,bool),zmed=z,cnt=np.ones(1,int),X0=X0,Y1=Y1,W=3400)
