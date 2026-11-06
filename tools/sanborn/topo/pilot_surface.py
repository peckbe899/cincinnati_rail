"""Pilot 1912 surface: robust thin-plate fit to labelled contour pixels (4 m), segments that disagree with the
surface implied by their neighbours are down-weighted (IRLS). Output S1912 (m NAVD88) + band bounds."""
import numpy as np, sys, json
import scipy.sparse as sp, pyamg
from scipy import ndimage as ndi
FT=1200/3937
name=sys.argv[1]; LAM=float(sys.argv[2]) if len(sys.argv)>2 else 5.0; d=np.load(f'pilot_{name}_labels2.npz')
E,N,inv,lab,isb,cnt=d['E'],d['N'],d['inv'],d['lab'],d['isb'],d['cnt']; X0=float(d['X0']); Y1=float(d['Y1']); W=int(d['W'])
R=4.0; nx=ny=int(W/R)
pl=lab[inv]; ok=np.isfinite(pl)
ix=((E-X0)/R).astype(int); iy=((Y1-N)/R).astype(int); ok&=(ix>=0)&(ix<nx)&(iy>=0)&(iy<ny)
ok&=(np.arange(len(ok))%2==0)                            # every 2nd skeleton pixel (~1.4 m apart)
seg=inv[ok]; val=pl[ok]*FT          # metres
fx=(E[ok]-X0)/R-0.5; fy=(Y1-N[ok])/R-0.5; jx=np.clip(np.floor(fx).astype(int),0,nx-2); jy=np.clip(np.floor(fy).astype(int),0,ny-2)
tx=np.clip(fx-jx,0,1); ty=np.clip(fy-jy,0,1); cell=jy*nx+jx
no=len(val); rows=np.repeat(np.arange(no),4)
cols=np.c_[cell,cell+1,cell+nx,cell+nx+1].ravel(); wts=np.c_[(1-tx)*(1-ty),tx*(1-ty),(1-tx)*ty,tx*ty].ravel()
nn=nx*ny; idx=np.arange(nn).reshape(ny,nx)
# Laplacian with Neumann-ish boundary
rr=[];cc=[]
for a,b in ((idx[:,:-1],idx[:,1:]),(idx[:-1,:],idx[1:,:])): rr.append(a.ravel()); cc.append(b.ravel())
rr=np.concatenate(rr); cc=np.concatenate(cc); Adj=sp.csr_matrix((np.ones(len(rr)),(rr,cc)),shape=(nn,nn)); Adj=Adj+Adj.T
Lp=(sp.diags(np.asarray(Adj.sum(1)).ravel())-Adj).tocsr()
Bi=(Lp.T@Lp).tocsr()
ws=np.ones(len(np.unique(seg))); useg,sinv=np.unique(seg,return_inverse=True)
base=np.where(isb[useg],3.0,1.0)
for it in range(4):
    wp=(base*ws)[sinv]
    H=sp.csr_matrix((wts,(rows,cols)),shape=(no,nn)); HW=H.T@sp.diags(wp)
    A=(HW@H+LAM*Bi+0.02*Lp+sp.diags(np.full(nn,1e-8))).tocsr(); Wv=HW@val
    ml=pyamg.smoothed_aggregation_solver(A,max_coarse=500)
    x0=None if it==0 else S.ravel()
    S=ml.solve(Wv,x0=x0,tol=1e-9,maxiter=400,accel='cg').reshape(ny,nx)
    res=H@S.ravel()-val
    o=np.argsort(sinv,kind='stable'); cn=np.bincount(sinv); bnd=np.r_[0,np.cumsum(cn)]
    rs=np.array([np.median(res[o[bnd[k]:bnd[k+1]]]) for k in range(len(useg))])/FT   # ft
    thr_lo,thr_hi=np.where(isb[useg],3.0,2.0),np.where(isb[useg],8.0,5.0)
    ws=np.clip((thr_hi-np.abs(rs))/(thr_hi-thr_lo),0,1)
    print(f'{name} it{it}: segments down-weighted {np.mean(ws<0.5):.0%} (index {np.mean(ws[isb[useg]]<0.5):.0%}), |seg residual| p90 {np.percentile(np.abs(rs),90):.1f} ft',flush=True)
# band: bracketing 5 ft levels around S, widened by 3 ft accuracy and 2 m georef x slope
Sft=S/FT; gy,gx=np.gradient(S,R); sl=np.hypot(gx,gy)
lo=(np.floor(Sft/5)*5-3)*FT-2.0*sl; hi=(np.ceil(Sft/5)*5+3)*FT+2.0*sl
cov=ndi.distance_transform_edt(np.bincount(cell,minlength=nn).reshape(ny,nx)==0)*R<60
np.savez_compressed(f'pilot_{name}_S1912.npz',cov=cov,S=S.astype(np.float32),lo=lo.astype(np.float32),hi=hi.astype(np.float32),X0=X0,Y1=Y1,R=R,segw=ws,useg=useg)
