"""Canon interstate earthworks for map 3 (new-build sections of Ben's four alignments).
Design assumptions (mine): 5% max grade, vertical curves R>=6000 m, 40 m formation, 1:2 cut/fill slopes,
bridge where fill >12 m or over the river, tunnel where cut >30 m, Price Hill trench 7 m deep with vertical walls (tracker 4B).
Profile = L1 fit to ground under grade/curvature limits (LP). Existing freeways the alignment follows are not carved;
the profile is pinned to them near the ends of each new section."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, json, sys
from pyproj import Transformer
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree
from scipy.optimize import linprog
from scipy import sparse
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
B=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/OSM/")
DM=json.load(open('dem2m.json')); X0=DM['x0']; Y1=DM['y1']; R=DM['res']; H=DM['h']; W_=DM['w']
X1=X0+W_*R; Y0=Y1-H*R
T=Transformer.from_crs('EPSG:4326','EPSG:26916',always_xy=True)
D0=np.load('dem2m.npy'); D=D0.copy()
DS=10.0; HALF=20.0; SLOPE=0.5; GMAX=0.05; RV=6000.0; BR=12.0; TU=30.0; TR_DEPTH=7.0
def g_at(x,y,arr):
    c=(np.asarray(x)-X0)/R-0.5; r=(Y1-np.asarray(y))/R-0.5
    return map_coordinates(arr,[r,c],order=1,mode='nearest')/10.0
roads=json.load(open(B+'roads.geojson'))['features']
def ul(f): a=np.array(f['geometry']['coordinates']); e,n=T.transform(a[:,0],a[:,1]); return LineString(np.c_[e,n])
MT=[ul(f) for f in roads if f['properties']['highway'] in ('motorway','trunk','motorway_link','trunk_link')]
PR=[ul(f) for f in roads if f['properties']['highway']=='primary']
tMT=STRtree(MT); tPR=STRtree(PR)
wt=json.load(open(B+'water.geojson'))['features']
ohio=[ul(f) for f in wt if f['properties'].get('name')=='Ohio River' and f['properties'].get('waterway')=='river'][0]
def near(tree,geoms,p,tol=45.0):
    idx=tree.query(p.buffer(tol)); return len(idx)>0 and min(p.distance(geoms[i]) for i in idx)<tol
def runs(lab):
    out=[]; s=0
    for i in range(1,len(lab)+1):
        if i==len(lab) or lab[i]!=lab[s]: out.append([lab[s],s,i]); s=i
    return out
def clean(lab,minlen):
    lab=list(lab)
    for _ in range(3):
        rr=runs(lab)
        for k,(v,a,b) in enumerate(rr):
            if 0<k<len(rr)-1 and (b-a)*DS<minlen.get(v,0) and rr[k-1][0]==rr[k+1][0]:
                for i in range(a,b): lab[i]=rr[k-1][0]
    return lab
def profile(g,w,target,wf=None,zmin=None):
    n=len(g); I=sparse.identity(n,format='csr')
    # vars: z, tp, tm ; z - tp + tm = target
    Aeq=sparse.hstack([I,-I,I]).tocsr()
    d1=sparse.diags([-1,1],[0,1],shape=(n-1,n)); d2=sparse.diags([1,-2,1],[0,1,2],shape=(n-2,n))
    Z1=sparse.csr_matrix((n-1,2*n)); Z2=sparse.csr_matrix((n-2,2*n))
    Aub=sparse.vstack([sparse.hstack([d1,Z1]),sparse.hstack([-d1,Z1]),sparse.hstack([d2,Z2]),sparse.hstack([-d2,Z2])]).tocsr()
    bub=np.r_[np.full(2*(n-1),GMAX*DS),np.full(2*(n-2),DS*DS/RV)]
    wf=w if wf is None else wf
    c=np.r_[np.zeros(n),wf,w]
    zb=[(None,None)]*n if zmin is None else [(None if not np.isfinite(v) else float(v),None) for v in zmin]
    bounds=zb+[(0,None)]*(2*n)
    r=linprog(c,A_ub=Aub,b_ub=bub,A_eq=Aeq,b_eq=target,bounds=bounds,method='highs')
    assert r.status==0,r.message
    return r.x[:n]
NI=json.load(open('../kmz_ni/new_interstates.json'))
TRENCH={'I-75 Alignment':(39.085,39.122,-84.620,-84.540)}   # West + East Price Hill (tracker 4B)
out={}; changed=np.zeros(D.shape,bool)
for nm,pts in NI.items():
    a=np.array(pts); e,n=T.transform(a[:,0],a[:,1]); L=LineString(np.c_[e,n])
    s=np.arange(0,L.length,DS); P=np.array([L.interpolate(x).coords[0] for x in s])
    ins=(P[:,0]>X0+300)&(P[:,0]<X1-300)&(P[:,1]>Y0+300)&(P[:,1]<Y1-300)
    if ins.sum()<50: continue
    i0,i1=np.nonzero(ins)[0][[0,-1]]; s=s[i0:i1+1]; P=P[i0:i1+1]; ins=ins[i0:i1+1]
    t=np.gradient(P,axis=0); t/=np.linalg.norm(t,axis=1)[:,None]; nrm=np.c_[-t[:,1],t[:,0]]
    offs=np.arange(-HALF,HALF+0.1,4.0)
    gx=P[:,0][:,None]+nrm[:,0][:,None]*offs; gy=P[:,1][:,None]+nrm[:,1][:,None]*offs
    gm=np.median(g_at(gx.ravel(),gy.ravel(),D0).reshape(gx.shape),axis=1); gc=g_at(P[:,0],P[:,1],D0)
    lab=['mt' if near(tMT,MT,Point(p)) else ('pr' if near(tPR,PR,Point(p)) else 'new') for p in P]
    lab=clean(lab,{'new':300,'pr':300,'mt':200})
    lab=np.array(lab); carve=(lab!='mt')&ins
    lon,lat=T.transform(P[:,0],P[:,1],direction='INVERSE'); lon=np.asarray(lon); lat=np.asarray(lat)
    river=np.array([Point(p).distance(ohio)<450 for p in P])&(gm<146)
    trench=np.zeros(len(P),bool)
    if nm in TRENCH:
        la0,la1,lo0,lo1=TRENCH[nm]; trench=carve&(lat>la0)&(lat<la1)&(lon>lo0)&(lon<lo1)
    # weights
    idx=np.arange(len(P)); cidx=idx[carve]
    dist_to_carve=np.min(np.abs(idx[:,None]-cidx[None,:]),axis=1)*DS if len(cidx) else np.full(len(P),1e9)
    w=np.where(carve,1.0,np.where(dist_to_carve<400,30.0,0.0)); w[river]=0.0; w[~ins]=0.0
    target=gm.copy(); target[trench]=gm[trench]-TR_DEPTH; w[trench]=3.0
    # Ohio navigation clearance: Brent Spence companion bridge, 81.2 ft over normal pool 453.6 ft (USCG PN 921-24)
    # => low member 534.8 ft = 163.0 m; deck assumed 4 m above low member
    zmin=np.where(river,163.0+4.0,-np.inf)
    # edge trim: no carving within 1.5 km (along the line) of where it leaves the DEM extent
    for v,a0,b0 in runs(list(ins)):
        if v: carve[a0:min(b0,a0+150)]=False; carve[max(a0,b0-150):b0]=False
    w=np.where(carve,1.0,np.where(dist_to_carve<400,30.0,0.0)); w[river]=0.0; w[~ins]=0.0; w[trench]=3.0
    wf=w.copy(); wf[trench]=20.0; w[trench]=1.0   # trench: stay at least 7 m under ground wherever grades allow
    for it in range(4):   # once fill passes the bridge threshold, height is nearly free (a bridge costs length, not height)
        z=profile(gm,w,target,wf,zmin)
        br=(z-gc>BR)&carve; wf=np.where(br,0.02*w,np.where(trench,20.0,w))
    fill=z-gc
    typ=np.where(~carve,'existing',np.where(river|(fill>BR),'bridge',np.where(fill<-TU,'tunnel',np.where(trench,'trench','grade'))))
    typ=np.array(clean(list(typ),{'bridge':60,'tunnel':60,'grade':60,'trench':60}))
    # carve on the 2 m grid
    sel=carve
    if sel.any():
        # dense centerline, 2 m
        sd=np.arange(s[0],s[-1],2.0); Pd=np.array([L.interpolate(x).coords[0] for x in sd])
        k=np.clip(np.round((sd-s[0])/DS).astype(int),0,len(s)-1)
        zd=np.interp(sd,s,z); td=typ[k]
        kt=cKDTree(Pd)
        BUF=HALF+60.0
        for ch in range(0,len(Pd),1000):
            m=(td[ch:ch+1000]!='existing')
            if not m.any(): continue
            Q=Pd[ch:ch+1000][m]
            c0=int((Q[:,0].min()-BUF-X0)/R); c1=int((Q[:,0].max()+BUF-X0)/R)+1
            r0=int((Y1-Q[:,1].max()-BUF)/R); r1=int((Y1-Q[:,1].min()+BUF)/R)+1
            c0=max(c0,0); r0=max(r0,0); c1=min(c1,W_); r1=min(r1,H)
            if c1<=c0 or r1<=r0: continue
            cc,rr=np.meshgrid(np.arange(c0,c1),np.arange(r0,r1))
            X=X0+(cc+0.5)*R; Y=Y1-(rr+0.5)*R
            dd,j=kt.query(np.c_[X.ravel(),Y.ravel()],distance_upper_bound=BUF)
            ok=np.isfinite(dd); jj=np.where(ok,j,0)
            ok&=(jj>=ch)&(jj<ch+1000)&(td[jj]!='existing')
            dd=dd.reshape(X.shape); ok=ok.reshape(X.shape); jj=jj.reshape(X.shape)
            g=D[r0:r1,c0:c1].astype(np.float32)/10
            zr=zd[jj]; tt=td[jj]; ex=np.maximum(0,dd-HALF)
            lo=zr-ex*SLOPE   # 1:2 => 0.5 m rise per m out
            hi=zr+ex*SLOPE
            hi=np.where((tt=='trench')&(dd>HALF),np.inf,hi)
            new=np.clip(g,lo,hi)
            new=np.where(tt=='bridge',np.minimum(g,hi),new)
            new=np.where(tt=='tunnel',np.maximum(g,lo),new)
            new=np.where(g<146,g,new)   # never touch the river surface
            upd=ok&(np.abs(new-g)>0.05)
            blk=D[r0:r1,c0:c1]; blk[upd]=np.round(new[upd]*10).astype(np.int16); changed[r0:r1,c0:c1]|=upd
    out[nm]={'s':s.tolist(),'lon':lon.tolist(),'lat':lat.tolist(),'ground':np.round(gm,2).tolist(),'ground_ctr':np.round(gc,2).tolist(),
             'z':np.round(z,2).tolist(),'type':typ.tolist(),'follow':lab.tolist()}
    rr=runs(list(typ))
    print('==',nm,'stations',len(s),'carved km %.1f'%(carve.sum()*DS/1000))
    for v,a0,b0 in rr:
        if v=='existing' or (b0-a0)*DS<150: continue
        seg=slice(a0,b0)
        print('  %-7s %5.2f-%5.2f km  start %.4f,%.4f  max cut %4.1f  max fill %4.1f  grade %.1f%%'%(v,s[a0]/1000,s[b0-1]/1000,lat[a0],lon[a0],
              max(0,(gc[seg]-z[seg]).max()),max(0,(z[seg]-gc[seg]).max()),100*np.abs(np.diff(z[seg])).max()/DS if b0-a0>1 else 0))
json.dump(out,open('canon_hw_profiles.json','w'))
rows,cols=np.nonzero(changed)
np.savez_compressed('canon_hw_carve.npz',rows=rows.astype(np.int32),cols=cols.astype(np.int32),old=D0[rows,cols],new=D[rows,cols])
print('changed px',changed.sum(),'area km2 %.2f'%(changed.sum()*R*R/1e6))
