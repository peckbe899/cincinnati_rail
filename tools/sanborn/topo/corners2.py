try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import cv2, numpy as np, json, re, glob, os, sys
from PIL import Image
from multiprocessing import Pool
Image.MAX_IMAGE_PIXELS=None
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
def hits(g,side,n=160):
    H,W=g.shape; bg=np.median(g[::8,::8])
    out=[]
    for t in np.linspace(0.06,0.94,n):
        if side in('top','bottom'):
            x=int(t*W); col=g[:,max(0,x-3):x+4].mean(1)
            rng=range(int(0.01*H),int(0.45*H)) if side=='top' else range(int(0.99*H),int(0.55*H),-1)
            for y in rng:
                if col[y]<bg-55: out.append((x,y)); break
        else:
            y=int(t*H); row=g[max(0,y-3):y+4,:].mean(0)
            rng=range(int(0.01*W),int(0.45*W)) if side=='left' else range(int(0.99*W),int(0.55*W),-1)
            for x in rng:
                if row[x]<bg-55: out.append((x,y)); break
    return np.array(out,float)
def ransac_line(p,horiz,thr=3.0,it=600,rng=np.random.default_rng(0)):
    best=None
    for _ in range(it):
        i,j=rng.choice(len(p),2,replace=False); a,b=p[i],p[j]
        if horiz and abs(b[0]-a[0])<len(p): continue
        if not horiz and abs(b[1]-a[1])<len(p): continue
        d=b-a; nrm=np.array([-d[1],d[0]])/np.linalg.norm(d); dist=np.abs((p-a)@nrm)
        inl=dist<thr
        # prefer the outermost consistent line: score by inliers
        if best is None or inl.sum()>best[0]: best=(inl.sum(),inl)
    inl=best[1]; q=p[inl]
    vx,vy,x0,y0=cv2.fitLine(q.astype(np.float32),cv2.DIST_L2,0,0.01,0.01).ravel()
    return (vx,vy,x0,y0), q, inl.mean()
def X(l1,l2):
    (a,b,c,d),(e,f,g_,h)=l1,l2
    t=np.linalg.solve(np.array([[a,-e],[b,-f]]),[g_-c,h-d]); return np.array([c+a*t[0],d+b*t[0]])
def run(fn):
    sid=re.search(r'Sheet_(\d+)',fn).group(1)
    g=np.asarray(Image.open(fn).convert('L')).astype(np.float32)
    g=cv2.GaussianBlur(g,(3,3),0)
    L={};frac={};pts={}
    for s in ('top','bottom','left','right'):
        p=hits(g,s); L[s],pts[s],frac[s]=ransac_line(p,s in('top','bottom'))
    C=np.array([X(L['top'],L['left']),X(L['top'],L['right']),X(L['bottom'],L['right']),X(L['bottom'],L['left'])])
    bow={}
    for s in L:
        vx,vy,x0,y0=L[s]; q=pts[s]; nrm=np.array([-vy,vx]); dev=(q-[x0,y0])@nrm
        bow[s]=round(float(dev.max()-dev.min()),1)
    return sid,dict(file=os.path.basename(fn),size=[g.shape[1],g.shape[0]],corners=C.round(1).tolist(),inlier_frac={k:round(float(v),2) for k,v in frac.items()},inlier_spread=bow)
if __name__=='__main__':
    files=sorted(glob.glob(base+"Sheet_*.jpg"))
    with Pool(8) as p: res=dict(p.map(run,files))
    json.dump(res,open('sheets/corners2.json','w'),indent=1)
    for sid in sorted(res):
        r=res[sid]; c=np.array(r['corners'])
        w1,w2=np.linalg.norm(c[1]-c[0]),np.linalg.norm(c[2]-c[3]); h1,h2=np.linalg.norm(c[3]-c[0]),np.linalg.norm(c[2]-c[1])
        print(sid,'top %.0f bot %.0f left %.0f right %.0f ratio %.3f'%(w1,w2,h1,h2,(w1+w2)/(h1+h2)),'inl',r['inlier_frac'])
