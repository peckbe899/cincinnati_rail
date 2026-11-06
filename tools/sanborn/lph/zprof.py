try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import rasterio, numpy as np, json, sys
from shapely.geometry import LineString
E=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/LiDAR_2m/")
srcs=[rasterio.open(E+f) for f in ['DEM2m_E710_N4330.tif','DEM2m_E710_N4335.tif']]
def z(e,n):
    for s in srcs:
        b=s.bounds
        if b.left<=e<b.right and b.bottom<=n<b.top: return float(list(s.sample([(e,n)]))[0][0])
SP=_ws.DATA
