"""Joint fit: continuous regional field F(grid) (bilinear on a node lattice, ft) + per-sheet cubic shape terms
(zero normal component at the neatline), point-to-line ICP against LiDAR 25-ft lines."""
import numpy as np, json, sys, time
import scipy.sparse as sp
from icp import basis
from geo import S
ids=sorted(k for k in S if not k.startswith('_'))
SP=float(sys.argv[1]) if len(sys.argv)>1 else 4000.0
L2=float(sys.argv[2]) if len(sys.argv)>2 else 100.0
SHAPE=int(sys.argv[3]) if len(sys.argv)>3 else 1
X0,X1,Y0,Y1=-56000,52000,-32000,44000
nx=int(np.ceil((X1-X0)/SP))+1; ny=int(np.ceil((Y1-Y0)/SP))+1; NN=nx*ny
DEG=3; lo=np.array([i+j<=1 for i in range(DEG+1) for j in range(DEG+1-i)]); NS=int((~lo).sum())
nF=2*NN; nSh=2*NS if SHAPE else 0; N=nF+nSh*len(ids)
def bil(g):
    fx=(g[:,0]-X0)/SP; fy=(g[:,1]-Y0)/SP; i=np.clip(np.floor(fx).astype(int),0,nx-2); j=np.clip(np.floor(fy).astype(int),0,ny-2)
    tx=fx-i; ty=fy-j
    cols=np.stack([j*nx+i,j*nx+i+1,(j+1)*nx+i,(j+1)*nx+i+1],1)
    w=np.stack([(1-tx)*(1-ty),tx*(1-ty),(1-tx)*ty,tx*ty],1)
    return cols,w
D={}
for k,sid in enumerate(ids):
    P=np.load(f'cache/{sid}_pts.npz')
    d={kk:P[kk] for kk in P.files}
    d['ind']=np.load(f'cache/{sid}_ind.npy',mmap_mode='r'); d['nrm']=np.load(f'cache/{sid}_nrm.npy',mmap_mode='r')
    d['cols'],d['bw']=bil(d['g'].astype(np.float64))
    d['Phi']=basis(d['px']/d['W'],d['py']/d['H'],DEG)[:,~lo]
    Pe=basis(d['ex']/d['W'],d['ey']/d['H'],DEG)[:,~lo]; d['Ae']=np.hstack([d['enx'][:,None]*Pe,d['eny'][:,None]*Pe])
    d['off']=nF+k*nSh; D[sid]=d
# regulariser on F: second differences in x and y for each component, small first difference + ridge
rows=[]; 
def idx(i,j): return j*nx+i
R=[]
for c in range(2):
    for j in range(ny):
        for i in range(1,nx-1): R.append(([c*NN+idx(i-1,j),c*NN+idx(i,j),c*NN+idx(i+1,j)],[1,-2,1]))
    for j in range(1,ny-1):
        for i in range(nx): R.append(([c*NN+idx(i,j-1),c*NN+idx(i,j),c*NN+idx(i,j+1)],[1,-2,1]))
ri=[];rj=[];rv=[]
for r,(cc,vv) in enumerate(R):
    ri+= [r]*len(cc); rj+=cc; rv+=vv
Rg=sp.csr_matrix((rv,(ri,rj)),shape=(len(R),N))
REG=L2*(Rg.T@Rg)+sp.diags(np.r_[np.full(nF,1e-3),np.full(N-nF,1.0)])
sol=np.zeros(N); TUK=12.0
def corr(d,sol):
    F=sol[:nF].reshape(2,NN)
    fx=(F[0][d['cols']]*d['bw']).sum(1); fy=(F[1][d['cols']]*d['bw']).sum(1)
    J=d['J']; du=J[0,0]*fx+J[0,1]*fy; dv=J[1,0]*fx+J[1,1]*fy
    if SHAPE:
        s=sol[d['off']:d['off']+nSh]; du=du+d['Phi']@s[:NS]; dv=dv+d['Phi']@s[NS:]
    return du,dv
for it in range(int(sys.argv[4]) if len(sys.argv)>4 else 15):
    t0=time.time(); AtA=sp.csr_matrix((N,N)); Atb=np.zeros(N); stats={}
    for sid,d in D.items():
        du,dv=corr(d,sol); qx=d['px']+du; qy=d['py']+dv; H,W=int(d['H']),int(d['W'])
        qi=np.clip(np.round(qy).astype(int),0,H-1); qj=np.clip(np.round(qx).astype(int),0,W-1)
        lin=qi*W+qj; ind=d['ind'].reshape(2,-1); cy=ind[0][lin].astype(np.int64); cx=ind[1][lin].astype(np.int64)
        nr=d['nrm'].reshape(2,-1); l2=cy*W+cx; nxv=nr[0][l2].astype(np.float64); nyv=nr[1][l2].astype(np.float64)
        e=nxv*(cx-qx)+nyv*(cy-qy); w=np.where(np.abs(e)<TUK,(1-(e/TUK)**2)**2,0.0)/16.0
        stats[sid]=(float(np.sqrt(np.sum(w*e*e)/max(np.sum(w),1e-9))),float((w>0).mean()))
        t=nxv*du+nyv*dv+e
        J=d['J']; ax=nxv*J[0,0]+nyv*J[1,0]; ay=nxv*J[0,1]+nyv*J[1,1]   # d(n.dp)/dFx, /dFy
        n=len(e); r=np.arange(n)
        ci=np.c_[d['cols'],d['cols']+NN]; cv=np.c_[d['bw']*ax[:,None],d['bw']*ay[:,None]]
        Ai=[np.repeat(r,8)]; Aj=[ci.ravel()]; Av=[cv.ravel()]
        if SHAPE:
            sc=np.arange(d['off'],d['off']+nSh); sv=np.c_[nxv[:,None]*d['Phi'],nyv[:,None]*d['Phi']]
            Ai.append(np.repeat(r,nSh)); Aj.append(np.tile(sc,n)); Av.append(sv.ravel())
        A=sp.csr_matrix((np.concatenate(Av),(np.concatenate(Ai),np.concatenate(Aj))),shape=(n,N))
        Aw=A.multiply(w[:,None]).tocsr(); AtA=AtA+A.T@Aw; Atb+=Aw.T@t
        if SHAPE:
            Ae=sp.csr_matrix((d['Ae'].ravel(),(np.repeat(np.arange(len(d['Ae'])),nSh),np.tile(np.arange(d['off'],d['off']+nSh),len(d['Ae'])))),shape=(len(d['Ae']),N))
            AtA=AtA+Ae.T@Ae
    new=sp.linalg.spsolve((AtA+REG).tocsc(),Atb); dmax=np.abs(new-sol).max(); sol=new
    rms=np.mean([v[0] for v in stats.values()]); inl=np.mean([v[1] for v in stats.values()])
    F=sol[:nF].reshape(2,NN)
    print(f'it {it:2d} mean rms {rms:.3f} inl {inl:.3f} dmax {dmax:.3f} |F| median {np.median(np.hypot(*F)):.1f} ft max {np.hypot(*F).max():.1f}  {time.time()-t0:.0f}s',flush=True)
    if dmax<0.05: break
np.savez(f'joint_{int(SP)}_{int(L2)}_{SHAPE}.npz',sol=sol,nx=nx,ny=ny,SP=SP,X0=X0,Y0=Y0,NN=NN,NS=NS,DEG=DEG,ids=ids,nF=nF,nSh=nSh)
json.dump({k:v for k,v in stats.items()},open(f'joint_{int(SP)}_{int(L2)}_{SHAPE}_stats.json','w'))
