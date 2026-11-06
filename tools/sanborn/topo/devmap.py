try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, cv2, sys
from geo import S
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
sid=sys.argv[1]; out=sys.argv[2]; sc=4
L=np.load(f'lab/{sid}_labels.npz'); xs=L['inv_x']; ys=L['inv_y']; inv=L['inv']; dev=(L['lab']-L['zmed'])[inv]
im=cv2.imread(base+S[sid]['file']); im=cv2.resize(im,(im.shape[1]//(2*sc)*1,im.shape[0]//(2*sc)),interpolation=cv2.INTER_AREA)
v=(im*0.45+140).astype(np.uint8)
for lo,hi,c in ((-1e9,-12.5,(150,0,0)),(-12.5,-5,(255,140,60)),(-5,5,(0,160,0)),(5,12.5,(60,140,255)),(12.5,1e9,(0,0,170))):
    m=(dev>=lo)&(dev<hi); v[np.clip(ys[m]//sc,0,v.shape[0]-1),np.clip(xs[m]//sc,0,v.shape[1]-1)]=c
cv2.imwrite(out,v); print(v.shape)
