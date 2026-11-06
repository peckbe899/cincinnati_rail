try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, math, numpy as np
from shapely.geometry import LineString, Point
SP=_ws.DATA
A=np.array
T=json.load(open(SP+'deckpage/tracks_v90.json')); C=json.load(open(SP+'deckpage/context.json'))
G_=json.load(open(SP+'rer1023/geom.json'))
def chain(c): return np.r_[0, np.cumsum(np.hypot(*np.diff(c, axis=0).T))]
def resample(L, step=2.0):
    n=int(L.length//step); return A([L.interpolate(i*L.length/n).coords[0] for i in range(n+1)])
F={f['properties'].get('name'):LineString(f['geometry']['coordinates']) for f in T['features'] if f['geometry']['type']=='LineString'}
W1,W2=F['Lower-level pair W, track 1, on the viaduct'],F['Lower-level pair W, track 2, on the viaduct']
Dl=LineString([r for r in C['rer'] if r['id']=='R-D-710306-4337028'][0]['c'])
A5,A6=F['APEx north approach 5 of 6'],F['APEx north approach 6 of 6']
def mid(L1,L2,step=2.0):
    c=resample(L1,step); return A([(p+A(L2.interpolate(L2.project(Point(p))).coords[0]))/2 for p in c])
Wc=mid(W1,W2)
# deck centre along D, from D s 900 to the east end of the arm
dD=resample(Dl,2.0); sD=chain(dD)
def near(L,p): return A(L.interpolate(L.project(Point(p))).coords[0])
deck=A([(2*p+near(A5,p)+near(A6,p))/4 for p in dD])
def normals(c):
    t=np.gradient(c,axis=0); t/=np.hypot(*t.T)[:,None]; return np.c_[-t[:,1],t[:,0]]   # left normal
def smooth(c,k=5):
    c=c.copy()
    for _ in range(k): c[1:-1]=(c[:-2]+2*c[1:-1]+c[2:])/4
    return c
trunk=A(G_['trunk']); ts=chain(trunk)
from shapely.ops import unary_union
Cv=json.load(open(SP+'deckpage/context_v90.json'))
def exist_union(extra_trunk=None):
    gs=[LineString(f['geometry']['coordinates']) for f in T['features'] if f['geometry']['type']=='LineString' and not f['properties'].get('name','').startswith('R5')]
    gs+=[LineString(t['c']) for t in C['tracks'] if t['sys'] in ('rer','metro')]
    return unary_union([g.buffer(4.2) for g in gs]).buffer(3).buffer(-3)
def tangent_arc(line_pts, curve_pts, R, side_line, side_curve):
    """circle radius R tangent to polyline line_pts (centre on side_line of it: +1 left) and to dense curve curve_pts at J (centre on side_curve of curve's direction).
    returns list of (iJ, O, K) solutions"""
    L=LineString(line_pts); nC=normals(curve_pts)*side_curve
    O=curve_pts+nC*R
    f=[]
    for o in O:
        q=near(L,o); s=L.project(Point(o)); t=A(L.interpolate(min(s+1,L.length)).coords[0])-A(L.interpolate(max(s-1,0)).coords[0]); nl=np.array([-t[1],t[0]])/np.hypot(*t)
        f.append(np.dot(o-q,nl)*side_line - R)
    f=A(f); out=[]
    for i in range(len(f)-1):
        if f[i]==0 or f[i]*f[i+1]<0:
            w=f[i]/(f[i]-f[i+1]); o=O[i]*(1-w)+O[i+1]*w; out.append((i+w, o, near(L,o)))
    return out
def arc_pts(O,P0,P1,R,turn,step=2.0):
    a0=math.atan2(*(P0-O)[::-1]); a1=math.atan2(*(P1-O)[::-1])
    if turn>0:   # ccw (left turn)
        while a1<a0: a1+=2*math.pi
    else:
        while a1>a0: a1-=2*math.pi
    n=max(2,int(abs(a1-a0)*R/step)); a=np.linspace(a0,a1,n+1); return O+R*np.c_[np.cos(a),np.sin(a)]
