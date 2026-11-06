try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# every Metro / RER piece end that does not meet another piece of the same line, and how far the nearest piece of that line is
import json, sys, numpy as np, collections
from shapely.geometry import LineString, Point
SP=_ws.DATA
C=json.load(open(sys.argv[1] if len(sys.argv)>1 else SP+'deckpage/context.json'))
def lines_of(m, sysn): return [m['name']] if sysn=='metro' else ['RER '+l for l in m.get('lines',[])]
G=collections.defaultdict(list)
for sysn in ('metro','rer'):
    for m in C[sysn]:
        c=m['c'] if isinstance(m['c'][0][0],(int,float)) else m['c'][0]
        for ln in lines_of(m,sysn): G[ln].append((m['id'],LineString(c)))
gaps=[]
for ln,ps in G.items():
    for pid,g in ps:
        for e in (0,-1):
            q=Point(g.coords[e]); others=[(o.distance(q),oid) for oid,o in ps if oid!=pid]
            selfd=min([LineString(g.coords[1:]).distance(q) if e==0 else LineString(g.coords[:-1]).distance(q)]) if len(g.coords)>2 else 1e9
            if not others: continue
            d,oid=min(others)
            if d>1.0 and d<600: gaps.append((ln,pid,'start' if e==0 else 'end',round(d,1),oid,[round(v) for v in q.coords[0]]))
for g in sorted(gaps): print(g)
print(len(gaps),'loose ends within 600 m of another piece of the same line')
