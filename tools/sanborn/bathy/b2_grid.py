import numpy as np, pickle
from rasterio import features
from affine import Affine
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import cKDTree
from scipy import ndimage as ndi
from shapely.ops import unary_union
P=np.load('bathy/work/pts.npy')
O,Lk=pickle.load(open('topo/canon_river.pkl','rb'))
X0,Y1,RES=695000,4350000,4.0; W,H=10000,8750
tr=Affine(RES,0,X0,0,-RES,Y1)
U=unary_union([O,Lk])
dom=features.rasterize([(U,1)],out_shape=(H,W),transform=tr).astype(bool)
print('domain km2',dom.sum()*16/1e6)
# edge points every 8 m on boundary, only where no survey within 40 m
t=cKDTree(P[:,:2])
from shapely.geometry import box
B=U.intersection(box(X0,Y1-H*RES,X0+W*RES,Y1)).boundary
L=B.length; s=np.arange(0,L,8.0); E=np.array([B.interpolate(v).coords[0] for v in s])
d,_=t.query(E); E=E[d>40]
# no pool-level edge points along the canon Embankment wall: the wall stands in today's river, so the bed there comes from the soundings
import rasterio
with rasterio.open('topo/map3_riverworks_mode.tif') as s_: tm=s_.read(1); tt=s_.transform
wall=ndi.binary_dilation(tm==1,iterations=15)   # 30 m
ci=((E[:,0]-tt.c)/tt.a).astype(int); ri=((E[:,1]-tt.f)/tt.e).astype(int)
ok=(ri>=0)&(ri<tm.shape[0])&(ci>=0)&(ci<tm.shape[1])
nearwall=np.zeros(len(E),bool); nearwall[ok]=wall[ri[ok],ci[ok]]
print('edge points dropped at the wall',nearwall.sum()); E=E[~nearwall]
POOL=455.0*0.3048
pts=np.vstack([P[:,:2],E]); z=np.r_[P[:,2],np.full(len(E),POOL)]
f=LinearNDInterpolator(pts,z)
r,c=np.nonzero(dom); x=X0+(c+0.5)*RES; y=Y1-(r+0.5)*RES
zz=f(x,y)
bed=np.full((H,W),np.nan,np.float32); bed[r,c]=zz
dist,_=t.query(np.c_[x,y]); D=np.full((H,W),np.nan,np.float32); D[r,c]=dist
np.save('bathy/work/bed_real4.npy',bed); np.save('bathy/work/dist4.npy',D)
print('edge pts',len(E),'nan in domain',np.isnan(zz).sum(),'dist>100m km2',(dist>100).sum()*16/1e6,'dist>300m km2',(dist>300).sum()*16/1e6)
