"""Export the final 1912-sheet georeference model (Coons neatline + regional field F + per-sheet shape) and provide px<->ground."""
import numpy as np, json
from geo import S, Sheet, NEAT, _curve, O, FT, loc2utm, utm2loc
from icp import basis
JF='joint_4000_100_1.npz'
def export(path='georef_1912.json'):
    Z=np.load(JF); ids=list(Z['ids']); NS=int(Z['NS']); nF=int(Z['nF']); nSh=int(Z['nSh']); DEG=int(Z['DEG'])
    out={'_meta':{'origin_lat':O[0],'origin_lon':O[1],'foot_m':FT,'grid':'1912 survey grid, feet, origin Hughes HS station, axes true north at origin; local azimuthal equidistant (WGS84 ellipsoid)',
                  'target_crs':'EPSG:26916','datum_offset_ft':0.0,
                  'model':'px -> ground: q = p + 2*(J.F(g0) + S(p/2 - (u0,v0))); grid = CoonsInverse(q); g0 = CoonsInverse(p)',
                  'F':{'X0':float(Z['X0']),'Y0':float(Z['Y0']),'SP':float(Z['SP']),'nx':int(Z['nx']),'ny':int(Z['ny']),
                       'Fx':Z['sol'][:nF].reshape(2,-1)[0].round(3).tolist(),'Fy':Z['sol'][:nF].reshape(2,-1)[1].round(3).tolist()},
                  'shape_basis':f'monomials a^i b^j, i+j in 2..{DEG}, a=(u/2-u0)/W, b=(v/2-v0)/H'}}
    for k,sid in enumerate(ids):
        d=np.load(f'cache/{sid}_pts.npz'); sh=Sheet(sid,coons=True)
        out[sid]={'file':S[sid]['file'],'x_w':S[sid]['x_w'],'x_e':S[sid]['x_e'],'y_n':S[sid]['y_n'],'y_s':S[sid]['y_s'],'corners':S[sid]['corners'],
                  'H_grid_to_px':sh.H.tolist(),'neatline_offsets_px':{e:np.round(sh.C[e][1],2).tolist() for e in sh.C},'neatline_normals':{e:sh.N[e].tolist() for e in sh.N},
                  'J':d['J'].tolist(),'u0':int(d['u0']),'v0':int(d['v0']),'W':int(d['W']),'H':int(d['H']),
                  'shape_x':Z['sol'][nF+k*nSh:nF+k*nSh+NS].tolist(),'shape_y':Z['sol'][nF+k*nSh+NS:nF+(k+1)*nSh].tolist()}
    json.dump(out,open(path,'w'))
class Final:
    def __init__(self,path='georef_1912.json'):
        M=json.load(open(path)); self.M=M; f=M['_meta']['F']
        self.F=np.array([f['Fx'],f['Fy']]); self.X0,self.Y0,self.SP,self.nx,self.ny=f['X0'],f['Y0'],f['SP'],f['nx'],f['ny']
        self.sh={}; self.lo=None
    def _s(self,sid):
        if sid not in self.sh: self.sh[sid]=Sheet(sid,coons=True)
        return self.sh[sid]
    def Fat(self,g):
        fx=(g[:,0]-self.X0)/self.SP; fy=(g[:,1]-self.Y0)/self.SP; i=np.clip(np.floor(fx).astype(int),0,self.nx-2); j=np.clip(np.floor(fy).astype(int),0,self.ny-2); tx=fx-i; ty=fy-j
        c=np.stack([j*self.nx+i,j*self.nx+i+1,(j+1)*self.nx+i,(j+1)*self.nx+i+1],1); w=np.stack([(1-tx)*(1-ty),tx*(1-ty),(1-tx)*ty,tx*ty],1)
        return (self.F[0][c]*w).sum(1),(self.F[1][c]*w).sum(1)
    def p2g(self,sid,u,v):
        u=np.asarray(u,float).ravel(); v=np.asarray(v,float).ravel(); m=self.M[sid]; sh=self._s(sid)
        g0=np.c_[sh.p2g(u,v)]; fx,fy=self.Fat(g0); J=np.array(m['J'])
        du=J[0,0]*fx+J[0,1]*fy; dv=J[1,0]*fx+J[1,1]*fy
        a=(u/2-m['u0'])/m['W']; b=(v/2-m['v0'])/m['H']; P=basis(a,b,3); lo=np.array([i+j<=1 for i in range(4) for j in range(4-i)]); P=P[:,~lo]
        du=du+P@np.array(m['shape_x']); dv=dv+P@np.array(m['shape_y'])
        return sh.p2g(u+2*du,v+2*dv)
    def g2p(self,sid,gx,gy,it=6):
        sh=self._s(sid); T=np.c_[sh.g2p(gx,gy)]; p=T.copy()
        for _ in range(it):
            g=np.c_[self.p2g(sid,p[:,0],p[:,1])]; p=p+(T-np.c_[sh.g2p(g[:,0],g[:,1])])
        return p[:,0],p[:,1]
    def p2utm(self,sid,u,v):
        gx,gy=self.p2g(sid,u,v); E,N=loc2utm.transform(gx*FT,gy*FT); return np.asarray(E),np.asarray(N)
    def utm2p(self,sid,E,N):
        e,n=utm2loc.transform(np.asarray(E,float).ravel(),np.asarray(N,float).ravel()); return self.g2p(sid,np.asarray(e)/FT,np.asarray(n)/FT)
if __name__=='__main__':
    export(); F=Final()
    u=np.array([1000.,5000,9000]); v=np.array([1000.,4000,7000])
    E,N=F.p2utm('29',u,v); print(E.round(2),N.round(2)); print(np.array(F.utm2p('29',E,N)).round(3))
