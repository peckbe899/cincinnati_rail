try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import numpy as np, glob, json, sys
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS=None
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
R=json.load(open(sys.argv[1])); sheets=sys.argv[2].split(','); out=sys.argv[3]
half=int(sys.argv[4]) if len(sys.argv)>4 else 80
F=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
S=2; T=2*half*S
canvas=Image.new('RGB',(4*(T+6),len(sheets)*(T+6)),'white')
for r,sid in enumerate(sheets):
    im=Image.open(glob.glob(base+'Sheet_%s_*.jpg'%sid)[0]).convert('RGB')
    for c,k in enumerate(['TL','TR','BL','BR']):
        x,y=R[sid][k]['px']; xi,yi=int(round(x)),int(round(y))
        cr=im.crop((xi-half,yi-half,xi+half,yi+half)).resize((T,T),Image.NEAREST)
        d=ImageDraw.Draw(cr); cx=(x-(xi-half))*S; cy=(y-(yi-half))*S
        d.line([(cx-12,cy),(cx-4,cy)],fill=(255,0,0)); d.line([(cx+4,cy),(cx+12,cy)],fill=(255,0,0))
        d.line([(cx,cy-12),(cx,cy-4)],fill=(255,0,0)); d.line([(cx,cy+4),(cx,cy+12)],fill=(255,0,0))
        for t in range(-half,half+1,10):
            d.line([((t+half)*S,0),((t+half)*S,5 if t%50 else 12)],fill=(0,120,255))
            d.line([(0,(t+half)*S),(5 if t%50 else 12,(t+half)*S)],fill=(0,120,255))
        d.text((14,14),f'{sid} {k} ({x:.0f},{y:.0f})',fill=(0,0,200),font=F)
        canvas.paste(cr,(c*(T+6),r*(T+6)))
canvas.save(out)
