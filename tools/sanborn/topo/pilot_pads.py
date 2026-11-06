"""Large-pad mask for the core (fixes 2 + 4):
 a) OSM footprints over 1,000 m2, +4 m, grown up to 30 m over adjacent cut/fill (slope breaks)
 b) LiDAR flat pads: slope < 3%, 1,500-60,000 m2, with a >= 1 m step around at least 40% of the edge (6-12 m out);
    kept (not erased) where the 1912 sheet shows water or park tint over half the pad."""
import numpy as np, json, cv2, sys, rasterio
from rasterio.windows import from_bounds
from pyproj import Transformer
from shapely.geometry import Polygon
from scipy import ndimage as ndi
from pilot_common import load
name=sys.argv[1]; d=load(name); L,n,X0,Y1=d['L'],d['n'],d['X0'],d['Y1']
T=Transformer.from_crs('EPSG:4326','EPSG:26916',always_xy=True)
O=json.load(open(f'pilot_{name}_osm.json'))
big=np.zeros((n,n),np.uint8); nbig=0
for f in O['buildings']:
    g=f['geometry']; rings=[g['coordinates'][0]] if g['type']=='Polygon' else [pp[0] for pp in g['coordinates']]
    for r in rings:
        a=np.array(r); e,nn=T.transform(a[:,0],a[:,1]); e=np.asarray(e); nn=np.asarray(nn)
        if Polygon(np.c_[e,nn]).area>1000:
            cv2.fillPoly(big,[np.c_[(e-X0)/2,(Y1-nn)/2].astype(np.int32)],1); nbig+=1
big=ndi.binary_dilation(big.astype(bool),iterations=2)
gy,gx=np.gradient(L,2.0); s=np.hypot(gx,gy); Ls_=ndi.gaussian_filter(L,10); gy2,gx2=np.gradient(Ls_,2.0)
anom=np.abs(s-np.hypot(gx2,gy2))>0.12
grown=big.copy()
for _ in range(15): grown|=ndi.binary_dilation(grown)&anom
# flat pads
Lq=ndi.median_filter(L,size=5); gy,gx=np.gradient(Lq,2.0)
edge=(ndi.maximum_filter(Lq,size=4)-ndi.minimum_filter(Lq,size=4))>0.8      # steps over ~8 m split flats apart
flat=ndi.binary_opening((np.hypot(gx,gy)<0.03)&(Lq>146)&~edge,iterations=3)
lab,k=ndi.label(flat); idx=np.arange(1,k+1)
area=ndi.sum(np.ones_like(lab),lab,idx)*4.0
with rasterio.open('warped/1912_Survey_Mosaic.vrt') as ds:
    w=from_bounds(X0,Y1-2*n,X0+2*n,Y1,ds.transform); img=ds.read([1,2,3],window=w,out_shape=(3,n,n),boundless=True,fill_value=255).astype(np.int16)
R_,G_,B_=img
water=(B_>R_+15)&(B_>=G_)
park=(G_>R_+4)&(G_>B_+4)
pads=np.zeros((n,n),bool); kept=np.zeros((n,n),bool); stats=[0,0]
for i in np.nonzero((area>=1500)&(area<=60000))[0]+1:
    sl=ndi.find_objects((lab==i).astype(np.uint8))[0]
    sl=tuple(slice(max(a.start-8,0),a.stop+8) for a in sl)
    m=lab[sl]==i; ring=ndi.binary_dilation(m,iterations=6)&~ndi.binary_dilation(m,iterations=3)
    step=np.abs(Lq[sl][ring]-np.median(Lq[sl][m]))
    if np.mean(step>1.0)<0.4: continue                     # no cut/fill edge: natural flat or basin floor
    if np.mean((water|park)[sl][m])>0.5: kept[sl]|=m; stats[1]+=1; continue
    pads[sl]|=m; stats[0]+=1
pads=ndi.binary_dilation(pads,iterations=2)
mask=grown|pads
np.save(f'pilot_{name}_padmask.npy',np.stack([grown,pads,kept]))
print(f'{name}: {nbig} footprints over 1,000 m2 -> {grown.mean():.1%} of ground with their pads; flat pads erased {stats[0]} ({pads.mean():.1%}), kept by 1912 check {stats[1]}')
