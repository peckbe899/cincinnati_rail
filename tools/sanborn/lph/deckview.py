"""1904 overview (tiles_n at 0.25 m, sampled) + basin streets (black) + deck features (blue streets, outlines) + labels."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np, os
from PIL import Image, ImageDraw, ImageFont
SP=_ws.DATA
x0,y0,x1,y1,res=map(float,sys.argv[1:6]); out=sys.argv[6]
W,H=int((x1-x0)/res),int((y1-y0)/res)
img=Image.new('RGB',(W,H),(250,250,250))
for d in ['deckpage/tiles_b','deckpage/tiles_n']:
    I=json.load(open(SP+d+'/index.json')); T=I['size']; r=I['res']
    for tx,ty in I['tiles']:
        if tx+T<x0 or tx>x1 or ty+T<y0 or ty>y1: continue
        fn=SP+d+f'/{tx}_{ty}.webp'
        if not os.path.exists(fn): continue
        t=Image.open(fn).convert('RGBA'); n=int(T/res); t=t.resize((n,n),Image.LANCZOS)
        img.paste(t,(int((tx-x0)/res),int((y1-ty-T)/res)),t)
dr=ImageDraw.Draw(img,'RGBA'); px=lambda e,n:((e-x0)/res,(y1-n)/res)
F=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',12)
for f in json.load(open(SP+'deckpage/basin.json'))['features']:
    if f['properties']['layer']=='street':
        c=f['geometry']['coordinates']; dr.line([px(*p) for p in c],fill=(0,0,0,200),width=3)
for f in json.load(open(SP+'deckpage/deck.json'))['features']:
    g=f['geometry']; L=f['properties'].get('layer')
    if g['type']=='LineString': dr.line([px(*p) for p in g['coordinates']],fill=(30,60,220,230),width=4)
    elif g['type']=='Polygon': dr.line([px(*p) for p in g['coordinates'][0]],fill=(30,60,220,160),width=2)
    elif g['type']=='MultiPolygon':
        for poly in g['coordinates']: dr.line([px(*p) for p in poly[0]],fill=(30,60,220,160),width=2)
lab=set()
for fn,col in [('deckpage/basin.json',(120,0,0)),('deckpage/deck.json',(0,0,160))]:
    for f in json.load(open(SP+fn))['features']:
        p=f['properties']; g=f['geometry']
        if g['type']!='LineString' or not p.get('name'): continue
        c=np.array(g['coordinates']); m=c[len(c)//2]
        if not (x0<m[0]<x1 and y0<m[1]<y1): continue
        k=(p['name'],round(m[0]/150),round(m[1]/150))
        if k in lab: continue
        lab.add(k); dr.text(px(*m),p['name'].replace(' Street','').replace(' Avenue',' Av'),fill=col,font=F)
img.save(out,quality=85); print(img.size)
