import numpy as np, sys, cv2
from pilot_common import load, hs, panel
name=sys.argv[1]; tags=sys.argv[2].split(','); out=sys.argv[3]
d=load(name); L,S=d['L'],d['S']; n=d['n']
Ts=[('LiDAR',L),('1912 surface',S)]+[(t,np.load(f'iter_{name}_{t}.npy')) for t in tags]
full=[panel(hs(T),lab,600) for lab,T in Ts]
crops={'otr':[(1000,420),(560,780),(1250,800)],'westwood':[(500,500),(900,1150),(300,1300)]}[name]
rows=[np.hstack(full)]
for r,c in crops:
    h=170; r=min(max(r,h),n-h); c=min(max(c,h),n-h); w=np.s_[r-h:r+h,c-h:c+h]
    rows.append(np.hstack([panel(hs(T[w]),lab,600) for lab,T in Ts]))
cv2.imwrite(out,np.vstack(rows),[cv2.IMWRITE_JPEG_QUALITY,80])
