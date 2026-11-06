try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, rasterio, glob, json, re
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/LiDAR_2m/")
fs=sorted(glob.glob(base+"DEM2m_E*_N*.tif"))
x0=695000; y1=4350000; res=2.0; y0=4315000
W=int((735000-x0)/res); H=int((y1-y0)/res)
old=json.load(open('dem2m.json'))
out=np.lib.format.open_memmap('dem2m_new.npy',mode='w+',dtype=np.int16,shape=(H,W)); out[:]=-32768
for f in fs:
    with rasterio.open(f) as s:
        a=s.read(1); b=s.bounds
        c=int(round((b.left-x0)/res)); r=int(round((y1-b.top)/res))
        out[r:r+a.shape[0],c:c+a.shape[1]]=a
out.flush()
print(len(fs),H,W,'nodata frac',(np.asarray(out[::10,::10])==-32768).mean())
json.dump(dict(old,h=H,w=W),open('dem2m_new.json','w'))
