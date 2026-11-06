try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, cv2, sys
from geo import S
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
sid=sys.argv[1]; x0,y0,x1,y1=map(int,sys.argv[2:6]); out=sys.argv[6]; key=sys.argv[7] if len(sys.argv)>7 else 'lab'
L=np.load(f'lab/{sid}_labels.npz'); xs=L['inv_x']; ys=L['inv_y']; inv=L['inv']; lab=L[key] if key!='dev' else L['lab']-L['zmed']
im=cv2.imread(base+S[sid]['file']); im=cv2.resize(im,(im.shape[1]//2,im.shape[0]//2),interpolation=cv2.INTER_AREA)
v=(im[y0:y1,x0:x1]*0.5+127).astype(np.uint8); v=cv2.resize(v,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC)
sel=(xs>=x0)&(xs<x1)&(ys>=y0)&(ys<y1)
cols=[(0,0,255),(0,160,255),(0,200,0),(255,120,0),(200,0,200)]
for x,y,k in zip(xs[sel],ys[sel],inv[sel]):
    if key=='dev':
        dv=lab[k]; c=(0,0,255) if dv>5 else (255,0,0) if dv<-5 else (0,170,0)
    else: c=cols[int(lab[k]//5)%5]
    cv2.circle(v,((x-x0)*2,(y-y0)*2),1,c,-1)
done=set()
for k in np.unique(inv[sel]):
    m=sel&(inv==k)
    if m.sum()<25: continue
    i=np.nonzero(m)[0][m.sum()//2]
    t=f"{int(lab[k])}" if key!='dev' else f"{lab[k]:+.0f}"
    cv2.putText(v,t,((xs[i]-x0)*2+3,(ys[i]-y0)*2-3),0,0.38,(0,0,0),1)
cv2.imwrite(out,v)
