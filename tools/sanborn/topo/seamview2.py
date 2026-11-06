try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, cv2, sys, json
from geo import S, Sheet, FT, loc2utm
from scipy.ndimage import map_coordinates, gaussian_filter
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
DM=json.load(open('dem2m.json')); DEM=np.load('dem2m.npy',mmap_mode='r')
A,B,kind,c,t0,t1=sys.argv[1],sys.argv[2],sys.argv[3],float(sys.argv[4]),float(sys.argv[5]),float(sys.argv[6]); half=float(sys.argv[7]); out=sys.argv[8]
res=1.0
ims={s:cv2.imread(base+S[s]['file']) for s in (A,B)}
if kind=='v':
    gx=np.arange(c-half,c+half,res); gy=np.arange(t1,t0,-res); GX,GY=np.meshgrid(gx,gy); side={A:GX<c,B:GX>=c}
else:
    gx=np.arange(t0,t1,res); gy=np.arange(c+half,c-half,-res); GX,GY=np.meshgrid(gx,gy); side={A:GY>=c,B:GY<c}
img=np.zeros(GX.shape+(3,),np.uint8)
for s in (A,B):
    sh=Sheet(s,coons=True); u,v=sh.g2p(GX.ravel(),GY.ravel())
    w=cv2.remap(ims[s],u.reshape(GX.shape).astype(np.float32),v.reshape(GX.shape).astype(np.float32),cv2.INTER_LINEAR); img[side[s]]=w[side[s]]
# LiDAR iso-lines (25 ft) at the same ground points; optional shift of the ground frame (grid ft) to apply correction
sx=float(sys.argv[9]) if len(sys.argv)>9 else 0; sy=float(sys.argv[10]) if len(sys.argv)>10 else 0
E,N=loc2utm.transform((GX.ravel()+sx)*FT,(GY.ravel()+sy)*FT); E=np.asarray(E);N=np.asarray(N)
r=DM['res']; c0=int((E.min()-50-DM['x0'])/r); c1=int((E.max()+50-DM['x0'])/r)+1; r0=int((DM['y1']-N.max()-50)/r); r1=int((DM['y1']-N.min()+50)/r)+1
a=gaussian_filter(np.asarray(DEM[r0:r1,c0:c1]).astype(np.float32)/10/FT,1.0)
z=map_coordinates(a,[(DM['y1']-N)/r-r0-0.5,(E-DM['x0'])/r-c0-0.5],order=1).reshape(GX.shape)
for iv,col in ((5,(255,200,120)),(25,(200,60,0))):
    q=np.floor(z/iv); e=np.zeros(z.shape,bool); e[:,1:]|=q[:,1:]!=q[:,:-1]; e[1:,:]|=q[1:,:]!=q[:-1,:]
    if iv==5: img[e]=(img[e]*0.4+np.array(col)*0.6).astype(np.uint8)
    else: img[cv2.dilate(e.astype(np.uint8),np.ones((2,2))).astype(bool)]=col
cv2.imwrite(out,img)
