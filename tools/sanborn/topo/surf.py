"""1912 ground surface = LiDAR + C, C harmonic-interpolated from labelled-contour residuals (4 m), output 5 km tiles."""
import numpy as np, json, glob, os, sys, cv2, time
import scipy.sparse as sp, pyamg
from scipy.spatial import cKDTree
from scipy.ndimage import zoom, binary_dilation
from final_model import Final
from geo import S, FT
DM=json.load(open('dem2m.json')); DEM=np.load('dem2m.npy',mmap_mode='r')
X0,Y1=DM['x0'],DM['y1']; R4=4.0; NX=int(DM['w']*DM['res']/R4); NY=int(DM['h']*DM['res']/R4)
ids=sorted(k for k in S if not k.startswith('_'))
def observations2():
    E=[];N=[];C=[]
    for sid in ids:
        d=np.load(f'lab/{sid}_seg.npz'); L=np.load(f'lab/{sid}_labels2.npz'); inv=L['inv']; c=L['C'][inv]; ok=np.isfinite(c)
        E.append(d['E'][ok]); N.append(d['N'][ok]); C.append(c[ok])
    return np.concatenate(E),np.concatenate(N),np.concatenate(C)
def observations(thr=1.5,nb_r=40.0):
    E=[];N=[];C=[];SID=[]
    for sid in ids:
        if not os.path.exists(f'lab/{sid}_labels.npz'): continue
        d=np.load(f'lab/{sid}_seg.npz'); L=np.load(f'lab/{sid}_labels.npz')
        inv=L['inv']; lab=L['lab']; z=d['z'].astype(float); r=lab[inv]-z
        n=len(lab); cnt=np.bincount(inv,minlength=n)
        o=np.argsort(inv,kind='stable'); b=np.r_[0,np.cumsum(cnt)]
        cs=np.array([np.nanmedian(r[o[b[k]:b[k+1]]]) if cnt[k] else np.nan for k in range(n)])
        ce=np.bincount(inv,weights=d['E'],minlength=n)/np.maximum(cnt,1); cn=np.bincount(inv,weights=d['N'],minlength=n)/np.maximum(cnt,1)
        ok=np.isfinite(cs)&(cnt>0)
        # label-error cleaning against neighbours
        T=cKDTree(np.c_[ce[ok],cn[ok]]); cso=cs[ok].copy(); new=cso.copy()
        for i,nb in enumerate(T.query_ball_point(np.c_[ce[ok],cn[ok]],nb_r)):
            nb=[j for j in nb if j!=i]
            if len(nb)<4: continue
            v=cso[nb]; m=np.median(v)
            if abs(cso[i]-m)>=4 and np.median(np.abs(v-m))<2.5: new[i]=m
        cs2=cs.copy(); cs2[ok]=new
        cs2=np.sign(cs2)*np.maximum(0,np.abs(cs2)-thr)
        good=np.isfinite(cs2[inv])
        E.append(d['E'][good]); N.append(d['N'][good]); C.append(cs2[inv][good]); SID.append(np.full(good.sum(),int(sid)))
    return np.concatenate(E),np.concatenate(N),np.concatenate(C)
def coverage():
    F=Final(); M=np.zeros((NY,NX),np.uint8)
    for sid in ids:
        c=S[sid]['corners']; P=np.array([c['TL'],c['TR'],c['BR'],c['BL']],float); t=np.linspace(0,1,40)
        edge=np.vstack([P[a]+(P[b]-P[a])*t[:,None] for a,b in ((0,1),(1,2),(2,3),(3,0))])
        e,n=F.p2utm(sid,edge[:,0],edge[:,1]); poly=np.c_[(e-X0)/R4,(Y1-n)/R4].astype(np.int32)
        cv2.fillPoly(M,[poly],1)
    return M.astype(bool)
WOBS=0.05
def solve_tile(ix0,iy0,size,sumC,cntC,lam=1.0,eps=1e-4):
    s=(slice(iy0,iy0+size),slice(ix0,ix0+size)); sc=sumC[s]; cc=cntC[s]; h,w=sc.shape
    wobs=np.minimum(cc,8.0)*WOBS; obs=np.where(cc>0,sc/np.maximum(cc,1e-9),0)
    nn=h*w; idx=np.arange(nn).reshape(h,w)
    rows=[];cols=[]
    for a,b in ((idx[:,:-1],idx[:,1:]),(idx[:-1,:],idx[1:,:])): rows.append(a.ravel()); cols.append(b.ravel())
    r=np.concatenate(rows); c=np.concatenate(cols); ones=np.ones(len(r))
    Adj=sp.csr_matrix((ones,(r,c)),shape=(nn,nn)); Adj=Adj+Adj.T; deg=np.asarray(Adj.sum(1)).ravel()
    Lp=sp.diags(deg)-Adj
    A=(sp.diags(wobs.ravel()+eps)+lam*Lp).tocsr(); rhs=(wobs*obs).ravel()
    ml=pyamg.smoothed_aggregation_solver(A); x=ml.solve(rhs,tol=1e-6,maxiter=200)
    return x.reshape(h,w)
if __name__=='__main__':
    t0=time.time(); E,N,C=observations2(); print('obs',len(E),'nonzero frac %.3f'%(np.abs(C)>0).mean(),f'{time.time()-t0:.0f}s',flush=True)
    ix=((E-X0)/R4).astype(int); iy=((Y1-N)/R4).astype(int); ok=(ix>=0)&(ix<NX)&(iy>=0)&(iy<NY)
    sumC=np.zeros((NY,NX)); cntC=np.zeros((NY,NX)); np.add.at(sumC,(iy[ok],ix[ok]),C[ok]); np.add.at(cntC,(iy[ok],ix[ok]),1)
    Cg=np.zeros((NY,NX),np.float32); Wg=np.zeros((NY,NX),np.float32)
    core=1250; ov=125; ramp=np.ones(core+2*ov,np.float32); ramp[:2*ov]=np.linspace(0,1,2*ov); ramp[-2*ov:]=np.linspace(1,0,2*ov)
    for ty in range(0,NY,core):
        for tx in range(0,NX,core):
            x0=max(0,tx-ov); y0=max(0,ty-ov); x1=min(NX,tx+core+ov); y1=min(NY,ty+core+ov)
            if cntC[y0:y1,x0:x1].sum()==0: continue
            sol=solve_tile(x0,y0,max(x1-x0,y1-y0),sumC,cntC)[:y1-y0,:x1-x0]
            wy=np.interp(np.arange(y0,y1),[ty-ov,ty+ov,ty+core-ov,ty+core+ov],[0,1,1,0]); wx=np.interp(np.arange(x0,x1),[tx-ov,tx+ov,tx+core-ov,tx+core+ov],[0,1,1,0])
            wy=np.maximum(wy,1e-3); wx=np.maximum(wx,1e-3); ww=np.outer(wy,wx)
            Cg[y0:y1,x0:x1]+=sol*ww; Wg[y0:y1,x0:x1]+=ww
            print('tile',tx,ty,f'{time.time()-t0:.0f}s',flush=True)
    Cg=np.where(Wg>0,Cg/np.maximum(Wg,1e-9),0); cov=coverage()
    np.save('C4m.npy',Cg.astype(np.float32)); np.save('cov4m.npy',cov); print('done',f'{time.time()-t0:.0f}s')
