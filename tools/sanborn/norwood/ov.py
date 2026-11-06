import json, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import Polygon, LineString
J=json.load(open('topo/dem2m.json')); D=np.load('topo/dem2m.npy', mmap_mode='r')
import sys; x0,x1,y0,y1=[int(v) for v in sys.argv[1:5]] if len(sys.argv)>4 else (719500,721100,4337450,4338450)
r0=int((J['y1']-y1)/2); r1=int((J['y1']-y0)/2); c0=int((x0-J['x0'])/2); c1=int((x1-J['x0'])/2)
Z=np.array(D[r0:r1,c0:c1],float); Z[Z==J['nodata']]=np.nan; Z/=10
gy,gx=np.gradient(Z,2); sl=np.arctan(np.hypot(gx,gy)); az=np.arctan2(-gx,gy)
hs=np.cos(np.radians(45))*np.cos(sl)+np.sin(np.radians(45))*np.sin(sl)*np.cos(np.radians(315)-az)
fig,ax=plt.subplots(figsize=(16,10),dpi=110)
ax.imshow(hs,cmap='gray',extent=(x0,x1,y0,y1),alpha=1)
cs=ax.contour(np.linspace(x0,x1,Z.shape[1]),np.linspace(y1,y0,Z.shape[0]),Z,levels=range(150,280,5),linewidths=.5,colors='peru')
ax.clabel(cs,fontsize=6,fmt='%d')
A=Polygon(json.load(open('norwood/area_utm.json'))); ax.plot(*A.exterior.xy,'r-',lw=2)
d=json.load(open('deckpage/context.json')); T=json.load(open('deckpage/tracks.json'))
col={'rer':'#1f77ff','metro':'#2ca02c'}
for f in d['tracks']:
    c=np.array(f['c']); ax.plot(c[:,0],c[:,1],color=col.get(f['sys'],'k'),lw=.8)
for f in T['features']:
    g=f['geometry']
    if g['type']=='LineString': c=np.array(g['coordinates']); ax.plot(c[:,0],c[:,1],color='m',lw=1.5)
for k in ['stations','rer_stations']:
    for s in d[k]:
        p=s['p']
        if x0<p[0]<x1 and y0<p[1]<y1: ax.plot(*p,'o',ms=5,color='k'); ax.text(p[0]+8,p[1]+8,s['name']+' '+str(s.get('line') or s.get('lines')),fontsize=7)
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); plt.tight_layout(); plt.savefig('norwood/area_ov%s.png'%(sys.argv[5] if len(sys.argv)>5 else ''))
