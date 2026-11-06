"""Cache per-sheet ICP fields (nearest 25-ft iso pixel + normals) and bold points under the Coons base mapping."""
import numpy as np, json, sys, os
from scipy.ndimage import distance_transform_edt
from icp import sheet_field, edge_obs
from geo import Sheet, S
def prep(sid,smin=0.08):
    out=f'cache/{sid}_pts.npz'
    if os.path.exists(out): return sid,'kept'
    sh=Sheet(sid,coons=True); z,bad,(u0,v0)=sheet_field(sh); H,W=z.shape
    s_=S[sid]; ftpx=(s_['x_e']-s_['x_w'])/np.hypot(*np.subtract(s_['corners']['TR'],s_['corners']['TL'])); HPft=2*ftpx
    gy,gx=np.gradient(z,HPft); slope=np.hypot(gx,gy)
    q=np.floor(z/25.0); iso=np.zeros(z.shape,bool)
    iso[:,1:]|=q[:,1:]!=q[:,:-1]; iso[1:,:]|=q[1:,:]!=q[:-1,:]; iso&=~bad
    ind=distance_transform_edt(~iso,return_indices=True,return_distances=False).astype(np.int16)
    np.save(f'cache/{sid}_ind.npy',ind); del ind
    nrm=(np.stack([gx,gy],0)/np.maximum(slope,1e-6)).astype(np.float16); np.save(f'cache/{sid}_nrm.npy',nrm); del nrm
    np.save(f'cache/{sid}_z.npy',z.astype(np.float32))
    B=np.load(f'boldx/{sid}.npz'); k=B['ink']>=B['thr']
    px=B['x'][k].astype(np.float32)/2-u0; py=B['y'][k].astype(np.float32)/2-v0
    ii=np.clip(np.round(py).astype(int),0,H-1); jj=np.clip(np.round(px).astype(int),0,W-1)
    keep=(slope[ii,jj]>smin)&~bad[ii,jj]; px,py=px[keep],py[keep]
    g=np.c_[sh.p2g((px+u0)*2,(py+v0)*2)].astype(np.float32)
    # local Jacobian half-res px per grid ft (finite difference of g2p at sheet centre)
    cx=(s_['x_w']+s_['x_e'])/2; cy=(s_['y_n']+s_['y_s'])/2
    p0=np.c_[sh.g2p([cx],[cy])][0]; px_=np.c_[sh.g2p([cx+100],[cy])][0]; py_=np.c_[sh.g2p([cx],[cy+100])][0]
    J=np.c_[(px_-p0)/100,(py_-p0)/100]/2       # 2x2: columns d(p_half)/d(gx), d(p_half)/d(gy)
    ex,ey,enx,eny=edge_obs(sid,u0,v0,W,H)
    np.savez(out,px=px,py=py,g=g,J=J,u0=u0,v0=v0,W=W,H=H,ex=ex,ey=ey,enx=enx,eny=eny,slope=slope[np.clip(np.round(py).astype(int),0,H-1),np.clip(np.round(px).astype(int),0,W-1)].astype(np.float32))
    return sid,f'{len(px)} pts {W}x{H}'
if __name__=='__main__':
    from multiprocessing import Pool
    ids=sys.argv[1:] or sorted(k for k in S if not k.startswith('_'))
    with Pool(2) as p:
        for sid,msg in p.imap_unordered(prep,ids): print(sid,msg,flush=True)
