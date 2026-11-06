import pickle, json, numpy as np, collections, sys
sys.path.insert(0,'fit'); sys.path.insert(0,'.')
from solve import apply
from osmx import lines_osm
from shapely.geometry import Point
from shapely.ops import unary_union
from names import key, base
D=pickle.load(open('fit/obs.pkl','rb')); R=D['R']; P={k:np.array(v) for k,v in json.load(open('fit/tf.json')).items()}
X=pickle.load(open('fit/osmx.pkl','rb')); osm=X['osm']
OL={k:unary_union(v) for k,v in lines_osm().items()}
def normal(k,e,n):
    g=OL[k]; d=g.project(Point(e,n)); a=g.interpolate(max(0,d-15)); b=g.interpolate(d+15)
    t=np.array([b.x-a.x,b.y-a.y]); t/=np.hypot(*t)+1e-9; return np.array([-t[1],t[0]])
proj=collections.defaultdict(list)
for r in R:
    if r['fr'] not in P: continue
    e,n=apply(P[r['fr']],r['x'],r['y'])
    for c in r['cand']:
        if c[2]!='osm': continue
        if np.hypot(c[0]-e,c[1]-n)>25: continue
        v=np.array([e-c[0],n-c[1]])
        for k in c[3]: proj[k].append((float(v@normal(k,c[0],c[1])), r['fr']))
rows=[]
for k,v in proj.items():
    a=np.array([x for x,_ in v]); rows.append((k,len(a),np.median(a),np.percentile(np.abs(a),75),sorted({f for _,f in v},key=lambda f:int(''.join(c for c in f if c.isdigit())))))
rows.sort(key=lambda t:-abs(t[2]))
for k,n,m,q,fr in rows[:45]: print(f'{k:22s} n={n:3d} median {m:6.1f}  p75|.| {q:5.1f}  {fr[:12]}')
