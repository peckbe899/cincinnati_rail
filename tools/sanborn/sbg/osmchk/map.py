try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import pickle, json, sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
SP=_ws.DATA
D=pickle.load(open(SP+'sbg/osmchk/samples.pkl','rb')); A=D['SAMP']; B=D['OSMS']
osm=json.load(open(SP+'basin/osm_basin.geojson'))['features']
box=[float(v) for v in sys.argv[1:5]]; out=sys.argv[5]; px=int(sys.argv[6]) if len(sys.argv)>6 else 2000
x0,y0,x1,y1=box; fig=plt.figure(figsize=(px/100,px/100*(y1-y0)/(x1-x0)),dpi=100); ax=fig.add_axes([0,0,1,1])
for f in osm:
    if f['properties'].get('highway') in ('footway','steps','path','cycleway','corridor'): continue
    c=np.array(f['geometry']['coordinates'])
    if c[:,0].max()<x0 or c[:,0].min()>x1 or c[:,1].max()<y0 or c[:,1].min()>y1: continue
    ax.plot(c[:,0],c[:,1],color='#bbb',lw=0.5,zorder=1)
def col(s):
    if s['st']=='same': d=s['d']; return '#1a9850' if d<2 else '#a6d96a' if d<3 else '#fdae61' if d<5 else '#f46d43' if d<8 else '#a50026'
    if s['st']=='other': return '#4575b4'
    return '#999999'
xs=np.array([s['x'] for s in A]); ys=np.array([s['y'] for s in A]); cs=[col(s) for s in A]
ax.scatter(xs,ys,c=cs,s=2.2 if px/(x1-x0)<1 else 6,lw=0,zorder=3)
mb=[s for s in B if not s['hit']]
ax.scatter([s['x'] for s in mb],[s['y'] for s in mb],c='#e7298a',s=2.2 if px/(x1-x0)<1 else 6,lw=0,zorder=2)
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
fig.savefig(out); print('saved',out)
