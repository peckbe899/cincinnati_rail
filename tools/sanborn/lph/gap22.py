"""1922 halves (tf22_cw) over a window with 1904 overview + streets + sheet outlines + 1922 pick points."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
SP=_ws.DATA
sys.path.insert(0,_ws.CODE+'lph'); sys.path.insert(0,_ws.CODE+'sbg')
import mos22
mos22.TF=json.load(open(SP+'lph/'+(sys.argv[8] if len(sys.argv)>8 else 'tf22_cw.json')))
x0,y0,x1,y1,res=map(float,sys.argv[1:6]); out=sys.argv[6]; halves=sys.argv[7].split(',')
m=mos22.mosaic(x0,y0,x1,y1,res,halves)
img=Image.fromarray(m).convert('RGB')
W,H=img.size
O=json.load(open(SP+'deckpage/tiles_n/overview.json')); ov=Image.open(SP+'deckpage/tiles_n/overview.webp').convert('RGBA')
sc=O['res']/res; ov=ov.resize((int(ov.size[0]*sc),int(ov.size[1]*sc)))
a=np.asarray(ov).copy(); a[...,3]=(a[...,3]*0.55).astype(np.uint8); ov=Image.fromarray(a)
img.paste(ov,(int((O['E0']-x0)/res),int((y1-O['N1'])/res)),ov)
dr=ImageDraw.Draw(img); px=lambda e,n:((e-x0)/res,(y1-n)/res)
F=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',13)
for fn in ['basin/osm_basin.geojson','deck/osm_valley.geojson']:
    for f in json.load(open(SP+fn))['features']:
        g=f['geometry']
        if g['type']=='LineString': dr.line([px(*p) for p in g['coordinates']],fill=(235,120,120),width=1)
for f in json.load(open(SP+'deckpage/basin.json'))['features']:
    if f['properties']['layer']=='street': dr.line([px(*p) for p in f['geometry']['coordinates']],fill=(20,20,20),width=2)
for s in json.load(open(SP+'deckpage/sheets.json')):
    p=s['poly']; dr.line([px(*q) for q in p+[p[0]]],fill=(0,150,0),width=1)
    c=np.mean(p,0); dr.text(px(*c),str(s['sheet']),fill=(0,110,0),font=F)
for h in halves:
    d=json.load(open(SP+f'sbg/picks22/s22-{h}.json'))
    for p in d['intersections']:
        if p.get('part')=='inset': continue
        e,n=mos22.ap(mos22.TF[h],p['x'],p['y']); q=px(e,n)
        dr.ellipse([q[0]-3,q[1]-3,q[0]+3,q[1]+3],outline=(200,0,200),width=2)
img.save(out,quality=85); print(img.size)
