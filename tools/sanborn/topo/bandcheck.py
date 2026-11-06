import numpy as np, sys
from seamfeat import Joint
from icp import basis
from geo import S
def corr_fn(J):
    def f(sid,d):
        k=J.ids.index(sid); fx,fy=J.Fat(d['g'].astype(float)); Jm=d['J']
        du=Jm[0,0]*fx+Jm[0,1]*fy; dv=Jm[1,0]*fx+Jm[1,1]*fy
        if J.nSh:
            s=J.sol[J.nF+k*J.nSh:J.nF+(k+1)*J.nSh]; P=basis(d['px']/d['W'],d['py']/d['H'],J.DEG)[:,~J.lo]; du=du+P@s[:J.NS]; dv=dv+P@s[J.NS:]
        return du,dv
    return f
def band_shift(d,ind,nrm,qx,qy,sel,iters=15,tuk=12.0):
    H,W=int(d['H']),int(d['W']); t=np.zeros(2); qx=qx[sel]; qy=qy[sel]
    for _ in range(iters):
        x=qx+t[0]; y=qy+t[1]; qi=np.clip(np.round(y).astype(int),0,H-1); qj=np.clip(np.round(x).astype(int),0,W-1)
        lin=qi*W+qj; cy=ind[0][lin].astype(float); cx=ind[1][lin].astype(float); l2=(cy*W+cx).astype(np.int64)
        nx=nrm[0][l2].astype(float); ny=nrm[1][l2].astype(float); e=nx*(cx-x)+ny*(cy-y)
        w=np.where(np.abs(e)<tuk,(1-(e/tuk)**2)**2,0)
        A=np.c_[nx,ny]; M=(A*w[:,None]).T@A+np.eye(2)*1e-3*w.sum(); dt=np.linalg.solve(M,(A*w[:,None]).T@e); t=t+dt
        if np.abs(dt).max()<0.02: break
    return t*2  # full px
models={'coons':None}
for f in sys.argv[1:]: models[f]=corr_fn(Joint(f))
ids=sorted(k for k in S if not k.startswith('_'))
out={m:[] for m in models}
for sid in ids:
    d=dict(np.load(f'cache/{sid}_pts.npz'))
    if len(d['px'])<30000: continue
    ind=np.load(f'cache/{sid}_ind.npy',mmap_mode='r').reshape(2,-1); nrm=np.load(f'cache/{sid}_nrm.npy',mmap_mode='r').reshape(2,-1)
    a=d['px']/d['W']; b=d['py']/d['H']
    bands={'W':a<0.15,'E':a>0.85,'N':b<0.15,'S':b>0.85}
    for m,f in models.items():
        du,dv=(0*a,0*b) if f is None else f(sid,d)
        for bn,sel in bands.items():
            if sel.sum()<4000: continue
            t=band_shift(d,ind,nrm,d['px']+du,d['py']+dv,sel); out[m].append(np.hypot(*t))
for m in models: v=np.array(out[m]); print(f'{m:24s} bands {len(v)}  median |residual shift| {np.median(v):.1f} px  mean {v.mean():.1f}  p90 {np.percentile(v,90):.1f}')
