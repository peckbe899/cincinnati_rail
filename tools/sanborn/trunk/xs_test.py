try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np
sys.path.insert(0,(_ws.CODE + 'trunk'))
from shapely.geometry import LineString, shape
import plan as P
SP=_ws.DATA
C=json.load(open(SP+sys.argv[1])); T=json.load(open(SP+sys.argv[2])); F={'N':P.FN,'E':P.FE}[sys.argv[3]]
L=[]
ab={'APEx north approach':'A','Lower-level pair W':'TVv','Lower-level pair E':'ORv','APEx Dayton':'AD','APEx Norwood':'AN','Transvalley':'TV','ORR X2':'X2','ORR,':'OR','Crossover':'xo','R5 to':'R5'}
for f in T['features']:
    n=f['properties'].get('name') or ''
    if f['geometry']['type']!='LineString': continue
    for k,v in ab.items():
        if n.startswith(k): L.append((v+(n[20] if v=='A' else ''),shape(f['geometry'])))
for t in C['tracks']:
    if t['sys']=='rer' and t.get('pid','')[:4] in ('R-BD','R-B-','R-D-'): L.append(('B' if t['line']=='B' else 'D' if t['line']=='D' else 'BD',LineString(t['c'])))
for s in [float(v) for v in sys.argv[4:]]:
    p=F.at(s)[0]; e=F.at(s,1.0)[0]-p; cut=LineString([p-e*150,p+e*150]); row=[]
    for n,g in L:
        X=g.intersection(cut)
        for q in getattr(X,'geoms',[X]):
            if not X.is_empty and q.geom_type=='Point': row.append((round(float((np.array(q.coords[0])-p)@e),1),n))
    print(int(s),' '.join(f'{o}:{n}' for o,n in sorted(row)))
