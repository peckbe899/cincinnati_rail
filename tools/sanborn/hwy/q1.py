import json
from shapely.geometry import LineString, Point, box
SP=''
B=json.load(open('deckpage/basin.json')); L=json.load(open('dbread5/deck/layout.json'))['streets']
D=json.load(open('hwy/data.json')); O=D['origin']
oh=[s for s in D['segs'] if s['r']=='OH-75' and s['a'] in (14.54,19.4) and 'BRT' not in s['t']]
OH=LineString([ (x+O[0],y+O[1]) for s in oh for x,y in s['c']])
def km(p):
    # chainage from the 14.54 piece start
    s0=[s for s in oh if s['a']==14.54][0]; L0=LineString([(x+O[0],y+O[1]) for x,y in s0['c']])
    d=OH.project(Point(p)); return 14.54+d/1000*(19.4-14.54)/(L0.length/1000)
st={}
for f in B['features']:
    p=f['properties']
    if p['layer']!='street': continue
    e=L.get(p['id'],{})
    if e.get('del'): continue
    n=e.get('n') or p.get('name') or ''
    if any(k in n for k in ('Central Parkway','Ludlow','Albone','Spring Grove')):
        c=e.get('c') or f['geometry']['coordinates']; g=LineString(c)
        if g.intersects(box(712300,4336400,713300,4337600)):
            print(p['id'],n,round(e.get('w',p.get('width_m',0)),1),[tuple(map(round,c[0])),tuple(map(round,c[-1]))],'len',round(g.length))
            st[p['id']]=(n,g)
            x=g.intersection(OH)
            if not x.is_empty: print('   x OH-75 at',[ (round(q.x),round(q.y),round(km((q.x,q.y)),3)) for q in getattr(x,'geoms',[x])])
C=json.load(open('deckpage/context.json'))
for t in C['tracks']:
    g=LineString(t['c'])
    if not g.intersects(box(712600,4336750,713100,4337300)): continue
    xs=[]
    for i,(n,s) in st.items():
        x=g.intersection(s)
        if not x.is_empty: xs.append((n,[(round(q.x),round(q.y)) for q in getattr(x,'geoms',[x]) if q.geom_type=='Point']))
    xo=g.intersection(OH)
    print('TRK',t.get('sys'),t.get('name','')[:40],xs, 'OH:',[(round(q.x),round(q.y)) for q in getattr(xo,'geoms',[xo]) if q.geom_type=='Point'] if not xo.is_empty else '')
