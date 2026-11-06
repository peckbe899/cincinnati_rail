try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import glob, sys, json
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS=None
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
out=(_ws.DATA + "topo/zoomB/")
F=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
CTR=json.loads(sys.argv[2]) if len(sys.argv)>2 else {'TL':(360,620),'TR':(9570,630),'BR':(9560,7310),'BL':(360,7320)}
HALF=int(sys.argv[3]) if len(sys.argv)>3 else 200
sid=sys.argv[1]
fn=glob.glob(base+'Sheet_%s_*.jpg'%sid)[0]
im=Image.open(fn).convert('RGB')
tiles=[]
for k in ('TL','TR','BL','BR'):
    cx,cy=CTR[k]; x0,y0=int(cx-HALF),int(cy-HALF)
    c=im.crop((x0,y0,x0+2*HALF,y0+2*HALF))
    d=ImageDraw.Draw(c)
    for v in range((x0//20+1)*20,x0+2*HALF,20):
        X=v-x0; d.line([(X,0),(X,c.size[1])],fill=(0,170,255) if v%100==0 else (170,225,255),width=1)
        if v%100==0: d.text((X+2,2),str(v),fill=(0,90,200),font=F)
    for v in range((y0//20+1)*20,y0+2*HALF,20):
        Y=v-y0; d.line([(0,Y),(c.size[0],Y)],fill=(0,170,255) if v%100==0 else (170,225,255),width=1)
        if v%100==0: d.text((2,Y+2),str(v),fill=(0,90,200),font=F)
    d.text((c.size[0]-30,c.size[1]-16),k,fill=(255,0,0),font=F)
    tiles.append(c)
w=tiles[0].size[0]; o=Image.new('RGB',(2*w+10,2*w+10),'white')
for i,t in enumerate(tiles): o.paste(t,((i%2)*(w+10),(i//2)*(w+10)))
o.save(out+'z_%s.png'%sid)
