try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json,sys,numpy as np
SP=_ws.DATA
sys.path.insert(0,_ws.CODE+'nv'); import geom27 as G
from shapely.geometry import Point
def pt(s):
    if s<=5420: i=int(np.argmin(np.abs(G._S-s))); return np.array(G._P[i])
    return np.array(G.C.interpolate(s).coords[0])
Bd=np.load(SP+'trunk2/band.npy'); ss=Bd[:,0]; lo=Bd[:,1]; hi=Bd[:,2]
sel=ss<=7250; ss,lo,hi=ss[sel],lo[sel],hi[sel]
P0=np.array([pt(s) for s in ss]); t=np.gradient(P0,axis=0); t/=np.hypot(t[:,0],t[:,1])[:,None]; E=np.c_[t[:,1],-t[:,0]]
M=2.0  # margin inside the band
lo2=lo+M; hi2=hi-M
# fixed ends: o=0 at both ends with zero slope (blend)
o=np.clip(np.zeros_like(ss),lo2,hi2)
def geom(o): return P0+E*o[:,None]
def curv(P):
    d1=np.gradient(P,10.0,axis=0); d2=np.gradient(d1,10.0,axis=0); return (d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0])/np.hypot(d1[:,0],d1[:,1])**3
for it in range(4000):
    P=geom(o)
    # smooth the geometry (Laplacian), measure the change as an offset change
    Q=P.copy(); Q[1:-1]=(P[:-2]+P[2:])/2*0.5+P[1:-1]*0.5
    do=np.einsum('ij,ij->i',Q-P,E); o=o+do
    o[:3]=0; o[-3:]=0
    o=np.clip(o,lo2,hi2)
P=geom(o); k=np.abs(curv(P))
R=1/np.maximum(k,1e-9)
k0=np.abs(curv(P0)); R0=1/np.maximum(k0,1e-9)
from scipy.ndimage import uniform_filter1d
Rs=1/np.maximum(uniform_filter1d(k,7),1e-9); R0s=1/np.maximum(uniform_filter1d(k0,7),1e-9)
print('min radius (70 m window) now %.0f -> smoothed %.0f'%(R0s[5:-5].min(),Rs[5:-5].min()))
for s,oo,a,b,r in zip(ss[::10],o[::10],lo[::10],hi[::10],Rs[::10]): print(int(s),'offset %.1f (band %.1f..%.1f) R %.0f'%(oo,a,b,r))
np.save(SP+'trunk2/lud8.npy',np.c_[ss,P])
