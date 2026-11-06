"""Preview: 1922 halves (full page, inset) under the 1904 overviews."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
SP=_ws.DATA
sys.path.insert(0,_ws.CODE+'lph'); sys.path.insert(0,_ws.CODE+'sbg')
import mos22
from sb import find
Image.MAX_IMAGE_PIXELS=None
TF=json.load(open(SP+'lph/tf22_cw.json'))
POLY=json.load(open(SP+'lph/poly22.json')) if len(sys.argv)>8 else {}
from matplotlib.path import Path
x0,y0,x1,y1,res=map(float,sys.argv[1:6]); out=sys.argv[6]; halves=sys.argv[7].split(',')
W,H=int((x1-x0)/res),int((y1-y0)/res)
jj,ii=np.meshgrid(np.arange(W),np.arange(H)); E=x0+(jj+0.5)*res; N=y1-(ii+0.5)*res
acc=np.full((H,W,3),250,np.uint8); best=np.zeros((H,W))
F=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',14)
lab=[]
for h in halves:
    im=Image.open(find('22-'+h)); w,hh=im.size; im=np.asarray(im.convert('RGB'))
    x,y=mos22.inv(TF[h],E,N)
    if h in POLY: ok=Path(np.array(POLY[h])).contains_points(np.c_[x.ravel(),y.ravel()]).reshape(H,W)
    else: ok=(x>60)&(y>60)&(x<w-20)&(y<hh-60)
    dep=np.minimum(np.minimum(x,w-x),np.minimum(y,hh-y))
    m=ok&(dep>best)
    for k in range(3): acc[...,k][m]=ndi.map_coordinates(im[...,k],[y[m],x[m]],order=1)
    best[m]=dep[m]
    e,n=mos22.ap(TF[h],w/2,hh/2); lab.append((h,e,n))
img=Image.fromarray(acc)
for d in ['deckpage/tiles_b','deckpage/tiles_n']:
    O=json.load(open(SP+d+'/overview.json')); ov=Image.open(SP+d+'/overview.webp').convert('RGBA')
    sc=O['res']/res; ov=ov.resize((int(ov.size[0]*sc),int(ov.size[1]*sc)))
    if len(sys.argv)>9: a=np.asarray(ov).copy(); a[...,3]=(a[...,3]*0.25).astype(np.uint8); ov=Image.fromarray(a)
    img.paste(ov,(int((O['E0']-x0)/res),int((y1-O['N1'])/res)),ov)
dr=ImageDraw.Draw(img)
for h,e,n in lab: dr.text(((e-x0)/res,(y1-n)/res),h,fill=(200,0,200),font=F)
img.save(out,quality=85); print(img.size)
