try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import shape, box, LineString
SP=_ws.DATA
C=json.load(open(SP+sys.argv[1])); T=json.load(open(SP+sys.argv[2])); out=sys.argv[3]
views=[[float(v) for v in a.split(',')] for a in sys.argv[4:]]
H=json.load(open(SP+'deckpage/hwy.json')); BJ=json.load(open(SP+'deckpage/basin.json')); N=json.load(open(SP+'deckpage/norwood.json'))
S=json.load(open(SP+'deckpage/structures.json')) if len(sys.argv)>99 else None
fig,axs=plt.subplots(1,len(views),figsize=(9*len(views),9))
if len(views)==1: axs=[axs]
def col(p):
    n=p.get('name') or ''
    if n.startswith('APEx Dayton') or n.startswith('APEx north approach 1') or n.startswith('APEx north approach 2'): return 'k',1.0
    if n.startswith('APEx Norwood') or n.startswith('APEx north approach 3') or n.startswith('APEx north approach 4'): return '0.45',1.0
    if 'Transvalley' in n or 'pair W' in n: return 'tab:green',1.0
    if n.startswith('ORR X2'): return 'tab:cyan',1.2
    if n.startswith('ORR') or 'pair E' in n: return 'tab:blue',1.0
    if n.startswith('Crossover'): return 'm',0.8
    if p.get('layer')=='apex': return 'k',0.6
    if p.get('layer')=='lower': return 'tab:blue',0.6
    return None,0
for ax,(x0,y0,x1,y1) in zip(axs,views):
    B=box(x0,y0,x1,y1)
    for f in BJ['features']:
        if f['properties'].get('layer')!='street': continue
        g=shape(f['geometry'])
        if g.intersects(B):
            for q in getattr(g,'geoms',[g]): ax.plot(*q.xy,color='#ccc',lw=0.5)
    for f in H['features']:
        if f['properties'].get('layer')=='hw_piece':
            g=shape(f['geometry'])
            if g.intersects(B):
                gg=g.buffer(f['properties'].get('w',0)/2,cap_style=2)
                for q in getattr(gg,'geoms',[gg]): ax.fill(*q.exterior.xy,color='#f3c',alpha=0.15)
    for t in C['tracks']:
        g=LineString(t['c'])
        if not g.intersects(B): continue
        if t['sys']=='metro': ax.plot(*g.xy,color='tab:purple',lw=0.4,alpha=0.6)
        else:
            c='red' if t.get('line')=='D' else 'darkorange'
            ax.plot(*g.xy,color=c,lw=1.1)
    for p in C['plats']:
        g=shape({'type':'Polygon','coordinates':[p['c']]})
        if g.intersects(B) and p['sys']=='rer': ax.fill(*g.exterior.xy,color='orange',alpha=0.6)
    for f in T['features']:
        g=shape(f['geometry'])
        if g.geom_type!='LineString' or not g.intersects(B): continue
        c,lw=col(f['properties'])
        if c: ax.plot(*g.xy,color=c,lw=lw)
    for f in N['features']:
        if f['properties'].get('layer')=='nw_track':
            g=shape(f['geometry'])
            if g.intersects(B): ax.plot(*g.xy,color='tab:red',lw=0.6)
    for f in T['features']:
        p=f['properties']
        if f['geometry']['type']=='Point' and p.get('layer') in ('marker','label'):
            x,y=f['geometry']['coordinates']
            if x0<x<x1 and y0<y<y1 and (p.get('label') or p.get('text')): ax.plot(x,y,'r.',ms=3); ax.text(x,y,(p.get('label') or p.get('text'))[:60],fontsize=5)
    for m in C['rer_marks']:
        x,y=m['p']
        if x0<x<x1 and y0<y<y1: ax.plot(x,y,'s',color='darkorange',ms=3); ax.text(x,y,m['label'][:70],fontsize=5,color='saddlebrown')
    for r in C['rer_struct']:
        if r['line'] in ('B','B/D','D (with the Indianapolis pair)'):
            g=LineString(r['c'])
            if g.intersects(B): ax.plot(*g.xy,color={'viaduct':'k','embankment':'g','ramp':'b','tunnel':'0.6'}[r['state']],lw=3,alpha=0.15)
    ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.grid(alpha=.3); ax.tick_params(labelsize=6)
plt.savefig(SP+out,dpi=100,bbox_inches='tight')
