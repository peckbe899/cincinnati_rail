try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np, rasterio, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import LineString, box
SP=_ws.DATA
x0,y0,x1,y1=[float(v) for v in sys.argv[1:5]]; out=sys.argv[5]
L=json.load(open(SP+'nv/lines.json')); R=json.load(open(SP+'nv/orr_near.json'))['lines']
DEM=rasterio.open(SP+'handoff/out/map3_profile_dem_dm.vrt')
win=rasterio.windows.from_bounds(x0,y0,x1,y1,DEM.transform); Z=DEM.read(1,window=win,out_shape=(int((y1-y0)/8),int((x1-x0)/8))).astype(float); Z[Z<-30000]=np.nan; Z/=10
fig,ax=plt.subplots(figsize=(14,14*(y1-y0)/(x1-x0)))
ax.imshow(Z,extent=(x0,x1,y0,y1),cmap='gist_earth',vmin=145,vmax=240,alpha=0.45)
B=box(x0,y0,x1,y1)
col={'APEx':'#16252a','CR':'#d07a1c','TRIMET3D':'#2a7ab0'}
seen=set()
for o in L:
    if o['src']=='CR' and 'RER' not in o['folder']: continue
    g=LineString(o['c']); key=(o['src'],o['name'],round(g.length))
    if key in seen: continue
    seen.add(key)
    ax.plot(*g.xy,color=col[o['src']],lw=1.4 if o['src']=='APEx' else 0.9,ls='-' if o['src']!='TRIMET3D' else '--',alpha=0.8)
    gi=g.intersection(B)
    if not gi.is_empty and gi.length>50:
        m=gi.interpolate(0.3,normalized=True)
        ax.text(m.x,m.y,o['src'][:4]+':'+o['name'],fontsize=5,color=col[o['src']])
cm=plt.get_cmap('tab10')
for i,o in enumerate(R):
    g=LineString(o['pts']); c=cm(i%10)
    ax.plot(*g.xy,color=c,lw=2.2,alpha=0.6)
    gi=g.intersection(B)
    if not gi.is_empty and gi.length>50:
        m=gi.interpolate(0.55 if i%2 else 0.15,normalized=True)
        ax.text(m.x,m.y,'ORR '+o['path'][-1]+' '+o['name'],fontsize=6,color=c,weight='bold')
C=json.load(open(SP+'deckpage/context.json'))
for s in C['rer_stations']+C['stations']:
    if x0<s['p'][0]<x1 and y0<s['p'][1]<y1: ax.plot(*s['p'],'o',ms=3,color='#d07a1c' if 'lines' in s else '#5b5f97'); ax.text(s['p'][0]+20,s['p'][1],s['name'],fontsize=5)
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.tick_params(labelsize=6); ax.grid(lw=0.2)
plt.savefig(out,dpi=120,bbox_inches='tight')
