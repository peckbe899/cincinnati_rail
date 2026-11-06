try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import pickle, json, sys, re, numpy as np, collections
sys.path.insert(0,'.'); sys.path.insert(0,'fit')
from names import key, base
from shapely.geometry import shape, Point, MultiPoint, Polygon, box
from shapely.ops import unary_union
from shapely import affinity
from load import load, frame_of, DECK
SP=_ws.DATA
R=pickle.load(open('osmchk/runs.pkl','rb')); RA,RB=R['RA'],R['RB']
L=json.load(open('fit/basin_sanborn.json'))['features']; ST=[f for f in L if f['properties']['layer']=='street']
byk=collections.defaultdict(list)
for f in ST:
    if f['properties']['name']: byk[key(f['properties']['name'])].append(shape(f['geometry'])); byk['B:'+base(key(f['properties']['name']))].append(shape(f['geometry']))
# Sanborn coverage (frame hulls, same as tiles.py) + deck sheets
P={k:np.array(v) for k,v in json.load(open('fit/tf.json')).items()}; SZ={int(k):v[0] for k,v in json.load(open('fit/sizes.json')).items()}
Rr,Oo=load(); pts=collections.defaultdict(list)
for r in Rr:
    if r['fr']: pts[r['fr']].append((r['x'],r['y']))
regs=[]
for fr,pp in pts.items():
    s=int(''.join(c for c in fr if c.isdigit()))
    if fr not in P or len(pp)<2: continue
    W,H=SZ[s]; buf=330 if s<200 else 560
    hull=MultiPoint(pp).convex_hull.buffer(buf,join_style=2).intersection(box(40,40,W-40,H-40)); p=P[fr]
    M=[p[0],p[1],p[2],p[3],p[4],p[5]] if len(p)==6 else [p[0],p[1],p[1],-p[0],p[2],p[3]]
    regs.append(affinity.affine_transform(hull,M))
COV=unary_union(regs)
pickle.dump(COV,open('osmchk/cov.pkl','wb'))
MOD=re.compile(r"(\bWay\b|Transit Center|Bridge|Plaza|\bDrive\b|\bWalk\b|Circle|\bLane\b|Serpentine|Viaduct|Columbia Parkway|Government Square|Longworth Square|Court$|Ezzard)")
keep=[]; stats=collections.Counter()
for r in RB:
    k=key(r['name']); g=byk.get(k) or byk.get('B:'+base(k),[])
    pp=[Point(*q) for q in r['pts']]
    if g and np.mean([min(h.distance(q) for h in g)<30 for q in pp])>0.6: r['why']='offset (same street, see A)'; stats['offset']+=1; continue
    if MOD.search(r['name']): r['why']='modern by name'; stats['modern']+=1; continue
    cov=np.mean([COV.contains(q) for q in pp])
    if cov<0.5: r['why']='outside Sanborn cover'; stats['nocover']+=1; continue
    if r['L']<28: r['why']='short'; stats['short']+=1; continue
    keep.append(r)
print(stats, 'to review', len(keep), sum(r['L'] for r in keep))
for r in sorted(keep,key=lambda r:-r['L']): print(f"B {r['name'][:30]:30s} {r['hw']:12s} L{r['L']:4d} @ {r['x']:.0f},{r['y']:.0f}")
pickle.dump(dict(RA=RA,RB=RB,keepB=keep),open('osmchk/runs2.pkl','wb'))
