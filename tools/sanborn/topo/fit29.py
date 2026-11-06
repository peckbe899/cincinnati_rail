try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import cv2, numpy as np, csv
from PIL import Image
from pyproj import Transformer
Image.MAX_IMAGE_PIXELS=None
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
Hm=np.load('H29.npy')
corners={'TL':((353,576),(-5000,2000)),'TR':((9572,595),(6000,2000)),'BL':((369,7341),(-5000,-6000)),'BR':((9566,7305),(6000,-6000))}
pj=np.float32([v[0] for v in corners.values()]); gft=np.float32([v[1] for v in corners.values()])
# 1) direct: where is grid (0,0) on the scan?
G2P=cv2.getPerspectiveTransform(gft,pj)
z=cv2.perspectiveTransform(np.float32([[[0,0]]]),G2P)[0,0]; print('grid zero at JPG px',np.round(z,1))
im=Image.open(base+"Sheet_29_Mt._Auburn.jpg")
x,y=map(int,z); im.crop((x-250,y-250,x+250,y+250)).save('z29_zero.png')
# 2) through Ben's georeference
rows=[r for r in csv.reader(open(base+"PNG/29 OTR-Mt Auburn.png.points",encoding='latin-1')) if r and not r[0].startswith('#') and r[0]!='mapX']
g=np.array([[float(v) for v in r[:4]] for r in rows if r[4]=='1'])
lat0,lon0=39.12861,-84.52167
loc=f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +units=m +datum=WGS84"
to_loc=Transformer.from_crs("EPSG:3857",loc,always_xy=True); to_ll=Transformer.from_crs(loc,"EPSG:4326",always_xy=True)
E,N=to_loc.transform(g[:,0],g[:,1]); A=np.c_[g[:,2],-g[:,3],np.ones(len(g))]
ce=np.linalg.lstsq(A,E,rcond=None)[0]; cn=np.linalg.lstsq(A,N,rcond=None)[0]
r=np.hypot(A@ce-E,A@cn-N); print('Ben GCPs',len(g),'affine resid m median',round(float(np.median(r)),1),'max',round(float(r.max()),1))
pp=cv2.perspectiveTransform(pj[None],Hm)[0]; B=np.c_[pp,np.ones(4)]
Y=np.c_[B@ce,B@cn]; X=gft.astype(float)*0.3048
mx,my=X.mean(0),Y.mean(0); U,s,Vt=np.linalg.svd((X-mx).T@(Y-my)); R=(U@Vt).T; sc=s.sum()/((X-mx)**2).sum(); t=my-sc*R@mx
print('scale',round(sc,5),'rot deg',round(np.degrees(np.arctan2(R[1,0],R[0,0])),3),'corner resid m',np.round(np.hypot(*((sc*(R@X.T)).T+t-Y).T),1))
lo,la=to_ll.transform(*t); print('grid origin lat/lon',round(la,6),round(lo,6),' offset from Wikipedia Hughes (m E,N):',np.round(t,1))
