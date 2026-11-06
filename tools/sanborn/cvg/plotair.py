try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys
from shapely.geometry import shape
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch
def pp(ax,q,**k):
    rings=[q.exterior]+list(q.interiors); v=[];c=[]
    for r in rings:
        xy=list(r.coords); v+=xy; c+=[Path.MOVETO]+[Path.LINETO]*(len(xy)-2)+[Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(v,c),**k))
S=_ws.DATA
A=json.load(open(S+'deckpage/airport.json')); x0,y0,x1,y1=map(float,sys.argv[1:5])
fig,ax=plt.subplots(figsize=(14,14*(y1-y0)/(x1-x0)))
col={'cvg_apron':'#ccc','cvg_taxi':'#888','cvg_runway':'k','cvg_building':'m','cvg_area':'none','cvg_stand':'none'}
for L in ('cvg_area','cvg_taxi','cvg_apron','cvg_runway','cvg_building','cvg_stand','cvg_taxi_cl'):
  for f in A['features']:
    if f['properties']['layer']!=L: continue
    g=shape(f['geometry'])
    for q in getattr(g,'geoms',[g]):
        if q.geom_type=='Polygon':
            pp(ax,q,fc=('#f90' if f['properties'].get('cls')=='L' else '#3a3') if L=='cvg_stand' else col[L],alpha=0.5 if L=='cvg_stand' else 1,ec='b' if L=='cvg_stand' else 'none',lw=0.6)
        elif L=='cvg_taxi_cl': ax.plot(*q.xy,color='#cc0',lw=0.7)
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.grid(alpha=0.3)
fig.savefig(S+'cvgkmz/'+sys.argv[5],dpi=int(sys.argv[6]) if len(sys.argv)>6 else 60,bbox_inches='tight')
