try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import sys,numpy as np
sys.path.insert(0,(_ws.CODE + 'trunk2'))
import geo3 as Q
from shapely.geometry import LineString
L=Q.build(); ab={'ORR/TV west':'W','ORR/TV east':'E','APEx Dayton':'Dy','APEx Norwood':'Nw','APEx Indy':'In','RER B':'B','RER D':'D'}
G=[(next(v for k,v in ab.items() if n.startswith(k))+n.split()[-1][0],LineString(d['c'])) for n,d in L.items()]
for s in [float(v) for v in sys.argv[1:]]:
    p=Q.TR.at(s)[0]; e=Q.TR.at(s,1.0)[0]-p; cut=LineString([p-e*150,p+e*150]); row=[]
    for n,g in G:
        X=g.intersection(cut)
        for q in getattr(X,'geoms',[X]):
            if not X.is_empty and q.geom_type=='Point': row.append((round(float((np.array(q.coords[0])-p)@e),1),n))
    print(int(s),' '.join(f'{o}:{n}' for o,n in sorted(row)))
