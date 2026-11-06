import numpy as np, json
from scipy.spatial import cKDTree
from scipy import ndimage as ndi
from pyproj import Transformer
T=Transformer.from_crs(4326,26916,always_xy=True)
bed=np.load('bathy/work/bed_canon4_s.npy'); cl=np.load('bathy/work/cl.npy')
P8=cl[:,:2]; ch=cl[:,2]; t=cKDTree(P8*2)
import pickle
from rasterio import features
from affine import Affine
O,Lk=pickle.load(open('topo/canon_river.pkl','rb'))
ohio=features.rasterize([(O,1)],out_shape=bed.shape,transform=Affine(4,0,695000,0,-4,4350000)).astype(bool)
r,c=np.nonzero(ohio&np.isfinite(bed)); _,k=t.query(np.c_[r,c])
smin=np.full(len(ch),np.inf); np.minimum.at(smin,k,bed[r,c])
# section deepest point per ~50 m
order=np.argsort(ch); 
def sec_at(s,half=25):
    m=(ch>=s-half)&(ch<=s+half); return smin[m].min()
for lid in ['Line_1','Line_2','Line_3','Line_6','Line_8','Line_10']:
    j=json.load(open(f'handoff/out/lines/{lid}.json')); p=np.array(j['path']); x,y=T.transform(p[:,1],p[:,2])
    for rv in j['rivers']:
        if rv['name']!='Ohio River': continue
        cm=(rv['c0']+rv['c1'])/2; xm=np.interp(cm,p[:,0],x); ym=np.interp(cm,p[:,0],y)
        _,kk=t.query([[(4350000-ym)/4,(xm-695000)/4]]); s0=ch[kk[0]]
        here=sec_at(s0)
        out=[]
        for W in (250,500,1000):
            ss=np.arange(s0-W,s0+W+1,10); vals=np.array([sec_at(s) for s in ss]); i=np.argmax(vals)
            out.append(f'±{W} m: shallowest {vals[i]:.1f} at {ss[i]-s0:+.0f} m (gain {vals[i]-here:.1f})')
        print(f'{lid:8s} at river km {s0/1000:5.2f}: deepest here {here:.1f}  | '+' | '.join(out))
