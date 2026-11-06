try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import json, sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
SP=_ws.DATA
D=json.load(open(SP+'sbg/fit/streets_raw.json')); F=D['feats']
osm=json.load(open(SP+'basin/osm_basin.geojson'))['features']
deck=[f for f in json.load(open(SP+'deckpage/deck.json'))['features']]
def draw(ax, box, scale):
    x0,y0,x1,y1=box
    for f in osm:
        if f['properties'].get('highway') in ('footway','steps','path','cycleway','corridor','service'): continue
        c=np.array(f['geometry']['coordinates'])
        if c[:,0].max()<x0 or c[:,0].min()>x1 or c[:,1].max()<y0 or c[:,1].min()>y1: continue
        ax.plot(c[:,0],c[:,1],color='#3a7bd5',lw=0.6,alpha=0.8,zorder=3)
    for f in deck:
        if f['properties'].get('layer')=='street':
            c=np.array(f['geometry']['coordinates']); ax.plot(c[:,0],c[:,1],color='#c0392b',lw=f['properties']['width_m']*scale,alpha=0.5,solid_capstyle='butt',zorder=1)
    for f in F:
        c=np.array(f['coords'])
        if c[:,0].max()<x0 or c[:,0].min()>x1 or c[:,1].max()<y0 or c[:,1].min()>y1: continue
        w=max(0.3,f['ft']*0.3048*scale)
        ax.plot(c[:,0],c[:,1],color='#555' if f['kind']=='we_street' else '#999',lw=w,solid_capstyle='butt',alpha=0.75,zorder=2)
        if f['how']=='default': ax.plot(c[:,0],c[:,1],color='orange',lw=0.5,zorder=4)
    ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
def render(box, out, px=1600):
    x0,y0,x1,y1=box; W=x1-x0; H=y1-y0; dpi=100; fw=px/dpi; fh=fw*H/W
    fig=plt.figure(figsize=(fw,fh),dpi=dpi); ax=fig.add_axes([0,0,1,1])
    scale=px/W*72/dpi   # points per metre
    draw(ax, box, scale); fig.savefig(out); plt.close(fig); print('saved',out)
if __name__=='__main__':
    b=[float(v) for v in sys.argv[1:5]]; render(b, sys.argv[5], int(sys.argv[6]) if len(sys.argv)>6 else 1600)
