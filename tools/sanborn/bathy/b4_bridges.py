import numpy as np
from pyproj import Transformer
from scipy import ndimage as ndi
T=Transformer.from_crs(4326,26916,always_xy=True)
bed=np.load('bathy/work/bed_real4.npy'); m=~np.isnan(bed)
P=np.load('bathy/work/pts.npy')
from scipy.spatial import cKDTree
t=cKDTree(P[:,:2])
# smooth reference: normalized gaussian 60 m
b0=np.where(m,bed,0); w=ndi.gaussian_filter(m.astype(float),15); s=ndi.gaussian_filter(b0,15)/np.maximum(w,1e-6)
res=np.where(m,bed-s,np.nan)
br={'Cincinnati Southern (rail)':(-84.5530,39.0940),'Brent Spence':(-84.5236,39.0925),'C&O (rail)':(-84.5197,39.0933),'Clay Wade Bailey':(-84.5180,39.0931),
'Roebling':(-84.5099,39.0925),'Taylor-Southgate':(-84.5020,39.0957),'L&N':(-84.4963,39.0976),'Daniel Carter Beard (I-471)':(-84.4929,39.0989),'Combs-Hehl (I-275)':(-84.4180,39.0285)}
print('overall residual sd',np.nanstd(res))
for n,(lo,la) in br.items():
    x,y=T.transform(lo,la); c=int((x-695000)/4); r=int((4350000-y)/4)
    win=res[r-30:r+31,c-30:c+31]; bw=bed[r-30:r+31,c-30:c+31]
    # soundings within 120 m: min depth anomaly
    idx=t.query_ball_point([x,y],120); z=P[idx,2] if idx else np.array([np.nan])
    print(f'{n:30s} in-river cells {np.isfinite(win).sum():5d}  min resid {np.nanmin(win) if np.isfinite(win).any() else np.nan:6.2f}  deepest bed {np.nanmin(bw) if np.isfinite(bw).any() else np.nan:7.2f}  soundings {len(idx)} min {np.nanmin(z):.2f}')
