try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import json, sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP
SP=_ws.DATA
L=json.load(open(SP+'sbg/fit/basin_sanborn.json'))['features']
deck=json.load(open(SP+'deckpage/deck.json'))['features']
def render(box,out,px=1600,osm=False,img=None):
    x0,y0,x1,y1=box; W=x1-x0; H=y1-y0; dpi=100; fw=px/dpi; fh=fw*H/W
    fig=plt.figure(figsize=(fw,fh),dpi=dpi); ax=fig.add_axes([0,0,1,1]); sc=px/W*72/dpi
    if img is not None: ax.imshow(img[0],extent=img[1],zorder=0)
    for F in (deck,L):
        for f in F:
            p=f['properties']
            if p.get('layer')=='block':
                c=np.array(f['geometry']['coordinates'][0] if f['geometry']['type']=='Polygon' else f['geometry']['coordinates'][0][0])
                if c[:,0].max()<x0 or c[:,0].min()>x1 or c[:,1].max()<y0 or c[:,1].min()>y1: continue
                col={'building':'#e8dcc4','park':'#b9d6a3','square':'#d9d3c7','planting':'#cfe3c0'}.get(p.get('type'),'#e8dcc4')
                ax.add_patch(MP(c,closed=True,fc=col,ec='#333',lw=0.4,alpha=0.55 if img is not None else 0.95,zorder=2))
    for F in (deck,L):
        for f in F:
            p=f['properties']
            if p.get('layer')!='street': continue
            c=np.array(f['geometry']['coordinates'])
            if c[:,0].max()<x0 or c[:,0].min()>x1 or c[:,1].max()<y0 or c[:,1].min()>y1: continue
            w=max(0.6,p['width_m']*sc); al=p['kind']=='we_alley'
            ax.plot(c[:,0],c[:,1],color='#222',lw=w+1.2,alpha=0.55,solid_capstyle='butt',solid_joinstyle='round',zorder=3)
            ax.plot(c[:,0],c[:,1],color='#f4efe4' if not al else '#e9e2d3',lw=w,solid_capstyle='butt',solid_joinstyle='round',zorder=4)
    if osm:
        for f in json.load(open(SP+'basin/osm_basin.geojson'))['features']:
            if f['properties'].get('highway') in ('footway','steps','path','cycleway','corridor','service'): continue
            c=np.array(f['geometry']['coordinates'])
            if c[:,0].max()<x0 or c[:,0].min()>x1 or c[:,1].max()<y0 or c[:,1].min()>y1: continue
            ax.plot(c[:,0],c[:,1],color='#2a6fdb',lw=0.7,alpha=0.9,zorder=5)
    ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([]); ax.set_facecolor('#faf8f3')
    fig.savefig(out); plt.close(fig); print('saved',out)
if __name__=='__main__':
    b=[float(v) for v in sys.argv[1:5]]; render(b,sys.argv[5],int(sys.argv[6]) if len(sys.argv)>6 else 1600, osm=len(sys.argv)>7)
