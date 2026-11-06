try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import cv2, numpy as np, json, sys, os, time, warnings
warnings.filterwarnings('ignore')
from skimage.filters import sato
from skimage.morphology import skeletonize, remove_small_objects
from multiprocessing import Pool
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
S=json.load(open('sheets/sheet_index.json'))
K=2  # work at half resolution
def run(sid):
    out=f'contours/{sid}_contours.png'
    if os.path.exists(out): return sid,'kept'
    t=time.time(); s=S[sid]
    im=cv2.imread(base+s['file']); im=cv2.resize(im,(im.shape[1]//K,im.shape[0]//K),interpolation=cv2.INTER_AREA)
    lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB).astype(np.float32); del im
    L,a=lab[...,0],lab[...,1]-128; del lab
    bga=cv2.medianBlur((a+128).astype(np.uint8),21).astype(np.float32)-128
    r=np.clip(a-bga,0,None); del bga
    black=cv2.dilate((L<110).astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
    R=sato(r,sigmas=[0.6,1.0,1.5],black_ridges=False)
    # mask outside the neatline (margins, labels)
    P=np.float32([s['corners'][k] for k in ('TL','TR','BR','BL')])/K
    frame=np.zeros(L.shape,np.uint8); cv2.fillPoly(frame,[P.astype(np.int32)],1)
    frame=cv2.erode(frame,np.ones((9,9),np.uint8)).astype(bool)
    thr=np.percentile(R[frame],90)
    m=(R>thr)&(r>2.5)&~black&frame
    m=remove_small_objects(m,20)
    # bold (index) strokes: wider than ~2.5 px at half res
    dt=cv2.distanceTransform(m.astype(np.uint8),cv2.DIST_L2,3)
    sk=skeletonize(m); sk=remove_small_objects(sk,12,connectivity=2)
    bold=sk&(dt>=1.6)
    cv2.imwrite(out,(sk*255).astype(np.uint8))
    cv2.imwrite(f'contours/{sid}_bold.png',(bold*255).astype(np.uint8))
    return sid,f'{time.time()-t:.0f}s skel {int(sk.sum())} bold {int(bold.sum())}'
if __name__=='__main__':
    ids=sys.argv[1:] or sorted(S)
    with Pool(2) as p:
        for sid,msg in p.imap_unordered(run,ids): print(sid,msg,flush=True)
