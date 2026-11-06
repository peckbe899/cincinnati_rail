"""Coverage map: Sanborn overviews (deck+north, basin), basin/north streets (white), deck streets (blue), sheet outlines + labels, OSM (thin red)."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
SP=_ws.DATA
x0,y0,x1,y1,res=map(float,sys.argv[1:6]); out=sys.argv[6]
W,H=int((x1-x0)/res),int((y1-y0)/res)
img=Image.new('RGB',(W,H),(250,250,250))
for d in ['deckpage/tiles_n','deckpage/tiles_b']:
    O=json.load(open(SP+d+'/overview.json')); ov=Image.open(SP+d+'/overview.webp').convert('RGBA')
    sc=O['res']/res; ov=ov.resize((int(ov.size[0]*sc),int(ov.size[1]*sc)))
    img.paste(ov,(int((O['E0']-x0)/res),int((y1-O['N1'])/res)),ov)
dr=ImageDraw.Draw(img); px=lambda e,n:((e-x0)/res,(y1-n)/res)
try: F=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',12)
except: F=ImageFont.load_default()
for fn in ['basin/osm_basin.geojson','deck/osm_valley.geojson']:
    for f in json.load(open(SP+fn))['features']:
        g=f['geometry']
        if g['type']=='LineString': dr.line([px(*p) for p in g['coordinates']],fill=(235,120,120),width=1)
for f in json.load(open(SP+'deckpage/basin.json'))['features']:
    if f['properties']['layer']=='street': dr.line([px(*p) for p in f['geometry']['coordinates']],fill=(20,20,20),width=2)
for f in json.load(open(SP+'deckpage/deck.json'))['features']:
    if f['properties']['layer']=='street': dr.line([px(*p) for p in f['geometry']['coordinates']],fill=(30,60,200),width=3)
    if f['properties']['layer']=='deck':
        g=f['geometry']; cs=g['coordinates'] if g['type']=='Polygon' else [r for poly in g['coordinates'] for r in poly][:1]
        dr.line([px(*p) for p in cs[0]],fill=(30,60,200),width=1)
for s in json.load(open(SP+'deckpage/sheets.json')):
    p=s['poly']; dr.line([px(*q) for q in p+[p[0]]],fill=(0,150,0) if not s.get('basin') else (150,150,0),width=1)
    c=np.mean(p,0); dr.text(px(*c),str(s['sheet']),fill=(0,110,0),font=F)
img.save(out,quality=85); print(img.size)
