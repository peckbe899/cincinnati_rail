try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import numpy as np, glob, json, sys
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS=None
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
R=json.load(open(sys.argv[1])); sheets=sys.argv[2].split(','); out=sys.argv[3]
F=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
w,h=560,170; sc=0.5
tw,th=int(w*sc),int(h*sc)
canvas=Image.new('RGB',(4*(tw+4),len(sheets)*(th+4)),'white')
for r,sid in enumerate(sheets):
    im=Image.open(glob.glob(base+'Sheet_%s_*.jpg'%sid)[0]).convert('RGB')
    for c,k in enumerate(['TL','TR','BL','BR']):
        x,y=map(int,R[sid][k]['px'])
        x0 = x-380 if k in('TL','BL') else x-180
        y0 = y-140 if k in('TL','TR') else y-30
        cr=im.crop((x0,y0,x0+w,y0+h)).resize((tw,th),Image.LANCZOS)
        d=ImageDraw.Draw(cr); d.text((2,th-16),f'{sid}{k}',fill=(255,0,0),font=F)
        canvas.paste(cr,(c*(tw+4),r*(th+4)))
canvas.save(out)
