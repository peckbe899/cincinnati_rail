try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np, rasterio, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import LineString, shape, box
SP=_ws.DATA
x0,y0,x1,y1=[float(v) for v in sys.argv[1:5]]; out=sys.argv[5]
BB=box(x0,y0,x1,y1)
DEM=rasterio.open(SP+'handoff/out/map3_profile_dem_dm.vrt')
win=rasterio.windows.from_bounds(x0,y0,x1,y1,DEM.transform); Z=DEM.read(1,window=win,out_shape=(int((y1-y0)/3),int((x1-x0)/3))).astype(float)/10
fig,ax=plt.subplots(figsize=(15,15*(y1-y0)/(x1-x0)))
ax.imshow(Z,extent=(x0,x1,y0,y1),cmap='gist_earth',vmin=140,vmax=175,alpha=0.5)
cs=ax.contour(np.linspace(x0,x1,Z.shape[1]),np.linspace(y1,y0,Z.shape[0]),Z,levels=np.arange(140,176,2),linewidths=0.3,colors='k',alpha=0.5); ax.clabel(cs,fontsize=5,fmt='%d')
B=json.load(open(SP+'deckpage/basin.json'))['features']; D=json.load(open(SP+'deck/deck.json'))['features']
for f in B:
    p=f['properties']; g=shape(f['geometry'])
    if not g.intersects(BB): continue
    if p['layer']=='street':
        ax.plot(*g.xy,color='#333',lw=0.9 if p.get('kind')!='we_alley' else 0.4)
        if p.get('name') and g.length>80:
            m=g.intersection(BB).interpolate(0.5,normalized=True); ax.text(m.x,m.y,p['name'],fontsize=5,color='#333')
    elif p['layer'] in ('block',) and g.geom_type in ('Polygon','MultiPolygon'):
        for q in getattr(g,'geoms',[g]): ax.fill(*q.exterior.xy,color='#c9b28a',alpha=0.25,lw=0)
for f in D:
    p=f['properties']; g=shape(f['geometry'])
    if not g.intersects(BB): continue
    if p['layer']=='street':
        ax.plot(*g.xy,color='#1f4f7a',lw=1.0); 
        if p.get('name') and g.length>60:
            m=g.intersection(BB).interpolate(0.5,normalized=True); ax.text(m.x,m.y,p['name'],fontsize=5,color='#1f4f7a')
    if p['layer']=='deck':
        for q in getattr(g,'geoms',[g]): ax.plot(*q.exterior.xy,'k--',lw=0.7)
C=json.load(open(SP+'deckpage/context.json'))
for r in C['rer']:
    g=LineString(r['c'])
    if g.intersects(BB): ax.plot(*g.xy,color='#d07a1c',lw=1.5,alpha=0.8)
for s in C['rer_stations']:
    if BB.contains(LineString([s['p'],s['p']]).centroid): ax.plot(*s['p'],'o',color='#d07a1c',ms=5); ax.text(s['p'][0]+8,s['p'][1]+8,s['name']+' '+''.join(s['lines']),fontsize=6,color='#d07a1c')
L=json.load(open(SP+'nv/lines.json'))
for o in L:
    if o['src']=='APEx' or o['src']=='TRIMET3D':
        g=LineString(o['c'])
        if g.intersects(BB): ax.plot(*g.xy,color='#16252a' if o['src']=='APEx' else '#2a7ab0',lw=1.0,ls='-' if o['src']=='APEx' else '--')
R=json.load(open(SP+'nv/orr_near.json'))['lines']
for o in R:
    g=LineString(o['pts'])
    if g.intersects(BB) and 'SW-10' in o['path'][-1]: ax.plot(*g.xy,color='#b0207a',lw=2,alpha=0.6); 
P=json.load(open(SP+'nv/profile.json')); CC=LineString(P['C'])
for s in range(3800,6000,100):
    p=CC.interpolate(s)
    if BB.contains(p): ax.text(p.x+5,p.y,'s%d'%s,fontsize=5,color='r')
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.tick_params(labelsize=6); ax.grid(lw=0.2)
plt.savefig(out,dpi=110,bbox_inches='tight')
