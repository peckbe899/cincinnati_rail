"""Clean basin streets, deck style: one fitted polyline per street, one width per name, ends snapped to crossings,
blocks cut from the faces between streets (traced 1912 blocks only decide which faces are blocks)."""
import json, numpy as np, collections, math
from shapely.geometry import shape, mapping, LineString, Point, Polygon, MultiLineString, box
from shapely.ops import unary_union, polygonize, nearest_points, substring
from shapely.strtree import STRtree
FT=0.3048
deck=json.load(open('../deckpage/deck.json'))
dk=[shape(f['geometry']) for f in deck['features'] if f['properties']['layer']=='deck'][0]
cutz=unary_union([shape(f['geometry']) for f in deck['features'] if f['properties']['layer'] in ('cut_precinct','cut_building')])
FORE=box(712972,4331768,713108,4331948)
excl=unary_union([dk.buffer(1),cutz.buffer(1),FORE])
A=json.load(open('aoi.json')); AOI=shape(A['aoi_we']).union(shape(A['aoi_east'])).buffer(1).buffer(-1).difference(excl)
GEN={'Alley','Unnamed','?'}
# ---------------------------------------------------------------- input edges
SW=json.load(open('named_we.geojson'))['features']; SE=json.load(open('named_east.geojson'))['features']
E=[]
for f in SW+SE:
    p=f['properties']
    if p['kind']=='drop': continue
    g=shape(f['geometry']).difference(excl)
    for part in getattr(g,'geoms',[g]):
        if part.geom_type=='LineString' and part.length>=3:
            E.append(dict(name=('Unnamed' if p['name']=='?' else p['name']),w=p['w'],g=part,kind=p['kind']))
print('edges',len(E))
# one width per name (length-weighted median), snapped to a 1912 standard width in feet
STD=[8,10,12,15,16,20,24,25,30,33,35,40,45,50,55,60,66,70,75,80,90,100,110,120]
def snapw(m):
    ft=m/FT; return min(STD,key=lambda s:abs(s-ft))*FT
byn=collections.defaultdict(list)
for e in E: byn[e['name']].append((e['w'],e['g'].length))
def wmed(v):
    v=sorted(v); tot=sum(L for _,L in v); acc=0
    for w,L in v:
        acc+=L
        if acc>=tot/2: return w
NW={k:snapw(wmed(v)) for k,v in byn.items() if k not in GEN}
# ---------------------------------------------------------------- split edges into straight pieces
def pieces(g):
    s=g.simplify(2.5); c=list(s.coords)
    if len(c)<2: return []
    out=[]; cur=[c[0]]
    for i in range(1,len(c)-1):
        a=np.subtract(c[i],c[i-1]); b=np.subtract(c[i+1],c[i])
        ang=math.degrees(math.acos(np.clip(np.dot(a,b)/max(np.linalg.norm(a)*np.linalg.norm(b),1e-9),-1,1)))
        cur.append(c[i])
        if ang>35: out.append(cur); cur=[c[i]]
    cur.append(c[-1]); out.append(cur)
    return [LineString(q) for q in out if LineString(q).length>=3]
P=[]
ncurb=0
for e in E:
    if e['name'] not in GEN and e['w']<0.5*NW[e['name']]: ncurb+=1; continue
    for q in pieces(e['g']):
        d=np.subtract(q.coords[-1],q.coords[0]); ang=math.degrees(math.atan2(d[1],d[0]))%180
        P.append(dict(name=e['name'],w=e['w'],g=q,ang=ang,kind=e['kind']))
print('pieces',len(P),'curb traces dropped',ncurb)
# ---------------------------------------------------------------- group collinear pieces of the same street
par=list(range(len(P)))
def find(x):
    while par[x]!=x: par[x]=par[par[x]]; x=par[x]
    return x
def angd(a,b): d=abs(a-b)%180; return min(d,180-d)
def perp(pt,g):
    c=np.array(g.coords); a,b=c[0],c[-1]; d=b-a; L=np.linalg.norm(d)
    if L<1e-6: return np.linalg.norm(pt-a)
    return abs((pt[0]-a[0])*d[1]-(pt[1]-a[1])*d[0])/L
traced=unary_union([shape(f['geometry']).buffer(0) for f in json.load(open('blocks_all.geojson'))['features']])
TT=STRtree(list(getattr(traced,'geoms',[traced])))
TG=list(getattr(traced,'geoms',[traced]))
def bridge_ok(a,b):
    p1,p2=nearest_points(a,b)
    if p1.distance(p2)<1: return True
    br=LineString([p1,p2]).buffer(1.5)
    return sum(TG[k].intersection(br).area for k in TT.query(br))<15
tree=STRtree([p['g'] for p in P])
for i,p in enumerate(P):
    nm=p['name']; gapmax=3 if nm=='Unnamed' else (22 if nm=='Alley' else 160)
    for j in tree.query(p['g'].buffer(gapmax)):
        if j<=i or P[j]['name']!=nm: continue
        q=P[j]
        if angd(p['ang'],q['ang'])>12: continue
        w=NW.get(nm,max(p['w'],q['w']))
        tol=max(4.0,0.45*w)
        mi=np.array(q['g'].interpolate(0.5,normalized=True).coords[0]); mj=np.array(p['g'].interpolate(0.5,normalized=True).coords[0])
        if perp(mi,p['g'])>tol or perp(mj,q['g'])>tol: continue
        dd=p['g'].distance(q['g'])
        if dd>gapmax: continue
        if dd>20 and not bridge_ok(p['g'],q['g']): continue
        par[find(i)]=find(j)
G=collections.defaultdict(list)
for i in range(len(P)): G[find(i)].append(i)
print('groups',len(G))
# ---------------------------------------------------------------- fit one clean polyline per group
def fit(idx):
    pts=[]; wts=[]
    for i in idx:
        g=P[i]['g']; n=max(2,int(g.length//1.0))
        for k in range(n+1): pts.append(g.interpolate(k/n,normalized=True).coords[0])
    X=np.array(pts); c=X.mean(0); U,S,Vt=np.linalg.svd(X-c,full_matrices=False); ax=Vt[0]; nx=np.array([-ax[1],ax[0]])
    s=(X-c)@ax; t=(X-c)@nx
    if len(s)<4: return None
    B=6.0; k=np.floor((s-s.min())/B).astype(int)
    sm=[];tm=[]
    for b in np.unique(k):
        m=k==b
        if m.sum()<2: continue
        sm.append(np.median(s[m])); tm.append(np.median(t[m]))
    if len(sm)<2: sm=[s.min(),s.max()]; tm=[np.median(t)]*2
    sm=np.array(sm); tm=np.array(tm)
    # extend to the true ends of the point cloud
    sm[0]=s.min(); sm[-1]=s.max()
    line=LineString(list(zip(sm,tm))).simplify(1.8)
    q=np.array(line.coords)
    # merge near-collinear vertices
    keep=[0]
    for i in range(1,len(q)-1):
        a=q[i]-q[keep[-1]]; b=q[i+1]-q[i]
        ang=math.degrees(abs(math.atan2(a[0]*b[1]-a[1]*b[0],a@b)))
        if ang>2.5: keep.append(i)
    keep.append(len(q)-1); q=q[keep]
    W=c+np.outer(q[:,0],ax)+np.outer(q[:,1],nx)
    return LineString(W)
ST=[]
for gid,idx in G.items():
    nm=P[idx[0]]['name']; L=fit(idx)
    if L is None or L.length<8: continue
    w=NW.get(nm) or snapw(float(np.median([P[i]['w'] for i in idx])))
    if nm in GEN: w=min(w,6.1)
    alley=nm.endswith('Alley') or nm=='Alley' or w<6.5
    ST.append(dict(name=nm,w=w,g=L,kind='we_alley' if alley else 'we_street'))
print('fitted streets',len(ST))
# ---------------------------------------------------------------- snap ends to the street they meet
def ext_ray(g,end,length):
    c=list(g.coords)
    if end==0: a,b=np.array(c[1]),np.array(c[0])
    else: a,b=np.array(c[-2]),np.array(c[-1])
    d=(b-a)/max(np.linalg.norm(b-a),1e-9); return b,d
for it in range(2):
    tr=STRtree([s['g'] for s in ST])
    for i,s in enumerate(ST):
        for end in (0,1):
            g=s['g']; p,d=ext_ray(g,end,30)
            ray=LineString([p-d*12,p+d*30])
            best=None
            for j in tr.query(ray):
                if j==i: continue
                o=ST[j]['g']; x=ray.intersection(o)
                if x.is_empty: continue
                for pt in getattr(x,'geoms',[x]):
                    if pt.geom_type!='Point': continue
                    along=np.dot(np.array(pt.coords[0])-p,d)
                    # skip crossings of streets that run nearly parallel
                    if abs(along)<0.01 and False: pass
                    if best is None or abs(along)<abs(best[0]): best=(along,pt.coords[0])
            if best is None: continue
            along,q=best
            c=list(g.coords)
            if along>=0:      # extend to the crossing
                c=([q]+c) if end==0 else (c+[q])
                if end==0: c=[q]+c[1:] if np.linalg.norm(np.subtract(c[1],q))<1e-6 else c
            else:             # trim back to the crossing
                if end==0:
                    t=g.project(Point(q)); c=list(substring(g,t,g.length).coords)
                else:
                    t=g.project(Point(q)); c=list(substring(g,0,t).coords)
            if len(c)>=2 and LineString(c).length>=4: s['g']=LineString(c)
# drop exact duplicate starting point repeats
for s in ST:
    c=[]; 
    for q in s['g'].coords:
        if not c or np.hypot(q[0]-c[-1][0],q[1]-c[-1][1])>0.05: c.append(q)
    s['g']=LineString(c)
# clip to the area, drop stubs
OUT=[]
for s in ST:
    g=s['g'].intersection(AOI.buffer(2))
    for part in getattr(g,'geoms',[g]):
        if part.geom_type!='LineString': continue
        minlen=30 if s['name']=='Unnamed' else 12
        if part.length<minlen: continue
        OUT.append(dict(s,g=part))
print('final streets',len(OUT),'km',round(sum(s['g'].length for s in OUT)/1000,1))
# ---------------------------------------------------------------- blocks: traced 1912 blocks grown out to the clean street edges
import rasterio.features as rf, scipy.ndimage as ndi
from rasterio.transform import from_origin
from skimage.segmentation import expand_labels
E0g,N1g,R=712300,4334200,0.5
Bt=np.load('B.npy'); H_,W_=Bt.shape; T=from_origin(E0g,N1g,R,R)
bands=unary_union([s['g'].buffer(s['w']/2,cap_style=2,join_style=2,mitre_limit=3) for s in OUT])
bandr=rf.rasterize([(bands,1)],out_shape=(H_,W_),transform=T,all_touched=False).astype(bool)
aoir=rf.rasterize([(AOI,1)],out_shape=(H_,W_),transform=T).astype(bool)
free=aoir&~bandr
L=np.where(free,Bt,0)
L=expand_labels(L,distance=24); L[~free]=0
# parks: leftover free space holding a park seed
PARKS={'Lincoln Park':(713230,4331860),'Sinton Park':(714010,4330960),'McKinley Park':(714020,4332195),'Washington Park':(714690,4331852),'Lytle Park':(715875,4330907)}
pk={}
left=free&(L==0); ll,_=ndi.label(left)
nxt=L.max()+1
for nm,(x,y) in PARKS.items():
    r,c=int((N1g-y)/R),int((x-E0g)/R)
    if L[r,c]>0: pk[int(L[r,c])]=nm; continue
    k=ll[r,c]
    if k and (ll==k).sum()*0.25<80000: L[ll==k]=nxt; pk[nxt]=nm; nxt+=1
polys=collections.defaultdict(list)
for g,v in rf.shapes(L.astype(np.int32),mask=L>0,transform=T):
    polys[int(v)].append(shape(g))
BLK=[]
for v,ps in polys.items():
    g=unary_union(ps)
    for part in getattr(g,'geoms',[g]):
        if part.area<150: continue
        q=part.buffer(0.6,join_style=2).difference(bands).intersection(AOI).buffer(0)
        q=q.buffer(-0.4,join_style=2).buffer(0.4,join_style=2).simplify(0.5)
        for qq in getattr(q,'geoms',[q]):
            if qq.geom_type!='Polygon' or qq.area<150: continue
            nm=pk.get(v,'')
            BLK.append(dict(g=qq,type='park' if nm else 'building',name=nm))
print('blocks',len(BLK),'km2',round(sum(b['g'].area for b in BLK)/1e6,2))
# ---------------------------------------------------------------- write
def r2(g):
    m=mapping(g)
    def rr(c):
        if isinstance(c,(list,tuple)) and c and isinstance(c[0],(int,float)): return [round(c[0],1),round(c[1],1)]
        return [rr(x) for x in c]
    m['coordinates']=rr(m['coordinates']); return m
WE=shape(A['aoi_we'])
F=[]
for i,s in enumerate(OUT):
    area='West End' if WE.contains(s['g'].interpolate(0.5,normalized=True)) else 'Basin east of Plum'
    F.append(dict(type='Feature',properties=dict(layer='street',id=f'W{i+1:04d}',name=s['name'],kind=s['kind'],width_m=round(s['w'],2),width_ft=round(s['w']/FT),side='',src='1912 survey',area=area),geometry=r2(s['g'])))
for i,b in enumerate(BLK):
    F.append(dict(type='Feature',properties=dict(layer='block',id=f'WB{i+1:04d}',type=b['type'],area_m2=round(b['g'].area),name=b['name'],src='1912 survey'),geometry=r2(b['g'])))
F.append(dict(type='Feature',properties=dict(layer='we_forecourt',name='CUT east forecourt (open)'),geometry=r2(FORE)))
json.dump(dict(crs='EPSG:26916',source='1912 City Topographic Survey (sheets 18, 19, 29, 30, 32, 33), aligned to OSM surviving streets; streets fitted as straight runs with one 1912 standard width per street; names read from the 1912 sheets',features=F),open('../deckpage/basin.json','w'))
import os; print('KB',os.path.getsize('../deckpage/basin.json')//1024)
