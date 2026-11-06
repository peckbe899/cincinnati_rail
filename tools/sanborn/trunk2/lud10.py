try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json,sys,numpy as np
from scipy.interpolate import make_interp_spline, CubicSpline
from scipy.optimize import minimize
SP=_ws.DATA
sys.path.insert(0,_ws.CODE+'nv'); import geom27 as G
def pt(s):
    if s<=5420: i=int(np.argmin(np.abs(G._S-s))); return np.array(G._P[i])
    return np.array(G.C.interpolate(s).coords[0])
Bd=np.load(SP+'trunk2/band.npy'); ss=Bd[:,0]; lo=Bd[:,1]+1.0; hi=Bd[:,2]-1.0
sel=(ss>=4950)&(ss<=7300); ss,lo,hi=ss[sel],lo[sel],hi[sel]
# reference: a smooth version of the current line (so offsets are against a smooth base)
P0=np.array([pt(s) for s in ss])
from scipy.ndimage import gaussian_filter1d
Pb=np.c_[gaussian_filter1d(P0[:,0],8,mode='nearest'),gaussian_filter1d(P0[:,1],8,mode='nearest')]
# offsets of Pb relative to P0 frame, so band applies: band is relative to P0 normals
t=np.gradient(P0,axis=0); t/=np.hypot(t[:,0],t[:,1])[:,None]; E=np.c_[t[:,1],-t[:,0]]
knots=np.arange(4950,7301,75.0)
def line(x):
    y=np.r_[0.0,0.0,x,0.0,0.0]; kk=np.r_[knots[0]-150,knots[0]-75,knots,knots[-1]+75,knots[-1]+150]
    cs=CubicSpline(kk,y); o=cs(ss); return P0+E*o[:,None], o
def kappa(P):
    d1=np.gradient(P,10.0,axis=0); d2=np.gradient(d1,10.0,axis=0); return (d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0])/np.hypot(d1[:,0],d1[:,1])**3
def obj(x):
    P,o=line(x); k=kappa(P); return np.sum((np.abs(k)*1000)**8)**(1/8)
cons=[{'type':'ineq','fun':lambda x: line(x)[1]-lo},{'type':'ineq','fun':lambda x: hi-line(x)[1]}]
x0=np.zeros(len(knots))
# start from a feasible point: clip the band middle
o0=np.clip(np.zeros_like(ss),lo,hi); x0=np.interp(knots,ss,o0)
r=minimize(obj,x0,constraints=cons,method='SLSQP',options=dict(maxiter=500,ftol=1e-9))
P,o=line(r.x); k=np.abs(kappa(P)); R=1/np.maximum(k,1e-12)
P0k=np.abs(kappa(P0))
print(r.success, r.message, 'min R new %.0f (current %.0f)'%(R[3:-3].min(), (1/np.maximum(P0k,1e-12))[3:-3].min()))
viol=np.max(np.r_[lo-o,o-hi]); print('max band violation',round(viol,2))
for s,oo,rr in zip(ss[::10],o[::10],R[::10]): print(int(s),round(oo,1),round(rr))
np.save(SP+'trunk2/lud10.npy',np.c_[ss,P])
