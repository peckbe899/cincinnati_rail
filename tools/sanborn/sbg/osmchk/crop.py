"""Sanborn underlay + basin streets (red centreline, faint band) + OSM roads (blue), around a point."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import json, sys, os, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0,(_ws.CODE + 'sbg/fit'))
from viz3 import mosaic
SP=_ws.DATA
L=json.load(open(SP+'sbg/fit/basin_sanborn.json'))['features']
OSM=json.load(open(SP+'basin/osm_basin.geojson'))['features']
def crop(cx,cy,half,out,px=1100,title=''):
    x0,y0,x1,y1=cx-half,cy-half,cx+half,cy+half
    img=mosaic((x0,y0,x1,y1),0.25 if half<=200 else 0.5)
    fig=plt.figure(figsize=(px/100,px/100),dpi=100); ax=fig.add_axes([0,0,1,1]); ax.imshow(img,extent=[x0,x1,y0,y1])
    sc=px/(2*half)*0.72
    for f in L:
        p=f['properties']
        if p['layer']!='street': continue
        c=np.array(f['geometry']['coordinates'])
        if c[:,0].max()<x0 or c[:,0].min()>x1 or c[:,1].max()<y0 or c[:,1].min()>y1: continue
        ax.plot(c[:,0],c[:,1],color='#ff2000',lw=p['width_m']*sc,alpha=0.13,solid_capstyle='butt')
        ax.plot(c[:,0],c[:,1],color='#e00000',lw=1.1)
        m=c[len(c)//2] if len(c)>2 else c.mean(0)
        if x0<m[0]<x1 and y0<m[1]<y1 and p['name']: ax.text(m[0],m[1],p['name'][:18],color='#c00000',fontsize=7)
    for f in OSM:
        h=f['properties'].get('highway')
        if h in ('footway','steps','path','cycleway','corridor'): continue
        c=np.array(f['geometry']['coordinates'])
        if c[:,0].max()<x0 or c[:,0].min()>x1 or c[:,1].max()<y0 or c[:,1].min()>y1: continue
        ax.plot(c[:,0],c[:,1],color='#0050ff',lw=1.1,ls='--')
        n=f['properties'].get('name')
        if n and len(c)>1:
            m=c[len(c)//2]
            if x0<m[0]<x1 and y0<m[1]<y1: ax.text(m[0],m[1]-6,n[:18],color='#0040c0',fontsize=7)
    ax.text(x0+5,y1-15,title,fontsize=10,color='k',bbox=dict(fc='w',alpha=0.8))
    ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_xticks([]); ax.set_yticks([]); fig.savefig(out); plt.close(fig)
if __name__=='__main__':
    crop(float(sys.argv[1]),float(sys.argv[2]),float(sys.argv[3]),sys.argv[4],title=sys.argv[5] if len(sys.argv)>5 else '')
