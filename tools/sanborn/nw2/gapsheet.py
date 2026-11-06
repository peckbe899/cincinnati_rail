try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, math, subprocess
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import LineString, Point, Polygon
exec(open(SP:=_ws.CODE+'nw2/gapcheck2.py').read().split("rows=[];seen")[0])
rows=[];seen=set()
for ln,ps in G.items():
    for pid,g,ed in ps:
        for e in (0,-1):
            q=Point(g.coords[e]); others=[(o.distance(q),oid,o) for oid,o,oed in ps if oid!=pid]
            if not others: continue
            d,oid,o=min(others,key=lambda r:r[0])
            if not (3<d<600): continue
            key=tuple(sorted((pid,oid)))+(ln,)
            if key in seen: continue
            seen.add(key); p2=o.interpolate(o.project(q)); rows.append((ln,d,pid,oid,q,p2))
rows.sort(key=lambda r:(r[0],r[1]))
n=len(rows); cols=6; rws=math.ceil(n/cols)
fig,axs=plt.subplots(rws,cols,figsize=(cols*4,rws*4))
for ax,(ln,d,pid,oid,q,p2) in zip(axs.flat,rows):
    cx,cy=(q.x+p2.x)/2,(q.y+p2.y)/2; R=max(150,d*1.2)
    for lnn,ps in G.items():
        for qid,g,ed in ps:
            x,y=g.xy; col='r' if qid==pid else ('b' if qid==oid else '0.7')
            ax.plot(x,y,col,lw=1.5 if col!='0.7' else .6)
    for pq in C['plats']:
        x,y=Polygon(pq['c']).exterior.xy; ax.fill(x,y,color='orange',alpha=.5)
    ax.plot([q.x],[q.y],'ko',ms=3)
    ax.set_xlim(cx-R,cx+R); ax.set_ylim(cy-R,cy+R); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(f'{ln} {d:.0f}m\n{pid[:16]}>{oid[:16]}',fontsize=7)
for ax in axs.flat[n:]: ax.axis('off')
plt.tight_layout(); plt.savefig(SP+'nw2/gapsheet.png',dpi=60)
print(n)
