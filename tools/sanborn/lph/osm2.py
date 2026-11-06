try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, collections, pickle
SP=_ws.DATA
sys.path.insert(0,_ws.CODE+'sbg'); sys.path.insert(0,_ws.CODE+'sbg/fit')
from names import key
from osmx import inters, ROADS
from shapely.geometry import LineString
G=collections.defaultdict(list); seen=set()
for f in json.load(open(SP+'basin/osm_basin.geojson'))['features']+json.load(open(SP+'deck/osm_valley.geojson'))['features']:
    p=f['properties']; n=p.get('name')
    if not n or (p.get('highway') and p.get('highway') not in ROADS): continue
    if f['geometry']['type']!='LineString': continue
    c=tuple(map(tuple,f['geometry']['coordinates']))
    if c in seen: continue
    seen.add(c); G[key(n)].append(LineString(c))
O=inters(G); print(len(O))
pickle.dump(dict(O),open(SP+'lph/osm2.pkl','wb'))
print([k for k in O if 'state' in k][:30])
