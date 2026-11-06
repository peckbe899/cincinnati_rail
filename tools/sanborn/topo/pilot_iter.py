"""Iteration I1: LiDAR-based everywhere (fidelity), cleaned of buildings/streets, generalised to a contour-like smoothness;
1912 surface only inside works / big-change zones where the 1912 contours are dense.
  1. median LiDAR (26 m)
  2. erase every building (+4 m) and street (grown over its shoulders); refill = average of membrane and thin plate
  3. on developed ground only: close then open with a D m disk, then Gaussian; natural ground keeps light smoothing
  4. zones: OSM works + band-found changes; dense-contour zones -> 1912 surface + edge offset, sparse -> keep refilled LiDAR
usage: pilot_iter.py name tag D(m) sigma_dev(m) sigma_nat(m)"""
import numpy as np, sys, cv2, json
from scipy import ndimage as ndi
from pilot_common import *
name,tag=sys.argv[1],sys.argv[2]; MODE=sys.argv[6] if len(sys.argv)>6 else 'morph'; SL=float(sys.argv[7]) if len(sys.argv)>7 else 20.0; DISK=float(sys.argv[3]); SD=float(sys.argv[4]); SN=float(sys.argv[5])
d=load(name); L,S,cov,n=d['L'],d['S'],d['cov'],d['n']; X0,Y1=d['X0'],d['Y1']
grown,bld,zone1,natural1=np.load(f'pilot_{name}_masks.npy')
Lm=median26(L)
# ---- zones
lb=np.load(f'pilot_{name}_labels2.npz'); ok=np.isfinite(lb['lab'][lb['inv']])
cx=((lb['E'][ok]-X0)/2).astype(int); cy=((Y1-lb['N'][ok])/2).astype(int); g=(cx>=0)&(cx<n)&(cy>=0)&(cy<n)
cont=np.zeros((n,n),bool); cont[cy[g],cx[g]]=True
near=ndi.distance_transform_edt(~cont)*2.0<20
Zf=detect_changes(Lm,d['lo'],d['hi'],cov)
zl,zk=ndi.label((d['Z']|Zf)&cov); dense=np.zeros((n,n),bool); sparse=np.zeros((n,n),bool)
for i in range(1,zk+1):
    m=zl==i
    if near[m].mean()>=0.5: dense|=m
    else: sparse|=m
# ---- 2. erase and refill
pg,pp,pk=np.load(f'pilot_{name}_padmask.npy')
mask=ndi.binary_dilation(bld|grown|sparse|pg|pp,iterations=1)&~dense
F1=fill_masked(Lm,mask,order=1); F2=fill_masked(Lm,mask,order=2)
C=np.where(mask,0.5*(F1+F2),Lm)
# ---- 3. generalise developed ground
# ---- 4 (moved before generalising): dense zones from the 1912 surface, feathered 10 m, so the filter runs across the seam
off=fill_masked(np.where(dense,0.0,C-S),dense,order=1)
wz=np.clip(ndi.gaussian_filter(dense.astype(float),5)*2,0,1)*dense+ndi.gaussian_filter(dense.astype(float),5)*(~dense)
C=C+wz*((S+off)-C)
dev=ndi.gaussian_filter((ndi.distance_transform_edt(~(bld|grown))*2.0<30).astype(float),5)
r=int(round(DISK/4)); se=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*r+1,2*r+1))
M=cv2.morphologyEx(cv2.morphologyEx(C.astype(np.float32),cv2.MORPH_CLOSE,se),cv2.MORPH_OPEN,se)
if MODE=='morph': Gd=ndi.gaussian_filter(M,SD/2)
else:   # LiDAR shape above SL m, 1912 texture below it (outside 1912 cover: smoothed LiDAR)
    lowC=ndi.gaussian_filter(M if MODE=='mix_m' else C,SL/2); hiS=S-ndi.gaussian_filter(S,SL/2)
    Gd=np.where(cov,lowC+hiS,ndi.gaussian_filter(M,SD/2))
G=dev*Gd+(1-dev)*ndi.gaussian_filter(C,SN/2)
# ---- 4. dense zones from the 1912 surface, joined to the surroundings
T=G
np.save(f'iter_{name}_{tag}.npy',T.astype(np.float32))
# ---- scores
if cov.sum()<1000: print(f'{name} {tag}: fallback tile, no 1912 cover, no scores'); sys.exit(0)
hp=lambda z,s: z-ndi.gaussian_filter(z,s)
m=ndi.binary_dilation(grown|bld,iterations=3)&cov&~dense
hL=hp(ndi.median_filter(L,size=5),8)
imp=np.corrcoef(hp(T,8)[m],hL[m])[0,1]
outb=((T<d['lo'])|(T>d['hi']))[cov&~dense].mean()
big=np.percentile(np.abs(ndi.gaussian_filter(T,20)-ndi.gaussian_filter(L,20))[cov&~dense&~sparse],95)
rough=lambda z: hp(z,5)[cov].std()
print(f'{name} {tag}: imprint {imp:.2f}; outside 1912 band {outb:.0%}; shift from LiDAR at >40 m (p95) {big:.2f} m; fine relief T {rough(T):.2f} / S1912 {rough(S):.2f} / LiDAR {rough(L):.2f} m; zones dense {dense.mean():.0%} sparse {sparse.mean():.0%}')
