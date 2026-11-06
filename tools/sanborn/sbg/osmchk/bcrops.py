try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import json, sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0,'fit'); from viz3 import mosaic
from shapely.geometry import shape
from PIL import Image
L=json.load(open('fit/basin_sanborn.json'))['features']; ST={f['properties']['id']:f for f in L if f['properties']['layer']=='street'}
OSM=json.load(open((_ws.DATA + 'basin/osm_basin.geojson')))['features']
rows=[r for r in json.load(open(sys.argv[1])) if r['run']>=12]
rows.sort(key=lambda r:-r['run'])
def one(r, out, half=75, px=550):
    g=shape(ST[r['id']]['geometry']); a,b=r['span']; m=g.interpolate((a+b)/2); cx,cy=m.x,m.y
    x0,y0,x1,y1=cx-half,cy-half,cx+half,cy+half
    img=mosaic((x0,y0,x1,y1),0.25)
    fig=plt.figure(figsize=(px/100,px/100),dpi=100); ax=fig.add_axes([0,0,1,1]); ax.imshow(img,extent=[x0,x1,y0,y1])
    for f in L:
        p=f['properties']
        if p['layer']!='street': continue
        c=np.array(f['geometry']['coordinates'])
        if c[:,0].max()<x0 or c[:,0].min()>x1 or c[:,1].max()<y0 or c[:,1].min()>y1: continue
        ax.plot(c[:,0],c[:,1],color='#ffd400' if p['id']==r['id'] else '#e00000',lw=2.2 if p['id']==r['id'] else 1.0)
    for f in OSM:
        if f['properties'].get('highway') in ('footway','steps','path','cycleway','corridor'): continue
        c=np.array(f['geometry']['coordinates'])
        if c[:,0].max()<x0 or c[:,0].min()>x1 or c[:,1].max()<y0 or c[:,1].min()>y1: continue
        ax.plot(c[:,0],c[:,1],color='#0050ff',lw=0.9,ls=(0,(4,3)))
    ax.text(x0+3,y1-3,f"{r['id']} {r['name'][:22]} run {r['run']} m",fontsize=9,va='top',bbox=dict(fc='w',alpha=0.85))
    ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_xticks([]); ax.set_yticks([]); fig.savefig(out); plt.close(fig)
import os
os.makedirs('osmchk/bc',exist_ok=True)
for i,r in enumerate(rows): one(r,f'osmchk/bc/{i:02d}.png')
for k in range(0,len(rows),4):
    ims=[Image.open(f'osmchk/bc/{i:02d}.png') for i in range(k,min(k+4,len(rows)))]
    big=Image.new('RGB',(1100,1100),'white')
    for j,im in enumerate(ims): big.paste(im,((j%2)*550,(j//2)*550))
    big.save(f'osmchk/bc/grid_{k//4:02d}.png')
print(len(rows))
