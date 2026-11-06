try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ludlow trunk inside the Mill Creek / OH-75 band: maximise the minimum radius (LP), then make curvature piecewise linear (spirals + arcs)
import sys, numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix, csr_matrix, hstack, vstack, identity
SP=_ws.DATA
sys.path.insert(0,_ws.CODE+'nv'); import geom27 as G
_Sa,_ia=np.unique(G._S[::-1],return_index=True); _Pa=G._P[::-1][_ia]
def ref(s): return np.array([np.interp(s,_Sa,_Pa[:,0]),np.interp(s,_Sa,_Pa[:,1])]) if s<4950 else np.array(G.C.interpolate(s).coords[0])
h=5.0; S0,S1=4650.0,7650.0; ss=np.arange(S0,S1+0.1,h); n=len(ss)
P0=np.array([ref(s) for s in ss]); t=np.gradient(P0,axis=0); t/=np.hypot(t[:,0],t[:,1])[:,None]
for _ in range(6): t[1:-1]=(t[:-2]+2*t[1:-1]+t[2:])/4
t/=np.hypot(t[:,0],t[:,1])[:,None]; E=np.c_[t[:,1],-t[:,0]]
Bd=np.load(SP+'trunk2/band_open.npy'); M=1.5
lo=np.interp(ss,Bd[:,0],Bd[:,1])+M; hi=np.interp(ss,Bd[:,0],Bd[:,2])-M
out=ss<4950; lo[out]=-1.0; hi[out]=1.0
br=ss>=7200; lo[br]=np.maximum(lo[br],-1.0); hi[br]=np.minimum(hi[br],1.0)
bg=(ss>=7265)&(ss<=7400); lo[bg]=-1.0; hi[bg]=1.0     # the existing Mill Creek bridge
fix=(ss<=4700)|(ss>=7600); lo[fix]=0; hi[fix]=0
def kap(o):
    P=P0+E*o[:,None]; a,b,c=P[:-2],P[1:-1],P[2:]
    cr=(b-a)[:,0]*(c-b)[:,1]-(b-a)[:,1]*(c-b)[:,0]
    return 2*cr/(np.hypot(*(b-a).T)*np.hypot(*(c-b).T)*np.hypot(*(c-a).T))
def jac(o,eps=1e-3):
    k0=kap(o); J=lil_matrix((n-2,n))
    for j in range(n):
        d=np.zeros(n); d[j]=eps; dk=(kap(o+d)-k0)/eps
        for i in range(max(0,j-2),min(n-2,j+1)):
            if dk[i]!=0: J[i,j]=dk[i]
    return k0, csr_matrix(J)
L12=np.load(SP+'trunk2/lud12.npy'); o=np.zeros(n)
for i,sv in enumerate(ss):
    if 4950<=sv<=7300: q=np.array([np.interp(sv,L12[:,0],L12[:,1]),np.interp(sv,L12[:,0],L12[:,2])]); o[i]=(q-P0[i])@E[i]
from scipy.ndimage import gaussian_filter1d
o=gaussian_filter1d(o,4); o=np.clip(o,lo,hi)
W_=(ss[1:-1]>=4720)&(ss[1:-1]<=7450)   # radius objective only where the line is free (the KMZ polyline beyond is coarse)
for stage in (1,2):
    for it in range(22 if stage==1 else 10):
        TRU=[3,3,2,2,2,1.5,1.5,1,1,1,1,1,1,1,.7,.7,.5,.5,.4,.3,.2,.2][it] if stage==1 else 1.0
        k0,J=jac(o); m=n-2
        b_lo=np.maximum(lo-o,-TRU); b_hi=np.minimum(hi-o,TRU)
        if stage==1:      # vars: d (n), t
            c=np.r_[np.zeros(n),1.0]
            Jw=J[W_]; A=vstack([hstack([Jw,-np.ones((W_.sum(),1))]),hstack([-Jw,-np.ones((W_.sum(),1))])]); b=np.r_[-k0[W_],k0[W_]]
            res=linprog(c,A_ub=A,b_ub=b,bounds=list(zip(b_lo,b_hi))+[(0,None)],method='highs')
            o=o+res.x[:n]; print('stage1 it',it,'min R %.1f'%(1/np.abs(kap(o)[W_]).max()))
        else:             # vars: d (n), u (m-2) for |second difference of curvature|
            D=lil_matrix((m-2,m))
            for i in range(m-2): D[i,i]=1; D[i,i+1]=-2; D[i,i+2]=1
            D=csr_matrix(D); DJ=D@J; dk0=D@k0; q=m-2
            c=np.r_[np.zeros(n),np.ones(q)]
            Jw=J[W_]; mw=W_.sum()
            A=vstack([hstack([DJ,-identity(q)]),hstack([-DJ,-identity(q)]),hstack([Jw,csr_matrix((mw,q))]),hstack([-Jw,csr_matrix((mw,q))])])
            b=np.r_[-dk0,dk0,KM-k0[W_],KM+k0[W_]]
            res=linprog(c,A_ub=A,b_ub=b,bounds=list(zip(b_lo,b_hi))+[(0,None)]*q,method='highs')
            if res.x is None: print('infeasible'); break
            o=o+res.x[:n]; k=kap(o); print('stage2 it',it,'min R %.1f  sum|d2k| %.3e'%(1/np.abs(k[W_]).max(),np.abs(np.diff(k,2)).sum()))
    if stage==1: KM=np.abs(kap(o)[W_]).max()*1.03
# stage 3: least land take (smallest shift off the existing line) at the same radius and nearly the same smoothness
k=kap(o); m=n-2; S2=np.abs(np.diff(k,2)).sum()*1.15
D=lil_matrix((m-2,m))
for i in range(m-2): D[i,i]=1; D[i,i+1]=-2; D[i,i+2]=1
D=csr_matrix(D)
for it in range(30):
    k0,J=jac(o); DJ=D@J; dk0=D@k0; q=m-2; Jw=J[W_]; mw=W_.sum()
    TR3=3.0 if it<20 else 1.0; b_lo=np.maximum(lo-o,-TR3); b_hi=np.minimum(hi-o,TR3)
    # vars d(n), u(n) >= |o+d|, v(q) >= |d2k|
    c=np.r_[np.zeros(n),np.ones(n),np.zeros(q)]
    Z=lambda r,cc: csr_matrix((r,cc))
    A=vstack([hstack([identity(n),-identity(n),Z(n,q)]),hstack([-identity(n),-identity(n),Z(n,q)]),
              hstack([DJ,Z(q,n),-identity(q)]),hstack([-DJ,Z(q,n),-identity(q)]),
              hstack([Z(1,n),Z(1,n),csr_matrix(np.ones((1,q)))]),
              hstack([Jw,Z(mw,n),Z(mw,q)]),hstack([-Jw,Z(mw,n),Z(mw,q)])])
    b=np.r_[-o,o,-dk0,dk0,S2,KM-k0[W_],KM+k0[W_]]
    res=linprog(c,A_ub=A,b_ub=b,bounds=list(zip(b_lo,b_hi))+[(0,None)]*(n+q),method='highs')
    if res.x is None: print('stage3 infeasible'); break
    o=o+res.x[:n]; k=kap(o); print('stage3 it',it,'min R %.1f  sum|o| %.0f  max|o| %.1f'%(1/np.abs(k[W_]).max(),np.abs(o).sum()*h,np.abs(o).max()))
k=kap(o)
j=np.argmax(np.abs(k)*W_); print('binding: min R %.0f at s %.0f'%(1/abs(k[j]),ss[j+1]))
for s,oo,a,bb,kk in zip(ss[1:-1][::20],o[1:-1][::20],lo[1:-1][::20],hi[1:-1][::20],k[::20]): print(int(s),'o %.1f band %.1f..%.1f R %.0f'%(oo,a,bb,1/max(abs(kk),1e-9)))
np.save(SP+'trunk2/lud17.npy',np.c_[ss,P0+E*o[:,None],o])
