try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json,sys,numpy as np
from scipy.ndimage import gaussian_filter1d, uniform_filter1d
SP=_ws.DATA
sys.path.insert(0,_ws.CODE+'nv'); import geom27 as G
def pt(s):
    if s<=5420: i=int(np.argmin(np.abs(G._S-s))); return np.array(G._P[i])
    return np.array(G.C.interpolate(s).coords[0])
Bd=np.load(SP+'trunk2/band.npy'); ss=Bd[:,0]; lo=Bd[:,1]+1.5; hi=Bd[:,2]-1.5
sel=(ss>=4950)&(ss<=7300); ss,lo,hi=ss[sel],lo[sel],hi[sel]
P0=np.array([pt(s) for s in ss]); t=np.gradient(P0,axis=0); t/=np.hypot(t[:,0],t[:,1])[:,None]; E=np.c_[t[:,1],-t[:,0]]
lo[ss>7200]=np.maximum(lo[ss>7200],-1); hi[ss>7200]=np.minimum(hi[ss>7200],1)   # back on the line at the creek bridge
lo[ss<5000]=-0.5; hi[ss<5000]=0.5
o=np.clip(np.zeros_like(ss),lo,hi)
def kap(P):
    d1=np.gradient(P,10.0,axis=0); d2=np.gradient(d1,10.0,axis=0); return (d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0])/np.hypot(d1[:,0],d1[:,1])**3
for it in range(int(sys.argv[1]) if len(sys.argv)>1 else 30000):
    P=P0+E*o[:,None]
    L4=np.zeros_like(P); L4[2:-2]=P[:-4]-4*P[1:-3]+6*P[2:-2]-4*P[3:-1]+P[4:]
    do=-0.05*np.einsum('ij,ij->i',L4,E); o=np.clip(o+do,lo,hi); o[:2]=0; o[-2:]=0
P=P0+E*o[:,None]; k=uniform_filter1d(np.abs(kap(P)),5); R=1/np.maximum(k,1e-12)
k0=uniform_filter1d(np.abs(kap(P0)),5); R0=1/np.maximum(k0,1e-12)
j=4+np.argmin(R[4:-4]); print('min R (50 m window) current %.0f, new %.0f at s %.0f'%(R0[4:-4].min(),R[4:-4].min(),ss[j]))
for s,oo,a,b,r in zip(ss[::10],o[::10],lo[::10],hi[::10],R[::10]): print(int(s),'o %.1f band %.1f..%.1f R %.0f'%(oo,a,b,r))
np.save(SP+'trunk2/lud12.npy',np.c_[ss,P])
