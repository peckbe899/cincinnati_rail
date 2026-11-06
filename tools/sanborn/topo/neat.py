try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, cv2, json, sys
from multiprocessing import Pool
from scipy.ndimage import map_coordinates, median_filter
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
S=json.load(open('sheets/sheet_index.json'))
NS=240; HALF=36; ALONG=7
def trace(a,p0,p1,out):
    p0=np.array(p0,float);p1=np.array(p1,float);L=np.linalg.norm(p1-p0);d=(p1-p0)/L;n=np.array(out,float)
    n=n-d*np.dot(n,d); n/=np.linalg.norm(n)
    ts=np.linspace(0.015,0.985,NS); ss=np.arange(-HALF,HALF+1,0.5); ks=np.arange(-(ALONG//2),ALONG//2+1)
    C=p0[None]+(p1-p0)[None]*ts[:,None]                       # NS x 2
    P=C[:,None,None,:]+ss[None,:,None,None]*n+ks[None,None,:,None]*d   # NS x nS x nk x 2
    v=map_coordinates(a,[P[...,1].ravel(),P[...,0].ravel()],order=1).reshape(P.shape[:3]).mean(2)
    cand=[]
    for i in range(NS):
        pr=v[i]; bg=np.percentile(pr,75)
        mins=[j for j in range(2,len(pr)-2) if pr[j]<=pr[j-1] and pr[j]<=pr[j+1] and pr[j]<bg-30]
        cand.append([(ss[j],bg-pr[j]) for j in mins])
    # track from each corner inward (s=0 at the corners by construction), gate 3 px per step
    def track(order):
        out=np.full(NS,np.nan); ref=0.0; miss=0
        for i in order:
            cs=cand[i]; g=3.0+min(miss,10)*0.5
            if cs:
                j=np.argmin([abs(c[0]-ref) for c in cs])
                if abs(cs[j][0]-ref)<=g: out[i]=cs[j][0]; ref=out[i]; miss=0; continue
            miss+=1
        return out
    A=track(range(NS)); B=track(range(NS-1,-1,-1))
    sel=np.where(np.isnan(A),B,np.where(np.isnan(B),A,np.where(np.abs(A-B)<1.5,(A+B)/2,np.nan)))
    ok=~np.isnan(sel)
    return ts,sel,int(ok.sum())
def run(sid):
    s=S[sid]; a=cv2.imread(base+s['file'],0).astype(np.float32)
    c=s['corners']
    E={'top':(c['TL'],c['TR'],(0,-1)),'bottom':(c['BL'],c['BR'],(0,1)),'left':(c['TL'],c['BL'],(-1,0)),'right':(c['TR'],c['BR'],(1,0))}
    res={}
    for k,(p0,p1,o) in E.items():
        ts,sel,n=trace(a,p0,p1,o)
        res[k]={'t':ts.round(4).tolist(),'s':[None if np.isnan(x) else float(x) for x in sel],'n':n}
    return sid,res
if __name__=='__main__':
    ids=sys.argv[1:] or sorted(k for k in S if not k.startswith('_'))
    out={}
    with Pool(2) as p:
        for sid,res in p.imap_unordered(run,ids):
            out[sid]=res
            summ={k:(v['n'],round(np.nanmin(np.array(v['s'],float)),1) if v['n'] else None,round(np.nanmax(np.array(v['s'],float)),1) if v['n'] else None) for k,v in res.items()}
            print(sid,summ,flush=True)
    json.dump(out,open('neat_raw.json' if len(sys.argv)==1 else 'neat_test.json','w'))
