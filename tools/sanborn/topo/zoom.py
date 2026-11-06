try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import sys, json, glob
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS=None
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
out=(_ws.DATA + "topo/zoom/")
F=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
est=json.loads(sys.argv[1])  # {"25":{"TL":[x,y],...}}
HALF=int(sys.argv[2]) if len(sys.argv)>2 else 120
SC=480/(2*HALF)
for sid,cs in est.items():
    fn=glob.glob(base+f"Sheet_{int(sid):02d}_*.jpg")[0]
    im=Image.open(fn).convert('RGB')
    tiles=[]
    for k in ('TL','TR','BL','BR'):
        cx,cy=cs[k]; x0,y0=int(cx-HALF),int(cy-HALF)
        c=im.crop((x0,y0,x0+2*HALF,y0+2*HALF)).resize((480,480),Image.LANCZOS)
        d=ImageDraw.Draw(c)
        step=10 if HALF<=150 else 25
        for v in range((x0//step+1)*step,x0+2*HALF,step):
            X=(v-x0)*SC; major=v%50==0
            d.line([(X,0),(X,480)],fill=(0,150,255) if major else (170,225,255),width=1)
            if major: d.text((X+2,2),str(v),fill=(0,60,200),font=F)
        for v in range((y0//step+1)*step,y0+2*HALF,step):
            Y=(v-y0)*SC; major=v%50==0
            d.line([(0,Y),(480,Y)],fill=(0,150,255) if major else (170,225,255),width=1)
            if major: d.text((2,Y+2),str(v),fill=(0,60,200),font=F)
        d.text((440,462),k,fill=(255,0,0),font=F)
        tiles.append(c)
    o=Image.new('RGB',(970,970),'white')
    for i,t in enumerate(tiles): o.paste(t,((i%2)*490,(i//2)*490))
    o.save(out+f"z{sid}.png")
    print(sid)
