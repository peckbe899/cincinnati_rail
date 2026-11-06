import numpy as np, json, sys
from icp import basis
from geo import S, Sheet, FT
Z=np.load(sys.argv[1]); sol=Z['sol']; nx=int(Z['nx']); ny=int(Z['ny']); SP=float(Z['SP']); X0=float(Z['X0']); Y0=float(Z['Y0'])
NN=int(Z['NN']); NS=int(Z['NS']); DEG=int(Z['DEG']); ids=list(Z['ids']); nF=int(Z['nF']); nSh=int(Z['nSh'])
lo=np.array([i+j<=1 for i in range(DEG+1) for j in range(DEG+1-i)])
F=sol[:nF].reshape(2,NN)
def Fat(g):
    fx=(g[:,0]-X0)/SP; fy=(g[:,1]-Y0)/SP; i=np.clip(np.floor(fx).astype(int),0,nx-2); j=np.clip(np.floor(fy).astype(int),0,ny-2); tx=fx-i; ty=fy-j
    c=np.stack([j*nx+i,j*nx+i+1,(j+1)*nx+i,(j+1)*nx+i+1],1); w=np.stack([(1-tx)*(1-ty),tx*(1-ty),(1-tx)*ty,tx*ty],1)
    return (F[0][c]*w).sum(1),(F[1][c]*w).sum(1)
def shape(k,d,px,py):
    if nSh==0: return 0*px,0*py
    s=sol[nF+k*nSh:nF+(k+1)*nSh]; P=basis(px/d['W'],py/d['H'],DEG)[:,~lo]; return P@s[:NS],P@s[NS:]
res={}
for k,sid in enumerate(ids):
    d=dict(np.load(f'cache/{sid}_pts.npz')); z=np.load(f'cache/{sid}_z.npy',mmap_mode='r'); H,W=z.shape
    fx,fy=Fat(d['g'].astype(float)); J=d['J']; du=J[0,0]*fx+J[0,1]*fy; dv=J[1,0]*fx+J[1,1]*fy
    su,sv=shape(k,d,d['px'],d['py']); qx=d['px']+du+su; qy=d['py']+dv+sv
    def coh(x,y):
        zz=z[np.clip(np.round(y).astype(int),0,H-1),np.clip(np.round(x).astype(int),0,W-1)]; ph=np.exp(2j*np.pi*zz/25); return abs(ph.mean()),np.angle(ph.mean())/2/np.pi*25
    R0,_=coh(d['px'],d['py']); R1,zr=coh(qx,qy)
    res[sid]=dict(n=len(qx),R0=R0,R=R1,zres=zr,F=(float(np.median(fx)),float(np.median(fy))),shape=float(np.percentile(np.hypot(su,sv),90))*2)
good=[s for s in ids if res[s]['n']>20000]
print('sheets n>20k:',len(good),' mean R %.3f -> %.3f'%(np.mean([res[s]['R0'] for s in good]),np.mean([res[s]['R'] for s in good])))
w=np.array([res[s]['n']*res[s]['R']**2 for s in good]); zr=np.array([res[s]['zres'] for s in good])
print('datum residual (z mod 25 phase), weighted mean %.2f ft, median %.2f'%((w*zr).sum()/w.sum(),np.median(zr)))
if len(sys.argv)>2:
    for s in ids: r=res[s]; print(s,'n%6d R %.2f->%.2f zres %5.2f F median (%5.1f,%5.1f) ft shape p90 %.1f px'%(r['n'],r['R0'],r['R'],r['zres'],*r['F'],r['shape']))
# seam discrepancy from shape terms (F is continuous)
out=[]
for A in ids:
    for B in ids:
        a,b=S[A],S[B]
        if a['x_e']==b['x_w']:
            y0,y1=max(a['y_s'],b['y_s']),min(a['y_n'],b['y_n']); 
            if y1-y0<2000: continue
            gy=np.linspace(y0+300,y1-300,15); gx=np.full_like(gy,a['x_e'])
        elif a['y_s']==b['y_n']:
            x0,x1=max(a['x_w'],b['x_w']),min(a['x_e'],b['x_e'])
            if x1-x0<2000: continue
            gx=np.linspace(x0+300,x1-300,15); gy=np.full_like(gx,a['y_s'])
        else: continue
        dd=[]
        for sid in (A,B):
            k=ids.index(sid); d=dict(np.load(f'cache/{sid}_pts.npz')); sh=Sheet(sid,coons=True)
            u,v=sh.g2p(gx,gy); su,sv=shape(k,d,u/2-d['u0'],v/2-d['v0']); Ji=np.linalg.inv(d['J'])
            dd.append(np.c_[Ji[0,0]*su+Ji[0,1]*sv,Ji[1,0]*su+Ji[1,1]*sv]*FT)
        out.append(np.hypot(*(dd[0]-dd[1]).T).mean())
out=np.array(out); print('seams %d: shape-term discrepancy mean %.2f m p90 %.2f max %.2f'%(len(out),out.mean(),np.percentile(out,90),out.max()))
