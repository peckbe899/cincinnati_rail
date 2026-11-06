try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import numpy as np, glob, json, sys
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
CTR={'TL':(360,630),'TR':(9580,625),'BR':(9590,7330),'BL':(360,7340)}
POFF={'TL':(0,0),'TR':(460,0),'BL':(0,460),'BR':(460,460)}
# displayed estimates (vertical-line X, horizontal-line Y) in composite pixels
EST={
'38':{'TL':(222,190),'TR':(709,200),'BL':(230,706),'BR':(694,672)},
'39':{'TL':(224,191),'TR':(745,212),'BL':(234,702),'BR':(731,686)},
'40':{'TL':(198,197),'TR':(706,203),'BL':(209,720),'BR':(699,686)},
'41':{'TL':(212,198),'TR':(699,212),'BL':(216,696),'BR':(689,677)},
'42':{'TL':(221,194),'TR':(712,199),'BL':(232,709),'BR':(707,676)},
'43':{'TL':(207,231),'TR':(697,238),'BL':(212,723),'BR':(682,700)},
'44':{'TL':(227,181),'TR':(726,207),'BL':(225,704),'BR':(711,681)},
'45':{'TL':(211,193),'TR':(713,202),'BL':(228,719),'BR':(712,681)},
'46':{'TL':(238,191),'TR':(736,216),'BL':(246,717),'BR':(718,704)},
'47':{'TL':(256,216),'TR':(760,241),'BL':(261,722),'BR':(746,692)},
'48':{'TL':(232,197),'TR':(709,223),'BL':(235,704),'BR':(684,691)},
}
def to_orig(sid,k,X,Y,W,H):
    sx,sy=W/10008,H/7947; cx,cy=CTR[k]; x0=int(cx*sx-450); y0=int(cy*sy-450)
    return x0+(X-POFF[k][0])*2, y0+(Y-POFF[k][1])*2
def fitline(g,est_c,along0,along1,vertical,win=40,blk=16):
    pts=[]
    for a in range(int(along0),int(along1),blk):
        if vertical:
            sub=g[a:a+blk, int(est_c-win):int(est_c+win)]
            prof=np.median(sub,axis=0)
        else:
            sub=g[int(est_c-win):int(est_c+win), a:a+blk]
            prof=np.median(sub,axis=1)
        prof=np.convolve(prof,np.ones(3)/3,'same')
        i=int(np.argmin(prof[1:-1]))+1
        contrast=np.median(prof)-prof[i]
        if contrast>25: pts.append((a+blk/2, est_c-win+i, contrast))
    p=np.array(pts)
    if len(p)<5: return None,len(p)
    for _ in range(3):
        A=np.vstack([p[:,0],np.ones(len(p))]).T
        m,c=np.linalg.lstsq(A,p[:,1],rcond=None)[0]
        r=np.abs(p[:,1]-(m*p[:,0]+c))
        keep=r<max(2.5,np.median(r)*3)
        if keep.all(): break
        p=p[keep]
    return (m,c),len(p)
out={}
for sid,ests in EST.items():
    fn=glob.glob(base+'Sheet_%s_*.jpg'%sid)[0]
    g=np.asarray(Image.open(fn).convert('L')).astype(np.float32)
    H,W=g.shape; out[sid]={}
    for k,(X,Y) in ests.items():
        ex,ey=to_orig(sid,k,X,Y,W,H)
        dx=1 if k in('TL','BL') else -1   # direction inward along horizontal line
        dy=1 if k in('TL','TR') else -1
        # vertical line: sample rows from ey+dy*40 to ey+dy*1500
        a0,a1=sorted([ey+dy*40, ey+dy*1500])
        v,nv=fitline(g,ex,a0,a1,True)
        b0,b1=sorted([ex+dx*40, ex+dx*1500])
        h,nh=fitline(g,ey,b0,b1,False)
        if v is None or h is None:
            out[sid][k]=dict(est=[ex,ey],fail=True,nv=nv,nh=nh); continue
        # x = mv*y+cv ; y = mh*x+ch
        mv,cv=v; mh,ch=h
        y=(mh*cv+ch)/(1-mh*mv); x=mv*y+cv
        out[sid][k]=dict(est=[ex,ey],px=[round(x,1),round(y,1)],nv=nv,nh=nh,slopes=[round(mv,4),round(mh,4)])
    print(sid,{k:(v.get('est'),v.get('px'),v.get('nv'),v.get('nh')) for k,v in out[sid].items()})
json.dump(out,open(sys.argv[1],'w'),indent=1)
