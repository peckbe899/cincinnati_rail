import numpy as np, json, pickle
from scipy.spatial import cKDTree
from pyproj import Transformer
from rasterio import features
from affine import Affine
T=Transformer.from_crs(4326,26916,always_xy=True)
bed=np.load('bathy/work/bed_canon4_s.npy'); cl=np.load('bathy/work/cl.npy'); P8=cl[:,:2]; ch=cl[:,2]; t=cKDTree(P8*2)
O,Lk=pickle.load(open('topo/canon_river.pkl','rb'))
ohio=features.rasterize([(O,1)],out_shape=bed.shape,transform=Affine(4,0,695000,0,-4,4350000)).astype(bool)
r,c=np.nonzero(ohio&np.isfinite(bed)); _,k=t.query(np.c_[r,c]); s_cell=ch[k]
smin=np.full(len(ch),np.inf); np.minimum.at(smin,k,bed[r,c])
sec=lambda s,h=25: smin[(ch>=s-h)&(ch<=s+h)].min()
new=bed.copy(); target=np.full(len(r),-np.inf); wmax=np.zeros(len(r)); log=[]
for lid in ['Line_1','Line_2','Line_3','Line_6','Line_8','Line_10']:
    j=json.load(open(f'handoff/out/lines/{lid}.json')); p=np.array(j['path']); x,y=T.transform(p[:,1],p[:,2])
    for rv in j['rivers']:
        cm=(rv['c0']+rv['c1'])/2; xm=np.interp(cm,p[:,0],x); ym=np.interp(cm,p[:,0],y)
        if not O.contains(__import__('shapely').geometry.Point(xm,ym)): continue
        _,kk=t.query([[(4350000-ym)/4,(xm-695000)/4]]); s0=ch[kk[0]]
        ss=np.arange(s0-500,s0+501,10); vals=np.array([sec(s) for s in ss]); R=vals.max(); here=sec(s0)
        d=np.abs(s_cell-s0); w=np.clip((250-d)/150,0,1)
        sel=w>0; raised=np.maximum(bed[r[sel],c[sel]],R)
        val=bed[r[sel],c[sel]]+w[sel]*(raised-bed[r[sel],c[sel]])
        cur=new[r[sel],c[sel]]; new[r[sel],c[sel]]=np.maximum(cur,val)
        log.append((lid,rv['name'],round(s0),round(here,1),round(R,1)))
np.save('bathy/work/bed_canon4_r.npy',new)
for l in log: print(l)
