"""Sheet <-> ground mapping: grid homography + Coons-patch neatline correction (+ optional residual field)."""
import numpy as np, cv2, json
from pyproj import Transformer
S=json.load(open('sheets/sheet_index.json'))
NEAT=json.load(open('neat_raw.json'))
try: LENS=json.load(open('lens.json'))
except Exception: LENS={}
O=(39.128686,-84.521455); FT=1200/3937
AEQD=f"+proj=aeqd +lat_0={O[0]} +lon_0={O[1]} +units=m +datum=WGS84"
loc2utm=Transformer.from_crs(AEQD,"EPSG:26916",always_xy=True)
utm2loc=Transformer.from_crs("EPSG:26916",AEQD,always_xy=True)
def _curve(v):
    t=np.array(v['t']); s=np.array([np.nan if x is None else x for x in v['s']],float); ok=~np.isnan(s)
    t=np.r_[0,t[ok],1]; s=np.r_[0,s[ok],0]
    # robust smooth: running median 9 then mean 9 on a dense resample
    T=np.linspace(0,1,401); f=np.interp(T,t,s)
    from scipy.ndimage import median_filter, uniform_filter1d
    f=uniform_filter1d(median_filter(f,9,mode='nearest'),9,mode='nearest'); f[0]=f[-1]=0
    return T,f
class Sheet:
    def __init__(self,sid,coons=True,resid=None):
        s=S[sid]; self.sid=sid; self.s=s; self.lens=None
        if coons=='lens':
            L=LENS[sid]; self.lens=(np.array(L['H']),np.array(L['c']),np.array(L['k'])); coons=False
        G=np.float32([[s['x_w'],s['y_n']],[s['x_e'],s['y_n']],[s['x_w'],s['y_s']],[s['x_e'],s['y_s']]])
        P=np.float32([s['corners'][k] for k in ('TL','TR','BL','BR')])
        self.H=cv2.getPerspectiveTransform(G,P).astype(np.float64); self.Hi=np.linalg.inv(self.H)
        self.coons=coons; self.resid=resid
        c={k:np.array(s['corners'][k],float) for k in ('TL','TR','BL','BR')}
        def nrm(p0,p1,out):
            d=(p1-p0)/np.linalg.norm(p1-p0); n=np.array(out,float); n=n-d*np.dot(n,d); return n/np.linalg.norm(n)
        self.N={'top':nrm(c['TL'],c['TR'],(0,-1)),'bottom':nrm(c['BL'],c['BR'],(0,1)),
                'left':nrm(c['TL'],c['BL'],(-1,0)),'right':nrm(c['TR'],c['BR'],(1,0))}
        self.C={k:_curve(NEAT[sid][k]) for k in self.N}
    def st(self,gx,gy):
        s=self.s; return (gx-s['x_w'])/(s['x_e']-s['x_w']),(s['y_n']-gy)/(s['y_n']-s['y_s'])
    def disp(self,gx,gy):
        a,b=self.st(gx,gy); a=np.clip(a,0,1); b=np.clip(b,0,1)
        f=lambda k,x: np.interp(x,*self.C[k])[:,None]*self.N[k][None]
        D=(1-b)[:,None]*f('top',a)+b[:,None]*f('bottom',a)+(1-a)[:,None]*f('left',b)+a[:,None]*f('right',b)
        return D
    def g2p(self,gx,gy):
        gx=np.asarray(gx,float).ravel(); gy=np.asarray(gy,float).ravel()
        if self.lens is not None or self.resid is not None:
            # Newton-free fixed point: start from homography, correct by forward residual
            T=cv2.perspectiveTransform(np.c_[gx,gy][None],self.H)[0]; p=T.copy()
            for _ in range(10):
                g=np.c_[self.p2g(p[:,0],p[:,1])]
                p=p+(T-cv2.perspectiveTransform(g[None],self.H)[0])
            return p[:,0],p[:,1]
        p=cv2.perspectiveTransform(np.c_[gx,gy][None],self.H)[0]
        if self.coons: p=p+self.disp(gx,gy)
        return p[:,0],p[:,1]
    def _und(self,p):
        Hm,c,k=self.lens; F=5000.0
        x=(p[:,0]-c[0])/F; y=(p[:,1]-c[1])/F; r2=x*x+y*y; k1,k2,p1,p2=k; rad=1+k1*r2+k2*r2*r2
        return np.c_[(x*rad+2*p1*x*y+p2*(r2+2*x*x))*F+c[0],(y*rad+p1*(r2+2*y*y)+2*p2*x*y)*F+c[1]]
    def p2g(self,u,v):
        u=np.asarray(u,float).ravel(); v=np.asarray(v,float).ravel()
        if len(u)==0: return u.copy(),v.copy()
        if self.resid is not None:
            a,b=self.st(*self._p2g0(u,v)); D=self.resid(a,b); u=u+D[:,0]; v=v+D[:,1]
        return self._p2g0(u,v)
    def _p2g0(self,u,v):
        if self.lens is not None:
            g=cv2.perspectiveTransform(self._und(np.c_[u,v])[None],self.lens[0])[0]; return g[:,0],g[:,1]
        g=cv2.perspectiveTransform(np.c_[u,v][None],self.Hi)[0]
        if self.coons:
            for _ in range(4):
                D=self.disp(g[:,0],g[:,1]); g=cv2.perspectiveTransform(np.c_[u-D[:,0],v-D[:,1]][None],self.Hi)[0]
        return g[:,0],g[:,1]
    def p2utm(self,u,v):
        gx,gy=self.p2g(u,v); E,N=loc2utm.transform(gx*FT,gy*FT); return np.asarray(E),np.asarray(N)
    def utm2p(self,E,N):
        e,n=utm2loc.transform(np.asarray(E,float).ravel(),np.asarray(N,float).ravel()); return self.g2p(np.asarray(e)/FT,np.asarray(n)/FT)
