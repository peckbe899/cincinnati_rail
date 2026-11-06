"""Trial 4: one weighted solve for the ground D = result - 1912 surface (2 m):
  natural ground: D = LiDAR - S1912 (weight 1)  -> full LiDAR detail
  1912 contour pixels off natural ground: D = 0 (weight 0.3) -> the result sits on the 1912 contours there
  everywhere: weak pull to 0, plus membrane smoothness -> transitions decided by the solve, no fixed blend radius.
Outside 1912 coverage the solve follows median LiDAR."""
import numpy as np, sys, cv2
import scipy.sparse as sp, pyamg
from scipy import ndimage as ndi
from pilot_common import *
name=sys.argv[1]; d=load(name); L,S,cov,n=d['L'],d['S'],d['cov'],d['n']; X0,Y1=d['X0'],d['Y1']
grown,bld,zone,natural=np.load(f'pilot_{name}_masks.npy')
Lm=median26(L)
lb=np.load(f'pilot_{name}_labels2.npz'); ok=np.isfinite(lb['lab'][lb['inv']])
cx=((lb['E'][ok]-X0)/2).astype(int); cy=((Y1-lb['N'][ok])/2).astype(int); g=(cx>=0)&(cx<n)&(cy>=0)&(cy<n)
cont=np.zeros((n,n),bool); cont[cy[g],cx[g]]=True
w=np.full((n,n),0.002); tgt=np.zeros((n,n))
w[cont&~natural]=0.3
w[natural]=1.0; tgt[natural]=(L-S)[natural]
w[~cov]=1.0; tgt[~cov]=(Lm-S)[~cov]
Lp=lap_matrix(n); A=(Lp*1.0+sp.diags(w.ravel())).tocsr()
ml=pyamg.smoothed_aggregation_solver(A,max_coarse=500)
D=ml.solve((w*tgt).ravel(),tol=1e-8,maxiter=300,accel='cg').reshape(n,n)
T4=S+D
np.save(f'pilot_{name}_trial4.npy',T4.astype(np.float32))
T3=np.load(f'pilot_{name}_trial3.npy')
print(f'{name}: trial 4 vs trial 3 |difference| p50 {np.median(np.abs(T4-T3)):.2f} m, p95 {np.percentile(np.abs(T4-T3),95):.2f} m')
T1=np.load(f'pilot_{name}_trial1.npy'); T2=np.load(f'pilot_{name}_trial2.npy')
P=[panel(hs(T1),'Trial 1: change-gated',800),panel(hs(T2),'Trial 2: erase and refill',800),panel(hs(T3),'Trial 3: 1912 base',800),panel(hs(T4),'Trial 4: one weighted solve',800)]
cv2.imwrite(f'pilot_{name}_trials1234.jpg',np.vstack([np.hstack(P[:2]),np.hstack(P[2:])]),[cv2.IMWRITE_JPEG_QUALITY,85])
