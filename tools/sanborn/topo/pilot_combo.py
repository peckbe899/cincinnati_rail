"""Combo: inside the 1912 built-up core, median LiDAR with only mapped works (OSM) rebuilt to the 1912 contours;
outside it, trial 4 (1912 surface, LiDAR on natural ground, change finder on). One weighted solve for D = result - S1912,
with the core feathered over 100 m so the two regimes meet without a seam."""
import numpy as np, sys, cv2
import scipy.sparse as sp, pyamg
from scipy import ndimage as ndi
from pilot_common import *
name=sys.argv[1]; PADS=len(sys.argv)>2 and sys.argv[2]=='pads'; d=load(name); L,S,cov,n=d['L'],d['S'],d['cov'],d['n']; X0,Y1=d['X0'],d['Y1']
grown,bld,zone1,natural1=np.load(f'pilot_{name}_masks.npy')
Lm=median26(L)
# ---- 1912 built-up core (2 m grid): ink density > 0.03 at ~100 m scale, gaps between blocks closed (150 m), thin strips opened (60 m)
dens=np.load(f'pilot_{name}_inkdens.npy')
disk=lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*r+1,2*r+1))
core=(ndi.gaussian_filter(dens,40)>0.03).astype(np.uint8)        # ~100 m support so lettering and lone buildings don't count
core=cv2.morphologyEx(core,cv2.MORPH_CLOSE,disk(75)); core=cv2.morphologyEx(core,cv2.MORPH_OPEN,disk(30)).astype(bool)
lab,k=ndi.label(core); sz=ndi.sum(np.ones_like(lab),lab,np.arange(1,k+1))*4.0
core=np.isin(lab,np.nonzero(sz>=200000)[0]+1)&cov
sd=np.where(core,ndi.distance_transform_edt(core),-ndi.distance_transform_edt(~core))*2.0
wc=np.clip(0.5+sd/100.0,0,1)
# ---- zones: mapped works everywhere; band-found changes only outside the core
Zf=detect_changes(Lm,d['lo'],d['hi'],cov)&(wc<0.5)
zone=(d['Z']|Zf)&cov
dev=ndi.distance_transform_edt(~(grown|bld))*2.0
inband=(Lm>d['lo']-0.5)&(Lm<d['hi']+0.5)
natural=ndi.binary_opening(cov&(dev>25)&~zone&inband&(wc<0.5),iterations=3)
lb=np.load(f'pilot_{name}_labels2.npz'); ok=np.isfinite(lb['lab'][lb['inv']])
cx=((lb['E'][ok]-X0)/2).astype(int); cy=((Y1-lb['N'][ok])/2).astype(int); g=(cx>=0)&(cx<n)&(cy>=0)&(cy<n)
cont=np.zeros((n,n),bool); cont[cy[g],cx[g]]=True
# ---- weighted terms (summed): weight, target for D
W=np.full((n,n),0.002); B=np.zeros((n,n))
def add(w,t):
    global W,B; W=W+w; B=B+w*t
add(np.where(cont&~natural&~zone,0.3*(1-wc),0.0),0.0)          # outside core: sit on the 1912 contours
add(np.where(cont&zone,0.3,0.0),0.0)                           # works: rebuilt to the 1912 contours
add(np.where(natural,1.0,0.0),L-S)                              # natural ground: full LiDAR
if PADS:                                                        # big footprints + flat pads erased, refilled from their edges
    pg,pp,pk=np.load(f'pilot_{name}_padmask.npy'); padm=(pg|pp)&(wc>0)&~zone
    # works zones in the core where the 1912 contours are sparse (basin flats): refill from the edges, not the 1912 surface
    near=ndi.distance_transform_edt(~cont)*2.0<20
    zl,zk=ndi.label(zone&(wc>0.5)); sparse=np.zeros_like(zone)
    for i in range(1,zk+1):
        m=zl==i
        if near[m].mean()<0.5: sparse|=m
    padm|=sparse; zone=zone&~sparse
    Lc=fill_masked(Lm,ndi.binary_dilation(padm,iterations=1),order=2)   # thin plate: slope carries across, no dents
else: Lc=Lm; padm=np.zeros_like(core)
add(np.where(cov&~zone,wc,0.0),Lc-S)                            # core: median LiDAR
add(np.where(~cov,1.0,0.0),Lm-S)                                # no 1912 survey: median LiDAR
A=(lap_matrix(n)+sp.diags(W.ravel())).tocsr()
D=pyamg.smoothed_aggregation_solver(A,max_coarse=500).solve(B.ravel(),tol=1e-8,maxiter=300,accel='cg').reshape(n,n)
TC=S+D
tag='_pads' if PADS else ''
np.save(f'pilot_{name}_combo{tag}.npy',TC.astype(np.float32)); np.save(f'pilot_{name}_combo_masks{tag}.npy',np.stack([core,zone,natural,padm]))
# ---- scorecard (same measures as the trials)
lo,hi=d['lo'],d['hi']; outband=((TC<lo)|(TC>hi))[cov].mean()
m=ndi.binary_dilation(grown|bld,iterations=3)&cov&~zone
hp8=lambda z: z-ndi.gaussian_filter(z,8); hL=hp8(ndi.median_filter(L,size=5))
imp=np.corrcoef(hp8(TC)[m],hL[m])[0,1]; impc=np.corrcoef(hp8(TC)[m&core],hL[m&core])[0,1] if (m&core).any() else np.nan
hp5=lambda z: z-ndi.gaussian_filter(z,5); nat=np.corrcoef(hp5(TC)[natural],hp5(L)[natural])[0,1] if natural.any() else np.nan
print(f'{name}{tag}: core {core[cov].mean():.0%} of surveyed ground; outside 1912 band {outband:.0%}; imprint left {imp:.2f} (core {impc:.2f}); natural detail kept {nat:.2f}')
if PADS:
    T0=np.load(f'pilot_{name}_combo.npy')
    P=[outline(panel(hs(L),'LiDAR 2026 (red: erased pads)',800),padm,(0,0,255),800),panel(hs(T0),'Combo before',800),panel(hs(TC),'Combo with big pads erased',800)]
    cv2.imwrite(f'pilot_{name}_combo_pads.jpg',np.hstack(P),[cv2.IMWRITE_JPEG_QUALITY,85])
else:
    T4=np.load(f'pilot_{name}_trial4.npy')
    P=[outline(panel(hs(L),'LiDAR 2026 (red: 1912 built-up core)',800),core,(0,0,255),800),panel(hs(TC),'Combo',800),panel(hs(T4),'Trial 4 alone',800)]
    cv2.imwrite(f'pilot_{name}_combo.jpg',np.hstack(P),[cv2.IMWRITE_JPEG_QUALITY,85])
