try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, numpy as np, rasterio
from shapely.geometry import LineString, Point, shape, box
from shapely.ops import linemerge, unary_union, substring
SP=_ws.DATA
L=json.load(open(SP+'nv/lines.json'))
def get(src,name,minlen=0):
    gs=[LineString(o['c']) for o in L if o['src']==src and o['name']==name]
    return max(gs,key=lambda g:g.length)
DEM=rasterio.open(SP+'handoff/out/map3_profile_dem_dm.vrt')
def gz(e,n): v=list(DEM.sample([(e,n)]))[0][0]; return None if v==-32768 else v/10
# APEx centre path: Cincinnati-Camp Washington then Camp Washington-St Bernard (North Coast Flyer pieces)
a=get('APEx','Cincinnati-Camp Washington'); b=get('APEx','Camp Washington-St Bernard')
ca=list(a.coords); cb=list(b.coords)
if Point(ca[0]).distance(Point(712830,4331870))>Point(ca[-1]).distance(Point(712830,4331870)): ca=ca[::-1]
if Point(cb[0]).distance(Point(ca[-1]))>Point(cb[-1]).distance(Point(ca[-1])): cb=cb[::-1]
# KMZ glitch: the 'Cincinnati-Camp Washington' piece starts with (712252.5, 4335706.8) then (712257.3, 4335836.9) before jumping back south;
# in CUT-north order its last three vertices are out of order. Rebuild in true order and drop the duplicate join vertex.
tail=ca[-3:]; tail=sorted(tail,key=lambda p:p[1]); ca=ca[:-3]+tail
pts=[ca[0]]
for q in ca[1:]+cb:
    if (q[0]-pts[-1][0])**2+(q[1]-pts[-1][1])**2>4: pts.append(q)
C=LineString(pts)
import numpy as _np
_a=_np.array(pts); _d=_np.diff(_a,axis=0); _b=_np.degrees(_np.arctan2(_d[:,0],_d[:,1]))
_t=_np.abs((_np.diff(_b)+180)%360-180); print('max vertex turn %.1f deg' % _t.max())
print('centre length', round(C.length), C.coords[0], C.coords[-1])
s_mar=C.project(Point(712742.7,4334346)); s_tip=C.project(Point(712247,4335576))
print('s Marshall', round(s_mar), 's tip', round(s_tip))
T3={o['name']:o for o in L if o['src']=='TRIMET3D'}
def z3(name,p):
    o=T3[name]; c=np.array(o['c']); i=int(np.argmin(np.hypot(c[:,0]-p.x,c[:,1]-p.y))); return float(o['z'][i]), float(np.hypot(c[i,0]-p.x,c[i,1]-p.y))
# divergences
for nm,(src,name) in {'APEx Greensburg':('APEx','Greensburg-CUT TRIMET'),'Vandalia (Dayton)':('APEx','Vandalia-Cincinnati'),'Norwood':('APEx','Cincinnati-Norwood'),'TRIMET Greensburg':('TRIMET3D','Greensburg-California 3D'),'TRIMET Dayton-Indep':('TRIMET3D','Dayton-Independence 3D'),'TRIMET Oxford-Aurora':('TRIMET3D','Oxford-Aurora 3D'),'TRIMET Loveland-Batavia':('TRIMET3D','Loveland-Batavia 3D'),'TRIMET Lebanon-Walton':('TRIMET3D','Lebanon-Walton 3D'),'RER B trunk':('CR','RER Mill Creek Trunk'),'RER B Cincinnati-Dayton':('CR','Cincinnati-Dayton')}.items():
    g=get(src,name)
    # walk along C from the tip; first chainage where g is farther than 25 m
    last=None
    for s in np.arange(s_tip-400, C.length, 10):
        d=g.distance(C.interpolate(s))
        if d>25 and last is not None and last<=25: print('  %-24s leaves the APEx path at s %5d (%s), %.0f m' % (nm, s, [round(v) for v in C.interpolate(s).coords[0]], d))
        last=d
O=json.load(open(SP+'lph/osm_north.geojson'))['features']
B=json.load(open(SP+'deckpage/basin.json'))['features']
D=json.load(open(SP+'deck/deck.json'))['features']
streets=[]
for f in O:
    g=shape(f['geometry']); p=f['properties']
    if g.geom_type=='LineString' and p.get('name') and p.get('highway') not in ('footway','path','cycleway','service','steps','track',None): streets.append(('OSM',p['name'],p.get('highway'),p.get('bridge'),g))
for f in B:
    if f['properties']['layer']=='street' and f['properties'].get('name'): streets.append(('basin',f['properties']['name'],f['properties'].get('set'),f['properties'].get('structure'),LineString(f['geometry']['coordinates'])))
for f in D:
    if f['properties']['layer']=='street': streets.append(('deck',f['properties']['name'],f['properties'].get('zone'),None,LineString(f['geometry']['coordinates'])))
X=[]
seg=substring(C, s_mar-50, C.length)
for src,nm,k,br,g in streets:
    x=seg.intersection(g)
    for q in getattr(x,'geoms',[x]):
        if q.is_empty or q.geom_type!='Point': continue
        s=C.project(q); X.append((s,src,nm,k,br,round(q.x),round(q.y),gz(q.x,q.y), z3('Dayton-Independence 3D',q)))
X.sort()
seen=set()
for r in X:
    key=(r[2],round(r[0]/30))
    if key in seen: continue
    seen.add(key)
    print('%6d %-6s %-38s %-10s %-6s %s ground %.1f  TRIMET %.1f (%.0f m off)' % (r[0], r[1], r[2][:38], str(r[3])[:10], str(r[4])[:6], (r[5],r[6]), r[7] or -1, r[8][0], r[8][1]))
prof=[(s, gz(*C.interpolate(s).coords[0])) for s in range(int(s_mar)-200, int(C.length), 50)]
json.dump(dict(C=list(C.coords), s_mar=s_mar, s_tip=s_tip, prof=prof, X=[list(map(str,r[:5]))+[r[5],r[6],r[7],r[8][0]] for r in X]), open(SP+'nv/profile.json','w'))
print([ (s, z) for s,z in prof][::4])
