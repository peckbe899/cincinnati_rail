try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np, os
from PIL import Image, ImageDraw, ImageFont
SP=_ws.DATA
src=sys.argv[1]; dst=sys.argv[2]; x0,y0,x1,y1,res=map(float,sys.argv[3:8])
img=Image.open(src).convert('RGB'); dr=ImageDraw.Draw(img,'RGBA'); px=lambda e,n:((e-x0)/res,(y1-n)/res)
F=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',11)
lab=set()
for fn in ['lph/osm_north.geojson']:
    for f in json.load(open(SP+fn))['features']:
        g=f['geometry']; p=f['properties']
        if g['type']!='LineString': continue
        c=np.array(g['coordinates'])
        if c[:,0].max()<x0 or c[:,0].min()>x1 or c[:,1].max()<y0 or c[:,1].min()>y1: continue
        hw=p.get('highway','')
        if hw in ('footway','service','path','steps','cycleway','track','pedestrian'): continue
        dr.line([px(*q) for q in c],fill=(230,0,0,150),width=2)
        n=p.get('name')
        if n:
            m=c[len(c)//2]; k=(n,round(m[0]/250),round(m[1]/250))
            if k not in lab: lab.add(k); dr.text(px(*m),n,fill=(170,0,0),font=F)
img.save(dst,quality=85)
