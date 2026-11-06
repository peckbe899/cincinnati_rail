try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, math
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import Point
SP=_ws.DATA
LNS=sys.argv[1:]; sys.argv=sys.argv[:1]
exec(open(_ws.CODE+'nw2/gapcheck2.py').read().split("ST=[")[0])
cols=plt.cm.tab20.colors
for ln in LNS:
    ps=G[ln]; fig,ax=plt.subplots(figsize=(14,14))
    for i,(pid,g,ed) in enumerate(ps):
        x,y=g.xy; ax.plot(x,y,color=cols[i%20],lw=2)
        for e in (0,-1):
            q=Point(g.coords[e]); touch=any(o.distance(q)<0.5 for oid,o,_ in ps if oid!=pid)
            if not touch: ax.plot(q.x,q.y,'kx' if e==0 else 'ko',ms=6,mfc='none')
        m=g.interpolate(0.5,normalized=True); ax.text(m.x,m.y,pid[2:]+(' ED' if ed else ''),fontsize=7,color=cols[i%20])
    ax.set_aspect('equal'); ax.set_title(ln+'  x=start o=end (loose)')
    plt.savefig(SP+f'nw2/line_{ln.replace(" ","")}.png',dpi=70,bbox_inches='tight'); plt.close()
