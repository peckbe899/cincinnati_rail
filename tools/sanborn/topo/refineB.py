try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import glob, json, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS=None
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
outd=(_ws.DATA + "topo/zoomB/")
F=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
est=json.load(open(sys.argv[1]))
R=int(sys.argv[2]) if len(sys.argv)>2 else 30
res={}
for sid,c in est.items():
    fn=glob.glob(base+'Sheet_%s_*.jpg'%sid)[0]
    im=Image.open(fn).convert('L'); A=np.asarray(im).astype(float)
    res[sid]={}
    tiles=[]
    for k,(x,y) in c.items():
        sx = 1 if k in('TL','BL') else -1   # direction into map horizontally
        sy = 1 if k in('TL','TR') else -1
        # horizontal border: sample along x from corner into map 40..400
        xs=sorted([x+sx*40,x+sx*400]); 
        rows=A[y-R:y+R+1, xs[0]:xs[1]]
        prof=np.percentile(rows,30,axis=1)  # dark rows
        yy=y-R+int(np.argmin(prof))
        ys=sorted([y+sy*40,y+sy*400])
        cols=A[ys[0]:ys[1], x-R:x+R+1]
        profc=np.percentile(cols,30,axis=0)
        xx=x-R+int(np.argmin(profc))
        res[sid][k]=[xx,yy]
        H=110
        crop=Image.open(fn).convert('RGB').crop((xx-H,yy-H,xx+H,yy+H)).resize((440,440),Image.LANCZOS)
        d=ImageDraw.Draw(crop)
        x0,y0=xx-H,yy-H
        for v in range((x0//10+1)*10,x0+2*H,10):
            X=(v-x0)*2
            if v%50==0: d.line([(X,0),(X,440)],fill=(0,170,255) if v%100==0 else (170,225,255),width=1)
            if v%100==0: d.text((X+2,2),str(v),fill=(0,90,200),font=F)
        for v in range((y0//10+1)*10,y0+2*H,10):
            Y=(v-y0)*2
            if v%50==0: d.line([(0,Y),(440,Y)],fill=(0,170,255) if v%100==0 else (170,225,255),width=1)
            if v%100==0: d.text((2,Y+2),str(v),fill=(0,90,200),font=F)
        X,Y=(xx-x0)*2,(yy-y0)*2
        d.ellipse([X-6,Y-6,X+6,Y+6],outline=(255,0,0),width=2)
        d.text((5,420),'%s %s det (%d,%d)'%(sid,k,xx,yy),fill=(255,0,0),font=F)
        tiles.append(crop)
    o=Image.new('RGB',(890,890),'white')
    for i,t in enumerate(tiles): o.paste(t,((i%2)*450,(i//2)*450))
    o.save(outd+'r_%s.png'%sid)
print(json.dumps(res))
