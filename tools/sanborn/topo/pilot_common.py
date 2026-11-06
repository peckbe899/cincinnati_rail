"""Shared pieces for the 1912-LiDAR mixing trials (pilot windows)."""
import numpy as np, json, cv2
import scipy.sparse as sp, pyamg
from scipy import ndimage as ndi
DM=json.load(open('dem2m.json'))
def load(name):
    s=np.load(f'pilot_{name}_S1912.npz'); X0=float(s['X0']); Y1=float(s['Y1'])
    DEM=np.load('dem2m.npy',mmap_mode='r'); c0=int((X0-DM['x0'])/2); r0=int((DM['y1']-Y1)/2); n=s['S'].shape[0]*2
    L=np.asarray(DEM[r0:r0+n,c0:c0+n]).astype(np.float32)/10
    up=lambda a: cv2.resize(a.astype(np.float32),(n,n),interpolation=cv2.INTER_CUBIC)
    S=up(s['S']); lo=up(s['lo']); hi=up(s['hi'])
    c4=ndi.binary_fill_holes(ndi.binary_closing(s['cov'],iterations=4))   # flat ground between sparse contours is still surveyed
    cov=cv2.resize(c4.astype(np.uint8),(n,n),interpolation=cv2.INTER_NEAREST).astype(bool)
    ZA=np.load('Z_all.npy'); zr0=int((DM['y1']-Y1)/4); zc0=int((X0-DM['x0'])/4)
    Z=cv2.resize(ZA[zr0:zr0+n//2,zc0:zc0+n//2].astype(np.uint8),(n,n),interpolation=cv2.INTER_NEAREST).astype(bool)
    return dict(L=L,S=S,lo=lo,hi=hi,cov=cov,Z=Z,X0=X0,Y1=Y1,n=n)
def lap_matrix(n):
    idx=np.arange(n*n).reshape(n,n); rr=[];cc=[]
    for a,b in ((idx[:,:-1],idx[:,1:]),(idx[:-1,:],idx[1:,:])): rr.append(a.ravel()); cc.append(b.ravel())
    rr=np.concatenate(rr); cc=np.concatenate(cc); Adj=sp.csr_matrix((np.ones(len(rr)),(rr,cc)),shape=(n*n,n*n)); Adj=Adj+Adj.T
    return (sp.diags(np.asarray(Adj.sum(1)).ravel())-Adj).tocsr()
def fill_masked(val,mask,order=2):
    """Replace val inside mask by a smooth membrane (order 1) or thin plate (order 2) that matches val outside."""
    n=val.shape[0]; keep=~mask
    Lp=lap_matrix(n); A=Lp if order==1 else (Lp.T@Lp)
    w=keep.ravel().astype(float)*1e3
    M=(A+sp.diags(w+1e-9)).tocsr(); b=w*np.where(keep,val,0).ravel()
    ml=pyamg.smoothed_aggregation_solver(M,max_coarse=500)
    x=ml.solve(b,x0=np.where(keep,val,np.median(val[keep])).ravel(),tol=1e-8,maxiter=300,accel='cg').reshape(n,n)
    return np.where(mask,x,val)
def median26(L): return ndi.median_filter(L,size=13)
def hs(z,res=2.0,ex=2.0):
    gy,gx=np.gradient(z*ex,res); sl=np.arctan(np.hypot(gx,gy)); asp=np.arctan2(-gx,gy); a=np.radians(315); b=np.radians(45)
    return np.clip((np.sin(b)*np.cos(sl)+np.cos(b)*np.sin(sl)*np.cos(a-asp))*255,0,255).astype(np.uint8)
def panel(im,label,size=900):
    im=cv2.resize(im,(size,size),interpolation=cv2.INTER_AREA)
    if im.ndim==2: im=cv2.cvtColor(im,cv2.COLOR_GRAY2BGR)
    cv2.rectangle(im,(0,0),(size,34),(255,255,255),-1); cv2.putText(im,label,(8,25),cv2.FONT_HERSHEY_SIMPLEX,0.75,(0,0,0),2); return im
def outline(im,mask,col=(0,0,255),size=900):
    m=cv2.resize(mask.astype(np.uint8),(size,size),interpolation=cv2.INTER_NEAREST)
    cs,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE); out=im.copy(); cv2.drawContours(out,cs,-1,col,1); return out
def detect_changes(Lm,lo,hi,cov,excess=1.0,min_area=2000.0):
    import os; excess=float(os.environ.get('ZEXCESS',excess)); min_area=float(os.environ.get('ZAREA',min_area))
    """Big changes: median LiDAR outside the 1912 band by more than `excess` m, over patches of at least min_area m2."""
    out=np.maximum(Lm-hi,lo-Lm)>excess
    out=ndi.binary_opening(out,iterations=2)&cov
    lab,k=ndi.label(out); sz=ndi.sum(np.ones_like(lab),lab,np.arange(1,k+1))*4.0
    keep=np.isin(lab,np.nonzero(sz>=min_area)[0]+1)
    return ndi.binary_dilation(keep,iterations=5)      # 10 m skirt over the cut/fill shoulders
