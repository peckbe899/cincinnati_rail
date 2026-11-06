import json, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import shape, LineString
A=json.load(open('deckpage/airport_v58.json'))
fig,ax=plt.subplots(figsize=(14,12))
for f in A['features']:
    p=f['properties']; g=shape(f['geometry'])
    if p['layer']=='cvg_runway_cl':
        ax.plot(*g.xy,'k-',lw=1); s=g.buffer(150,cap_style=2); ax.fill(*s.exterior.xy,color='r',alpha=.08)
        for o in (190,): pass
    if p['layer']=='cvg_building':
        ax.fill(*g.exterior.xy,color='b',alpha=.4); ax.text(g.centroid.x,g.centroid.y,p['name'],fontsize=7)
        for i,(x,y) in enumerate(g.exterior.coords[:-1]): ax.text(x,y,str(i),fontsize=5,color='m')
    if p['layer']=='cvg_area': ax.plot(*g.exterior.xy,'g--',lw=.6)
ax.set_xlim(700300,704000); ax.set_ylim(4324300,4326800); ax.set_aspect('equal'); ax.grid(lw=.2)
plt.savefig(sys.argv[1],dpi=110,bbox_inches='tight')
