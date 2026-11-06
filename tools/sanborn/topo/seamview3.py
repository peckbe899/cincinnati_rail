try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, cv2, sys
from geo import S, Sheet
from seamfeat import Joint
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
A,B,kind,c,t0,t1,half,model,out=sys.argv[1:10]; c,t0,t1,half=map(float,(c,t0,t1,half))
J=Joint(model) if model!='coons' else None
ims={s:cv2.imread(base+S[s]['file']) for s in (A,B)}
if kind=='v':
    gx=np.arange(c-half,c+half,1.0); gy=np.arange(t1,t0,-1.0); GX,GY=np.meshgrid(gx,gy); side={A:GX<c,B:GX>=c}
else:
    gx=np.arange(t0,t1,1.0); gy=np.arange(c+half,c-half,-1.0); GX,GY=np.meshgrid(gx,gy); side={A:GY>=c,B:GY<c}
img=np.zeros(GX.shape+(3,),np.uint8)
for s in (A,B):
    sh=Sheet(s,coons=True); T=np.c_[sh.g2p(GX.ravel(),GY.ravel())]; p=T.copy()
    if J is not None:
        for _ in range(6):
            g=np.c_[J.p2g(s,p[:,0],p[:,1])]; p=p+(T-np.c_[sh.g2p(g[:,0],g[:,1])])
    w=cv2.remap(ims[s],p[:,0].reshape(GX.shape).astype(np.float32),p[:,1].reshape(GX.shape).astype(np.float32),cv2.INTER_LINEAR); img[side[s]]=w[side[s]]
cv2.imwrite(out,img)
