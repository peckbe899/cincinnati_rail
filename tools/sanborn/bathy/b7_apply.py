import numpy as np, pickle
from scipy.spatial import cKDTree
from rasterio import features
from affine import Affine
from pyproj import Transformer
FS=146.3; POOL=455*0.3048
bed=np.load('bathy/work/bed_real4.npy'); cl=np.load('bathy/work/cl.npy')
O,Lk=pickle.load(open('topo/canon_river.pkl','rb'))
tr=Affine(4,0,695000,0,-4,4350000); H,W=8750,10000
ohio=features.rasterize([(O,1)],out_shape=(H,W),transform=tr).astype(bool)
P8=cl[:,:2]; f=cl[:,5]; t=cKDTree(P8*2)  # centreline in 8 m px -> 4 m px
m=~np.isnan(bed)
# fill the few nans by nearest valid
from scipy import ndimage as ndi
dom=m|(ohio)
idx=ndi.distance_transform_edt(~m,return_distances=False,return_indices=True)
bedf=bed[idx[0],idx[1]]; bedf[~dom]=np.nan
r,c=np.nonzero(ohio&dom); _,k=t.query(np.c_[r,c]); F=np.ones((H,W),np.float32); F[r,c]=f[k]
canon=np.where(ohio,FS-(FS-bedf)*F,bedf).astype(np.float32)
np.save('bathy/work/bed_canon4.npy',canon); np.save('bathy/work/bed_real4f.npy',bedf)
d=(bedf-canon)[ohio&dom]
print('deepening over Ohio cells: median %.2f  p90 %.2f  max %.2f m'%(np.median(d),np.percentile(d,90),d.max()))
T=Transformer.from_crs(4326,26916,always_xy=True)
def xs(n,a,b):
    (x1,y1),(x2,y2)=T.transform(*a),T.transform(*b); s=np.linspace(0,1,400)
    xx=x1+(x2-x1)*s; yy=y1+(y2-y1)*s; cc=((xx-695000)/4).astype(int); rr=((4350000-yy)/4).astype(int)
    zr=bedf[rr,cc]; zc=canon[rr,cc]; ok=np.isfinite(zc)
    if not ok.any(): print(n,'no river'); return
    print(f'{n:38s} river {ok.sum()/400*np.hypot(x2-x1,y2-y1):4.0f} m  deepest real {np.nanmin(zr):6.1f}  canon {np.nanmin(zc):6.1f} m NAVD88 ({POOL-np.nanmin(zc):4.1f} m below pool)')
xs('RER-2 Roebling-Rivercenter',(-84.50996,39.09598),(-84.50848,39.08994))
xs('RER-4 Pennsylvania-Mansion Hill',(-84.49753,39.10198),(-84.49001,39.09836))
xs('RER-5 Mill Creek-Ludlow',(-84.54229,39.10104),(-84.54809,39.09285))
