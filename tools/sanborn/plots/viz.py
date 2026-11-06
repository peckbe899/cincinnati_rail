import sys, numpy as np, json
sys.path.insert(0,'.')
from gen import block_plots, polys
from frontage import Faces
from common import Tiles
from shapely.geometry import Point
from PIL import Image, ImageDraw
F=Faces(); T=Tiles()
cx,cy,half=float(sys.argv[1]),float(sys.argv[2]),float(sys.argv[3]); out=sys.argv[4]
sel=[b for b in F.blocks if b['g'].intersects(Point(cx,cy).buffer(half))]
res=0.25*max(1,half/200); W=int(2*half/res); X0,Y1=cx-half,cy+half
xs=X0+(np.arange(W)+0.5)*res; ys=Y1-(np.arange(W)+0.5)*res; XX,YY=np.meshgrid(xs,ys)
lum=T.sample(XX.ravel(),YY.ravel()).reshape(W,W)
im=Image.fromarray(np.nan_to_num(lum,nan=240).astype(np.uint8)).convert('RGB'); d=ImageDraw.Draw(im,'RGBA')
px=lambda x,y:((x-X0)/res,(Y1-y)/res)
n=0
for b in sel:
    for p in block_plots(F,T,b):
        n+=1
        for q in polys(p['g']):
            col=(255,60,60,60) if p['kind']=='lot' else ((60,160,255,70) if p['kind']=='interior' else (60,200,60,70))
            d.polygon([px(*c) for c in q.exterior.coords], fill=col, outline=(200,0,0,255))
print('plots', n); im.save(out)
