"""Overlay basin (black) + deck (blue) streets, optional OSM north (red), labels, on a georeferenced image.
  python3 ov.py in.jpg out.jpg x0 y0 x1 y1 res [osm]"""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
SP=_ws.DATA
src,dst=sys.argv[1:3]; x0,y0,x1,y1,res=map(float,sys.argv[3:8]); osm=len(sys.argv)>8
img=Image.open(src).convert('RGB'); dr=ImageDraw.Draw(img,'RGBA'); px=lambda e,n:((e-x0)/res,(y1-n)/res)
F=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',11)
def inwin(c): c=np.array(c); return not (c[:,0].max()<x0 or c[:,0].min()>x1 or c[:,1].max()<y0 or c[:,1].min()>y1)
lab=set()
def label(c,n,col):
    c=np.array(c); m=c[len(c)//2]; k=(n,round(m[0]/200),round(m[1]/200))
    if k in lab or not (x0<m[0]<x1 and y0<m[1]<y1): return
    lab.add(k); dr.text(px(*m),n.replace(' Street','').replace(' Avenue',' Av'),fill=col,font=F)
if osm:
    for f in json.load(open(SP+'lph/osm_north.geojson'))['features']:
        c=f['geometry']['coordinates']
        if f['properties'].get('highway') in ('service',) or not inwin(c): continue
        dr.line([px(*q) for q in c],fill=(230,0,0,140),width=2)
        if f['properties'].get('name'): label(c,f['properties']['name'],(180,0,0))
for fn,col,w in [('deckpage/basin.json',(0,0,0,210),3),('deckpage/deck.json',(30,60,220,230),4)]+([('lph/add_streets.json',(0,170,0,240),4)] if __import__('os').path.exists(SP+'lph/add_streets.json') else []):
    for f in json.load(open(SP+fn))['features']:
        g=f['geometry']; p=f['properties']
        if p.get('layer') not in (None,'street') or g['type']!='LineString' or not inwin(g['coordinates']): continue
        dr.line([px(*q) for q in g['coordinates']],fill=col,width=w)
        if p.get('name'): label(g['coordinates'],p['name'],col[:3])
img.save(dst,quality=85)
