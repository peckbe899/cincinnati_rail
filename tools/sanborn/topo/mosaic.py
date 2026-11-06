try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, numpy as np, cv2, sys
from PIL import Image, ImageDraw
from pyproj import Transformer
Image.MAX_IMAGE_PIXELS=None
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
S=json.load(open('sheets/sheet_index.json'))
O=(39.128686,-84.521455); FT=1200/3937
AEQD=f"+proj=aeqd +lat_0={O[0]} +lon_0={O[1]} +units=m +datum=WGS84"
utm2loc=Transformer.from_crs("EPSG:26916",AEQD,always_xy=True)
ll2utm=Transformer.from_crs("EPSG:4326","EPSG:26916",always_xy=True)
RES=float(sys.argv[1]) if len(sys.argv)>1 else 6.0
box=[float(v) for v in sys.argv[2].split(',')] if len(sys.argv)>2 else None   # utm x0,y0,x1,y1
loc2utm=Transformer.from_crs(AEQD,"EPSG:26916",always_xy=True)
if box is None:
    xs,ys=loc2utm.transform(np.array([-55000,50000,-55000,50000])*FT,np.array([-30000,-30000,42000,42000])*FT)
    box=[min(xs)-300,min(ys)-300,max(xs)+300,max(ys)+300]
x0,y0,x1,y1=box; W=int((x1-x0)/RES); H=int((y1-y0)/RES)
gx=x0+(np.arange(W)+0.5)*RES; gy=y1-(np.arange(H)+0.5)*RES
GX,GY=np.meshgrid(gx,gy)
e,n=utm2loc.transform(GX.ravel(),GY.ravel()); fx=(e/FT).reshape(H,W).astype(np.float32); fy=(n/FT).reshape(H,W).astype(np.float32)
out=np.full((H,W,3),255,np.uint8)
for sid,s in sorted(S.items()):
    inside=(fx>=s['x_w'])&(fx<s['x_e'])&(fy<=s['y_n'])&(fy>s['y_s'])
    if not inside.any(): continue
    G=np.float32([[s['x_w'],s['y_n']],[s['x_e'],s['y_n']],[s['x_w'],s['y_s']],[s['x_e'],s['y_s']]])
    P=np.float32([s['corners'][k] for k in ('TL','TR','BL','BR')])
    Hm=cv2.getPerspectiveTransform(G,P)
    rr,cc=np.where(inside)
    pts=cv2.perspectiveTransform(np.c_[fx[rr,cc],fy[rr,cc]][None].astype(np.float32),Hm)[0]
    im=cv2.imread(base+s['file'])[:,:,::-1]
    # downsample source to roughly the output scale for speed/quality
    k=max(1,int(RES/0.362/1.5)); small=cv2.resize(im,(im.shape[1]//k,im.shape[0]//k),interpolation=cv2.INTER_AREA) if k>1 else im
    mx=(pts[:,0]/k).astype(np.float32); my=(pts[:,1]/k).astype(np.float32)
    N=len(mx); Wd=4096; Hd=(N+Wd-1)//Wd; pad=Hd*Wd-N
    MX=np.pad(mx,(0,pad),constant_values=-1).reshape(Hd,Wd); MY=np.pad(my,(0,pad),constant_values=-1).reshape(Hd,Wd)
    vals=cv2.remap(small,MX,MY,cv2.INTER_LINEAR,borderValue=(255,255,255)).reshape(-1,3)[:N]
    out[rr,cc]=vals
img=Image.fromarray(out); d=ImageDraw.Draw(img)
net=json.load(open('../editor/network.json'))['metro']
for k,pts in net.items():
    ux,uy=ll2utm.transform([p[0] for p in pts],[p[1] for p in pts])
    d.line([((a-x0)/RES,(y1-b)/RES) for a,b in zip(ux,uy)],fill=(0,120,255),width=max(1,int(6/RES*2)))
# sheet edges
for sid,s in S.items():
    cx,cy=loc2utm.transform(np.array([s['x_w'],s['x_e'],s['x_e'],s['x_w'],s['x_w']])*FT,np.array([s['y_n'],s['y_n'],s['y_s'],s['y_s'],s['y_n']])*FT)
    d.line([((a-x0)/RES,(y1-b)/RES) for a,b in zip(cx,cy)],fill=(255,0,180),width=1)
    if RES>=4: d.text(((np.mean(cx[:4])-x0)/RES,(y1-np.mean(cy[:4]))/RES),sid,fill=(255,0,180))
img.save(sys.argv[3] if len(sys.argv)>3 else 'mosaic.png'); print(img.size, box)
