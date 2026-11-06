"""Assemble the West End street and block layer for the deck page (westend.json, EPSG:26916)."""
import json, numpy as np
from shapely.geometry import shape, mapping, box, Point, Polygon
from shapely.ops import unary_union, polygonize
deck=json.load(open('../deckpage/deck.json'))
dk=[shape(f['geometry']) for f in deck['features'] if f['properties']['layer']=='deck'][0]
cutz=unary_union([shape(f['geometry']) for f in deck['features'] if f['properties']['layer'] in ('cut_precinct','cut_building')])
FORE=box(712972,4331768,713108,4331948)      # CUT east forecourt zone (1912 McLean Ave yard), left empty pending a ruling
excl=unary_union([dk.buffer(1),cutz.buffer(1),FORE])
def r2(g):
    m=mapping(g)
    def rr(c):
        if isinstance(c,(list,tuple)) and c and isinstance(c[0],(int,float)): return [round(c[0],1),round(c[1],1)]
        return [rr(x) for x in c]
    m['coordinates']=rr(m['coordinates']); return m
F=[]
SW=json.load(open('named_we.geojson'))['features']; SE=json.load(open('named_east.geojson'))['features']
from shapely.ops import unary_union as _uu
wl=_uu([shape(f['geometry']) for f in SW if f['properties']['kind']!='drop']).buffer(3)
keepE=[]
for f in SE:
    g=shape(f['geometry'])
    if g.length>0 and g.intersection(wl).length>0.7*g.length: continue
    keepE.append(f)
print('east edges dropped as duplicates of the West End set',len(SE)-len(keepE))
for f in SW: f['properties']['area']='West End'
for f in keepE: f['properties']['area']='Basin east of Plum'
S=SW+keepE
# one width per named street (length-weighted median of its edges); alleys keep their own, capped
import collections
byname=collections.defaultdict(list)
for f in S:
    p=f['properties']
    if p['kind']!='drop' and p['name'] not in ('?','Alley','Unnamed'): byname[p['name']].append((p['w'],shape(f['geometry']).length))
def wmed(v):
    v=sorted(v); tot=sum(L for _,L in v); acc=0
    for w,L in v:
        acc+=L
        if acc>=tot/2: return w
NW={k:wmed(v) for k,v in byname.items()}
sid=0; segs=[]
for f in S:
    p=f['properties']
    if p['kind']=='drop': continue
    g=shape(f['geometry']).difference(excl)
    for part in getattr(g,'geoms',[g]):
        if part.is_empty or part.geom_type!='LineString' or part.length<4: continue
        part=part.simplify(0.8)
        nm=p['name'] if p['name']!='?' else 'Unnamed'
        w0=NW.get(p['name'],p['w']) if p['name'] not in ('?','Alley','Unnamed') else min(p['w'],7.0)
        w=float(np.clip(round(w0*2)/2,2.5,40))
        sid+=1; segs.append((nm,part,w))
        F.append(dict(type='Feature',properties=dict(layer='street',id=f'W{sid:04d}',name=nm,kind=p['kind'],width_m=w,side='',src='1912 survey',area=p['area']),geometry=r2(part)))
# parks as faces of the street network where the 1912 park has no traced block
lines=[s[1] for s in segs]
faces=list(polygonize(unary_union(lines)))
def face_park(seed,inset=None):
    pt=Point(seed)
    for fc in faces:
        if fc.contains(pt):
            # inset by half the bounding street widths (approx. median of nearby widths)
            ws=[s[2] for s in segs if s[1].distance(fc.exterior)<2]
            d=(np.median(ws)/2) if ws else 6
            return fc.buffer(-d,join_style=2)
    return None
B=json.load(open('blocks_we.geojson'))['features']+json.load(open('blocks_east.geojson'))['features']
blocks=[]
for f in B:
    g=shape(f['geometry']).difference(excl).buffer(0)
    if g.is_empty or g.area<150: continue
    blocks.append(g)
PARKS={'Lincoln Park':(713230,4331860),'Sinton Park':(714010,4330960),'McKinley Park':(714020,4332195),'Washington Park':(714690,4331852),'Lytle Park':(715875,4330907)}
ptype={}
for nm,seed in PARKS.items():
    pt=Point(seed); hit=[i for i,g in enumerate(blocks) if g.contains(pt)]
    if hit: ptype[hit[0]]=nm
    else:
        pg=face_park(seed)
        if pg is not None and not pg.is_empty:
            blocks=[g.difference(pg).buffer(0) if g.intersects(pg) else g for g in blocks]
            blocks.append(pg); ptype[len(blocks)-1]=nm
bid=0
for i,g in enumerate(blocks):
    for part in getattr(g,'geoms',[g]):
        if part.area<150: continue
        bid+=1
        nm=ptype.get(i)
        F.append(dict(type='Feature',properties=dict(layer='block',id=f'WB{bid:04d}',type='park' if nm else 'building',area_m2=round(part.area),name=nm or '',src='1912 survey'),geometry=r2(part.simplify(0.5))))
F.append(dict(type='Feature',properties=dict(layer='we_forecourt',name='CUT east forecourt (open)'),geometry=r2(FORE)))
_A=json.load(open('aoi.json')); aoi=shape(_A['aoi_we']).union(shape(_A['aoi_east'])).buffer(1).buffer(-1)
out=dict(crs='EPSG:26916',source='1912 City Topographic Survey (sheets 18, 19, 29, 30, 32, 33), aligned to OSM surviving streets; names read from the 1912 sheets',
         aoi=r2(aoi.simplify(2)),features=F)
json.dump(out,open('../deckpage/basin.json','w'))
ns=sum(1 for f in F if f['properties']['layer']=='street'); nb=sum(1 for f in F if f['properties']['layer']=='block')
names=sorted(set(f['properties']['name'] for f in F if f['properties']['layer']=='street'))
print('streets',ns,'blocks',nb,'parks',list(ptype.values()),'names',len(names))
print('street km',round(sum(s[1].length for s in segs)/1000,1),'block km2',round(sum(shape(f['geometry']).area for f in F if f['properties']['layer']=='block')/1e6,2))
import os; print('size KB',os.path.getsize('../deckpage/basin.json')//1024)
