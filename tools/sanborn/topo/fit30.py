try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import cv2, numpy as np, csv
from PIL import Image
from pyproj import Transformer
Image.MAX_IMAGE_PIXELS=None
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
S=0.3
def load(p):
    im=Image.open(p).convert('L'); w,h=im.size
    return np.asarray(im.resize((int(w*S),int(h*S)),Image.LANCZOS)), (w,h)
J,_=load(base+"Sheet_30_Down_Town_Section.jpg")
P,_=load(base+"PNG/30 Downtown.png")
sift=cv2.SIFT_create(nfeatures=20000)
kj,dj=sift.detectAndCompute(J,None); kp,dp=sift.detectAndCompute(P,None)
m=cv2.BFMatcher().knnMatch(dj,dp,k=2)
good=[a for a,b in m if a.distance<0.75*b.distance]
src=np.float32([kj[g.queryIdx].pt for g in good])/S; dst=np.float32([kp[g.trainIdx].pt for g in good])/S
Hm,mask=cv2.findHomography(src,dst,cv2.RANSAC,6.0)
inl=mask.ravel().astype(bool); res=np.linalg.norm(cv2.perspectiveTransform(src[inl][None],Hm)[0]-dst[inl],axis=1)
print('matches',len(good),'inliers',inl.sum(),'median resid px',round(float(np.median(res)),2))
print("homography",np.round(Hm,4).tolist())
# Ben's GCPs: PNG pixel -> EPSG:3857 ; convert to local aeqd metres
rows=[r for r in csv.reader(open(base+"PNG/working/30 Downtown.png.points",encoding="latin-1")) if r and not r[0].startswith('#') and r[0]!='mapX']
g=np.array([[float(x) for x in r[:4]] for r in rows if r[4]=='1'])
lat0,lon0=39.12861,-84.52167
to_loc=Transformer.from_crs("EPSG:3857",f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +units=m +datum=WGS84",always_xy=True)
to_ll=Transformer.from_crs(f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +units=m +datum=WGS84","EPSG:4326",always_xy=True)
E,N=to_loc.transform(g[:,0],g[:,1]); px=g[:,2]; py=-g[:,3]
A=np.c_[px,py,np.ones_like(px)]
ce,_,_,_=np.linalg.lstsq(A,E,rcond=None); cn,_,_,_=np.linalg.lstsq(A,N,rcond=None)
r=np.hypot(A@ce-E,A@cn-N); print('Ben GCPs',len(px),'affine resid m: median',round(float(np.median(r)),1),'max',round(float(r.max()),1))
# grid corners in JPG pixels and their survey coordinates (ft; x east, y north; south negative)
corners={'TL':((273.5,613),(-5000,-6000)),'TR':((9526,648.5),(6000,-6000)),'BL':((280,7365),(-5000,-14000)),'BR':((9497.5,7331),(6000,-14000))}
pj=np.float32([v[0] for v in corners.values()]); gxy=np.array([v[1] for v in corners.values()],float)*0.3048
pp=cv2.perspectiveTransform(pj[None],Hm)[0]
WE=np.c_[pp[:,0],pp[:,1],np.ones(4)]@ce; WN=np.c_[pp[:,0],pp[:,1],np.ones(4)]@cn
# similarity fit grid(m) -> local world
X=gxy; Y=np.c_[WE,WN]
mx,my=X.mean(0),Y.mean(0); Xc,Yc=X-mx,Y-my
U,s,Vt=np.linalg.svd(Xc.T@Yc); R=(U@Vt).T
if np.linalg.det(R)<0: Vt[-1]*=-1; R=(U@Vt).T
scale=s.sum()/ (Xc**2).sum()
t=my-scale*R@mx
rot=np.degrees(np.arctan2(R[1,0],R[0,0]))
fit=(scale*(R@X.T)).T+t; print('corner fit resid m', np.round(np.hypot(*(fit-Y).T),1))
print('scale (1 = feet are exact)',round(scale,5),' rotation deg (CCW of true north)',round(rot,3))
ox,oy=t; lon,lat=to_ll.transform(ox,oy)
print('grid origin in local m from Wikipedia Hughes coords:',round(ox,1),round(oy,1),' -> lat/lon',round(lat,6),round(lon,6))
for k,(e,n) in zip(corners,Y): 
    lo,la=to_ll.transform(e,n); print(k,round(la,6),round(lo,6))
