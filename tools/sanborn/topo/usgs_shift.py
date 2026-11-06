try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import rasterio, numpy as np, cv2, json, sys
from pyproj import Transformer
from scipy.ndimage import map_coordinates, gaussian_filter
from skimage.morphology import skeletonize
DM=json.load(open('dem2m.json')); DEM=np.load('dem2m.npy',mmap_mode='r'); FT=1200/3937
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/USGS_Historical/")
def window_shift(s,c,r,half,iv,R=40,step=1):
    w=rasterio.windows.Window(c-half,r-half,2*half,2*half)
    img=np.dstack([s.read(i,window=w,boundless=True) for i in (3,2,1)])
    lab=cv2.cvtColor(img,cv2.COLOR_BGR2LAB).astype(np.float32); L,a,b=lab[...,0],lab[...,1]-128,lab[...,2]-128
    brown=(a>8)&(b>15)&(L>60)&(L<200)&(a<45)     # contour brown, not red roads
    brown=cv2.morphologyEx(brown.astype(np.uint8),cv2.MORPH_OPEN,np.ones((2,2),np.uint8)).astype(bool)
    sk=skeletonize(brown)
    tr=s.window_transform(w); H,W=sk.shape
    yy,xx=np.mgrid[0:H,0:W]; X=tr.c+(xx+0.5)*tr.a; Y=tr.f+(yy+0.5)*tr.e
    U=Transformer.from_crs(s.crs,'EPSG:26916',always_xy=True); E,N=U.transform(X.ravel(),Y.ravel()); E=np.asarray(E).reshape(H,W); N=np.asarray(N).reshape(H,W)
    px=abs(tr.a)
    # LiDAR on a grid extended by R px
    pad=R; ex=np.arange(-pad,W+pad); ey=np.arange(-pad,H+pad)
    EE=tr.c+(ex[None,:]+0.5)*tr.a+0*ey[:,None]; NN=tr.f+(ey[:,None]+0.5)*tr.e+0*ex[None,:]
    Eu,Nu=U.transform(EE.ravel(),NN.ravel()); Eu=np.asarray(Eu); Nu=np.asarray(Nu)
    r_=DM['res']; c0=int((Eu.min()-30-DM['x0'])/r_); r0=int((DM['y1']-Nu.max()-30)/r_)
    a_=np.asarray(DEM[r0:r0+int((Nu.max()-Nu.min())/r_)+60,c0:c0+int((Eu.max()-Eu.min())/r_)+60]).astype(np.float32)
    if (a_==DM['nodata']).mean()>0.2: return None
    a_=gaussian_filter(a_/10/FT,1.0)
    z=map_coordinates(a_,[(DM['y1']-Nu)/r_-r0-0.5,(Eu-DM['x0'])/r_-c0-0.5],order=1).reshape(EE.shape)
    gy,gx=np.gradient(z,px/FT); sl=np.hypot(gx,gy)
    q=np.floor(z/iv); e=np.zeros(z.shape,bool); e[:,1:]|=q[:,1:]!=q[:,:-1]; e[1:,:]|=q[1:,:]!=q[:-1,:]
    dt=np.minimum(cv2.distanceTransform((~e).astype(np.uint8),cv2.DIST_L2,5),15)
    pys,pxs=np.nonzero(sk); keep=sl[pys+pad,pxs+pad]>0.08; pys,pxs=pys[keep],pxs[keep]
    if len(pys)<500: return None
    best=None; C=np.zeros((2*R//step+1,2*R//step+1))
    for i,dy in enumerate(range(-R,R+1,step)):
        for j,dx in enumerate(range(-R,R+1,step)):
            C[i,j]=dt[pys+pad+dy,pxs+pad+dx].mean()
    i,j=np.unravel_index(np.argmin(C),C.shape); dy=(i*step-R); dx=(j*step-R)
    # shift in metres (sheet px -> ground): content at p matches LiDAR at p+(dx,dy)
    return dx*px, -dy*px, float(C[R//step,R//step]), float(C.min()), len(pys)
if __name__=='__main__':
    f=sys.argv[1]; iv=float(sys.argv[2]); half=int(sys.argv[3]); R=int(sys.argv[4])
    with rasterio.open(base+f) as s:
        H,W=s.height,s.width
        for fy in (0.25,0.45,0.65):
            for fx in (0.25,0.5,0.75):
                res=window_shift(s,int(W*fx),int(H*fy),half,iv,R)
                if res: print(f'{fx:.2f},{fy:.2f}  shift E {res[0]:6.1f} m  N {res[1]:6.1f} m  cost {res[2]:.2f}->{res[3]:.2f}  n {res[4]}',flush=True)
