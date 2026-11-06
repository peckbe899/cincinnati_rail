try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import glob, re, os
from PIL import Image, ImageDraw, ImageFont
from multiprocessing import Pool
Image.MAX_IMAGE_PIXELS=None
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
CTR={'TL':(360,630),'TR':(9580,625),'BR':(9590,7330),'BL':(360,7340)}
HALF=450; SC=0.5
try: F=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13)
except: F=ImageFont.load_default()
def run(fn):
    sid=re.search(r'Sheet_(\d+)',fn).group(1)
    im=Image.open(fn).convert('RGB'); W,H=im.size
    sx,sy=W/10008,H/7947
    tiles=[]
    for k in ('TL','TR','BL','BR'):
        cx,cy=CTR[k]; cx*=sx; cy*=sy
        x0,y0=int(cx-HALF),int(cy-HALF); c=im.crop((x0,y0,x0+2*HALF,y0+2*HALF)).resize((int(2*HALF*SC),)*2,Image.LANCZOS)
        d=ImageDraw.Draw(c)
        for v in range((x0//50+1)*50,x0+2*HALF,50):
            X=(v-x0)*SC; d.line([(X,0),(X,c.size[1])],fill=(0,170,255) if v%100==0 else (150,220,255),width=1)
            if v%100==0: d.text((X+2,2),str(v),fill=(0,90,200),font=F)
        for v in range((y0//50+1)*50,y0+2*HALF,50):
            Y=(v-y0)*SC; d.line([(0,Y),(c.size[0],Y)],fill=(0,170,255) if v%100==0 else (150,220,255),width=1)
            if v%100==0: d.text((2,Y+2),str(v),fill=(0,90,200),font=F)
        d.text((c.size[0]-40,c.size[1]-18),k,fill=(255,0,0),font=F)
        tiles.append(c)
    w=tiles[0].size[0]; out=Image.new('RGB',(2*w+10,2*w+10),'white')
    for i,t in enumerate(tiles): out.paste(t,((i%2)*(w+10),(i//2)*(w+10)))
    out.save(f'comp/sheet_{sid}.png')
    return sid
with Pool(8) as p: print(sorted(p.map(run,sorted(glob.glob(base+'Sheet_*.jpg')))))
