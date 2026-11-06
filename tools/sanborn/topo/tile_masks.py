"""Street (grown over shoulders) and building masks for a tile, as in pilot_trial23 (no fills)."""
import numpy as np, sys, json, cv2
from scipy import ndimage as ndi
from pyproj import Transformer
from pilot_common import load
name=sys.argv[1]; d=load(name); L,n,X0,Y1=d['L'],d['n'],d['X0'],d['Y1']
T=Transformer.from_crs('EPSG:4326','EPSG:26916',always_xy=True); O=json.load(open(f'pilot_{name}_osm.json'))
def px(coords):
    a=np.array(coords); E,N=T.transform(a[:,0],a[:,1]); return np.c_[(np.asarray(E)-X0)/2,(Y1-np.asarray(N))/2].astype(np.int32)
HW={'motorway':15,'trunk':12,'primary':10,'secondary':9,'tertiary':8,'residential':6,'unclassified':6,'living_street':5,
    'motorway_link':7,'trunk_link':7,'primary_link':7,'secondary_link':6,'tertiary_link':6,'service':4,'pedestrian':5}
street=np.zeros((n,n),np.uint8)
for f in O['streets']:
    p=f['properties']; h=HW.get(p.get('highway'))
    if h is None or p.get('bridge') not in (None,'no') or p.get('tunnel') not in (None,'no'): continue
    cv2.polylines(street,[px(f['geometry']['coordinates'])],False,1,max(1,int(round(h))))
bld=np.zeros((n,n),np.uint8)
for f in O['buildings']:
    g=f['geometry']; rings=[g['coordinates'][0]] if g['type']=='Polygon' else [pp[0] for pp in g['coordinates']]
    for r in rings: cv2.fillPoly(bld,[px(r)],1)
street=street.astype(bool); bld=ndi.binary_dilation(bld.astype(bool),iterations=2)
gy,gx=np.gradient(L,2.0); s=np.hypot(gx,gy); Ls_=ndi.gaussian_filter(L,10); gy2,gx2=np.gradient(Ls_,2.0)
anom=np.abs(s-np.hypot(gx2,gy2))>0.12
grown=street.copy()
for _ in range(10): grown|=ndi.binary_dilation(grown)&anom
z=np.zeros_like(grown); np.save(f'pilot_{name}_masks.npy',np.stack([grown,bld,z,z]))
