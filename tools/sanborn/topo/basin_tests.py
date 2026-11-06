import numpy as np, json, cv2
from scipy import ndimage as ndi
from pyproj import Transformer
from pilot_common import *
name='otr'; d=load(name); L,n,X0,Y1=d['L'],d['n'],d['X0'],d['Y1']
Tcp=np.load('pilot_otr_combo_pads.npy'); core,zone,nat,padm=np.load('pilot_otr_combo_masks_pads.npy')
grown,bld,zone1,natural1=np.load('pilot_otr_masks.npy')
Lm=median26(L)
# flat core ground: smoothed slope under 4%, feathered to 6%
gy,gx=np.gradient(ndi.gaussian_filter(L,10),2.0); sl=np.hypot(gx,gy)
wf=np.clip((0.06-sl)/0.02,0,1)*ndi.gaussian_filter(core.astype(float),10)
wf=ndi.gaussian_filter(wf,5); wf[zone]=0
# A: erase every footprint and street on flat core ground, thin-plate refill
mA=(bld|grown)&(wf>0.05)
LA=fill_masked(Lm,ndi.binary_dilation(mA,iterations=1),order=2)
TA=(1-wf)*Tcp+wf*LA
# B: morphological filter (closing then opening, 30 m disk) + light smoothing
se=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(31,31))
LB=cv2.morphologyEx(cv2.morphologyEx(Lm.astype(np.float32),cv2.MORPH_CLOSE,se),cv2.MORPH_OPEN,se)
LB=ndi.gaussian_filter(LB,3); TB=(1-wf)*Tcp+wf*LB
# C: heavy smoothing (24 m)
LC=ndi.gaussian_filter(Lm,12); TC=(1-wf)*Tcp+wf*LC
for k,T in (('A',TA),('B',TB),('C',TC)): np.save(f'basin_{k}.npy',T.astype(np.float32))
print('flat core share %.0f%%, A erased %.0f%% of it'%(100*(wf>0.5).mean(),100*mA[wf>0.5].mean()))
# how much each moves the basin, and how much natural basin shape (>60 m scale) it keeps
big=lambda z: ndi.gaussian_filter(z,30)
for k,T in (('current',Tcp),('A',TA),('B',TB),('C',TC)):
    m=wf>0.5; hp=T-ndi.gaussian_filter(T,8)
    print(f'{k}: fine relief left on flat core (std, m) {hp[m].std():.2f}; large-scale change vs LiDAR (p95, m) {np.percentile(np.abs(big(T)-big(L))[m],95):.2f}')
crops=[(1000,420,'basin west'),(1250,800,'basin centre'),(1480,1050,'downtown')]
rows=[]
for r,c,lab in crops:
    h=170; r=min(max(r,h),n-h); c=min(max(c,h),n-h); w=np.s_[r-h:r+h,c-h:c+h]
    rows.append(np.hstack([panel(hs(L[w]),f'LiDAR: {lab}',360),panel(hs(Tcp[w]),'current combo',360),panel(hs(TA[w]),'A: erase all footprints',360),panel(hs(TB[w]),'B: morphological filter',360),panel(hs(TC[w]),'C: heavy smoothing',360)]))
cv2.imwrite('basin_tests.jpg',np.vstack(rows),[cv2.IMWRITE_JPEG_QUALITY,85])
