"""Change zones from OSM footprints of post-1912 works, widened over cut/fill slopes from LiDAR.
Z_all  : every significant post-1912 work (maps 1 and 2 rebuild these).
Z_real : works canon does not have (map 3 rebuilds these). Classes marked 'confirm' are held out for Ben."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, json, cv2
from pyproj import Transformer
from scipy import ndimage as ndi
from shapely.geometry import shape, LineString, Point
from shapely.ops import nearest_points
B=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/OSM/")
DM=json.load(open('dem2m.json')); R=4.0; X0=DM['x0']; Y1=DM['y1']; NX=int(DM['w']*DM['res']/R); NY=int(DM['h']*DM['res']/R)
T=Transformer.from_crs('EPSG:4326','EPSG:26916',always_xy=True); Ti=Transformer.from_crs('EPSG:26916','EPSG:4326',always_xy=True)
def toxy(coords):
    a=np.array(coords); e,n=T.transform(a[:,0],a[:,1]); return np.c_[(np.asarray(e)-X0)/R,(Y1-np.asarray(n))/R]
roads=json.load(open(B+'roads.geojson'))['features']
mot=[f for f in roads if f['properties'].get('highway') in ('motorway','motorway_link','trunk','trunk_link')]
def refs(f): return (f['properties'].get('ref') or '')
def utm_line(f): a=np.array(f['geometry']['coordinates']); e,n=T.transform(a[:,0],a[:,1]); return LineString(np.c_[e,n])
# junctions
def junction(ra,rb):
    A=[utm_line(f) for f in mot if f['properties']['highway']=='motorway' and ra in refs(f)]
    Bl=[utm_line(f) for f in mot if f['properties']['highway']=='motorway' and rb in refs(f)]
    best=(1e9,None)
    for a in A:
        for b in Bl:
            d=a.distance(b)
            if d<best[0]: p,q=nearest_points(a,b); best=(d,((p.x+q.x)/2,(p.y+q.y)/2))
    return best
j74=junction('I 74','I 75'); jrw=junction('SR 562','I 71')
print('I-74/I-75 junction',[round(v) for v in j74[1]],'gap',round(j74[0]),' | SR562/I-71 (Rookwood)',[round(v) for v in jrw[1]],'gap',round(jrw[0]))
wt0=json.load(open(B+'water.geojson'))['features']
ohio=[np.array(f['geometry']['coordinates']) for f in wt0 if (f['properties'].get('name')=='Ohio River' and f['properties'].get('waterway')=='river')][0]
oe,on=T.transform(ohio[:,0],ohio[:,1]); oe=np.asarray(oe); on=np.asarray(on); o=np.argsort(oe); oe,on=oe[o],on[o]
def in_ky(x,y): return y<np.interp(x,oe,on)

NI=json.load(open('../kmz_ni/new_interstates.json'))
CANON=[]
for nm,pts in NI.items():
    a=np.array(pts); e,n=T.transform(a[:,0],a[:,1]); CANON.append(LineString(np.c_[e,n]))
from shapely.strtree import STRtree as _ST
_ct=_ST(CANON)
def follow_frac(L,tol=100.0):
    s=np.arange(0,L.length+1e-6,20.0); P=[L.interpolate(x) for x in s]
    return float(np.mean([min(p.distance(CANON[i]) for i in _ct.query(p.buffer(tol)))<tol if len(_ct.query(p.buffer(tol))) else False for p in P]))
def classify(f):
    p=f['properties']; r=refs(f); nm=p.get('name') or ''; L=utm_line(f); c=L.centroid
    if follow_frac(L)>=0.5: return 'kept:canon alignment'
    ky=('KY' in r) or ('Alexandria Pike' in nm) or ('AA' in r)
    if 'I 71;I 75' in r or 'I 71; I 75' in r or ('I 75' in r and in_ky(c.x,c.y)):
        return 'kept:KY I-71/75 boulevard (4D)' if in_ky(c.x,c.y) else 'real'
    if 'I 471' in r: return 'kept:reimagined I-471 (4D)'
    if 'I 74' in r or 'SR 126' in r or r=='CR RR' or 'SR 562' in r or 'Columbia Parkway' in nm or 'SR 32' in r or 'SR 125' in r or 'US 52' in r: return 'kept:list'
    if 'I 75' in r: return 'kept:list' if c.y>j74[1][1] else 'real'
    if 'I 71' in r: return 'kept:I-71 to Rookwood (4C)' if c.y>jrw[1][1] else 'real'
    if 'River Road' in nm: return 'kept:River Rd (4A)'
    if r=='US 50' and c.x>714500: return 'kept:Columbia Pkwy downtown end'
    if '6th Street' in nm or 'US 50' in r: return 'real'
    if 'I 275' in r: return 'real'
    if ky or 'US 27' in r: return 'kept:list'
    return 'unclassified:'+r+'|'+nm
def _old_classify(f):
    p=f['properties']; r=refs(f); nm=p.get('name') or ''; L=utm_line(f); c=L.centroid
    ky=('KY' in r) or ('Alexandria Pike' in nm) or ('AA' in r)
    if 'I 71;I 75' in r or 'I 71; I 75' in r or ('I 75' in r and in_ky(c.x,c.y)):
        return 'confirm:KY I-71/75 corridor' if in_ky(c.x,c.y) else 'real'
    if 'I 471' in r: return 'confirm:I-471'
    if 'I 74' in r or 'I 275' in r or 'SR 126' in r or r=='CR RR' or 'SR 562' in r or 'Columbia Parkway' in nm or 'SR 32' in r or 'SR 125' in r or 'US 52' in r: return 'kept'
    if 'I 75' in r: return 'kept' if c.y>j74[1][1] else 'real'
    if 'I 71' in r: return 'kept' if c.y>jrw[1][1] else 'real'
    if 'Red Bank' in nm: return 'confirm:Red Bank Expressway'
    if '6th Street' in nm or 'River Road' in nm or 'US 50' in r: return 'confirm:US 50 west (6th St Expressway, River Rd)'
    if ky: return 'kept'
    if 'US 27' in r: return 'kept'
    return 'unclassified:'+r+'|'+nm
cls={}
mot_main=[f for f in mot if f['properties']['highway'] in ('motorway','trunk')]
for f in mot_main: cls[f['properties']['@id']]=classify(f)
# real I-275 pieces under 1.5 km (connected) are interchange slivers the hand-drawn alignments miss: keep
from shapely.ops import unary_union as _uu
r275=[f for f in mot_main if cls[f['properties']['@id']]=='real' and 'I 275' in refs(f)]
if r275:
    blobs=_uu([utm_line(f).buffer(30) for f in r275]); blobs=list(getattr(blobs,'geoms',[blobs]))
    for b in blobs:
        mem=[f for f in r275 if utm_line(f).intersects(b)]
        if sum(utm_line(f).length for f in mem)<1500:
            for f in mem: cls[f['properties']['@id']]='kept:interchange sliver'
mainL=[(utm_line(f),cls[f['properties']['@id']]) for f in mot_main]
from shapely.strtree import STRtree
tree=STRtree([l for l,_ in mainL])
for f in mot:
    if f['properties']['highway'] in ('motorway_link','trunk_link'):
        L=utm_line(f); i=tree.nearest(L); cls[f['properties']['@id']]=mainL[i][1]
from collections import Counter
print(Counter(cls.values()))
from collections import defaultdict
km=defaultdict(float)
for f in mot_main:
    c=cls[f['properties']['@id']]; km[(c.split(':')[0] if c!='real' else 'real', refs(f) or f['properties'].get('name',''))]+=utm_line(f).length/1000
for k in sorted(km,key=lambda k:(k[0],-km[k])):
    if km[k]>0.3: print('  %-12s %-40s %6.1f km'%(k[0],k[1][:40],km[k]))
json.dump({f['properties']['@id']:cls[f['properties']['@id']] for f in mot},open('zone_classes_v2.json','w'))
HW={'motorway':18,'trunk':12,'motorway_link':8,'trunk_link':7}
masks={k:np.zeros((NY,NX),np.uint8) for k in ('all','real','confirm')}
cmasks={}
for f in mot:
    p=f['properties']
    if p.get('tunnel') in ('yes',) or p.get('bridge') in ('yes','viaduct'): continue
    xy=toxy(f['geometry']['coordinates']).astype(np.int32); w=max(1,int(round(2*HW[p['highway']]/R)))
    cv2.polylines(masks['all'],[xy],False,1,w)
    c=cls[p['@id']]
    if c=='real': cv2.polylines(masks['real'],[xy],False,1,w)
    if c.startswith('confirm'):
        m=cmasks.setdefault(c,np.zeros((NY,NX),np.uint8)); cv2.polylines(m,[xy],False,1,w)
# other works for maps 1-2
ew=json.load(open(B+'earthworks.geojson'))['features']
for f in ew:
    p=f['properties']; g=f['geometry']
    if g['type']=='Polygon' and (p.get('leisure')=='stadium' or p.get('landuse') in ('landfill','quarry','railway') or p.get('man_made')=='reinforced_slope'):
        cv2.fillPoly(masks['all'],[toxy(g['coordinates'][0]).astype(np.int32)],1)
        if p.get('leisure')=='stadium':
            cen=np.array(g['coordinates'][0]).mean(0)
            if -84.53<cen[0]<-84.49 and 39.090<cen[1]<39.102:   # riverfront stadiums / Banks
                cv2.fillPoly(masks['real'],[toxy(g['coordinates'][0]).astype(np.int32)],1)
    if g['type']=='LineString' and p.get('man_made') in ('dyke','embankment'):
        cv2.polylines(masks['all'],[toxy(g['coordinates']).astype(np.int32)],False,1,8)
wt=json.load(open(B+'water.geojson'))['features']
for f in wt:
    p=f['properties']
    if p.get('waterway')=='river' and 'Mill Creek' in (p.get('name') or ''):
        xy=toxy(f['geometry']['coordinates']).astype(np.int32); cv2.polylines(masks['all'],[xy],False,1,20)
        cen=np.array(f['geometry']['coordinates']).mean(0)
# grow over cut/fill slopes (LiDAR slope > 0.15) up to 60 m
sl=np.load('slope4m.npy') if np.load('slope4m.npy').shape==(NY,NX) else None
steep=sl>0.15
def grow(m,it=15):
    m=m.astype(bool)
    for _ in range(it): m=m|(ndi.binary_dilation(m)&steep)
    m=ndi.binary_closing(m,iterations=3)
    holes,n=ndi.label(~m); sz=ndi.sum(np.ones_like(holes),holes,np.arange(1,n+1))
    small=np.nonzero(sz*16<20000)[0]+1; m=m|np.isin(holes,small)
    return m
Z_all=grow(masks['all']); Z_real=grow(masks['real']); Zc={k:grow(v) for k,v in cmasks.items()}
np.save('Z_real.npy',Z_real)
for k,v in {}.items(): np.save('Zc_'+k.split(':')[1].split(' ')[0].replace('/','')+'.npy',v)
print('Z_all km2 %.1f  Z_real km2 %.1f'%(Z_all.sum()*16/1e6,Z_real.sum()*16/1e6),{k:round(v.sum()*16/1e6,2) for k,v in Zc.items()})
def to_geojson(mask,name,props):
    cs,_=cv2.findContours(mask.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    feats=[]
    for c in cs:
        if cv2.contourArea(c)*16<2000: continue
        c=cv2.approxPolyDP(c,1.0,True)[:,0,:]
        if len(c)<3: continue
        e=X0+(c[:,0]+0.5)*R; n=Y1-(c[:,1]+0.5)*R; lon,lat=Ti.transform(e,n); ring=np.c_[lon,lat].tolist(); ring.append(ring[0])
        feats.append({'type':'Feature','properties':dict(props),'geometry':{'type':'Polygon','coordinates':[ring]}})
    json.dump({'type':'FeatureCollection','name':name,'features':feats},open(name+'.geojson','w')); return len(feats)
print('features:',to_geojson(Z_all,'zones_maps1-2',{'set':'maps 1-2','rule':'rebuild from 1912/1914 sheets'}),
      to_geojson(Z_real,'zones_map3_real_only',{'set':'map 3','rule':'real work canon lacks'}),
      sum(to_geojson(v,'zones_confirm_'+k.split(':')[1].split(' ')[0].replace('/',''),{'set':'confirm','item':k.split(':')[1]}) for k,v in Zc.items()))
json.dump({'I74_I75_junction_utm':j74[1],'Rookwood_junction_utm':jrw[1]},open('junctions.json','w'))
