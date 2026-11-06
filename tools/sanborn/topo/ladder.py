try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, numpy as np, cv2, sys
from PIL import Image
from pyproj import Transformer
Image.MAX_IMAGE_PIXELS=None
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
FT=0.3048
O=(39.128686,-84.521455)   # grid zero, average of the sheet 29 and 30 fits
loc=f"+proj=aeqd +lat_0={O[0]} +lon_0={O[1]} +units=m +datum=WGS84"
ll2loc=Transformer.from_crs("EPSG:4326",loc,always_xy=True)
sheets={'29':("Sheet_29_Mt._Auburn.jpg",{(-5000,2000):(353,576),(6000,2000):(9572,595),(-5000,-6000):(369,7341),(6000,-6000):(9566,7305)}),
        '30':("Sheet_30_Down_Town_Section.jpg",{(-5000,-6000):(273.5,613),(6000,-6000):(9526,648.5),(-5000,-14000):(280,7365),(6000,-14000):(9497.5,7331)})}
line=sys.argv[1]; c0,c1=float(sys.argv[2]),float(sys.argv[3]); sid=sys.argv[4]
d=json.load(open(f'editor/lines/{line}.json'))
P=np.array(d['path']); gd=np.array([np.nan if v is None else v/10 for v in d['ground_dm']]); step=d['step_m']
fn,C=sheets[sid]
G=np.float32(list(C.keys())); X=np.float32(list(C.values()))
H=cv2.getPerspectiveTransform(G,X)
im=np.asarray(Image.open(base+fn).convert('RGB')).astype(int)
cs=np.arange(c0,c1,0.25)
lon=np.interp(cs,P[:,0],P[:,1]); lat=np.interp(cs,P[:,0],P[:,2])
e,n=ll2loc.transform(lon,lat)
px=cv2.perspectiveTransform(np.float32(np.c_[e/FT,n/FT])[None],H)[0]
red=[]
for x,y in px:
    xi,yi=int(round(x)),int(round(y))
    w=im[yi-1:yi+2,xi-1:xi+2].reshape(-1,3)
    r=((w[:,0]-w[:,1]>45)&(w[:,0]-w[:,2]>45)).any()
    red.append(r)
red=np.array(red)
# crossings = centres of red runs
runs=[];i=0
while i<len(red):
    if red[i]:
        j=i
        while j<len(red) and red[j]: j+=1
        runs.append(cs[(i+j-1)//2]); i=j
    else: i+=1
zg=np.interp(runs,np.arange(len(gd))*step,gd)
print(f"{line} {c0:.0f}-{c1:.0f} on sheet {sid}: {len(runs)} red crossings")
prev=None
for c,z in zip(runs,zg):
    k=(z/FT)/5
    print(f"  c={c:8.1f}  LiDAR {z:7.2f} m = {z/FT:7.1f} ft  ({k:6.2f} x 5 ft)  step {'' if prev is None else f'{(z-prev)/FT:+5.1f} ft'}")
    prev=z
