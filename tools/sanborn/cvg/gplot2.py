import json, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import shape
A=json.load(open('deckpage/airport_v58.json')); G=json.load(open(sys.argv[1])); P=G['params']
fig,ax=plt.subplots(figsize=(16,12))
for f in A['features']:
    p=f['properties']; g=shape(f['geometry'])
    if p['layer']=='cvg_runway_cl':
        ax.plot(*g.xy,'k-',lw=1)
        for d,c in ((P['rwy_to_parking'],'r'),): s=g.buffer(d,cap_style=2); ax.fill(*s.exterior.xy,color=c,alpha=.07)
    if p['layer']=='cvg_building' and p['name'].startswith('Term'):
        from shapely.affinity import translate; g=translate(g,*P.get('shift',{}).get(p['name'],(0,0))); ax.fill(*g.exterior.xy,color='b',alpha=.5)
for s in G['stands']:
    e=shape(s['env']); t=shape(s['tail'])
    ax.fill(*e.exterior.xy,color='orange' if s['cls']=='L' else 'green',alpha=.6,lw=.3,ec='k')
    ax.fill(*t.exterior.xy,color='grey',alpha=.15)
x0,y0,x1,y1=[float(v) for v in sys.argv[3:7]] if len(sys.argv)>3 else (700500,4324500,703700,4326700)
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.grid(lw=.2)
plt.savefig(sys.argv[2],dpi=100,bbox_inches='tight')
