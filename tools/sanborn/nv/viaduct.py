"""North trunk viaduct, Ludlow to the deck: proposal check (rail levels, street clearances, B/D dive)."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, math, numpy as np, rasterio
from shapely.geometry import LineString, Point, shape
SP=_ws.DATA
P=json.load(open(SP+'nv/profile.json')); C=LineString(P['C'])
DEM=rasterio.open(SP+'handoff/out/map3_profile_dem_dm.vrt')
def gz(e,n): return list(DEM.sample([(e,n)]))[0][0]/10
def deck(n): return 151.8+(n-4330700)/4840*8.2
L=json.load(open(SP+'nv/lines.json'))
T3={o['name']:o for o in L if o['src']=='TRIMET3D'}
BD=LineString(T3['Dayton-Independence 3D']['c']); BDZ=np.array(T3['Dayton-Independence 3D']['z'])
GR=LineString(T3['Greensburg-California 3D']['c']); GRZ=np.array(T3['Greensburg-California 3D']['z'])
s_tip=P['s_tip']; s_mar=P['s_mar']
LUD=[shape(f['geometry']) for f in json.load(open(SP+'lph/osm_north.geojson'))['features'] if f['properties'].get('name')=='Ludlow Avenue' and shape(f['geometry']).geom_type=='LineString']
s_lud=min(C.project(C.intersection(g)) for g in LUD if C.intersects(g) and C.intersection(g).geom_type=='Point')
Z_LUD=155.5
Z_TIP=deck(C.interpolate(s_tip).y)+6.5
G=(Z_TIP-Z_LUD)/(s_lud-s_tip)
def rail(s):
    if s>=s_lud: return Z_LUD
    if s>=s_tip: return Z_TIP-G*(s-s_tip)
    return deck(C.interpolate(s).y)+6.5
print('Ludlow s %.0f, tip s %.0f, rail at tip %.2f, grade %.3f%%, length %.0f m' % (s_lud, s_tip, Z_TIP, G*100, s_lud-s_tip))
print('Marshall s %.0f rail %.2f' % (s_mar, rail(s_mar)))
# streets: zone 3 originals (west end, 93.6 deg to Beekman), the lobe streets, 1904 crossings, Hopple
B=json.load(open(SP+'deckpage/basin.json'))['features']
def west_end(nm, near):
    best=None
    for f in B:
        if f['properties']['layer']!='street' or f['properties']['name']!=nm: continue
        c=np.array(f['geometry']['coordinates']); w=c[np.argmin(c[:,0])]; d=np.hypot(*(w-near))
        if best is None or d<best[0]: best=(d,w)
    return best[1]
u=np.array([math.sin(math.radians(273.6)),math.cos(math.radians(273.6))])
rows=[]
for nm,near in (('Stock Avenue',(712386,4335144)),('Ethan Avenue',(712455,4335241)),('Bates Avenue',(712454,4335316)),('Alabama Avenue',(712382,4335399)),('Monmouth Avenue',(712460,4335571)),('Sassafras Street',(712466,4335729)),('Arlington Street',(712468,4335803)),('Marquis Avenue',(712380,4335884)),('Adelaide Street',(712363,4335972)),('Brashears Street',(712458,4336082)),('Earl Avenue',(712442,4336218)),('Whiteley Street',(712431,4336300))):
    w=west_end(nm,np.array(near)); l=LineString([tuple(w),tuple(w+u*1200)])
    for path,lab in ((C,'APEx/ORR'),(BD,'TRI B/D')):
        x=path.intersection(l)
        if x.is_empty: continue
        q=x if x.geom_type=='Point' else list(x.geoms)[0]
        s=C.project(q); ondeck=s<s_tip+5
        zs=deck(q.y) if ondeck else gz(q.x,q.y)
        rows.append((nm,lab,round(s),round(q.x),round(q.y),round(zs,1)))
for f in B:
    p=f['properties']
    if p['layer']=='street' and p['name'] in ('Spring Grove Avenue','Ford Street','Colerain Avenue','Streng Street'):
        x=C.intersection(LineString(f['geometry']['coordinates']))
        for q in getattr(x,'geoms',[x]):
            if q.geom_type=='Point' and s_tip<C.project(q)<s_lud: rows.append((p['name'],'APEx/ORR',round(C.project(q)),round(q.x),round(q.y),round(gz(q.x,q.y),1)))
print('\nAPEx/ORR on the viaduct (street under needs 6.8 m; 6.5 m over deck streets as the arch viaduct):')
for r in sorted(rows,key=lambda r:r[2]):
    if r[1]!='APEx/ORR': continue
    z=rail(r[2]); d=z-r[5]; need=6.5 if r[2]<s_tip+5 else 6.8
    print('  %-20s s %5d rail %.1f street %.1f clear %.1f %s' % (r[0],r[2],z,r[5],d,'ok' if d>=need-0.05 else 'SHORT'))
# B/D dive: from <= street-5.2 at Alabama (box with cover) to >= street+6.8 at Monmouth
bd=[r for r in rows if r[1]=='TRI B/D']
ala=[r for r in bd if r[0].startswith('Alabama')][0]; mon=[r for r in bd if r[0].startswith('Monmouth')][0]
sa,sm=BD.project(Point(ala[3],ala[4])),BD.project(Point(mon[3],mon[4]))
need=(mon[5]+6.8)-(ala[5]-5.2)
print('\nB/D: Alabama s %.0f street %.1f -> rail <= %.1f; Monmouth s %.0f street %.1f -> rail >= %.1f; %.1f m in %.0f m = %.2f%%' % (sa,ala[5],ala[5]-5.2,sm,mon[5],mon[5]+6.8,need,sm-sa,need/(sm-sa)*100))
cw=BD.project(Point(712401.5,4334799.9)); print('B/D: Camp Washington station on the B/D line s %.0f (151.2 m); Alabama %.0f m north of it' % (cw, sa-cw))
# levels of the Greensburg lines where they leave
for nm,s in (('APEx Indianapolis leaves',4135),('TRI D leaves (TRIMET 3D)',4555)):
    q=C.interpolate(s); i=int(np.argmin(np.hypot(GR.xy[0]-np.array(q.x),np.array(GR.xy[1])-q.y)))
    print('%-28s s %d rail on viaduct %.1f; TRIMET 3D D there %.1f' % (nm,s,rail(s),GRZ[i]))
# Hopple
hop=[f for f in B if f['properties'].get('name')=='Hopple Street' and f['properties'].get('structure')=='viaduct'][0]
x=C.intersection(LineString(hop['geometry']['coordinates'])); s=C.project(x)
print('\nHopple crosses at s %.0f: viaduct rail %.1f, deck %.1f (Hopple at deck level gets %.1f m)' % (s, rail(s), deck(x.y), rail(s)-deck(x.y)))
json.dump(dict(s_lud=s_lud,s_tip=s_tip,s_mar=s_mar,Z_TIP=Z_TIP,Z_LUD=Z_LUD,G=G,rows=rows,bd=dict(sa=sa,sm=sm,za=ala[5]-5.2,zm=mon[5]+6.8,cw=cw)),open(SP+'nv/viaduct.json','w'))
