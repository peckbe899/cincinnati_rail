try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json,sys
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import shape,Polygon,box
SP=_ws.DATA
Z=json.loads(sys.argv[1]); out=sys.argv[2]
B=json.load(open(SP+'deckpage/basin.json')); W=json.load(open(SP+'wh/w1_streets.geojson'))['features']
A=Polygon(json.load(open(SP+'wh/area_utm.json')))
fig,axs=plt.subplots(1,len(Z),figsize=(8*len(Z),8),squeeze=False)
for ax,(t,x,y,R) in zip(axs[0],Z):
    bx=box(x-R,y-R,x+R,y+R)
    for f in B['features']:
        if f['properties'].get('set')=='w1': continue
        g=shape(f['geometry'])
        if not g.intersects(bx): continue
        if f['properties'].get('layer')=='street' and g.geom_type=='LineString': ax.plot(*g.xy,color='0.5',lw=1)
        elif f['properties'].get('layer')=='block' and g.geom_type=='Polygon': ax.fill(*g.exterior.xy,color='0.85')
    for f in W:
        g=shape(f['geometry'])
        if not g.intersects(bx): continue
        ax.plot(*g.xy,color='b' if f['properties']['id'].startswith('SW') else 'r',lw=1.2)
        if g.length>150: ax.text(*g.interpolate(.5,normalized=True).coords[0],f['properties']['name'],fontsize=5,clip_on=True)
    ax.plot(*A.exterior.xy,'k--',lw=1); ax.set_xlim(x-R,x+R); ax.set_ylim(y-R,y+R); ax.set_aspect('equal'); ax.set_title(t); ax.set_xticks([]); ax.set_yticks([])
plt.tight_layout(); plt.savefig(SP+out,dpi=60)
