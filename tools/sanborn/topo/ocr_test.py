"""Feasibility: find printed contour elevations (red numerals) on the 1912 sheets and read them with tesseract."""
import numpy as np, cv2, rasterio, pytesseract, sys, json
from rasterio.windows import from_bounds
from scipy import ndimage as ndi
from pilot_common import load
name=sys.argv[1]; d=load(name); X0,Y1,n=d['X0'],d['Y1'],d['n']; W=2.0*n; R=0.5; P=int(W/R)
with rasterio.open('warped/1912_Survey_Mosaic.vrt') as ds:
    w=from_bounds(X0,Y1-W,X0+W,Y1,ds.transform); img=ds.read([1,2,3],window=w,out_shape=(3,P,P),boundless=True,fill_value=255).astype(np.int16)
Rr,G,B=img
red=(Rr-G>35)&(Rr-B>35)&(Rr>120)
lab,k=ndi.label(red,np.ones((3,3)))
sl=ndi.find_objects(lab); area=np.bincount(lab.ravel())
cand=[]
for i,s in enumerate(sl,1):
    if s is None: continue
    h=s[0].stop-s[0].start; wd=s[1].stop-s[1].start
    if 6<=max(h,wd)<=26 and area[i]>=15 and area[i]<=0.7*h*wd: cand.append(((s[0].start+s[0].stop)/2,(s[1].start+s[1].stop)/2,i))
cand=np.array(cand)
# group digit-sized blobs into words (centroids within 14 px)
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
t=cKDTree(cand[:,:2]); pairs=t.query_pairs(14.0,output_type='ndarray')
import scipy.sparse as sp
G_=sp.coo_matrix((np.ones(len(pairs)),(pairs[:,0],pairs[:,1])),shape=(len(cand),len(cand)))
nc,cl=connected_components(G_,directed=False)
words=[np.nonzero(cl==c)[0] for c in range(nc)]
words=[wd for wd in words if 2<=len(wd)<=4]
out=[]
for wd in words:
    pts=cand[wd,:2]; c=pts.mean(0)
    if len(wd)>=2:
        v=np.linalg.svd(pts-c)[2][0]; ang=np.degrees(np.arctan2(v[0],v[1]))   # baseline angle (row,col) -> degrees
    else: ang=0
    r0,c0=int(c[0]),int(c[1]); hw=40
    if r0<hw or c0<hw or r0>P-hw or c0>P-hw: continue
    crop=np.isin(lab[r0-hw:r0+hw,c0-hw:c0+hw],cand[wd,2]).astype(np.uint8)*255
    best=None
    for a in (ang,ang+180):
        M=cv2.getRotationMatrix2D((hw,hw),a,1.0); rot=cv2.warpAffine(crop,M,(2*hw,2*hw))
        ys,xs=np.nonzero(rot)
        if len(ys)==0: continue
        rot=rot[max(ys.min()-4,0):ys.max()+5,max(xs.min()-4,0):xs.max()+5]
        big=cv2.resize(255-rot,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)
        dd=pytesseract.image_to_data(big,config='--psm 7 -c tessedit_char_whitelist=0123456789',output_type=pytesseract.Output.DICT)
        txt=''.join(dd['text']).strip(); conf=max([float(x) for x in dd['conf'] if x not in ('-1',-1)] or [0])
        if txt and (best is None or conf>best[1]): best=(txt,conf)
    if best:
        E=X0+(c[1]+0.5)*R; N=Y1-(c[0]+0.5)*R
        out.append((E,N,best[0],best[1]))
vals=[o for o in out if o[2].isdigit() and len(o[2])==3 and int(o[2])%5==0 and 400<=int(o[2])<=1000 and o[3]>=60]
print(f'{name}: red digit-sized blobs {len(cand)}, word candidates {len(words)}, read {len(out)}, plausible elevations {len(vals)}')
print(' sample:',[(v[2],round(v[3])) for v in vals[:25]])
json.dump([list(map(float,v[:2]))+[int(v[2]),float(v[3])] for v in vals],open(f'ocr_{name}.json','w'))
