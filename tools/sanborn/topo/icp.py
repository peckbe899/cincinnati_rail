"""Point-to-line ICP: 1912 index (25 ft) contours vs LiDAR 25-ft iso-lines, smooth polynomial residual field per sheet."""
import numpy as np, cv2, json, sys, time, pickle
from scipy.ndimage import map_coordinates, gaussian_filter, distance_transform_edt
from geo import Sheet, S, FT
DM=json.load(open('dem2m.json')); DEM=np.load('dem2m.npy',mmap_mode='r')
HP=2.0*1200/3937*3.2808399  # placeholder (unused)
def sheet_field(sh,step=16):
    """z (ft) and slope on the half-res pixel lattice covering the sheet frame"""
    c=np.array([S[sh.sid]['corners'][k] for k in ('TL','TR','BL','BR')],float)/2
    u0,v0=np.floor(c.min(0)).astype(int); u1,v1=np.ceil(c.max(0)).astype(int)
    W,H=u1-u0,v1-v0
    cu=np.arange(0,W+step,step); cv=np.arange(0,H+step,step)
    UU,VV=np.meshgrid(cu+u0,cv+v0)
    E,N=sh.p2utm(UU.ravel()*2,VV.ravel()*2); E=E.reshape(UU.shape); N=N.reshape(UU.shape)
    r=DM['res']; c0=int((E.min()-60-DM['x0'])/r); c1=int((E.max()+60-DM['x0'])/r)+1
    r0=int((DM['y1']-N.max()-60)/r); r1=int((DM['y1']-N.min()+60)/r)+1
    a=np.asarray(DEM[max(r0,0):r1,max(c0,0):c1]).astype(np.float32)
    pad=((max(0,-r0),0),(max(0,-c0),0)); a=np.pad(a,pad,constant_values=DM['nodata'])
    bad=a==DM['nodata']; a[bad]=np.nan; fill=np.nanmean(a) if (~bad).any() else 0
    a=np.where(bad,fill,a); a=gaussian_filter(a/10/FT,1.0)
    R=(DM['y1']-N)/r-r0-0.5; C=(E-DM['x0'])/r-c0-0.5
    out_z=np.empty((H,W),np.float32); out_bad=np.empty((H,W),bool)
    badf=gaussian_filter(bad.astype(np.float32),1.0)
    for y in range(0,H,512):
        yy,xx=np.mgrid[y:min(H,y+512),0:W].astype(np.float32)
        rr=map_coordinates(R,[yy/step,xx/step],order=1); cc=map_coordinates(C,[yy/step,xx/step],order=1)
        out_z[y:y+512]=map_coordinates(a,[rr,cc],order=1)
        out_bad[y:y+512]=map_coordinates(badf,[rr,cc],order=1)>0.05
    return out_z,out_bad,(u0,v0)
def basis(a,b,deg):
    cols=[a**i*b**j for i in range(deg+1) for j in range(deg+1-i)]
    return np.stack(cols,1)
def run(sid,deg=2,smin=0.08,tukey=12.0,iters=20,verbose=False,resid0=None,coons=True,arange=(0,1),brange=(0,1)):
    t0=time.time(); sh=Sheet(sid,coons=coons)
    z,bad,(u0,v0)=sheet_field(sh)
    H,W=z.shape; s_=S[sid]; HPft=2*(s_['x_e']-s_['x_w'])/np.hypot(*np.subtract(s_['corners']['TR'],s_['corners']['TL']))
    gy,gx=np.gradient(z,HPft); slope=np.hypot(gx,gy)
    q=np.floor(z/25.0); iso=np.zeros(z.shape,bool)
    iso[:,1:]|=q[:,1:]!=q[:,:-1]; iso[1:,:]|=q[1:,:]!=q[:-1,:]; iso&=~bad
    dist,ind=distance_transform_edt(~iso,return_indices=True); ind=ind.astype(np.int32)
    nrm=np.stack([gx,gy],0)/np.maximum(slope,1e-6)
    B=np.load(f'boldx/{sid}.npz'); k=B['ink']>=B['thr']
    px=B['x'][k].astype(np.float32)/2-u0; py=B['y'][k].astype(np.float32)/2-v0
    ii=np.clip(np.round(py).astype(int),0,H-1); jj=np.clip(np.round(px).astype(int),0,W-1)
    keep=(slope[ii,jj]>smin)&~bad[ii,jj]
    keep&=(px/W>=arange[0])&(px/W<=arange[1])&(py/H>=brange[0])&(py/H<=brange[1])
    px,py=px[keep],py[keep]
    a=px/W; b=py/H; Phi=basis(a,b,deg); m=Phi.shape[1]
    X=np.zeros(m); Y=np.zeros(m); hist=[]
    for it in range(iters):
        qx=px+Phi@X; qy=py+Phi@Y
        qi=np.clip(np.round(qy).astype(int),0,H-1); qj=np.clip(np.round(qx).astype(int),0,W-1)
        cy=ind[0,qi,qj]; cx=ind[1,qi,qj]
        nx=nrm[0,cy,cx]; ny=nrm[1,cy,cx]
        e=nx*(cx-qx)+ny*(cy-qy)
        w=np.where(np.abs(e)<tukey,(1-(e/tukey)**2)**2,0.0)
        hist.append((float(np.sqrt(np.sum(w*e*e)/np.sum(w))),float((w>0).mean())))
        t=nx*(Phi@X)+ny*(Phi@Y)+e
        A=np.hstack([nx[:,None]*Phi,ny[:,None]*Phi])
        Aw=A*w[:,None]; M=A.T@Aw+np.eye(2*m)*1e-2*w.sum()*1e-3; rhs=Aw.T@t
        sol=np.linalg.solve(M,rhs); dX,dY=sol[:m]-X,sol[m:]-Y; X,Y=sol[:m],sol[m:]
        if np.abs(np.r_[dX,dY]).max()<0.02: break
    # shift field at sheet centre and corners (half-res px -> full px)
    pts=np.array([[.5,.5],[0,0],[1,0],[0,1],[1,1]])
    P=basis(pts[:,0],pts[:,1],deg); sx=(P@X)*2; sy=(P@Y)*2
    # datum residual after alignment
    qx=px+Phi@X; qy=py+Phi@Y; qi=np.clip(np.round(qy).astype(int),0,H-1); qj=np.clip(np.round(qx).astype(int),0,W-1)
    ph=np.exp(1j*2*np.pi*z[qi,qj]/25); zres=float(np.angle(ph.mean())/2/np.pi*25); Rres=float(abs(ph.mean()))
    ph0=np.exp(1j*2*np.pi*z[np.clip(np.round(py).astype(int),0,H-1),np.clip(np.round(px).astype(int),0,W-1)]/25)
    res=dict(sid=sid,deg=deg,n=int(len(px)),X=X.tolist(),Y=Y.tolist(),W=W,H=H,u0=int(u0),v0=int(v0),
             rms0=hist[0][0],in0=hist[0][1],rms=hist[-1][0],inl=hist[-1][1],iters=len(hist),
             centre=(float(sx[0]),float(sy[0])),corners=[(float(a_),float(b_)) for a_,b_ in zip(sx[1:],sy[1:])],
             zres=zres,R=Rres,R0=float(abs(ph0.mean())),secs=time.time()-t0)
    return res
if __name__=='__main__':
    deg=int(sys.argv[1]); coons={'1':True,'0':False,'L':'lens'}[sys.argv[2]]; ids=sys.argv[3:]
    for sid in ids:
        r=run(sid,deg=deg,coons=coons); r['coons']=coons
        print(f"{sid} n{r['n']:6d} rms {r['rms0']:.2f}->{r['rms']:.2f} inl {r['in0']:.2f}->{r['inl']:.2f} it{r['iters']:2d} centre shift px ({r['centre'][0]:6.1f},{r['centre'][1]:6.1f}) R {r['R0']:.2f}->{r['R']:.2f} zres {r['zres']:5.2f} {r['secs']:.0f}s",flush=True)
        json.dump(r,open(f'boldx/icp{deg}{ {True:"c",False:"h","lens":"L"}[coons] }_{sid}.json','w'))

def edge_obs(sid,u0,v0,W,H):
    """neatline trace points (half-res, frame-relative) with outward unit normals"""
    from lens import edge_points
    s=S[sid]; c=s['corners']; rows=[]
    nrmv={'top':(0,-1),'bottom':(0,1),'left':(-1,0),'right':(1,0)}
    for k,x,y in edge_points(sid):
        rows.append((x/2-u0,y/2-v0,*nrmv[k]))
    E=np.array(rows,float); return E[:,0],E[:,1],E[:,2],E[:,3]
def run2(sid,deg=3,smin=0.08,tukey=12.0,iters=25,coons=True,edge_sigma=1.0,ridge=0.0,free_affine=True):
    """Coons base + polynomial residual; ICP point-to-line on 25-ft lines + neatline normal constraints (R.n=0)."""
    t0=time.time(); sh=Sheet(sid,coons=coons)
    z,bad,(u0,v0)=sheet_field(sh)
    H,W=z.shape; s_=S[sid]; HPft=2*(s_['x_e']-s_['x_w'])/np.hypot(*np.subtract(s_['corners']['TR'],s_['corners']['TL']))
    gy,gx=np.gradient(z,HPft); slope=np.hypot(gx,gy)
    q=np.floor(z/25.0); iso=np.zeros(z.shape,bool)
    iso[:,1:]|=q[:,1:]!=q[:,:-1]; iso[1:,:]|=q[1:,:]!=q[:-1,:]; iso&=~bad
    dist,ind=distance_transform_edt(~iso,return_indices=True); ind=ind.astype(np.int32); del dist
    nrm=np.stack([gx,gy],0)/np.maximum(slope,1e-6)
    B=np.load(f'boldx/{sid}.npz'); k=B['ink']>=B['thr']
    px=B['x'][k].astype(np.float32)/2-u0; py=B['y'][k].astype(np.float32)/2-v0
    ii=np.clip(np.round(py).astype(int),0,H-1); jj=np.clip(np.round(px).astype(int),0,W-1)
    keep=(slope[ii,jj]>smin)&~bad[ii,jj]; px,py=px[keep],py[keep]
    Phi=basis(px/W,py/H,deg); m=Phi.shape[1]
    ex,ey,enx,eny=edge_obs(sid,u0,v0,W,H); Pe=basis(ex/W,ey/H,deg)
    if free_affine:
        lo=np.array([i+j<=1 for i in range(deg+1) for j in range(deg+1-i)]); Pe=Pe.copy(); Pe[:,lo]=0
    Ae=np.hstack([enx[:,None]*Pe,eny[:,None]*Pe]); we=1.0/edge_sigma**2
    reg=np.ones(2*m)*ridge; reg[0]=reg[m]=0
    X=np.zeros(m); Y=np.zeros(m); hist=[]
    for it in range(iters):
        qx=px+Phi@X; qy=py+Phi@Y
        qi=np.clip(np.round(qy).astype(int),0,H-1); qj=np.clip(np.round(qx).astype(int),0,W-1)
        cy=ind[0,qi,qj]; cx=ind[1,qi,qj]; nx=nrm[0,cy,cx]; ny=nrm[1,cy,cx]
        e=nx*(cx-qx)+ny*(cy-qy)
        w=np.where(np.abs(e)<tukey,(1-(e/tukey)**2)**2,0.0)
        hist.append((float(np.sqrt(np.sum(w*e*e)/np.sum(w))),float((w>0).mean())))
        t=nx*(Phi@X)+ny*(Phi@Y)+e
        A=np.hstack([nx[:,None]*Phi,ny[:,None]*Phi]); Aw=A*(w/16.0)[:,None]   # ICP noise ~4 half-px
        M=A.T@Aw+we*Ae.T@Ae+np.diag(reg)+np.eye(2*m)*1e-6; rhs=Aw.T@t
        sol=np.linalg.solve(M,rhs); d=np.abs(sol-np.r_[X,Y]).max(); X,Y=sol[:m],sol[m:]
        if d<0.02: break
    qx=px+Phi@X; qy=py+Phi@Y; qi=np.clip(np.round(qy).astype(int),0,H-1); qj=np.clip(np.round(qx).astype(int),0,W-1)
    ph=np.exp(1j*2*np.pi*z[qi,qj]/25)
    ph0=np.exp(1j*2*np.pi*z[np.clip(np.round(py).astype(int),0,H-1),np.clip(np.round(px).astype(int),0,W-1)]/25)
    edge_res=Ae@np.r_[X,Y]
    return dict(sid=sid,deg=deg,n=int(len(px)),X=X.tolist(),Y=Y.tolist(),W=W,H=H,u0=int(u0),v0=int(v0),
                rms0=hist[0][0],rms=hist[-1][0],iters=len(hist),R0=float(abs(ph0.mean())),R=float(abs(ph.mean())),
                zres=float(np.angle(ph.mean())/2/np.pi*25),edge_rms=float(np.sqrt(np.mean(edge_res**2))),secs=time.time()-t0)
