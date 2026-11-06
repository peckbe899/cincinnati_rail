try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, math
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon, LineString
SP=_ws.DATA
Z=json.loads(sys.argv[1]); out=sys.argv[2]; sys.argv=sys.argv[:1]+sys.argv[3:4]
exec(open(_ws.CODE+'nw2/gapcheck2.py').read().split("G=collections")[0])
PIE=[]
for sysn in ('metro','rer'):
    for m in C[sysn]:
        g,ed=geom(m); PIE.append((sysn,m,LineString(g)))
cols=plt.cm.tab10.colors
n=len(Z); cc=min(3,n); rr=math.ceil(n/cc)
fig,axs=plt.subplots(rr,cc,figsize=(cc*7,rr*7),squeeze=False)
for ax,(title,x,y,R,sysf) in zip(axs.flat,Z):
    box=Polygon([(x-R,y-R),(x+R,y-R),(x+R,y+R),(x-R,y+R)]); i=0
    for pq in C['plats']:
        P=Polygon(pq['c'])
        if P.intersects(box): ax.fill(*P.exterior.xy,color='orange',alpha=.5)
    for t in C['tracks']:
        L=LineString(t['c'])
        if L.intersects(box) and t['sys'] in sysf: ax.plot(*L.xy,color='0.6',lw=.5)
    for sysn,m,g in PIE:
        if sysn not in sysf or not g.intersects(box): continue
        c=cols[i%10]; i+=1; ax.plot(*g.xy,color=c,lw=1.6)
        ax.plot(*g.coords[0],'x',color=c,ms=9); ax.plot(*g.coords[-1],'o',color=c,ms=9,mfc='none')
        p=g.interpolate(g.project(box.centroid))
        ax.text(p.x,p.y,m['id'][2:]+' '+str(m.get('lines',m['name'])),fontsize=8,color=c)
    ax.set_xlim(x-R,x+R); ax.set_ylim(y-R,y+R); ax.set_aspect('equal'); ax.set_title(title)
for ax in axs.flat[n:]: ax.axis('off')
plt.tight_layout(); plt.savefig(out,dpi=55)
