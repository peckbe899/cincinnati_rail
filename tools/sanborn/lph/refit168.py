try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben 2026-10-19: Reading Road and Deer Creek Road do not line up across sheets 166/167/168. Sheet 168's frame had control only along
# Elsinore (all three crossings in one line), so its top swung about 35 m west of sheet 167. Refit 168 alone (affine), others fixed:
# Elsinore crossings (Reading: fixed 159/160; Gilbert: OSM corner), the 167/168 match line A-B (four crossings read on both sheets),
# and Gilbert's centre near the top of 168 onto the OSM line (Gilbert unchanged along Eden Park).
import json, numpy as np
from shapely.geometry import shape, Point
from shapely.ops import unary_union, nearest_points
SP=_ws.DATA
T=json.load(open(SP+'lph/tf_all_ma.json'))
def ap(fr,x,y): a,b,c,d,e,f=T[fr]; return np.array([a*x+b*y+e, c*x+d*y+f])
J=json.load(open(SP+'lph/osm_east.geojson'))
def osm(n): return unary_union([shape(f['geometry']) for f in J['features'] if f['properties'].get('name')==n])
GIL=osm('Gilbert Avenue'); ELS=unary_union([osm('Elsinore Place'),osm('Elsinore Avenue')])
gx=GIL.intersection(ELS); gx=gx if gx.geom_type=='Point' else list(gx.geoms)[0]
obs=[]  # (x, y, E, N, w)
rdels=(ap('159',2493,2870)+ap('160',1499,878))/2
obs.append((391,4485,*rdels,1.0))
obs.append((2752,3926,gx.x,gx.y,1.0))
for (x7,y7),(x8,y8) in [((871.5,3814),(1441,934)),((1369,3814),(1929,840)),((1602.5,3814),(2146,796.5)),((2475,3814),(3016,617.5))]:
    obs.append((x8,y8,*ap('167',x7,y7),1.0))
P=np.array(T['168'],float)
gtop=(3188,631)
for it in range(10):
    e,n=P[0]*gtop[0]+P[1]*gtop[1]+P[4], P[2]*gtop[0]+P[3]*gtop[1]+P[5]
    q=nearest_points(GIL,Point(e,n))[0]
    O=obs+[(gtop[0],gtop[1],q.x,q.y,0.7)]
    A=[];b=[];W=[]
    for x,y,E,N,w in O:
        A.append([x,y,0,0,1,0]); b.append(E); W.append(w)
        A.append([0,0,x,y,0,1]); b.append(N); W.append(w)
    A=np.array(A);b=np.array(b);W=np.array(W)
    P=np.linalg.lstsq(A*W[:,None],b*W,rcond=None)[0]
for x,y,E,N,w in O:
    r=np.hypot(P[0]*x+P[1]*y+P[4]-E,P[2]*x+P[3]*y+P[5]-N); print('resid',x,y,round(r,2))
sx=np.hypot(P[0],P[2]); sy=np.hypot(P[1],P[3]); print('scales',sx,sy,'rot',np.degrees(np.arctan2(P[2],P[0])),np.degrees(np.arctan2(-P[1],-P[3])))
print('old',T['168']); print('new',list(P))
json.dump(list(map(float,P)),open(SP+'lph/tf168_refit.json','w'))
# similarity variant (one scale, one rotation): E = a x + c y + tx, N = c x - a y + ty
def simfit(O):
    A=[];b=[];W=[]
    for x,y,E,N,w in O:
        A.append([x,y,1,0]); b.append(E); W.append(w); A.append([-y,x,0,1]); b.append(N); W.append(w)
    A=np.array(A);b=np.array(b);W=np.array(W); return np.linalg.lstsq(A*W[:,None],b*W,rcond=None)[0]
S=simfit(O)
for x,y,E,N,w in O:
    r=np.hypot(S[0]*x+S[1]*y+S[2]-E,S[1]*x-S[0]*y+S[3]-N); print('sim resid',x,y,round(r,2))
print('sim scale',np.hypot(S[0],S[1]),'rot',np.degrees(np.arctan2(S[1],S[0])))
# leave-one-group-out: Elsinore only vs match only
for nm,sel in (('match+gil',[2,3,4,5,6]),('els+gil',[0,1,6])):
    Ss=simfit([O[i] for i in sel]); print(nm,'scale',round(np.hypot(*Ss[:2]),5),'rot',round(np.degrees(np.arctan2(Ss[1],Ss[0])),2),[round(np.hypot(Ss[0]*x+Ss[1]*y+Ss[2]-E,Ss[1]*x-Ss[0]*y+Ss[3]-N),1) for x,y,E,N,w in O])
