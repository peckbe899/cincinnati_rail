"""Pilot 1912 surface, method 2: every 5 ft contour is a level line whose level is a free unknown.
Propagated 5 ft labels enter only as one soft prior per segment (robust), so a mislabel can't drag a contour off its
neighbours; index contours are fixed at their labels. Segments whose pixels can't sit on one level (false contours,
text, street lines) are down-weighted. Solved by alternating: surface given levels, levels given surface."""
import numpy as np, sys
import scipy.sparse as sp, pyamg
import scipy.sparse.linalg as spla
from scipy import ndimage as ndi
FT=1200/3937
name=sys.argv[1]; LAM=float(sys.argv[2]) if len(sys.argv)>2 else 5.0
d=np.load(f'pilot_{name}_labels2.npz')
E,N,inv,lab,isb,cnt=d['E'],d['N'],d['inv'],d['lab'],d['isb'],d['cnt']; X0=float(d['X0']); Y1=float(d['Y1']); W=int(d['W'])
R=4.0; nx=ny=int(W/R); nn=nx*ny
ok=(cnt[inv]>=8)&(np.arange(len(inv))%2==0)
fx=(E-X0)/R-0.5; fy=(Y1-N)/R-0.5; ok&=(fx>=0)&(fx<nx-1)&(fy>=0)&(fy<ny-1)
isidx=isb[inv]&np.isfinite(lab[inv])
seg=inv[ok]; idxpix=isidx[ok]; fx=fx[ok]; fy=fy[ok]
jx=np.floor(fx).astype(int); jy=np.floor(fy).astype(int); tx=fx-jx; ty=fy-jy; cell=jy*nx+jx; no=len(seg)
H=sp.csr_matrix((np.c_[(1-tx)*(1-ty),tx*(1-ty),(1-tx)*ty,tx*ty].ravel(),(np.repeat(np.arange(no),4),np.c_[cell,cell+1,cell+nx,cell+nx+1].ravel())),shape=(no,nn))
useg,sinv=np.unique(seg,return_inverse=True); ns=len(useg)
segidx=isb[useg]&np.isfinite(lab[useg])
prior=lab[useg]*FT; hasprior=np.isfinite(prior)&~segidx
idx2=np.arange(nn).reshape(ny,nx); rr=[];cc=[]
for a,b in ((idx2[:,:-1],idx2[:,1:]),(idx2[:-1,:],idx2[1:,:])): rr.append(a.ravel()); cc.append(b.ravel())
rr=np.concatenate(rr); cc=np.concatenate(cc); Adj=sp.csr_matrix((np.ones(len(rr)),(rr,cc)),shape=(nn,nn)); Adj=Adj+Adj.T
Lp=(sp.diags(np.asarray(Adj.sum(1)).ravel())-Adj).tocsr(); Bi=(Lp.T@Lp).tocsr()
import os
S=(np.load(f'pilot_{name}_S1912_m1.npz')['S'].astype(float).ravel() if os.path.exists(f'pilot_{name}_S1912_m1.npz')
   else (d['S25']*FT).astype(float).ravel())       # warm start: previous fit, else the index-only surface
Ls=np.where(segidx,lab[useg]*FT,np.nan)
# initial free levels: surface mean along each segment
hs=H@S; Lfree=np.bincount(sinv,weights=hs,minlength=ns)/np.bincount(sinv,minlength=ns)
L=np.where(segidx,Ls,np.where(hasprior,prior,Lfree))
wshape=np.ones(ns); wprior=np.where(hasprior,4.0,0.0)
ml=None
for it in range(int(os.environ.get('NIT',10))):
    tgt=L[sinv]; wp=np.where(segidx[sinv],3.0,1.0)*wshape[sinv]
    HW=H.T@sp.diags(wp); A=(HW@H+LAM*Bi+0.02*Lp+sp.diags(np.full(nn,1e-8))).tocsr()
    if it%3==0: ml=pyamg.smoothed_aggregation_solver(A,max_coarse=500)
    S,info=spla.cg(A,HW@tgt,x0=S,rtol=1e-8,maxiter=300,M=ml.aspreconditioner(cycle='V'))   # hierarchy may be from an older A: use it only as a preconditioner
    hs=H@S; npx=np.bincount(sinv,minlength=ns)
    m=np.bincount(sinv,weights=hs,minlength=ns)/np.maximum(npx,1)
    # free level = weighted blend of where the surface puts the segment and its prior
    ws_=np.maximum(wshape,0.05); wsum=npx*ws_+wprior
    Lnew=np.where(segidx,Ls,(npx*ws_*m+wprior*np.nan_to_num(prior))/wsum)
    # robust weights: prior off by > 5 ft from the surface level -> dropped; segment that can't be one level -> dropped
    rp=np.abs(m-np.nan_to_num(prior))/FT
    wprior=np.where(hasprior,4.0*np.clip((5-rp)/3,0,1),0.0)
    sd=np.sqrt(np.maximum(np.bincount(sinv,weights=(hs-Lnew[sinv])**2,minlength=ns)/np.maximum(npx,1),0))/FT
    wshape=np.clip((6-sd)/3,0,1)
    dL=np.nanmax(np.abs(Lnew-L))/FT; L=Lnew
    print(f'{name} it{it}: priors dropped {np.mean(wprior[hasprior]<2):.0%}, segments dropped {np.mean(wshape<0.5):.0%}, max level change {dL:.1f} ft',flush=True)
S=S.reshape(ny,nx)
Sft=S/FT; gy,gx=np.gradient(S,R); sl=np.hypot(gx,gy)
lo=(np.floor(Sft/5)*5-3)*FT-2.0*sl; hi=(np.ceil(Sft/5)*5+3)*FT+2.0*sl
cov=ndi.distance_transform_edt(np.bincount(cell,minlength=nn).reshape(ny,nx)==0)*R<60
np.savez_compressed(f'pilot_{name}_S1912.npz',cov=cov,S=S.astype(np.float32),lo=lo.astype(np.float32),hi=hi.astype(np.float32),X0=X0,Y1=Y1,R=R)
