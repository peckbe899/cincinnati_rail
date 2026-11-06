"""Pilot: label 1912 contours in a window.
Index (bold) contours: nearest 25 ft to LiDAR on unchanged ground, unwrapped against neighbours.
5 ft contours: counted along gradient paths from the bracketing index contours; LiDAR only breaks ties inside the allowed range."""
import numpy as np, json, sys
import scipy.sparse as sp, pyamg
from scipy import ndimage as ndi
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
from pyproj import Transformer
FT=1200/3937
WIN={'westwood':(-84.595,39.135,['33','34','40','42']),'otr':(-84.512,39.115,['18','19','29','30'])}
name=sys.argv[1]
if name not in WIN:
    _t=json.load(open('tiles.json'))[name]; WIN[name]=(_t['lon'],_t['lat'],_t['sids'])
lon,lat,sids=WIN[name]; HALF=1700.0
T=Transformer.from_crs('EPSG:4326','EPSG:26916',always_xy=True); e0,n0=T.transform(lon,lat)
X0=e0-HALF; Y1=n0+HALF; W=int(2*HALF)
DM=json.load(open('dem2m.json')); ZA=np.load('Z_all.npy')
def zone_at(E,N):
    c=((E-DM['x0'])/4).astype(int); r=((DM['y1']-N)/4).astype(int); return ZA[np.clip(r,0,ZA.shape[0]-1),np.clip(c,0,ZA.shape[1]-1)]
# ---- gather skeleton pixels
E=[];N=[];Z=[];B=[];I=[]
for sid in sids:
    d=np.load(f'lab/{sid}_seg.npz'); m=(np.abs(d['E']-e0)<HALF)&(np.abs(d['N']-n0)<HALF)
    E.append(d['E'][m]); N.append(d['N'][m]); Z.append(d['z'][m]); B.append(d['bold'][m]); I.append(int(sid)*1_000_000+d['id'][m].astype(np.int64))
E=np.concatenate(E); N=np.concatenate(N); Z=np.concatenate(Z).astype(float); B=np.concatenate(B); I=np.concatenate(I)
u,inv=np.unique(I,return_inverse=True); n=len(u); cnt=np.bincount(inv)
unch=~zone_at(E,N)&np.isfinite(Z)
bf=np.bincount(inv,weights=B)/cnt
o=np.argsort(inv,kind='stable'); b=np.r_[0,np.cumsum(cnt)]
def segmed(v,mask):
    out=np.full(n,np.nan)
    for k in range(n):
        s=o[b[k]:b[k+1]]; s=s[mask[s]]
        if len(s)>=4: out[k]=np.median(v[s])
    return out
zmed=segmed(Z,unch); zall=segmed(Z,np.isfinite(Z))
cE=np.bincount(inv,weights=E)/cnt; cN=np.bincount(inv,weights=N)/cnt
isb=(bf>0.5)&(cnt>=12)
# ---- index labels
lab=np.full(n,np.nan)
bi=np.nonzero(isb&np.isfinite(zmed))[0]
C=25*np.round(zmed[bi]/25)-zmed[bi]
tr=cKDTree(np.c_[cE[bi],cN[bi]]); nb=tr.query_ball_point(np.c_[cE[bi],cN[bi]],80.0)
for it in range(10):
    newC=C.copy()
    for i,l in enumerate(nb):
        l=[j for j in l if j!=i]
        if len(l)>=3: m=np.median(C[l]); newC[i]=C[i]+25*np.round((m-C[i])/25)
    if np.allclose(newC,C): break
    C=newC
lab[bi]=np.round((zmed[bi]+C)/25)*25
# index segments with no unchanged pixels: nearest labelled index neighbours' residual
bz=np.nonzero(isb&~np.isfinite(zmed)&np.isfinite(zall))[0]
if len(bz):
    d,j=tr.query(np.c_[cE[bz],cN[bz]],k=5); Cn=np.median(C[j],axis=1); lab[bz]=np.round((zall[bz]+Cn)/25)*25
# ---- S25 from index pixels (4 m harmonic) for path directions
R4=4.0; nx=int(W/R4); ny=nx
pix=np.isfinite(lab[inv])&isb[inv]
ix=((E[pix]-X0)/R4).astype(int); iy=((Y1-N[pix])/R4).astype(int); ok=(ix>=0)&(ix<nx)&(iy>=0)&(iy<ny)
sm=np.zeros((ny,nx)); cn=np.zeros((ny,nx)); np.add.at(sm,(iy[ok],ix[ok]),lab[inv][pix][ok]); np.add.at(cn,(iy[ok],ix[ok]),1)
idx=np.arange(nx*ny).reshape(ny,nx); rr=[];cc=[]
for a,c_ in ((idx[:,:-1],idx[:,1:]),(idx[:-1,:],idx[1:,:])): rr.append(a.ravel()); cc.append(c_.ravel())
rr=np.concatenate(rr); cc=np.concatenate(cc); Adj=sp.csr_matrix((np.ones(len(rr)),(rr,cc)),shape=(nx*ny,nx*ny)); Adj=Adj+Adj.T
Lp=sp.diags(np.asarray(Adj.sum(1)).ravel())-Adj; w=(cn>0)*10.0
A=(sp.diags(w.ravel()+1e-6)+Lp).tocsr(); rhs=(w*np.where(cn>0,sm/np.maximum(cn,1),0)).ravel()
S25=pyamg.smoothed_aggregation_solver(A).solve(rhs,tol=1e-8,maxiter=300).reshape(ny,nx)
S25s=ndi.gaussian_filter(S25,2); gy,gx=np.gradient(S25s,R4)   # gy is d/drow (southward)
# ---- id raster, 1 m
G=np.zeros((W,W),np.int64); cx=((E-X0)).astype(int); cy=((Y1-N)).astype(int); ok=(cx>=0)&(cx<W)&(cy>=0)&(cy<W)
G[cy[ok],cx[ok]]=inv[ok]+1; G=ndi.grey_dilation(G,size=(3,3))
# ---- paths from 5 ft segments
ti=np.nonzero(~isb&(cnt>=8))[0]
rng=np.random.default_rng(0); P=[];PS=[]
for k in ti:
    s=o[b[k]:b[k+1]]; pick=s[rng.choice(len(s),min(6,len(s)),replace=False)]
    P.append(np.c_[E[pick],N[pick]]); PS.append(np.full(len(pick),k))
P=np.vstack(P); PS=np.concatenate(PS); M=len(P)
def trace(sign):
    x=(P[:,0]-X0).copy(); y=(Y1-P[:,1]).copy()          # metres from window TL
    last=PS+1; ncross=np.zeros(M,int); hit=np.full(M,np.nan); alive=np.ones(M,bool)
    for st in range(600):
        g1=map_coordinates(gx,[y/R4,x/R4],order=1,mode='nearest'); g2=map_coordinates(gy,[y/R4,x/R4],order=1,mode='nearest')
        # uphill in metres-from-TL coords: +x east, +y south; elevation gradient (east, south) = (gx, gy)
        nrm=np.hypot(g1,g2); stall=nrm<1e-4; alive&=~stall
        x=np.where(alive,x+sign*g1/np.maximum(nrm,1e-9),x); y=np.where(alive,y+sign*g2/np.maximum(nrm,1e-9),y)
        out=(x<0)|(x>=W)|(y<0)|(y>=W); alive&=~out
        idg=G[np.clip(y.astype(int),0,W-1),np.clip(x.astype(int),0,W-1)]
        new=alive&(idg>0)&(idg!=last)
        if new.any():
            k=idg[new]-1; bold=isb[k]
            nn=np.nonzero(new)[0]
            hb=nn[bold]; hit[hb]=lab[k[bold]]; alive[hb]=False
            ht=nn[~bold]; ncross[ht]+=1; last[ht]=idg[ht]
        if not alive.any(): break
    return hit,ncross
dl,dc=trace(-1.0); ul,uc=trace(+1.0)
# LiDAR z at each sample start (ft), for tie-breaking only
# sample z: nearest skeleton pixel z of that segment = segment median (unchanged) else all
pz=np.where(np.isfinite(zmed[PS]),zmed[PS],zall[PS])
labs=np.full(M,np.nan); cons=np.zeros(M,bool)
both=np.isfinite(dl)&np.isfinite(ul)&(ul-dl==25)
lo=np.where(np.isfinite(dl),dc+1,1); hi=np.where(np.isfinite(ul),4-uc,4)
base=np.where(np.isfinite(dl),dl,np.where(np.isfinite(ul),ul-25,np.nan))
okr=np.isfinite(base)&(lo<=hi)
want=np.clip(np.round((pz-base)/5),1,4)
pos=np.clip(want,lo,hi)
labs[okr]=(base+5*pos)[okr]
cons=both&(lo==hi)          # count alone fixes the label
inconsistent=both&(lo>hi)
labs[inconsistent]=(dl+5*np.clip(want,1,4))[inconsistent]
# per segment majority
seglab=np.full(n,np.nan); segcons=np.zeros(n)
from collections import Counter
order=np.argsort(PS,kind='stable'); PSs=PS[order]; Ls=labs[order]; Cs=cons[order]
st=np.r_[0,np.nonzero(np.diff(PSs))[0]+1,len(PSs)]
for a,c_ in zip(st[:-1],st[1:]):
    k=PSs[a]; v=Ls[a:c_]; v=v[np.isfinite(v)]
    if len(v): m=Counter(v.tolist()).most_common(1)[0]; seglab[k]=m[0]; segcons[k]=np.mean(Cs[a:c_])
lab[ti]=seglab[ti]
# ---- report
thin=~isb&np.isfinite(lab)&np.isfinite(zmed); bo=isb&np.isfinite(lab)&np.isfinite(zmed)
rt=(lab-zmed)[thin]; rb=(lab-zmed)[bo]; wt=cnt[thin]; wb=cnt[bo]
def wq(r,w,q): o_=np.argsort(r); c=np.cumsum(w[o_])/w.sum(); return r[o_][np.searchsorted(c,q)]
print(f'{name}: segments {n}, index {isb.sum()}, 5ft {len(ti)}; samples {M}: both brackets {both.mean():.0%}, count-fixed {cons.mean():.0%}, inconsistent {inconsistent.mean():.0%}')
for nm_,r,w_ in (('index',rb,wb),('5 ft',rt,wt)):
    print(f'  {nm_}: label-LiDAR on unchanged ground (ft, length-weighted) p5 {wq(r,w_,.05):.1f} p50 {wq(r,w_,.5):.1f} p95 {wq(r,w_,.95):.1f}; |r|>4 ft {np.average(np.abs(r)>4,weights=w_):.1%}')
np.savez_compressed(f'pilot_{name}_labels.npz',E=E,N=N,inv=inv,lab=lab,isb=isb,zmed=zmed,cnt=cnt,segcons=segcons,X0=X0,Y1=Y1,W=W,S25=S25)
# ---- diagnostics: estimator agreement on count-fixed samples
s25=map_coordinates(S25,[(Y1-P[:,1])/R4,(P[:,0]-X0)/R4],order=1,mode='nearest')
def r5(v):
    L=5*np.round(v/5); m25=(L%25==0); L[m25]=np.where(v[m25]>=L[m25],L[m25]+5,L[m25]-5); return L
truth=np.where(cons,labs,np.nan); f=np.isfinite(truth)
e_s25=(r5(s25)==truth)[f].mean(); e_lid=(r5(pz)==truth)[f].mean()
both_ok=(r5(s25)==r5(pz))
print(f'  on {f.sum()} count-fixed samples: S25-rounding right {e_s25:.0%}, LiDAR-rounding right {e_lid:.0%}; S25 and LiDAR agree on {both_ok.mean():.0%} of all samples, and are right {(r5(s25)==truth)[f&both_ok].mean():.0%} of the time when they agree')
