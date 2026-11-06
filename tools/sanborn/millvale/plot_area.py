try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, numpy as np, rasterio, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import shape, LineString, box
SP=_ws.DATA
X0,Y0,X1,Y1=711300,4334600,713100,4337200
r=rasterio.open(SP+'topo/I4_1912_ground_dm.tif'); win=rasterio.windows.from_bounds(X0,Y0,X1,Y1,r.transform); Z=r.read(1,window=win)/10.0
fig,ax=plt.subplots(figsize=(11,15.5)); ax.set_aspect('equal')
ext=[X0,X1,Y0,Y1]
ax.imshow(np.clip(Z,135,200),extent=ext,cmap='terrain',vmin=120,vmax=230,alpha=0.6)
cs=ax.contour(np.linspace(X0,X1,Z.shape[1]),np.linspace(Y1,Y0,Z.shape[0]),Z,levels=np.arange(145,231,5),colors='k',linewidths=0.4,alpha=0.6); ax.clabel(cs,fmt='%d',fontsize=6)
# creek low line
xs=np.linspace(X0,X1,Z.shape[1]); ys=np.linspace(Y1,Y0,Z.shape[0]); low=[]
for i in range(0,Z.shape[0],12):
    if not (4334850<ys[i]<4337100): continue
    row=Z[i]; m=(xs>711700)&(xs<712950); j=np.argmin(np.where(m,row,999)); low.append((xs[j],ys[i],row[j]))
low=np.array(low); ax.plot(low[:,0],low[:,1],'c.-',lw=1,ms=3,label='1912 ground low line (creek)')
B=box(X0,Y0,X1,Y1)
b=json.load(open(SP+'deckpage/basin.json'))
hl={'Dreman Street','Geringer Street','Beekman Street','Hopple Street'}
for f in b['features']:
    p=f['properties']
    if p['layer']!='street': continue
    g=shape(f['geometry'])
    if not g.intersects(B): continue
    for gg in getattr(g,'geoms',[g]):
        x,y=gg.xy; ax.plot(x,y,color='m' if p.get('name') in hl else '0.35',lw=2.2 if p.get('name') in hl else 0.9)
    if p.get('name') and g.length>120:
        c=g.interpolate(0.5,normalized=True); ax.text(c.x,c.y,p['name'].replace(' Street','').replace(' Avenue',''),fontsize=6,color='m' if p.get('name') in hl else 'k')
t=json.load(open(SP+'deckpage/tracks.json'))
for f in t['features']:
    g=shape(f['geometry'])
    if g.geom_type=='LineString' and g.intersects(B):
        x,y=g.xy; ax.plot(x,y,color='r',lw=0.6,alpha=0.7)
c=json.load(open(SP+'deckpage/context.json'))
for f in c['metro']:
    g=LineString(f['c'])
    if g.intersects(B): x,y=g.xy; ax.plot(x,y,'b--',lw=1); m=g.intersection(B).interpolate(0.5,normalized=True); ax.text(m.x,m.y,f['name'],color='b',fontsize=7)
for f in c['rer']:
    g=LineString(f['c'])
    if g.intersects(B): x,y=g.xy; ax.plot(x,y,color='orange',ls='--',lw=1)
for s in c['stations']+c['rer_stations']:
    if B.contains(shape({'type':'Point','coordinates':s['p']})): ax.plot(*s['p'],'ko',ms=4); ax.text(s['p'][0]+15,s['p'][1],s['name'],fontsize=7)
d=json.load(open(SP+'millvale/blvd2.json'))
x,y=zip(*d['blvd']); ax.plot(x,y,'g-',lw=4,alpha=0.7,label='boulevard (straightened)')
x,y=zip(*d['old']); ax.plot(x,y,'g--',lw=3,alpha=0.7,label='old boulevard to Hopple')
o=json.load(open(SP+'millvale/i75_bt.json')); x,y=zip(*o); ax.plot(x,y,color='g',lw=1,ls=':',label='first KML')
ax.set_xlim(X0,X1); ax.set_ylim(Y0,Y1); ax.legend(loc='lower left',fontsize=8); ax.grid(alpha=0.2)
plt.tight_layout(); plt.savefig(SP+'millvale/area.png',dpi=90)
np.save(SP+'millvale/creek_low.npy',low)
