import numpy as np, cv2, json, sys
from scipy.ndimage import map_coordinates, gaussian_filter
from geo import Sheet, S, FT
DM=json.load(open('dem2m.json')); DEM=np.load('dem2m.npy',mmap_mode='r')
def zfield(sh,u0,v0,n,step=2):
    uu,vv=np.meshgrid(u0+np.arange(n)*step,v0+np.arange(n)*step)
    E,N=sh.p2utm(uu.ravel(),vv.ravel())
    r=DM['res']; c0=int((E.min()-50-DM['x0'])/r); c1=int((E.max()+50-DM['x0'])/r)+1
    r0=int((DM['y1']-N.max()-50)/r); r1=int((DM['y1']-N.min()+50)/r)+1
    a=np.asarray(DEM[r0:r1,c0:c1]).astype(np.float32); bad=a==DM['nodata']
    if bad.mean()>0.2: return None,None
    a[bad]=np.nanmean(np.where(bad,np.nan,a)); a=gaussian_filter(a/10/FT,1.0)
    rr=(DM['y1']-N)/r-r0-0.5; cc=(E-DM['x0'])/r-c0-0.5
    z=map_coordinates(a,[rr,cc],order=1).reshape(uu.shape)
    gy,gx=np.gradient(z,step*1.0997)  # ft per ft (1 full px ~ 1.0997 ft)
    return z,np.hypot(gx,gy)
def iso(z,d,iv):
    q=np.floor((z+d)/iv); e=np.zeros(z.shape,bool)
    e[:,1:]|=q[:,1:]!=q[:,:-1]; e[1:,:]|=q[1:,:]!=q[:-1,:]; return e
def windows(sid,coons=True,W=1200,R=24,delta=0.0,smin=0.08,minpts=300,resid=None,cap=20,wexp=0.0):
    sh=Sheet(sid,coons=coons,resid=resid); B=np.load(f'boldx/{sid}.npz')
    bold=B['ink']>=B['thr']; by=B['y'][bold].astype(int); bx=B['x'][bold].astype(int)
    c=np.array([S[sid]['corners'][k] for k in ('TL','TR','BL','BR')])
    ux0,ux1=c[:,0].min(),c[:,0].max(); vy0,vy1=c[:,1].min(),c[:,1].max()
    nu=max(1,int(round((ux1-ux0)/W))); nv=max(1,int(round((vy1-vy0)/W)))
    Wu=(ux1-ux0)/nu; Wv=(vy1-vy0)/nv
    out=[]
    for j in range(nv):
        for i in range(nu):
            u0=ux0+i*Wu; v0=vy0+j*Wv; n=int(max(Wu,Wv)/2)+1
            sel=(bx>=u0)&(bx<u0+Wu)&(by>=v0)&(by<v0+Wv)
            if sel.sum()<minpts: continue
            z,s=zfield(sh,u0,v0,n)
            if z is None: continue
            py=(by[sel]-v0)/2; px=(bx[sel]-u0)/2
            iy=np.clip(np.round(py).astype(int),0,n-1); ix=np.clip(np.round(px).astype(int),0,n-1)
            k=s[iy,ix]>smin
            if k.sum()<minpts: continue
            py,px=py[k],px[k]; wt=s[iy,ix][k]**wexp; wt=wt/wt.sum()
            dt=cv2.distanceTransform((~iso(z,delta,25)).astype(np.uint8),cv2.DIST_L2,5)
            dt=np.minimum(dt,cap)
            sh_=np.arange(-R,R+1); C=np.zeros((len(sh_),len(sh_)))
            for a_,dy in enumerate(sh_):
                yy=np.clip(np.round(py+dy).astype(int),0,n-1)
                for b_,dx in enumerate(sh_):
                    xx=np.clip(np.round(px+dx).astype(int),0,n-1); C[a_,b_]=(dt[yy,xx]*wt).sum()
            a_,b_=np.unravel_index(np.argmin(C),C.shape)
            def sub(cm,c0,cp): d=cm-2*c0+cp; return 0.0 if d<=0 else 0.5*(cm-cp)/d
            sy=sh_[a_]+(sub(C[a_-1,b_],C[a_,b_],C[a_+1,b_]) if 0<a_<len(sh_)-1 else 0)
            sx=sh_[b_]+(sub(C[a_,b_-1],C[a_,b_],C[a_,b_+1]) if 0<b_<len(sh_)-1 else 0)
            # z modulo 25 at points after shift (datum check)
            yy=np.clip(np.round(py+sh_[a_]).astype(int),0,n-1); xx=np.clip(np.round(px+sh_[b_]).astype(int),0,n-1)
            ph=np.exp(1j*2*np.pi*z[yy,xx]/25); cm=np.angle(ph.mean())/2/np.pi*25
            edge=(a_ in (0,len(sh_)-1)) or (b_ in (0,len(sh_)-1))
            out.append(dict(u=u0+Wu/2,v=v0+Wv/2,n=int(k.sum()),c0=float(C[R,R]),cmin=float(C[a_,b_]),
                            dx=float(sx*2),dy=float(sy*2),edge=bool(edge),zres=float(cm),R=float(abs(ph.mean())),
                            C=C))
    return out
if __name__=='__main__':
    sid=sys.argv[1]
    for coons in (False,True):
        res=windows(sid,coons=coons)
        good=[w for w in res if not w['edge'] and w['c0']-w['cmin']>-1]
        d=np.array([[w['dx'],w['dy']] for w in res])
        print(f"sheet {sid} coons={coons} windows {len(res)}  median |shift| {np.median(np.hypot(*d.T)):.1f} px  mean c0 {np.mean([w['c0'] for w in res]):.2f} cmin {np.mean([w['cmin'] for w in res]):.2f}")
        for w in res: print(f"  u{w['u']:6.0f} v{w['v']:6.0f} n{w['n']:5d} c0 {w['c0']:5.2f} cmin {w['cmin']:5.2f} shift ({w['dx']:6.1f},{w['dy']:6.1f}){' EDGE' if w['edge'] else ''} zres {w['zres']:5.2f} R {w['R']:.2f}")
