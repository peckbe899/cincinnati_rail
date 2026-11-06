try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# crop the page's Sanborn tiles (tiles_n) over a box and mark points: tilecrop.py E0 N0 E1 N1 out.png [E,N,label ...]
import sys
from PIL import Image, ImageDraw
SP=_ws.DATA
E0,N0,E1,N1=map(float,sys.argv[1:5]); out=sys.argv[5]; R=0.25; T=512
W,H=int((E1-E0)/R),int((N1-N0)/R); can=Image.new('RGB',(W,H),'white')
import os
for tx in range(int(E0//T*T),int(E1)+1,T):
  for ty in range(int(N0//T*T),int(N1)+1,T):
    fn=SP+f'deckpage/tiles_n/{tx}_{ty}.webp'
    if not os.path.exists(fn): continue
    im=Image.open(fn).convert('RGBA'); can.paste(im,(int((tx-E0)/R),int((N1-(ty+T))/R)),im)
d=ImageDraw.Draw(can)
pts=[]
for a in sys.argv[6:]:
  e,n,l=a.split(','); x,y=(float(e)-E0)/R,(N1-float(n))/R; pts.append((x,y)); d.ellipse([x-8,y-8,x+8,y+8],outline='red',width=4); d.text((x+12,y-12),l,fill='red')
if len(pts)>1: d.line(pts,fill='red',width=2)
can.thumbnail((1400,1400)); can.save(SP+out)
