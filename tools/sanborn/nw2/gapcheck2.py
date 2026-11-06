try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, math, collections
from shapely.geometry import LineString, Point
SP=_ws.DATA
C=json.load(open(sys.argv[1] if len(sys.argv)>1 else SP+'deckpage/context.json'))
import os; E=json.load(open(os.environ.get('LAYOUT',SP+'dblive/deck/layout.json')))['transit']
def qpt(a,k,b,t):
    u=1-t; return [u*u*a[0]+2*u*t*k[0]+t*t*b[0], u*u*a[1]+2*u*t*k[1]+t*t*b[1]]
def render(v,K):
    if not K: return v
    out=[v[0]]
    for i in range(len(v)-1):
        a,b,k=v[i],v[i+1],K.get(str(i))
        if k:
            n=max(6,min(48,math.ceil(math.hypot(b[0]-a[0],b[1]-a[1])/3)))
            out+= [qpt(a,k,b,j/n) for j in range(1,n+1)]
        else: out.append(b)
    return out
def geom(m):
    e=E.get(m['id'])
    if e: return render(e['c'], e.get('k') or None), True
    return render(m['c'], m.get('k')), False
G=collections.defaultdict(list)
for sysn in ('metro','rer'):
    for m in C[sysn]:
        g,ed=geom(m)
        lns=[m['name']] if sysn=='metro' else ['RER '+l for l in m.get('lines',[])]
        for ln in lns: G[ln].append((m['id'],LineString(g),ed))
ST=[(s['name'],Point(s['p'])) for s in C['rer_stations']+C['stations']]
rows=[];seen=set()
for ln,ps in G.items():
    for pid,g,ed in ps:
        for e in (0,-1):
            q=Point(g.coords[e]); others=[(o.distance(q),oid,o,oed) for oid,o,oed in ps if oid!=pid]
            if not others: continue
            d,oid,o,oed=min(others,key=lambda r:r[0])
            if not (0.5<d<600): continue
            key=tuple(sorted((pid,oid)))+(ln,)
            if key in seen: continue
            seen.add(key)
            near=min(ST,key=lambda s:s[1].distance(q))
            rows.append((ln,round(d,1),pid,'end' if e else 'start',oid,'ED' if ed or oed else '',near[0],round(near[1].distance(q))))
for r in sorted(rows,key=lambda r:(r[0],r[1])): print(r)
print(len(rows),'gaps')
