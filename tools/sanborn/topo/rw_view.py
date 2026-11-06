import numpy as np, json, cv2, sys
from pyproj import Transformer
from pilot_common import hs
T=Transformer.from_crs('EPSG:4326','EPSG:26916',always_xy=True)
d=np.load('rw_setup.npz'); o=np.load('rw_out.npz'); x0=float(d['x0']); y1=float(d['y1'])
L=d['L']; S12=d['S12']; base2=np.where(np.isfinite(S12),S12,L)
def crop(a,lon,lat,hw,hh):
    e,n=T.transform(lon,lat); c=int((e-x0)/2); r=int((y1-n)/2); return a[max(r-hh,0):r+hh,max(c-hw,0):c+hw]
def panel(name,lon,lat,hw,hh,before,after,mode,z=3.0,scale=1):
    b=crop(before,lon,lat,hw,hh); a=crop(after,lon,lat,hw,hh); m=crop(mode,lon,lat,hw,hh)
    ib=cv2.cvtColor(hs(b,z,2),cv2.COLOR_GRAY2BGR); ia=cv2.cvtColor(hs(a,z,2),cv2.COLOR_GRAY2BGR)
    edge=(m>0)&~cv2.erode((m>0).astype(np.uint8),np.ones((3,3))).astype(bool); ia[edge]=(0,0,230)
    im=np.hstack([ib,np.full((ib.shape[0],6,3),255,np.uint8),ia])
    if scale!=1: im=cv2.resize(im,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA)
    cv2.imwrite(name,im,[cv2.IMWRITE_JPEG_QUALITY,85])
panel('rw3_deck.jpg',-84.5420,39.1210,700,1050,L,o['G3'],o['M3'],scale=0.6)
panel('rw3_downtown.jpg',-84.515,39.0985,1300,450,L,o['G3'],o['M3'],scale=0.55)
panel('rw3_lunken.jpg',-84.425,39.085,900,1000,L,o['G3'],o['M3'],scale=0.6)
panel('rw2_downtown.jpg',-84.522,39.100,1300,500,base2,o['G2'],o['M2'],scale=0.55)
