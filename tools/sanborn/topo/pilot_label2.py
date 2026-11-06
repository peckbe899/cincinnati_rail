"""Pilot labelling v2: topological propagation.
Gradient paths from many points on every contour record the ordered contours they cross. Consecutive crossings
are +1 level (5 ft) uphill. Index labels (nearest 25 ft to LiDAR on unchanged ground, unwrapped) anchor the levels;
5 ft levels are assigned by majority vote over all relations to already-labelled neighbours, iterated."""
import numpy as np, json, sys
from collections import defaultdict, Counter
from scipy import ndimage as ndi
from scipy.ndimage import map_coordinates
exec(open('pilot_label.py').read().split('# ---- paths from 5 ft segments')[0])
# direction field: smoothed LiDAR outside zones, S25 inside zones
DEM=np.load('dem2m.npy',mmap_mode='r')
c0=int((X0-DM['x0'])/2); r0=int((DM['y1']-Y1)/2); nw=int(W/2)
L2=np.asarray(DEM[r0:r0+nw,c0:c0+nw]).astype(np.float32)/10/FT
L2=ndi.gaussian_filter(L2,4)                                  # 8 m
Lz=L2[::2,::2][:ny,:nx]
zon=ZA[int((DM['y1']-Y1)/4):int((DM['y1']-Y1)/4)+ny, int((X0-DM['x0'])/4):int((X0-DM['x0'])/4)+nx]
zon=ndi.gaussian_filter(ndi.binary_dilation(zon,iterations=5).astype(float),3)
gyL,gxL=np.gradient(Lz,R4); gyS,gxS=np.gradient(S25s,R4)
nL=np.hypot(gxL,gyL)+1e-9; nS=np.hypot(gxS,gyS)+1e-9
gx=(1-zon)*gxL/nL+zon*gxS/nS; gy=(1-zon)*gyL/nL+zon*gyS/nS
# samples: up to 12 per segment, every segment with >= 8 px
rng=np.random.default_rng(1); P=[];PS=[]
for k in np.nonzero(cnt>=8)[0]:
    s=o[b[k]:b[k+1]]; pick=s[rng.choice(len(s),min(12,len(s)),replace=False)]
    P.append(np.c_[E[pick],N[pick]]); PS.append(np.full(len(pick),k))
P=np.vstack(P); PS=np.concatenate(PS); M=len(P)
def trace(sign,maxc=12,steps=700):
    x=(P[:,0]-X0).copy(); y=(Y1-P[:,1]).copy(); last=PS+1; nc=np.zeros(M,int); alive=np.ones(M,bool)
    recs=[]
    for st in range(steps):
        g1=map_coordinates(gx,[y/R4,x/R4],order=1,mode='nearest'); g2=map_coordinates(gy,[y/R4,x/R4],order=1,mode='nearest')
        nrm=np.hypot(g1,g2); alive&=nrm>0.2
        x=np.where(alive,x+sign*g1/np.maximum(nrm,1e-9),x); y=np.where(alive,y+sign*g2/np.maximum(nrm,1e-9),y)
        alive&=(x>=0)&(x<W)&(y>=0)&(y<W)
        idg=G[np.clip(y.astype(int),0,W-1),np.clip(x.astype(int),0,W-1)]
        new=alive&(idg>0)&(idg!=last)
        if new.any():
            nn=np.nonzero(new)[0]; nc[nn]+=1; recs.append(np.c_[nn,nc[nn],idg[nn]-1]); last[nn]=idg[nn]
            alive&=nc<maxc
        if not alive.any(): break
    return np.vstack(recs) if recs else np.zeros((0,3),int)
rel=defaultdict(Counter)       # rel[a][(b,delta)] : level(b)=level(a)+delta
for sign in (+1.0,-1.0):
    R=trace(sign); R=R[np.lexsort((R[:,1],R[:,0]))]
    prev_path=-1; prev_id=-1
    for p,k,i in R:
        a=PS[p] if p!=prev_path else prev_id
        if i!=a:
            d=int(sign)
            rel[a][(i,d)]+=1; rel[i][(a,-d)]+=1
        prev_path=p; prev_id=i
lev=np.full(n,np.nan); known=np.isfinite(lab)&isb; lev[known]=lab[known]/5
fixed=known.copy()
for it in range(40):
    changed=0
    for a in np.nonzero(~fixed&(cnt>=8))[0]:
        votes=Counter()
        for (bb,d),c in rel[a].items():
            if np.isfinite(lev[bb]): votes[lev[bb]-d]+=c
        if not votes: continue
        tot=sum(votes.values()); v,c=votes.most_common(1)[0]
        if v%5==0:                               # a 5 ft contour can't sit on an index level
            alt=[(vv,cc) for vv,cc in votes.most_common() if vv%5!=0]
            if not alt: continue
            v,c=alt[0]
        if c>=2 and c/tot>=0.6 and lev[a]!=v: lev[a]=v; changed+=1
    if changed==0: break
lab2=lab.copy(); thin=~isb&np.isfinite(lev); lab2[thin]=lev[thin]*5
# consistency: share of relations between two labelled segments that hold
ok=tot=0
for a,dct in rel.items():
    if not np.isfinite(lev[a]): continue
    for (bb,d),c in dct.items():
        if np.isfinite(lev[bb]): tot+=c; ok+=c*(lev[bb]-lev[a]==d)
cov=np.average(np.isfinite(lab2)&(cnt>=8),weights=cnt)
th=~isb&np.isfinite(lab2)&np.isfinite(zmed); r=(lab2-zmed)[th]
h,_=np.histogram(r,bins=np.arange(-27.5,30,5),weights=cnt[th])
print(f'{name}: labelled share of contour length {cov:.0%}; relations satisfied {ok/tot:.0%}; 5 ft residual hist {np.round(h/h.sum()*100).astype(int)}')
np.savez_compressed(f'pilot_{name}_labels2.npz',E=E,N=N,inv=inv,lab=lab2,isb=isb,zmed=zmed,cnt=cnt,X0=X0,Y1=Y1,W=W,S25=S25)
