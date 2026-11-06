import json, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import shape, box
E0,N0,E1,N1=[float(v) for v in sys.argv[1:5]]; out=sys.argv[5]
BX=box(E0,N0,E1,N1)
B=json.load(open('deckpage/basin.json')); L=json.load(open('dbread5/deck/layout.json'))['streets']; Hh=json.load(open('deckpage/hwy.json'))
fig,ax=plt.subplots(figsize=(12,12*(N1-N0)/(E1-E0)),dpi=110)
for f in B['features']:
    p=f['properties']; g=shape(f['geometry'])
    if not g.intersects(BX): continue
    if p['layer']=='block':
        for q in getattr(g,'geoms',[g]): ax.fill(*q.exterior.xy,color='#e8e2d6',lw=0.3,ec='#b9b0a0')
for f in B['features']:
    p=f['properties']
    if p['layer']!='street': continue
    e=L.get(p['id'],{})
    if e.get('del'): continue
    from shapely.geometry import LineString
    g=LineString(e.get('c') or f['geometry']['coordinates'])
    if not g.intersects(BX): continue
    w=e.get('w',p.get('width_m',10)); poly=g.buffer(w/2,cap_style=2,join_style=2,mitre_limit=2)
    for q in getattr(poly,'geoms',[poly]): ax.fill(*q.exterior.xy,color='#cfcfcf',lw=0)
COL={'lanes':'#555a60','brt':'#d6336c','median':'#7fb069','sep':'#999','shoulder':'#888','shoulder_r':'#888','verge':'#a8c98c','walk':'#e9e4da','plat':'#c9a7d8','load':'#7a7f86','wall':'#333','pocket':'#3b5ea8','brt_x':'#f08fb0','add_lane':'#6d7f9a','junction':'#555a60'}
for f in Hh['features']:
    p=f['properties']; g=shape(f['geometry'])
    if not g.intersects(BX): continue
    if p['layer']=='hw_strip':
        for q in getattr(g,'geoms',[g]): ax.fill(*q.exterior.xy,color=COL.get(p['kind'],'k'),alpha=0.45 if p.get('tunnel') else 0.95,lw=0)
for f in Hh['features']:
    p=f['properties']; g=shape(f['geometry'])
    if not g.intersects(BX): continue
    if p['layer']=='hw_line': ax.plot(*g.xy,color='w',lw=0.5,ls='--' if p['style']=='dash' else '-')
    if p['layer']=='hw_sig': ax.plot(g.x,g.y,'o',color='#f2b705',ms=4,mec='k')
    if p['layer']=='hw_lab': ax.text(g.x,g.y,p['text'],fontsize=7,rotation=p.get('ang',0),ha='center',color='k')
C=json.load(open('deckpage/context.json'))
for t in C['tracks']:
    g=LineString(t['c'])
    if g.intersects(BX) and t['sys']=='rer': ax.plot(*g.xy,color='#0b6fd6',lw=0.6)
ax.set_xlim(E0,E1); ax.set_ylim(N0,N1); ax.set_aspect('equal'); plt.tight_layout(); plt.savefig(out)
