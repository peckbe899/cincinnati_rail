try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import shape, box
SP=_ws.DATA
x0,y0,x1,y1=[float(v) for v in sys.argv[1:5]]; out=sys.argv[5]
B=box(x0,y0,x1,y1)
fig,ax=plt.subplots(figsize=(16,16*(y1-y0)/(x1-x0)))
BJ=json.load(open(SP+'deckpage/basin.json'))
for f in BJ['features']:
    if f['properties'].get('layer')!='street': continue
    g=shape(f['geometry'])
    if not g.intersects(B): continue
    for q in getattr(g,'geoms',[g]):
        x,y=q.xy; ax.plot(x,y,color='#bbb',lw=0.6)
H=json.load(open(SP+'deckpage/hwy.json'))
for f in H['features']:
    if f['properties'].get('layer')=='hw_piece':
        g=shape(f['geometry'])
        if g.intersects(B):
            for q in getattr(g,'geoms',[g]):
                if q.geom_type=='LineString': x,y=q.xy; ax.plot(x,y,color='#e9a',lw=2,alpha=.6)
T=json.load(open(SP+'deckpage/tracks.json'))
col={'apex':'k','lower':'tab:blue'}
for f in T['features']:
    g=shape(f['geometry']); p=f['properties']
    if g.geom_type!='LineString' or not g.intersects(B): continue
    x,y=g.xy; ax.plot(x,y,color=col.get(p.get('layer'),'tab:green'),lw=0.8)
C=json.load(open(SP+'deckpage/context.json'))
for t in C['tracks']:
    g=shape({'type':'LineString','coordinates':t['c']}) 
    if not g.intersects(B): continue
    x,y=g.xy; ax.plot(x,y,color='tab:orange' if t['sys']=='rer' else 'tab:purple',lw=0.7 if t['sys']=='rer' else 0.4)
for p in C['plats']:
    g=shape({'type':'Polygon','coordinates':[p['c']]})
    if g.intersects(B): x,y=g.exterior.xy; ax.fill(x,y,color='tab:orange' if p['sys']=='rer' else 'tab:purple',alpha=.6)
N=json.load(open(SP+'deckpage/norwood.json'))
for f in N['features']:
    g=shape(f['geometry'])
    if f['properties'].get('layer')=='nw_track' and g.intersects(B): x,y=g.xy; ax.plot(x,y,color='tab:red',lw=0.6)
for f in T['features']:
    p=f['properties']
    if p.get('layer') in('marker','label') and f['geometry']['type']=='Point':
        x,y=f['geometry']['coordinates']
        if x0<x<x1 and y0<y<y1: ax.plot(x,y,'r.',ms=3); ax.text(x,y,(p.get('label') or p.get('text') or '')[:40],fontsize=5)
for s in C['rer_stations']:
    x,y=s['p']
    if x0<x<x1 and y0<y<y1: ax.text(x,y,s['name'],fontsize=6,color='tab:orange')
for m in C.get('rer_marks',[]):
    pass
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.grid(alpha=.3)
plt.savefig(out,dpi=110,bbox_inches='tight')
