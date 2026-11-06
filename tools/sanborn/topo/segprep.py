"""Per sheet: contour skeleton (half-res) -> segments with ground coords, LiDAR z, bold flag."""
import numpy as np, cv2, json, sys, os
from scipy import ndimage as ndi
from scipy.ndimage import map_coordinates, gaussian_filter
from final_model import Final
from geo import S, FT
DM=json.load(open('dem2m.json')); DEM=np.load('dem2m.npy',mmap_mode='r')
F=Final()
def lidar(E,N):
    r=DM['res']; c0=int((E.min()-30-DM['x0'])/r); c1=int((E.max()+30-DM['x0'])/r)+1; r0=int((DM['y1']-N.max()-30)/r); r1=int((DM['y1']-N.min()+30)/r)+1
    a=np.asarray(DEM[r0:r1,c0:c1]).astype(np.float32); bad=a==DM['nodata']; a[bad]=np.nan
    z=map_coordinates(np.nan_to_num(a/10/FT,nan=-9999),[(DM['y1']-N)/r-r0-0.5,(E-DM['x0'])/r-c0-0.5],order=1)
    z[z<-1000]=np.nan; return z
def run(sid):
    sk=cv2.imread(f'contours/{sid}_contours.png',0)>0
    # bold map: rasterise full-res ink, max-pool to half res
    B=np.load(f'boldx/{sid}.npz'); H2,W2=sk.shape
    ink=np.zeros((H2,W2),np.float32); np.maximum.at(ink,(np.clip(B['y']//2,0,H2-1),np.clip(B['x']//2,0,W2-1)),B['ink'].astype(np.float32))
    ink=ndi.maximum_filter(ink,size=3); thr=float(B['thr'])
    # segments: break at junctions
    nb=ndi.convolve(sk.astype(np.uint8),np.ones((3,3),np.uint8),mode='constant')-1
    junc=sk&(nb>=3); seg=sk&~ndi.binary_dilation(junc,np.ones((3,3)))
    lab,n=ndi.label(seg,np.ones((3,3)))
    ys,xs=np.nonzero(lab); ids=lab[ys,xs]
    keep=np.bincount(ids,minlength=n+1)[ids]>=8
    ys,xs,ids=ys[keep],xs[keep],ids[keep]
    gx,gy=F._s(sid).p2g(xs*2.0,ys*2.0); sh=S[sid]; mg=15
    inn=(gx>sh['x_w']+mg)&(gx<sh['x_e']-mg)&(gy>sh['y_s']+mg)&(gy<sh['y_n']-mg)
    ys,xs,ids=ys[inn],xs[inn],ids[inn]
    keep=np.bincount(ids,minlength=n+1)[ids]>=8; ys,xs,ids=ys[keep],xs[keep],ids[keep]
    E,N=F.p2utm(sid,xs*2.0,ys*2.0); z=lidar(E,N)
    bold=ink[ys,xs]>=thr
    np.savez_compressed(f'lab/{sid}_seg.npz',x=xs.astype(np.int16),y=ys.astype(np.int16),id=ids.astype(np.int32),E=E.astype(np.float64),N=N.astype(np.float64),z=z.astype(np.float32),bold=bold)
    return sid,len(xs),len(np.unique(ids))
if __name__=='__main__':
    from multiprocessing import Pool
    ids=sys.argv[1:] or sorted(k for k in S if not k.startswith('_'))
    with Pool(2) as p:
        for r in p.imap_unordered(run,ids): print(*r,flush=True)
