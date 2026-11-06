"""Trials 2 and 3 on a pilot window.
Trial 2 (erase and refill): streets (grown over their cut/fill shoulders), building pads and big-change zones are
erased; the hole is refilled with the 1912 surface shifted to meet the surrounding LiDAR (membrane offset).
Trial 3 (1912 base): the 1912 surface everywhere it exists; LiDAR detail kept only on natural ground (well away from
streets and buildings, outside zones, inside the 1912 band), tapering to the 1912 surface over 30 m."""
import numpy as np, sys, json, cv2
from scipy import ndimage as ndi
from pyproj import Transformer
from pilot_common import *
name=sys.argv[1]; d=load(name); L,S,cov,n=d['L'],d['S'],d['cov'],d['n']; X0,Y1=d['X0'],d['Y1']
T=Transformer.from_crs('EPSG:4326','EPSG:26916',always_xy=True)
O=json.load(open(f'pilot_{name}_osm.json'))
def px(coords):
    a=np.array(coords); E,N=T.transform(a[:,0],a[:,1]); return np.c_[(np.asarray(E)-X0)/2,(Y1-np.asarray(N))/2].astype(np.int32)
HW={'motorway':15,'trunk':12,'primary':10,'secondary':9,'tertiary':8,'residential':6,'unclassified':6,'living_street':5,
    'motorway_link':7,'trunk_link':7,'primary_link':7,'secondary_link':6,'tertiary_link':6,'service':4,'pedestrian':5}
street=np.zeros((n,n),np.uint8)
for f in O['streets']:
    p=f['properties']; h=HW.get(p.get('highway'))
    if h is None or p.get('bridge') not in (None,'no') or p.get('tunnel') not in (None,'no'): continue
    cv2.polylines(street,[px(f['geometry']['coordinates'])],False,1,max(1,int(round(2*h/2))))
bld=np.zeros((n,n),np.uint8)
for f in O['buildings']:
    g=f['geometry']; rings=[g['coordinates'][0]] if g['type']=='Polygon' else [pp[0] for pp in g['coordinates']]
    for r in rings: cv2.fillPoly(bld,[px(r)],1)
street=street.astype(bool); bld=ndi.binary_dilation(bld.astype(bool),iterations=2)      # pad: footprint + 4 m
Lm=median26(L)
# grow streets over their cut/fill shoulders: pixels whose slope departs from the smoothed slope, up to 20 m out
gy,gx=np.gradient(L,2.0); s=np.hypot(gx,gy); Ls_=ndi.gaussian_filter(L,10); gy2,gx2=np.gradient(Ls_,2.0); ss=np.hypot(gx2,gy2)
anom=np.abs(s-ss)>0.12
grown=street.copy()
for _ in range(10): grown|=ndi.binary_dilation(grown)&anom
zone=np.load(f'pilot_{name}_zone1.npy')
# ---------- trial 2
mask2=ndi.binary_dilation(grown|bld|zone,iterations=2)    # 4 m margin so the fill starts on undisturbed ground
base=np.where(cov,S,ndi.gaussian_filter(Lm,15))
off=fill_masked(Lm-base,mask2,order=1)
T2=np.where(mask2,base+off,Lm)
# ---------- trial 3
dev=ndi.distance_transform_edt(~(street|bld))*2.0
inband=(Lm>d['lo']-0.5)&(Lm<d['hi']+0.5)
natural=cov&(dev>25)&~zone&inband
natural=ndi.binary_opening(natural,iterations=3)
dn=ndi.distance_transform_edt(~natural)*2.0
offn=fill_masked(np.where(natural,L-S,0.0),~natural,order=1)
w=np.where(natural,1.0,np.exp(-dn/30.0))
T3=np.where(cov,S+w*offn,Lm)
np.save(f'pilot_{name}_trial2.npy',T2.astype(np.float32)); np.save(f'pilot_{name}_trial3.npy',T3.astype(np.float32))
np.save(f'pilot_{name}_masks.npy',np.stack([grown,bld,zone,natural]))
print(f'{name}: trial 2 erased {mask2.mean():.0%} (streets+shoulders {grown.mean():.0%}, pads {bld.mean():.0%}, zones {zone.mean():.0%}); trial 3 natural ground {natural.mean():.0%}, no 1912 cover {(~cov).mean():.0%}')
T1=np.load(f'pilot_{name}_trial1.npy')
P=[panel(hs(L),'LiDAR 2026',800),panel(hs(T1),'Trial 1: change-gated',800),panel(hs(T2),'Trial 2: erase and refill',800),panel(hs(T3),'Trial 3: 1912 base, LiDAR on natural ground',800)]
cv2.imwrite(f'pilot_{name}_trials123.jpg',np.vstack([np.hstack(P[:2]),np.hstack(P[2:])]),[cv2.IMWRITE_JPEG_QUALITY,85])
mk=np.zeros((n,n,3),np.uint8)+235; mk[natural]=(90,160,60); mk[grown]=(60,60,200); mk[bld]=(40,40,40); mk[zone]=(200,120,40)
cv2.imwrite(f'pilot_{name}_masks.jpg',cv2.resize(mk,(800,800),interpolation=cv2.INTER_NEAREST))
