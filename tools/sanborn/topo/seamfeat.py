"""Tangential seam test: positions where line work (streets) crosses each seam, seen from both sheets, mapped to grid by each model."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, json, sys, cv2
from scipy.ndimage import map_coordinates, gaussian_filter1d
from geo import S, Sheet
from icp import basis
from corr import CSheet
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
ids=sorted(k for k in S if not k.startswith('_'))
class Joint:
    def __init__(self,f):
        Z=np.load(f); self.Z=Z; self.sol=Z['sol']; self.nx=int(Z['nx']); self.ny=int(Z['ny']); self.SP=float(Z['SP']); self.X0=float(Z['X0']); self.Y0=float(Z['Y0'])
        self.NN=int(Z['NN']); self.NS=int(Z['NS']); self.DEG=int(Z['DEG']); self.ids=list(Z['ids']); self.nF=int(Z['nF']); self.nSh=int(Z['nSh'])
        self.lo=np.array([i+j<=1 for i in range(self.DEG+1) for j in range(self.DEG+1-i)]); self.F=self.sol[:self.nF].reshape(2,self.NN)
        self.cache={}
    def Fat(self,g):
        fx=(g[:,0]-self.X0)/self.SP; fy=(g[:,1]-self.Y0)/self.SP; i=np.clip(np.floor(fx).astype(int),0,self.nx-2); j=np.clip(np.floor(fy).astype(int),0,self.ny-2); tx=fx-i; ty=fy-j
        c=np.stack([j*self.nx+i,j*self.nx+i+1,(j+1)*self.nx+i,(j+1)*self.nx+i+1],1); w=np.stack([(1-tx)*(1-ty),tx*(1-ty),(1-tx)*ty,tx*ty],1)
        return (self.F[0][c]*w).sum(1),(self.F[1][c]*w).sum(1)
    def p2g(self,sid,u,v):
        if sid not in self.cache: self.cache[sid]=(Sheet(sid,coons=True),dict(np.load(f'cache/{sid}_pts.npz')))
        sh,d=self.cache[sid]; k=self.ids.index(sid)
        g=np.c_[sh.p2g(u,v)]; fx,fy=self.Fat(g); J=d['J']
        ph_u=u/2-d['u0']; ph_v=v/2-d['v0']
        du=J[0,0]*fx+J[0,1]*fy; dv=J[1,0]*fx+J[1,1]*fy
        if self.nSh:
            s=self.sol[self.nF+k*self.nSh:self.nF+(k+1)*self.nSh]; P=basis(ph_u/d['W'],ph_v/d['H'],self.DEG)[:,~self.lo]; du=du+P@s[:self.NS]; dv=dv+P@s[self.NS:]
        return sh.p2g(u+2*du,v+2*dv)
def models():
    M={'coons':lambda sid,u,v: Sheet(sid,coons=True).p2g(u,v),
       'lens':lambda sid,u,v: Sheet(sid,coons='lens').p2g(u,v),
       'affine':lambda sid,u,v: CSheet(sid,1).p2g(u,v)}
    for f,name in (('joint_4000_100_1.npz','F+shape'),('joint_4000_100_0.npz','F only')):
        try: J=Joint(f); M[name]=(lambda J: (lambda sid,u,v: J.p2g(sid,u,v)))(J)
        except FileNotFoundError: pass
    return M
IM={}
def gray(sid):
    if sid not in IM:
        if len(IM)>3: IM.pop(next(iter(IM)))
        IM[sid]=cv2.imread(base+S[sid]['file'],0).astype(np.float32)
    return IM[sid]
def crossings(sid,seam,inside):
    """sample along the seam line `inside` ft into sheet sid; return pixel coords of dark line crossings"""
    kind,c,t0,t1=seam; sh=Sheet(sid,coons=True); t=np.arange(t0,t1,0.5)
    gx,gy=(np.full_like(t,c+inside),t) if kind=='v' else (t,np.full_like(t,c+inside))
    u,v=sh.g2p(gx,gy); a=gray(sid); prof=map_coordinates(a,[v,u],order=1); prof=gaussian_filter1d(prof,1.0)
    bg=np.percentile(prof,80); m=[i for i in range(2,len(prof)-2) if prof[i]<=prof[i-1] and prof[i]<=prof[i+1] and prof[i]<bg-45]
    return u[m],v[m]
def offset(ta,tb):
    if len(ta)<6 or len(tb)<6: return None
    d=(tb[None,:]-ta[:,None]).ravel(); d=d[np.abs(d)<60]
    if len(d)<6: return None
    h,e=np.histogram(d,bins=60,range=(-60,60)); k=np.argmax(h); pk=(e[k]+e[k+1])/2
    sel=d[np.abs(d-pk)<3]; 
    if len(sel)<5: return None
    return float(sel.mean()),len(sel)
if __name__=='__main__':
    M=models(); res={m:[] for m in M}
    seams=[]
    for A in ids:
        for B in ids:
            a,b=S[A],S[B]
            if a['x_e']==b['x_w']:
                y0,y1=max(a['y_s'],b['y_s']),min(a['y_n'],b['y_n'])
                if y1-y0>2000: seams.append((A,B,('v',a['x_e'],y0+150,y1-150)))
            elif a['y_s']==b['y_n']:
                x0,x1=max(a['x_w'],b['x_w']),min(a['x_e'],b['x_e'])
                if x1-x0>2000: seams.append((A,B,('h',a['y_s'],x0+150,x1-150)))
    for A,B,seam in seams:
        ua,va=crossings(A,seam,-12); ub,vb=crossings(B,seam,+12)
        if len(ua)<6 or len(ub)<6: continue
        row=[]
        for m,f in M.items():
            ga=np.c_[f(A,ua,va)]; gb=np.c_[f(B,ub,vb)]
            k=1 if seam[0]=='v' else 0
            o=offset(ga[:,k],gb[:,k]); res[m].append(o); row.append(f"{m}:{'--' if o is None else '%5.1f(%d)'%o}")
        print(A,B,seam[0],' '.join(row),flush=True)
    for m in M:
        v=np.array([o[0] for o in res[m] if o is not None])
        print(f'{m:8s} seams {len(v)}  median |offset| {np.median(np.abs(v)):.1f} ft  mean |offset| {np.mean(np.abs(v)):.1f} ft  p90 {np.percentile(np.abs(v),90):.1f} ft')
