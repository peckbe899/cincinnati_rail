"""Simple robust labels: bold -> nearest multiple of 25 to LiDAR median; thin -> nearest 5 not on a multiple of 25.
Residual field from bold contours only, unwrapped against neighbours (mod 25)."""
import numpy as np, sys, json
from scipy.spatial import cKDTree
def run(sid):
    d=np.load(f'lab/{sid}_seg.npz'); xs=d['x'].astype(int); ys=d['y'].astype(int); ids=d['id']; zp=d['z'].astype(float); bold=d['bold']
    u,inv=np.unique(ids,return_inverse=True); n=len(u); cnt=np.bincount(inv)
    o=np.argsort(inv,kind='stable'); b=np.r_[0,np.cumsum(cnt)]
    zmed=np.array([np.nanmedian(zp[o[b[k]:b[k+1]]]) for k in range(n)]); bf=np.bincount(inv,weights=bold)/cnt
    E=np.bincount(inv,weights=d['E'])/cnt; N=np.bincount(inv,weights=d['N'])/cnt
    isb=(bf>0.6)&(cnt>=12)&np.isfinite(zmed)
    Cw=np.full(n,np.nan); Cw[isb]=25*np.round(zmed[isb]/25)-zmed[isb]           # wrapped residual in (-12.5,12.5]
    # unwrap: iterate k so each bold residual is near the median of bold neighbours within 60 m
    bi=np.nonzero(isb)[0]; T=cKDTree(np.c_[E[bi],N[bi]]); nb=T.query_ball_point(np.c_[E[bi],N[bi]],60.0)
    C=Cw[bi].copy()
    for it in range(8):
        newC=C.copy()
        for i,lst in enumerate(nb):
            lst=[j for j in lst if j!=i]
            if len(lst)<3: continue
            m=np.median(C[lst]); k=np.round((m-C[i])/25); newC[i]=C[i]+25*k
        if np.allclose(newC,C): break
        C=newC
    Lb=zmed[bi]+C
    lab=5*np.round(zmed/5); t25=(~isb)&(lab%25==0); lab[t25]=np.where(zmed[t25]>=lab[t25],lab[t25]+5,lab[t25]-5)
    lab[bi]=25*np.round(Lb/25)
    Cs=np.full(n,np.nan); Cs[bi]=lab[bi]-zmed[bi]
    np.savez_compressed(f'lab/{sid}_labels2.npz',inv=inv,lab=lab,zmed=zmed,bf=bf,cnt=cnt,isb=isb,C=Cs,E=E,N=N)
    big=np.abs(Cs[bi])>12.5
    print(sid,'segments',n,'bold',len(bi),'unwrapped beyond 12.5 ft:',int(big.sum()),' |C|>5 frac (len) %.3f'%(np.average(np.abs(Cs[bi])>5,weights=cnt[bi])),flush=True)
if __name__=='__main__':
    for sid in sys.argv[1:]: run(sid)
