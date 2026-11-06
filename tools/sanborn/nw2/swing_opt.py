try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, numpy as np, itertools
from scipy.interpolate import splprep, splev
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import substring
SP=_ws.DATA
F=json.load(open(SP+'norwood/frame.json')); O=np.array(F['o']); t=np.array(F['t']); n=np.array(F['n'])
def P(s,o): return O+t*(s-4300)+n*o
def so(p): d=np.asarray(p)-O; return float(d@t)+4300, float(d@n)
C=json.load(open(SP+'deckpage/context.json'))
cc=lambda pid: next(m for m in C['rer'] if m['id']==pid)['c']
Aline=LineString(cc('R-A-718498-4336199')+cc('R-A-720547-4337903')[::-1]) if False else LineString(list(LineString(cc('R-A-718498-4336199')).coords)+list(LineString(cc('R-A-720547-4337903')).coords))
m=Aline.project(Point(P(5057,0))); box=substring(Aline,m-102.1,m+102.1).buffer(12,cap_style=2)
tail=[(5186.3,250.9),(5191.5,266.0),(5221.2,355.5),(5233.3,390.9)]
best=None
for s1,o1,s2,o2,s3,o3 in itertools.product((5040,5060,5080),(30,32.5,36),(5110,5125,5140),(45,52,60),(5160,5168,5176),(85,100,115)):
    wp=np.array([(4900,28.66),(4950,28.66),(4990,28.7),(s1,o1),(s2,o2),(s3,o3)]+tail)
    if np.any(np.diff(wp[:,0])<=0): continue
    try: tck,_=splprep([wp[:,0],wp[:,1]],s=0,k=3)
    except Exception: continue
    uu=np.linspace(0,1,900); x,y=splev(uu,tck)
    if np.any(np.diff(x)<-0.05): continue
    d1=np.array(splev(uu,tck,der=1)); d2=np.array(splev(uu,tck,der=2)); k=np.abs(d1[0]*d2[1]-d1[1]*d2[0])/np.power(d1[0]**2+d1[1]**2,1.5)
    r=1/k[5:-5].max()
    g=LineString([P(a,b) for a,b in zip(x,y)]); seg=[P(a,b) for a,b in zip(x,y) if b>70]
    clear=LineString(seg).distance(box) if len(seg)>1 else 0
    if clear<9: continue                                   # pair (up to 6.75 m half) plus 2 m clear of the box
    if best is None or r>best[0]: best=(r,(s1,o1),(s2,o2),(s3,o3),round(clear,1))
print(best)
