import numpy as np, cv2, json
from pyproj import Transformer
from scipy.ndimage import map_coordinates, gaussian_filter
S=json.load(open('sheets/sheet_index.json'))
O=(39.128686,-84.521455); FT=1200/3937
AEQD=f"+proj=aeqd +lat_0={O[0]} +lon_0={O[1]} +units=m +datum=WGS84"
loc2utm=Transformer.from_crs(AEQD,"EPSG:26916",always_xy=True)
utm2loc=Transformer.from_crs("EPSG:26916",AEQD,always_xy=True)
DM=json.load(open('dem2m.json')); DEM=np.load('dem2m.npy',mmap_mode='r')
K=2
def homog(sid):
    s=S[sid]
    G=np.float32([[s['x_w'],s['y_n']],[s['x_e'],s['y_n']],[s['x_w'],s['y_s']],[s['x_e'],s['y_s']]])
    P=np.float32([s['corners'][k] for k in ('TL','TR','BL','BR')])
    return cv2.getPerspectiveTransform(G,P)   # grid ft -> full px
def px2utm(sid,u,v):
    """half-res sheet px -> UTM (initial grid georeference)"""
    Hi=np.linalg.inv(homog(sid))
    p=cv2.perspectiveTransform(np.c_[u*K,v*K][None].astype(np.float64),Hi)[0]
    return loc2utm.transform(p[:,0]*FT,p[:,1]*FT)
def utm2px(sid,E,N):
    e,n=utm2loc.transform(E,N)
    p=cv2.perspectiveTransform(np.c_[e/FT,n/FT][None].astype(np.float64),homog(sid))[0]
    return p[:,0]/K,p[:,1]/K
class DemCrop:
    def __init__(self,E,N,margin=150,smooth=1.0):
        x0=DM['x0'];y1=DM['y1'];r=DM['res']
        c0=int((E.min()-margin-x0)/r); c1=int((E.max()+margin-x0)/r)+1
        r0=int((y1-N.max()-margin)/r); r1=int((y1-N.min()+margin)/r)+1
        a=np.asarray(DEM[r0:r1,c0:c1]).astype(np.float32)
        bad=a==DM['nodata']; a[bad]=np.nan
        self.z=a/10/FT                      # feet NAVD88
        if smooth: self.z=gaussian_filter(np.nan_to_num(self.z,nan=np.nanmean(self.z)),smooth)
        gy,gx=np.gradient(self.z,r/FT)       # ft per ft
        self.s=np.hypot(gx,gy)
        self.c0,self.r0,self.res=c0,r0,r
    def rc(self,E,N):
        return (DM['y1']-N)/self.res-self.r0-0.5,(E-DM['x0'])/self.res-self.c0-0.5
    def sample(self,E,N):
        r,c=self.rc(E,N)
        return map_coordinates(self.z,[r,c],order=1,mode='nearest'),map_coordinates(self.s,[r,c],order=1,mode='nearest')
def lattice_cost(z,s,delta,interval=5.0,smin=0.04,cap=25.0):
    r=(z+delta)/interval; r=np.abs(r-np.round(r))*interval      # vertical miss, ft
    d=r/np.maximum(s,smin)                                       # horizontal miss, ft
    return np.minimum(d,cap)
def contour_pts(sid,step=1):
    sk=cv2.imread(f'contours/{sid}_contours.png',0)>0
    v,u=np.where(sk); 
    if step>1: v,u=v[::step],u[::step]
    return u.astype(np.float64),v.astype(np.float64)
