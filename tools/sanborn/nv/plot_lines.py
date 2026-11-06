try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np, rasterio, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import LineString, shape, box
SP=_ws.DATA
x0,y0,x1,y1=[float(v) for v in sys.argv[1:5]]; out=sys.argv[5]
L=json.load(open(SP+'nv/lines.json'))
DEM=rasterio.open(SP+'handoff/out/map3_profile_dem_dm.vrt')
win=rasterio.windows.from_bounds(x0,y0,x1,y1,DEM.transform); Z=DEM.read(1,window=win,out_shape=(int((y1-y0)/6),int((x1-x0)/6))).astype(float); Z[Z<-30000]=np.nan; Z/=10
fig,ax=plt.subplots(figsize=(14,14*(y1-y0)/(x1-x0)))
ax.imshow(Z,extent=(x0,x1,y0,y1),cmap='gist_earth',vmin=145,vmax=230,alpha=0.55)
cs=ax.contour(np.linspace(x0,x1,Z.shape[1]),np.linspace(y1,y0,Z.shape[0]),Z,levels=np.arange(146,200,2),linewidths=0.3,colors='k',alpha=0.4)
ax.clabel(cs,fontsize=4,fmt='%d')
O=json.load(open(SP+'lph/osm_north.geojson'))['features']
B=box(x0,y0,x1,y1)
for f in O:
    g=shape(f['geometry'])
    if g.geom_type!='LineString' or not g.intersects(B): continue
    hw=f['properties'].get('highway','')
    nm=f['properties'].get('name')
    ax.plot(*g.xy,color='#888',lw=0.6 if hw in ('primary','secondary','trunk','motorway') else 0.3)
    if nm and hw in ('primary','secondary','tertiary','trunk') and g.length>150:
        m=g.interpolate(0.5,normalized=True)
        if B.contains(m): ax.text(m.x,m.y,nm,fontsize=4.5,color='#444')
col={'APEx':'#16252a','CR':'#d07a1c','TRIMET3D':'#2a7ab0'}
seen=set()
for o in L:
    if o['src']=='CR' and 'RER' not in o['folder']: continue
    g=LineString(o['c']); key=(o['src'],o['name'],round(g.length))
    if key in seen: continue
    seen.add(key)
    ax.plot(*g.xy,color=col[o['src']],lw=1.6 if o['src']=='APEx' else 1.0,ls='-' if o['src']!='TRIMET3D' else '--',alpha=0.85)
    gi=g.intersection(B)
    if not gi.is_empty:
        m=gi.interpolate(0.35 if o['src']=='APEx' else 0.6,normalized=True)
        ax.text(m.x,m.y,o['src'][:4]+':'+o['name'],fontsize=5,color=col[o['src']])
    if o['src']=='TRIMET3D':
        for i in range(0,len(o['c']),40):
            p=o['c'][i]
            if B.contains(LineString([p,p]).centroid if False else box(*p,*p)): ax.text(p[0],p[1],'%.0f'%o['z'][i],fontsize=4,color='#2a7ab0')
C=json.load(open(SP+'deckpage/context.json'))
for s in C['rer_stations']+C['stations']:
    if x0<s['p'][0]<x1 and y0<s['p'][1]<y1: ax.plot(*s['p'],'o',ms=3,color='#d07a1c' if 'lines' in s else '#5b5f97'); ax.text(s['p'][0]+20,s['p'][1],s['name'],fontsize=5)
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.tick_params(labelsize=6); ax.grid(lw=0.2)
plt.savefig(out,dpi=120,bbox_inches='tight')
