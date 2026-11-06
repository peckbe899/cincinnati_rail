try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, cv2, sys
from geo import S, Sheet
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
A,B,kind,c,t0,t1=sys.argv[1],sys.argv[2],sys.argv[3],float(sys.argv[4]),float(sys.argv[5]),float(sys.argv[6])
mode=sys.argv[7] if len(sys.argv)>7 else 'coons'
res=1.0; half=250
ims={s:cv2.imread(base+S[s]['file']) for s in (A,B)}
if kind=='v':
    gx=np.arange(c-half,c+half,res); gy=np.arange(t1,t0,-res); GX,GY=np.meshgrid(gx,gy)
    side={A:GX<c,B:GX>=c}
else:
    gx=np.arange(t0,t1,res); gy=np.arange(c+half,c-half,-res); GX,GY=np.meshgrid(gx,gy)
    side={A:GY>=c,B:GY<c}
out=np.zeros(GX.shape+(3,),np.uint8)
for s in (A,B):
    sh=Sheet(s,coons=True if mode=='coons' else 'lens'); u,v=sh.g2p(GX.ravel(),GY.ravel())
    w=cv2.remap(ims[s],u.reshape(GX.shape).astype(np.float32),v.reshape(GX.shape).astype(np.float32),cv2.INTER_LINEAR)
    out[side[s]]=w[side[s]]
cv2.imwrite(sys.argv[8] if len(sys.argv)>8 else 'seamview.png',out)
