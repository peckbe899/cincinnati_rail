try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np, collections
from shapely.geometry import LineString, Point
SP=_ws.DATA
C=json.load(open(sys.argv[1] if len(sys.argv)>1 else SP+'deckpage/context.json'))
def lines_of(m, sysn): return [m['name']] if sysn=='metro' else ['RER '+l for l in m.get('lines',[])]
G=collections.defaultdict(list); SYS={}
for sysn in ('metro','rer'):
    for m in C[sysn]:
        c=m['c'] if isinstance(m['c'][0][0],(int,float)) else m['c'][0]
        for ln in lines_of(m,sysn): G[ln].append((m['id'],LineString(c))); SYS[ln]=sysn
ST=[(s['name'],'RER '+' '.join(s['lines']),Point(s['p'])) for s in C['rer_stations']]+[(s['name'],s['line'],Point(s['p'])) for s in C['stations']]
ut=C['meta'].get('ut_box',{}); print('ut_box keys', list(ut.keys())[:8])
seen=set(); rows=[]
for ln,ps in G.items():
    for pid,g in ps:
        for e in (0,-1):
            q=Point(g.coords[e]); others=[(o.distance(q),oid,o) for oid,o in ps if oid!=pid]
            if not others: continue
            d,oid,o=min(others,key=lambda r:r[0])
            if not (1.0<d<600): continue
            key=tuple(sorted((pid,oid)))+(ln,)
            if key in seen: continue
            seen.add(key)
            p2=o.interpolate(o.project(q)); mid=Point((q.x+p2.x)/2,(q.y+p2.y)/2)
            near=min(ST,key=lambda s:s[2].distance(mid)); 
            x,y=q.coords[0]
            edge = any(abs(x-v)<15 for v in (716800,710300,710747)) or any(abs(y-v)<15 for v in (4329650,4339800))
            rows.append((ln,round(d,1),pid,oid,[round(x),round(y)],near[0],near[1],round(near[2].distance(mid)),edge))
for r in sorted(rows,key=lambda r:(r[0],r[1])): print(r)
print(len(rows),'gaps')
