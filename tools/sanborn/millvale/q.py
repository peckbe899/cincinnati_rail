try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, sys
SP=_ws.DATA
exec(open(_ws.CODE+'millvale/m3m6_options.py').read().split("fig,axs=plt.subplots")[0])
for nm,p in (('W3',pF3),('SE',pF6),('NE',pB3),('SW',pB6)):
    s=B.project(p); q=B.interpolate(s); print(nm,'s=%.1f'%s,'offset %.1f'%p.distance(q))
for k in (2,3,6,7): print('M%d'%k, 's=%.1f'%B.project(B.intersection(G[f'New street M{k}'][0])))
