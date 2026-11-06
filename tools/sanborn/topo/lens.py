"""Per-sheet camera model from the neatline: undistort (Brown radial+decentering about image centre) then homography to grid."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, json, cv2, sys
from scipy.optimize import least_squares
S=json.load(open('sheets/sheet_index.json')); NEAT=json.load(open('neat_raw.json'))
FSC=5000.0
def undist(p,c,k):
    x=(p[:,0]-c[0])/FSC; y=(p[:,1]-c[1])/FSC; r2=x*x+y*y
    k1,k2,p1,p2=k
    rad=1+k1*r2+k2*r2*r2
    xu=x*rad+2*p1*x*y+p2*(r2+2*x*x); yu=y*rad+p1*(r2+2*y*y)+2*p2*x*y
    return np.c_[xu*FSC+c[0],yu*FSC+c[1]]
def hom(h): return np.r_[h,1.0].reshape(3,3)
def apply(Hm,p):
    q=np.c_[p,np.ones(len(p))]@Hm.T; return q[:,:2]/q[:,2:]
def edge_points(sid):
    s=S[sid]; c=s['corners']; out=[]
    E={'top':(c['TL'],c['TR'],(0,-1)),'bottom':(c['BL'],c['BR'],(0,1)),'left':(c['TL'],c['BL'],(-1,0)),'right':(c['TR'],c['BR'],(1,0))}
    for k,(p0,p1,o) in E.items():
        p0=np.array(p0,float);p1=np.array(p1,float);d=(p1-p0)/np.linalg.norm(p1-p0);n=np.array(o,float);n=n-d*np.dot(n,d);n/=np.linalg.norm(n)
        v=NEAT[sid][k]
        for t,sv in zip(v['t'],v['s']):
            if sv is None: continue
            out.append((k,*(p0+(p1-p0)*t+n*sv)))
    return out
def fit(sid,size):
    s=S[sid]; c0=np.array([size[0]/2,size[1]/2])
    G=np.float64([[s['x_w'],s['y_n']],[s['x_e'],s['y_n']],[s['x_w'],s['y_s']],[s['x_e'],s['y_s']]])
    P=np.float64([s['corners'][k] for k in ('TL','TR','BL','BR')])
    ep=edge_points(sid); kind=np.array([e[0] for e in ep]); EP=np.array([e[1:] for e in ep])
    target={'top':s['y_n'],'bottom':s['y_s'],'left':s['x_w'],'right':s['x_e']}
    isx=np.isin(kind,['left','right']); tv=np.array([target[k] for k in kind])
    Hi0=np.linalg.inv(cv2.getPerspectiveTransform(P.astype(np.float32),G.astype(np.float32)).astype(np.float64)) # placeholder
    H0=cv2.getPerspectiveTransform(P.astype(np.float32),G.astype(np.float32)).astype(np.float64); H0/=H0[2,2]
    def resid(th):
        Hm=hom(th[:8]); k=th[8:12]; cc=c0+th[12:14]*1000
        gc=apply(Hm,undist(P,cc,k)); r1=(gc-G).ravel()*5     # corners weighted (read +-3 px)
        ge=apply(Hm,undist(EP,cc,k)); r2=np.where(isx,ge[:,0],ge[:,1])-tv
        return np.r_[r1,r2]
    th0=np.r_[H0.ravel()[:8],0,0,0,0,0,0]
    r0=resid(th0)
    sol=least_squares(resid,th0,x_scale=np.r_[np.abs(th0[:8])+1e-6,0.01,0.01,0.001,0.001,1,1],method='lm',max_nfev=4000)
    r=sol.fun
    return dict(sid=sid,H=hom(sol.x[:8]).tolist(),k=sol.x[8:12].tolist(),c=(c0+sol.x[12:14]*1000).tolist(),
                edge_rms0=float(np.sqrt(np.mean(r0[8:]**2))),edge_rms=float(np.sqrt(np.mean(r[8:]**2))),
                corner_res=float(np.abs(r[:8]/5).max()))
if __name__=='__main__':
    from PIL import Image
    base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
    out={}
    ids=sys.argv[1:] or sorted(k for k in S if not k.startswith('_'))
    for sid in ids:
        size=Image.open(base+S[sid]['file']).size
        r=fit(sid,size); out[sid]=r
        print(sid,'edge rms ft %.2f -> %.2f  corner max %.2f ft  k1 %.4f k2 %.4f p1 %.5f p2 %.5f  centre %.0f,%.0f (img %d,%d)'%(r['edge_rms0'],r['edge_rms'],r['corner_res'],*r['k'],*r['c'],size[0]//2,size[1]//2),flush=True)
    if len(sys.argv)==1: json.dump(out,open('lens.json','w'),indent=0)
