try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, cv2, sys, json
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
sheets={'30':("Sheet_30_Down_Town_Section.jpg",{'TL':(273.5,613),'TR':(9526,648.5),'BL':(280,7365),'BR':(9497.5,7331)}),
        '29':("Sheet_29_Mt._Auburn.jpg",{'TL':(353,576),'TR':(9572,595),'BL':(369,7341),'BR':(9566,7305)})}
out={}
for sid,(fn,C) in sheets.items():
    a=np.asarray(Image.open(base+fn).convert('L')).astype(float)
    def trace(p0,p1,outward,n=60,search=40):
        # sample along edge p0->p1; at each point scan perpendicular from outside inward, take first strong dark minimum
        p0=np.array(p0);p1=np.array(p1); d=(p1-p0)/np.linalg.norm(p1-p0); nrm=np.array(outward,float)
        pts=[]
        for t in np.linspace(0.03,0.97,n):
            c=p0+(p1-p0)*t
            prof=[]
            for s in range(search,-search-1,-1):   # from outside (+s) to inside (-s)
                q=c+nrm*s; x,y=int(round(q[0])),int(round(q[1]))
                # average 9 px along the edge direction
                vals=[a[int(round(y+d[1]*k)),int(round(x+d[0]*k))] for k in range(-4,5)]
                prof.append(np.mean(vals))
            prof=np.array(prof); bg=np.median(prof[:10])
            idx=np.where(prof<bg-35)[0]
            if len(idx)==0: pts.append(None); continue
            s=search-idx[0]   # first dark from outside
            # refine to local minimum within 3 px
            j=idx[0]; k=j+np.argmin(prof[j:j+4]); s=search-k
            pts.append((float(t),float(s)))
        return pts
    E={'top':(C['TL'],C['TR'],(0,-1)),'bottom':(C['BL'],C['BR'],(0,1)),'left':(C['TL'],C['BL'],(-1,0)),'right':(C['TR'],C['BR'],(1,0))}
    res={}
    for k,(p0,p1,o) in E.items():
        pts=[p for p in trace(p0,p1,o) if p]
        s=np.array([p[1] for p in pts]); t=np.array([p[0] for p in pts])
        # deviation from the straight corner-to-corner line (positive = outward)
        res[k]=dict(n=len(pts),max_out=round(float(s.max()),1),max_in=round(float(s.min()),1),mid=round(float(np.median(s[(t>0.4)&(t<0.6)])) if ((t>0.4)&(t<0.6)).any() else 0,1))
    out[sid]=res
print(json.dumps(out,indent=1))
