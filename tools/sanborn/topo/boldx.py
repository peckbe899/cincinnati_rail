try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import cv2, numpy as np, json, sys, os, time, warnings; warnings.filterwarnings('ignore')
from skimage.morphology import skeletonize, remove_small_objects
from skimage.filters import threshold_otsu
from scipy import ndimage as ndi
from multiprocessing import Pool
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
S=json.load(open('sheets/sheet_index.json'))
T=2048; OV=48
def tile(c):
    lab=cv2.cvtColor(c,cv2.COLOR_BGR2LAB); L=lab[...,0].astype(np.float32); a=lab[...,1]
    bga=cv2.medianBlur(a,31).astype(np.float32); r=np.clip(a.astype(np.float32)-bga,0,None)
    black=cv2.dilate((L<100).astype(np.uint8),np.ones((7,7),np.uint8)).astype(bool)
    m=(r>6)&~black; m=remove_small_objects(m,40)
    sk=skeletonize(m); sk=remove_small_objects(sk,20,connectivity=2)
    ink=cv2.boxFilter(r,-1,(7,7),normalize=False)/7.0
    nb=ndi.convolve(sk.astype(np.uint8),np.ones((3,3),np.uint8),mode='constant')-1
    seg=sk&(nb<=2); lab_,n=ndi.label(seg,np.ones((3,3)))
    if n==0: return sk,np.zeros(sk.shape,np.float32)
    idx=np.arange(1,n+1); med=ndi.median(ink,lab_,idx); size=ndi.sum(seg,lab_,idx)
    M=np.zeros(n+1,np.float32); M[1:]=np.where(size>=15,med,0)
    return sk,M[lab_]
def run(sid):
    out=f'boldx/{sid}.npz'
    if os.path.exists(out): return sid,'kept'
    t0=time.time(); s=S[sid]; im=cv2.imread(base+s['file'])
    P=np.float32([s['corners'][k] for k in ('TL','TR','BR','BL')])
    frame=np.zeros(im.shape[:2],np.uint8); cv2.fillPoly(frame,[P.astype(np.int32)],1)
    frame=cv2.erode(frame,np.ones((25,25),np.uint8)).astype(bool)
    H,W=im.shape[:2]; SK=np.zeros((H,W),bool); V=np.zeros((H,W),np.float32)
    for y in range(0,H,T):
        for x in range(0,W,T):
            ya,xa=max(0,y-OV),max(0,x-OV); yb,xb=min(H,y+T+OV),min(W,x+T+OV)
            sk,v=tile(im[ya:yb,xa:xb])
            SK[y:min(H,y+T),x:min(W,x+T)]=sk[y-ya:y-ya+min(T,H-y),x-xa:x-xa+min(T,W-x)]
            V[y:min(H,y+T),x:min(W,x+T)]=v[y-ya:y-ya+min(T,H-y),x-xa:x-xa+min(T,W-x)]
    del im
    SK&=frame; V[~SK]=0
    vals=V[V>0]; thr=float(threshold_otsu(vals)) if len(vals)>1000 else 57.0
    ys,xs=np.where(SK); vv=V[ys,xs]
    np.savez_compressed(out,y=ys.astype(np.int16),x=xs.astype(np.int16),ink=vv.astype(np.float16),thr=thr)
    return sid,f'{time.time()-t0:.0f}s skel {len(ys)} thr {thr:.1f} bold {(vv>=thr).sum()}'
if __name__=='__main__':
    ids=sys.argv[1:] or sorted(k for k in S if not k.startswith('_'))
    with Pool(2) as p:
        for sid,msg in p.imap_unordered(run,ids): print(sid,msg,flush=True)
