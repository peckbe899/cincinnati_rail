"""Trial 1: change-gated LiDAR. Median LiDAR everywhere; inside big-change zones (OSM works + changes found against
the 1912 band) the 1912 surface, shifted to meet the LiDAR at the zone edge."""
import numpy as np, sys, cv2
from pilot_common import *
name=sys.argv[1]; d=load(name); L,S,cov=d['L'],d['S'],d['cov']
Lm=median26(L)
Zf=detect_changes(Lm,d['lo'],d['hi'],cov)
zone=(d['Z']|Zf)&cov
off=fill_masked(np.where(cov,Lm-S,0.0),zone,order=1)        # offset field, membrane across each zone
T1=np.where(zone,S+off,Lm)
np.save(f'pilot_{name}_trial1.npy',T1.astype(np.float32)); np.save(f'pilot_{name}_zone1.npy',zone)
print(f'{name}: zone share {zone.mean():.1%} (OSM {(d["Z"]&cov).mean():.1%}, found from 1912 band {Zf.mean():.1%})')
im=[panel(hs(L),'LiDAR 2026'),outline(panel(hs(T1),'Trial 1: change-gated LiDAR'),zone),panel(hs(S),'1912 surface')]
cv2.imwrite(f'pilot_{name}_trial1.jpg',np.hstack(im),[cv2.IMWRITE_JPEG_QUALITY,85])
