"""Label 1912 contour segments: LiDAR anchors + uphill-neighbour relations, robust least squares, bold snapping."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, cv2, json, sys
import scipy.sparse as sp
from scipy.sparse.linalg import lsqr
from scipy import ndimage as ndi
from scipy.ndimage import map_coordinates, gaussian_filter
from final_model import Final
from geo import S, FT
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
DM=json.load(open('dem2m.json')); DEM=np.load('dem2m.npy',mmap_mode='r')
F=Final()
def zfield_half(sid,shape,step=16):
    H,W=shape; cu=np.arange(0,W+step,step); cv=np.arange(0,H+step,step); CU,CV=np.meshgrid(cu,cv)
    E,N=F.p2utm(sid,CU.ravel()*2.0,CV.ravel()*2.0); E=E.reshape(CU.shape); N=N.reshape(CU.shape)
    r=DM['res']; c0=int((E.min()-60-DM['x0'])/r); c1=int((E.max()+60-DM['x0'])/r)+1; r0=int((DM['y1']-N.max()-60)/r); r1=int((DM['y1']-N.min()+60)/r)+1
    pr=max(0,-r0); pc=max(0,-c0)
    a=np.pad(np.asarray(DEM[max(r0,0):r1,max(c0,0):c1]).astype(np.float32),((pr,0),(pc,0)),constant_values=DM['nodata'])
    bad=a==DM['nodata']; a=np.where(bad,np.nan,a/10/FT); a=np.where(np.isnan(a),np.nanmean(a),a)
    R=(DM['y1']-N)/r-r0-0.5; C=(E-DM['x0'])/r-c0-0.5
    z=np.empty((H,W),np.float32)
    for y in range(0,H,512):
        yy,xx=np.mgrid[y:min(H,y+512),0:W].astype(np.float32)
        z[y:y+512]=map_coordinates(a,[map_coordinates(R,[yy/step,xx/step],order=1),map_coordinates(C,[yy/step,xx/step],order=1)],order=1)
    return z
BW=0.5
def run(sid,verbose=True):
    d=np.load(f'lab/{sid}_seg.npz'); xs=d['x'].astype(int); ys=d['y'].astype(int); ids=d['id']; zp=d['z'].astype(float); bold=d['bold']
    u,inv=np.unique(ids,return_inverse=True); n=len(u); cnt=np.bincount(inv)
    sk=cv2.imread(f'contours/{sid}_contours.png',0); H,W=sk.shape
    segimg=np.full((H,W),-1,np.int32); segimg[ys,xs]=inv
    im=cv2.imread(base+S[sid]['file'],0); im=cv2.resize(im,(W,H),interpolation=cv2.INTER_AREA)
    black=im<110
    z=zfield_half(sid,(H,W)); zs=gaussian_filter(z,6.0); gy,gx=np.gradient(zs); gm=np.hypot(gx,gy)+1e-9; ux=gx/gm; uy=gy/gm
    # LiDAR anchor per segment: robust median
    srt=np.argsort(inv,kind='stable'); bnd=np.r_[0,np.cumsum(cnt)]; zmed=np.array([np.nanmedian(zp[srt[bnd[k]:bnd[k+1]]]) for k in range(n)])
    zmad=np.array([np.nanmedian(np.abs(zp[srt[bnd[k]:bnd[k+1]]]-zmed[k])) for k in range(n)])
    bf=np.bincount(inv,weights=bold)/cnt
    # rays uphill from every 2nd pixel
    sel=np.arange(0,len(xs),2); x0=xs[sel].astype(float); y0=ys[sel].astype(float); k0=inv[sel]
    dx=ux[ys[sel],xs[sel]]; dy=uy[ys[sel],xs[sel]]
    hit=np.full(len(sel),-1); hd=np.zeros(len(sel)); alive=np.ones(len(sel),bool)
    for st in range(2,46):
        xi=np.round(x0+dx*st).astype(int); yi=np.round(y0+dy*st).astype(int)
        ok=alive&(xi>=0)&(xi<W)&(yi>=0)&(yi<H); alive&=ok
        xi=np.clip(xi,0,W-1); yi=np.clip(yi,0,H-1)
        s=segimg[yi,xi]; h=alive&(s>=0)&(s!=k0)
        hit[h]=s[h]; hd[h]=st; alive&=~h
        alive&=~black[yi,xi]
    m=hit>=0
    zA=zs[ys[sel][m],xs[sel][m]]; xh=np.round(x0[m]+dx[m]*hd[m]).astype(int); yh=np.round(y0[m]+dy[m]*hd[m]).astype(int); zB=zs[np.clip(yh,0,H-1),np.clip(xh,0,W-1)]
    dz=zB-zA; ka=k0[m]; kb=hit[m]
    rel=np.where(dz>1.0,1.0,0.0)   # adjacent distinct contours: exactly one interval uphill
    keepr=rel>0; ka,kb,rel=ka[keepr],kb[keepr],rel[keepr]
    # aggregate pair relations: modal rel per (ka,kb)
    key=ka.astype(np.int64)*n+kb; o=np.lexsort((rel,key)); key,rel,ka,kb=key[o],rel[o],ka[o],kb[o]
    uk,st_,ct=np.unique(key,return_index=True,return_counts=True)
    P=[]
    for i,(s0,c) in enumerate(zip(st_,ct)):
        r=rel[s0:s0+c]; vals,cc=np.unique(r,return_counts=True); j=np.argmax(cc)
        P.append((ka[s0],kb[s0],vals[j],cc[j]))
    P=np.array(P,float); pa=P[:,0].astype(int); pb=P[:,1].astype(int); pr=P[:,2]*5; pw=np.minimum(P[:,3],15)
    # robust LSQ: h_b - h_a = pr (w_rel), h_k = zmed (w_anchor)
    wa0=np.where(np.isfinite(zmed),np.minimum(cnt,60)/60.0*0.15,0.0); zm=np.nan_to_num(zmed)
    h=zm.copy(); wr=pw.copy(); wa=wa0.copy(); isb=bf>0.6; wb0=np.where(isb,np.minimum(cnt,60)/60.0*BW,0.0); wb=0*wb0
    for it in range(16):
        tb=25*np.round(h/25)
        A=sp.vstack([sp.csr_matrix((np.r_[np.sqrt(wr),-np.sqrt(wr)],(np.r_[np.arange(len(pa)),np.arange(len(pa))],np.r_[pb,pa])),shape=(len(pa),n)),
                     sp.diags(np.sqrt(wa)),sp.diags(np.sqrt(wb))]).tocsr()
        b=np.r_[np.sqrt(wr)*pr,np.sqrt(wa)*zm,np.sqrt(wb)*tb]
        h=lsqr(A,b,x0=h,atol=1e-8,btol=1e-8,iter_lim=3000)[0]
        er=(h[pb]-h[pa])-pr; ea=h-zm
        wr=pw*np.where(np.abs(er)<4,(1-(er/4)**2)**2,0.02)
        wa=wa0*np.where(np.abs(ea)<12,(1-(ea/12)**2)**2,0.0)
        eb=h-25*np.round(h/25); wb=wb0*np.where(np.abs(eb)<6,1.0,0.1)*min(1.0,it/4)
    # snap: bold -> multiple of 25 if within 7.5, else nearest 5
    L5=5*np.round(h/5); L25=25*np.round(h/25)
    lab=np.where((bf>0.6)&(np.abs(h-L25)<7.5),L25,L5)
    # thin segments landing on a multiple of 25: push to the nearer neighbour level
    thin25=(bf<0.2)&(lab%25==0); lab[thin25]=np.where(h[thin25]>=lab[thin25],lab[thin25]+5,lab[thin25]-5)
    stats=dict(n=n,pairs=len(pa),bold_on25=float(np.average(lab[bf>0.7]%25==0,weights=cnt[bf>0.7])),
               bold_on25_raw=float(np.average((5*np.round(zmed[bf>0.7]/5))%25==0,weights=cnt[bf>0.7])),
               rel_ok=float(np.average(np.abs((lab[pb]-lab[pa])-pr)<1,weights=pw)),
               anchor_dev_med=float(np.median(np.abs(lab-zm)[np.isfinite(zmed)])),
               frac_changed_5=float(np.average(np.abs(lab-zm)>5,weights=cnt)))
    if verbose: print(sid,json.dumps({k:(round(v,3) if isinstance(v,float) else v) for k,v in stats.items()}))
    np.savez_compressed(f'lab/{sid}_labels.npz',u=u,inv_x=xs,inv_y=ys,inv=inv,lab=lab,h=h,zmed=zmed,bf=bf,cnt=cnt)
    return stats
if __name__=='__main__':
    for sid in sys.argv[1:]: run(sid)
