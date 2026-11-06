try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben 2026-10-19: after the sheet 168 refit, sheet 159's Reading Road at its north-east corner (far from 159's own control) sits
# 8 m off 168's, which now has control at both ends. Bend 159 locally with a thin-plate spline: its two Reading line points move onto
# 168's Reading centreline; 159's picked crossings (Highland, Reading/Elsinore) and a 60 m grid over the rest of the page (more than
# 120 m from the moved points) stay where the fit put them. Frame '159' in lph/tps.pkl, no taper.
import json, pickle, sys, numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points
from scipy.spatial import cKDTree
SP=_ws.DATA
sys.path.insert(0,_ws.CODE+'lph'); import tps
M=pickle.load(open(SP+'lph/tps.pkl','rb')); M.pop('159',None)
T=json.load(open(SP+'lph/tf_all_ma.json'))
def aff(fr,x,y): a,b,c,d,e,f=T[fr]; return np.array([a*x+b*y+e, c*x+d*y+f])
def ap(fr,x,y):
    p=aff(fr,x,y); dE,dN=tps.disp(fr,np.array([p[0]]),np.array([p[1]]),M); return p+[dE[0],dN[0]]
L=LineString([ap('168',x,y) for x,y in [(1196,1690),(1059,2269),(816,2803),(391,4485)]])
P=[];V=[]
for x,y in [(3415,923),(3168,1288)]:
    p=aff('159',x,y); q=nearest_points(L,Point(*p))[0]; P.append(p); V.append((q.x-p[0],q.y-p[1]))
mov=np.array(P)
J=json.load(open(SP+'sbg/picks/s159.json'))
Z=[aff('159',i['x'],i['y']) for i in J['intersections']]
xs,ys=np.meshgrid(np.arange(0,4126,700),np.arange(0,4764,700))
G=np.array([aff('159',x,y) for x,y in zip(xs.ravel(),ys.ravel())])
d,_=cKDTree(mov).query(G); G=G[d>120]
pts=np.r_[mov,np.array(Z),G]; vec=np.r_[np.array(V),np.zeros((len(Z)+len(G),2))]
sm=np.r_[np.full(len(mov),0.01),np.full(len(Z),0.05),np.full(len(G),0.5)]
M['159']=dict(pts=pts,vec=vec,smooth=sm,notaper=True)
pickle.dump(M,open(SP+'lph/tps.pkl','wb'))
print('moves',np.round(np.hypot(*np.array(V).T),2),'zero pts',len(Z),'anchors',len(G))
tps._RB.clear() if hasattr(tps,'_RB') else None
g=np.array([aff('159',x,y) for x,y in zip(xs.ravel(),ys.ravel())])
dE,dN=tps.disp('159',g[:,0],g[:,1],M); print('grid disp max',round(float(np.hypot(dE,dN).max()),2))
dE,dN=tps.disp('159',mov[:,0],mov[:,1],M); print('at moved',np.round(np.hypot(dE-np.array(V)[:,0],dN-np.array(V)[:,1]),2))
