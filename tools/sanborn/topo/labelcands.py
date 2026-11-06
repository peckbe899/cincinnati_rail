"""Printed-label candidates: gaps in index contours (two bold segment ends facing each other 6-30 m apart).
Crops come from the original full-resolution sheet scans, rotated so the gap runs left-right."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, cv2, json, sys
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from final_model import Final
from geo import S as SH
name=sys.argv[1]; d=np.load(f'pilot_{name}_labels2.npz')
E,N,inv,isb,lab=d['E'],d['N'],d['inv'],d['isb'],d['lab']; X0=float(d['X0']); Y1=float(d['Y1']); W=int(d['W'])
ends=[];endseg=[]
o=np.argsort(inv,kind='stable'); cnt=np.bincount(inv); bnd=np.r_[0,np.cumsum(cnt)]
for k in np.nonzero(isb&(cnt>=12))[0]:
    pts=np.c_[E[o[bnd[k]:bnd[k+1]]]-X0, Y1-N[o[bnd[k]:bnd[k+1]]]]
    c=pts.mean(0); A=pts[np.argmax(((pts-c)**2).sum(1))]; Bp=pts[np.argmax(((pts-A)**2).sum(1))]
    if np.hypot(*(A-Bp))<10: continue          # closed loop or blob
    ends+= [A,Bp]; endseg+=[k+1,k+1]
P=np.array(ends); sid_=np.array(endseg); t=cKDTree(P); pairs=t.query_pairs(30.0,output_type='ndarray')
cands=[]
for i,j in pairs:
    if sid_[i]==sid_[j]: continue
    dist=np.hypot(*(P[i]-P[j]))
    if dist<6: continue
    cands.append((i,j,dist))
# keep one candidate per segment end (shortest gap)
used=set(); out=[]
for i,j,dist in sorted(cands,key=lambda c:c[2]):
    if i in used or j in used: continue
    used|={i,j}; out.append((i,j,dist))
F=Final(); res=[]
sheets=sorted(set(SH)-{k for k in SH if k.startswith('_')})
WIN={'otr':['18','19','29','30'],'westwood':['33','34','40','42']}[name]
imgs={}
for k,(i,j,dist) in enumerate(out):
    mx=(P[i]+P[j])/2; e=X0+mx[0]; n=Y1-mx[1]
    ea=X0+P[i][0]; na=Y1-P[i][1]; eb=X0+P[j][0]; nb_=Y1-P[j][1]
    for sid in WIN:
        u,v=F.utm2p(sid,np.array([e,ea,eb]),np.array([n,na,nb_])); u=np.asarray(u); v=np.asarray(v)
        if sid not in imgs: imgs[sid]=cv2.imread(_ws.ext('/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/')+SH[sid]['file'])
        H_,W_=imgs[sid].shape[:2]
        if 60<u[0]<W_-60 and 60<v[0]<H_-60:
            ang=np.degrees(np.arctan2(v[2]-v[1],u[2]-u[1]))
            if ang>90: ang-=180
            if ang<-90: ang+=180
            M=cv2.getRotationMatrix2D((float(u[0]),float(v[0])),ang,1.0)
            rot=cv2.warpAffine(imgs[sid],M,(W_,H_),flags=cv2.INTER_CUBIC)
            gap=np.hypot(u[2]-u[1],v[2]-v[1]); hw=int(max(gap*0.75,40)); hh=24
            crop=rot[int(v[0])-hh:int(v[0])+hh,int(u[0])-hw:int(u[0])+hw]
            res.append(dict(id=len(res),E=float(e),N=float(n),segs=[int(sid_[i]-1),int(sid_[j]-1)],labs=[float(lab[sid_[i]-1]),float(lab[sid_[j]-1])],sheet=sid,crop=crop))
            break
print(name,'gap candidates',len(out),'with crops',len(res))
# contact sheets, 30 per page
cell_w,cell_h=360,110
for p in range(0,len(res),30):
    page=np.full((cell_h*10,cell_w*3,3),255,np.uint8)
    for q,r in enumerate(res[p:p+30]):
        c=cv2.resize(r['crop'],(cell_w-10,int((cell_w-10)*r['crop'].shape[0]/max(r['crop'].shape[1],1))))[:cell_h-22]
        y=(q//3)*cell_h; x=(q%3)*cell_w
        page[y+20:y+20+c.shape[0],x+5:x+5+c.shape[1]]=c
        cv2.putText(page,str(r['id']),(x+5,y+15),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,0,255),1)
    cv2.imwrite(f'lc_{name}_{p//30:02d}.jpg',page,[cv2.IMWRITE_JPEG_QUALITY,90])
json.dump([{k:v for k,v in r.items() if k!='crop'} for r in res],open(f'lc_{name}.json','w'))
