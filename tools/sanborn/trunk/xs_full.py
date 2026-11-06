try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np
from shapely.geometry import shape, LineString, Point
SP=_ws.DATA
T=json.load(open(SP+'deckpage/tracks.json')); C=json.load(open(SP+'deckpage/context.json'))
def g(nm): return [shape(f['geometry']) for f in T['features'] if (f['properties'].get('name') or '').startswith(nm)][0]
a2,a3=g('APEx north approach 2 of 6'),g('APEx north approach 3 of 6')
n=600; south=[((np.array(a2.interpolate(1-i/n,normalized=True).coords[0])+np.array(a3.interpolate(1-i/n,normalized=True).coords[0]))/2) for i in range(n+1)]
north=json.load(open(SP+'trunk/ref_north.json'))
ref=LineString(list(map(tuple,south))+[tuple(c) for c in north[1:]])
json.dump(list(ref.coords),open(SP+'trunk/ref_full.json','w'))
L=[]
for f in T['features']:
    nm=f['properties'].get('name') or ''; gg=shape(f['geometry'])
    if gg.geom_type!='LineString': continue
    if nm.startswith('APEx north approach'): L.append(('A'+nm[20],gg))
    elif nm.startswith('Lower-level pair'): L.append(('Low'+nm[17]+nm[26],gg))
    elif nm.startswith('APEx Southwest Chief, Trans'): L.append(('A'+nm[44],gg))
    elif nm.startswith('R5'): L.append(('R5',gg))
for t in C['tracks']:
    if t['sys']=='rer' and t.get('pid','')[:4] in ('R-BD','R-B-','R-D-'): L.append(('B/D' if 'BD' in t['pid'] else t['pid'][2], LineString(t['c'])))
if __name__=='__main__':
  print('ref',round(ref.length),'ludlow s',round(ref.project(Point(712743,4336966))))
  for s in [float(v) for v in sys.argv[1:]]:
    p=np.array(ref.interpolate(s).coords[0]); q=np.array(ref.interpolate(s+3).coords[0]); u=(q-p)/np.linalg.norm(q-p); nrm=np.array([-u[1],u[0]])
    cut=LineString([p-nrm*120,p+nrm*120]); row=[]
    for nm,gg in L:
        X=gg.intersection(cut)
        for pt in getattr(X,'geoms',[X]):
            if not X.is_empty and pt.geom_type=='Point': row.append((round(float((np.array(pt.coords[0])-p)@nrm),1),nm))
    print(int(s),[round(v) for v in p],' '.join(f'{o}:{n}' for o,n in sorted(row)))
