try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np
from shapely.geometry import LineString, shape
sys.path.insert(0,(_ws.CODE + 'trunk2')); import geo4 as Q
SP=_ws.DATA
T=json.load(open(SP+'deckpage/tracks.json')); C=json.load(open(SP+'deckpage/context.json'))
lines=[]
for f in T['features']:
    if f['geometry']['type']=='LineString':
        n=f['properties'].get('name') or ''; lines.append((n,LineString(np.asarray(f['geometry']['coordinates'])[:,:2])))
for t in C['tracks']:
    if t['sys']=='rer': lines.append(('RER '+(t.get('name') or t.get('pid')),LineString(t['c'])))
ab=lambda n: (n.replace('Lower-level pair ','L').replace(', on the viaduct','v').replace(', on the fill','f').replace('APEx north approach ','ap').replace(' of 6','').replace('APEx Dayton (Southwest Chief), track ','Dy').replace('APEx Norwood (Transcontinental), track ','Nw').replace(' of 2','').replace('RER R-','').replace('R5 to the Cumminsville Spur ','R5')[:14])
for s in [float(v) for v in sys.argv[1:]]:
    p=Q.TR.at(s)[0]; e=Q.TR.at(s,1.0)[0]-p; cut=LineString([p-e*70,p+e*70]); row=[]
    for n,g in lines:
        X=g.intersection(cut)
        for q in getattr(X,'geoms',[X]):
            if not X.is_empty and q.geom_type=='Point': row.append((round(float((np.array(q.coords[0])-p)@e),1),ab(n)))
    print(int(s),' '.join(f'{o}:{n}' for o,n in sorted(row)))
