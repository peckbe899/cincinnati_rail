"""Draw basin streets as width bands (alpha) + centrelines on an image; args like ov.py"""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString
SP=_ws.DATA
src,dst=sys.argv[1:3]; x0,y0,x1,y1,res=map(float,sys.argv[3:8]); extra=sys.argv[8:]
img=Image.open(src).convert('RGBA'); lay=Image.new('RGBA',img.size,(0,0,0,0)); dr=ImageDraw.Draw(lay); px=lambda e,n:((e-x0)/res,(y1-n)/res)
F=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',12)
files=['deckpage/basin.json']+extra
lab=set()
for i,fn in enumerate(files):
    col=[(255,140,0),(0,170,0),(200,0,200)][i%3]
    for f in json.load(open(SP+fn))['features']:
        g=f['geometry']; p=f['properties']
        if p.get('layer','street')!='street' or g['type']!='LineString': continue
        c=np.array(g['coordinates'])
        if c[:,0].max()<x0 or c[:,0].min()>x1 or c[:,1].max()<y0 or c[:,1].min()>y1: continue
        w=p.get('width_m') or 12
        poly=LineString(c).buffer(w/2,cap_style=2)
        for q in getattr(poly,'geoms',[poly]): dr.polygon([px(*t) for t in q.exterior.coords],fill=col+(70,))
        dr.line([px(*t) for t in c],fill=(0,0,0,255) if i==0 else col+(255,),width=2)
        m=c[len(c)//2]; k=(p.get('name'),round(m[0]/120),round(m[1]/120))
        if p.get('name') and k not in lab and x0<m[0]<x1 and y0<m[1]<y1: lab.add(k); dr.text(px(*m),p['name'].replace(' Street','').replace(' Avenue',' Av'),fill=(120,0,0,255),font=F)
Image.alpha_composite(img,lay).convert('RGB').save(dst,quality=85)
