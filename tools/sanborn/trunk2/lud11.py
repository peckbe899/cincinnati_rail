try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json,sys,numpy as np
from scipy.optimize import minimize
from scipy.spatial import cKDTree
SP=_ws.DATA
sys.path.insert(0,_ws.CODE+'nv'); import geom27 as G
def pt(s):
    if s<=5420: i=int(np.argmin(np.abs(G._S-s))); return np.array(G._P[i])
    return np.array(G.C.interpolate(s).coords[0])
Bd=np.load(SP+'trunk2/band.npy'); bs=Bd[:,0]; blo=Bd[:,1]+1.0; bhi=Bd[:,2]-1.0
P0=np.array([pt(s) for s in bs]); t=np.gradient(P0,axis=0); t/=np.hypot(t[:,0],t[:,1])[:,None]; E0=np.c_[t[:,1],-t[:,0]]
KD=cKDTree(P0)
S0,S1=5050.0,7350.0
A=pt(S0); hA=np.arctan2(*(pt(S0+10)-pt(S0-10))[::-1])           # heading angle (math, from x axis)
Bp=pt(S1); hB=np.arctan2(*(pt(S1+10)-pt(S1-10))[::-1])
N=24
def curve(x):
    L=x[0]; k=x[1:]; l=np.linspace(0,L,N); ls=np.linspace(0,L,600); kk=np.interp(ls,l,k)
    h=hA+np.r_[0,np.cumsum((kk[1:]+kk[:-1])/2*np.diff(ls))]
    P=A+np.c_[np.r_[0,np.cumsum((np.cos(h[1:])+np.cos(h[:-1]))/2*np.diff(ls))],np.r_[0,np.cumsum((np.sin(h[1:])+np.sin(h[:-1]))/2*np.diff(ls))]]
    return P,h,kk
def offs(P):
    d,i=KD.query(P); o=np.einsum('ij,ij->i',P-P0[i],E0[i]); return o,i
def endc(x):
    P,h,_=curve(x); return np.r_[P[-1]-Bp, [np.sin(h[-1]-hB)]]*np.r_[1,1,100]
def band(x):
    P,_,_=curve(x); o,i=offs(P); m=(bs[i]>5100)&(bs[i]<7300); return np.r_[(o-blo[i])[m],(bhi[i]-o)[m]]
def obj(x):
    _,_,kk=curve(x); return np.sum((np.abs(kk)*1000)**10)**0.1
L0=np.hypot(*(Bp-A))*1.05
best=None
for kmax in (1/600,1/800):
    x0=np.r_[L0, np.zeros(N)]
    r=minimize(obj,x0,constraints=[{'type':'eq','fun':endc},{'type':'ineq','fun':band}],method='SLSQP',options=dict(maxiter=800,ftol=1e-10))
    P,h,kk=curve(r.x); R=1/np.max(np.abs(kk)); viol=-min(0,band(r.x).min()); ee=np.abs(endc(r.x)).max()
    print(r.success, r.message, 'L %.0f minR %.0f band viol %.2f end err %.3f'%(r.x[0],R,viol,ee))
    if best is None or (viol<0.1 and ee<0.5 and R>best[0]): best=(R,P)
np.save(SP+'trunk2/lud11.npy',best[1]); print('best R', round(best[0]))
