try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np
from shapely.geometry import shape, LineString, Point, Polygon
SP=_ws.DATA
T=json.load(open(SP+'deckpage/tracks.json')); C=json.load(open(SP+'deckpage/context.json'))
H=json.load(open(SP+'deckpage/hwy.json')); BJ=json.load(open(SP+'deckpage/basin.json'))
g2=[shape(f['geometry']) for f in T['features'] if (f['properties'].get('name') or '').startswith('APEx Southwest Chief, Transcontinental Limited (2 of 4')][0]
g3=[shape(f['geometry']) for f in T['features'] if (f['properties'].get('name') or '').startswith('APEx Southwest Chief, Transcontinental Limited (3 of 4')][0]
n=400; ref=LineString([((np.array(g2.interpolate(i/n,normalized=True).coords[0])+np.array(g3.interpolate(i/n,normalized=True).coords[0]))/2) for i in range(n+1)])
json.dump(list(ref.coords),open(SP+'trunk/ref_north.json','w'))
print('ref length',round(ref.length))
L=[]
for f in H['features']:
    p=f['properties']
    if p.get('layer')=='hw_piece':
        g=shape(f['geometry']); L.append(('HW '+p['name'][:18],g,p.get('w',0)/2))
    if p.get('layer')=='hw_area': L.append(('CEM',shape(f['geometry']).boundary,0))
for t in C['tracks']:
    if t['sys']=='metro': L.append(('M '+t.get('line','')[:8],LineString(t['c']),0))
    elif t['sys']=='rer' and t.get('line')!='B': L.append(('R '+t.get('line',''),LineString(t['c']),0))
for f in BJ['features']:
    p=f['properties']
    if p.get('layer')=='street' and f['geometry']['type']=='LineString':
        L.append(('S '+(p.get('name') or '')[:14],shape(f['geometry']),p.get('width_m',12)/2))
for s in [float(v) for v in sys.argv[1:]]:
    p=np.array(ref.interpolate(s).coords[0]); q=np.array(ref.interpolate(min(s+5,ref.length)).coords[0]); 
    if s+5>ref.length: q=p; p=np.array(ref.interpolate(s-5).coords[0])
    u=(q-p)/np.linalg.norm(q-p); nrm=np.array([-u[1],u[0]])   # + = left (west/north)
    p=np.array(ref.interpolate(s).coords[0])
    cut=LineString([p-nrm*250,p+nrm*250]); row=[]
    for nm,g,hw in L:
        X=g.intersection(cut)
        if X.is_empty: continue
        for pt in getattr(X,'geoms',[X]):
            if pt.geom_type=='Point':
                o=float((np.array(pt.coords[0])-p)@nrm); row.append((round(o),nm+(f' ±{hw:.0f}' if hw else '')))
    print(int(s),[round(v) for v in p],sorted(row))
