try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import cv2, numpy as np, json, re, sys, glob, os
from PIL import Image
import pytesseract
from multiprocessing import Pool
Image.MAX_IMAGE_PIXELS=None
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
def coarse(g):
    S=8
    e=cv2.erode(g,np.ones((9,9),np.uint8))
    s=cv2.resize(e,(g.shape[1]//S,g.shape[0]//S),interpolation=cv2.INTER_AREA)
    bg=np.median(s); m=(s<bg-45).astype(np.uint8)
    n,lab,st,_=cv2.connectedComponentsWithStats(m,8)
    k=1+np.argmax(st[1:,cv2.CC_STAT_WIDTH]*st[1:,cv2.CC_STAT_HEIGHT])
    pts=np.column_stack(np.where(lab==k))[:,::-1].astype(np.float32)
    hull=cv2.convexHull(pts)
    for eps in np.linspace(0.005,0.08,40):
        ap=cv2.approxPolyDP(hull,eps*cv2.arcLength(hull,True),True)
        if len(ap)==4: break
    q=ap.reshape(-1,2)*S
    # order TL,TR,BR,BL
    s_=q.sum(1); d=q[:,0]-q[:,1]
    return np.array([q[np.argmin(s_)],q[np.argmax(d)],q[np.argmax(s_)],q[np.argmin(d)]],float)
def first_dark(g,p,nrm,along,search=45):
    # scan from outside (+search) to inside, average 9 px along the edge
    bgv=[];prof=[]
    for s in range(search,-search-1,-1):
        q=p+nrm*s
        v=[g[int(round(q[1]+along[1]*k)),int(round(q[0]+along[0]*k))] for k in range(-4,5)]
        prof.append(np.mean(v))
    prof=np.array(prof); bg=np.median(prof[:12])
    idx=np.where(prof<bg-40)[0]
    if len(idx)==0: return None
    j=idx[0]; j=j+int(np.argmin(prof[j:j+4]))
    return p+nrm*(search-j)
def refine(g,C):
    # trace each edge densely, fit lines, intersect
    E={'top':(0,1,(0,-1)),'right':(1,2,(1,0)),'bottom':(3,2,(0,1)),'left':(0,3,(-1,0))}
    lines={};tr={}
    for k,(a,b,o) in E.items():
        p0,p1=C[a],C[b]; L=np.linalg.norm(p1-p0); al=(p1-p0)/L; nrm=np.array(o,float)
        pts=[]
        for t in np.linspace(0.02,0.98,120):
            r=first_dark(g,p0+(p1-p0)*t,nrm,al)
            if r is not None: pts.append(r)
        pts=np.array(pts)
        # robust line: fit, drop >4 px outliers, refit
        for _ in range(3):
            vx,vy,x0,y0=cv2.fitLine(pts.astype(np.float32),cv2.DIST_HUBER,0,0.01,0.01).ravel()
            dist=np.abs((pts[:,0]-x0)*vy-(pts[:,1]-y0)*vx)
            keep=dist<max(4,np.percentile(dist,80)); pts=pts[keep] if keep.sum()>20 else pts
        lines[k]=(vx,vy,x0,y0); tr[k]=pts
    def X(l1,l2):
        (a,b,c,d),(e,f,g_,h)=l1,l2
        A=np.array([[a,-e],[b,-f]]); t=np.linalg.solve(A,[g_-c,h-d]); return np.array([c+a*t[0],d+b*t[0]])
    R=np.array([X(lines['top'],lines['left']),X(lines['top'],lines['right']),X(lines['bottom'],lines['right']),X(lines['bottom'],lines['left'])])
    # bow: max deviation of the traced edge from its fitted line (px), signed outward positive
    bow={}
    for k,(a,b,o) in E.items():
        vx,vy,x0,y0=lines[k]; pts=tr[k]; nrm=np.array(o,float)
        dev=((pts-[x0,y0])@nrm)-(np.array([vx,vy])@nrm)*((pts-[x0,y0])@[vx,vy])
        bow[k]=[round(float(np.percentile(dev,5)),1),round(float(np.percentile(dev,95)),1)]
    return R,bow,{k:v.tolist() for k,v in tr.items()}
def ocr(img):
    g=np.asarray(img.convert('L'))
    g=cv2.resize(g,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC)
    _,b=cv2.threshold(g,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    t=pytesseract.image_to_string(b,config='--psm 7 -c tessedit_char_whitelist=0123456789NSEWZRO')
    return t.strip()
def parse(t,axis):
    t=t.replace(' ','')
    if 'ZER' in t: return 0
    m=re.search(r'(\d{3,5})([NSEW])',t)
    if not m: return None
    v=int(m.group(1)); d=m.group(2)
    if axis=='x' and d in 'EW': return v if d=='E' else -v
    if axis=='y' and d in 'NS': return v if d=='N' else -v
    return None
def label_boxes(c,which):
    x,y=c
    if which=='TL': return dict(x=(x-160,y-110,x+260,y-8), y=(x-380,y-70,x-6,y+40))
    if which=='TR': return dict(x=(x-260,y-110,x+160,y-8), y=(x+6,y-70,x+380,y+40))
    if which=='BR': return dict(x=(x-260,y+8,x+160,y+110), y=(x+6,y-40,x+380,y+70))
    if which=='BL': return dict(x=(x-160,y+8,x+260,y+110), y=(x-380,y-40,x-6,y+70))
def run(fn):
    sid=re.search(r'Sheet_(\d+)',fn).group(1)
    im=Image.open(fn); g=np.asarray(im.convert('L')).astype(np.uint8)
    try:
        C=coarse(g); R,bow,tr=refine(g,C)
    except Exception as e:
        return sid,dict(error=str(e))
    labs={}
    for k,c in zip(['TL','TR','BR','BL'],R):
        bx=label_boxes(c,k)
        labs[k]={a:ocr(im.crop(tuple(int(v) for v in bx[a]))) for a in ('x','y')}
    vals={k:{a:parse(labs[k][a],a) for a in ('x','y')} for k in labs}
    return sid,dict(file=os.path.basename(fn),size=list(im.size),coarse=C.round(1).tolist(),corners=R.round(1).tolist(),bow=bow,ocr=labs,vals=vals)
if __name__=='__main__':
    files=sorted(glob.glob(base+"Sheet_*.jpg"))
    with Pool(8) as p: res=dict(p.map(run,files))
    json.dump(res,open('sheets/corners_raw.json','w'),indent=1)
    for sid in sorted(res):
        r=res[sid]
        if 'error' in r: print(sid,'ERROR',r['error']); continue
        v=r['vals']; c=np.array(r['corners'])
        print(sid, 'TL',v['TL'],'TR',v['TR'],'BR',v['BR'],'BL',v['BL'],'| w top %.0f h left %.0f'%(np.linalg.norm(c[1]-c[0]),np.linalg.norm(c[3]-c[0])))
