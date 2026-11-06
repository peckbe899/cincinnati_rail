try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np, cv2
from shapely.geometry import shape, LineString, box, Point
SP=_ws.DATA
E0,N0,E1,N1,res=[float(v) for v in sys.argv[1:6]]; out=sys.argv[6]
W,H=int((E1-E0)/res),int((N1-N0)/res); im=np.full((H,W,3),255,np.uint8)
def P(c): return np.array([(int((q[0]-E0)/res),int((N1-q[1])/res)) for q in c],np.int32)
B=json.load(open(SP+'deckpage/basin.json')); L=json.load(open(SP+'dbread5/deck/layout.json'))['streets']
for f in B['features']:
    p=f['properties']
    if p['layer']=='block':
        g=shape(f['geometry'])
        for pg in getattr(g,'geoms',[g]): cv2.fillPoly(im,[P(pg.exterior.coords)],(232,228,220))
for f in B['features']:
    p=f['properties']
    if p['layer']!='street': continue
    e=L.get(p['id'],{})
    if e.get('del'): continue
    c=e.get('c') or f['geometry']['coordinates']; w=e.get('w',p.get('width_m',10))
    hl=any(k in (e.get('n') or p.get('name') or '') for k in ('Central Parkway','Ludlow','Millvale','Spring Grove','Colerain'))
    cv2.polylines(im,[P(c)],False,(150,190,230) if hl else (205,205,205),max(1,int(w/res)),cv2.LINE_AA)
for f in B['features']:
    p=f['properties']; e=L.get(p.get('id'),{})
    if p['layer']=='street' and not e.get('del'):
        n=e.get('n') or p.get('name') or ''
        if any(k in n for k in ('Central Parkway','Ludlow','Millvale','Spring Grove','Colerain','Elmore','Hamilton','Blue Rock')):
            c=e.get('c') or f['geometry']['coordinates']; 
            for frac in (0.3,):
                q=LineString(c).interpolate(frac, normalized=True); x,y=P([q.coords[0]])[0]
                if 0<x<W and 0<y<H: cv2.putText(im,n[:28],(x,y),cv2.FONT_HERSHEY_SIMPLEX,0.4,(120,60,0),1)
C=json.load(open(SP+'deckpage/context.json')); T=json.load(open(SP+'deckpage/tracks.json'))
for f in T['features']:
    g=f['geometry']
    if g['type']=='LineString': cv2.polylines(im,[P(g['coordinates'])],False,(60,60,60),1,cv2.LINE_AA)
for t in C['tracks']:
    col=(0,110,230) if t['sys']=='rer' else (170,120,170)
    if t['sys'] in ('rer',): cv2.polylines(im,[P(t['c'])],False,col,1,cv2.LINE_AA)
D=json.load(open(SP+'hwy/data.json')); O=D['origin']
for l in D['lanes']+D['flanes']:
    c=[(x+O[0],y+O[1]) for x,y in l['c']]
    if LineString(c).intersects(box(E0,N0,E1,N1)): cv2.polylines(im,[P(c)],False,(0,0,200) if l in D['lanes'] else (0,120,0),max(1,int(l.get('w',3.5)/res)),cv2.LINE_AA)
for s in D['signals']:
    q=(s['p'][0]+O[0],s['p'][1]+O[1])
    if box(E0,N0,E1,N1).contains(Point(q)): x,y=P([q])[0]; cv2.circle(im,(x,y),4,(0,200,255),-1)
for s in C['stations']+C['rer_stations']:
    x,y=P([s['p']])[0]
    if 0<x<W and 0<y<H: cv2.circle(im,(x,y),4,(200,0,200),-1); cv2.putText(im,s['name'],(x+5,y+4),cv2.FONT_HERSHEY_SIMPLEX,0.4,(160,0,160),1)
for m in C['rer_marks']:
    x,y=P([m['p']])[0]
    if 0<x<W and 0<y<H: cv2.putText(im,m['label'][:40],(x+5,y-3),cv2.FONT_HERSHEY_SIMPLEX,0.33,(0,0,160),1)
step=100
for gx in range(int(E0//step*step),int(E1)+1,step):
    x=int((gx-E0)/res); cv2.line(im,(x,0),(x,H),(225,225,255),1); cv2.putText(im,str(gx),(x+2,12),cv2.FONT_HERSHEY_SIMPLEX,0.32,(0,0,200),1)
for gy in range(int(N0//step*step),int(N1)+1,step):
    y=int((N1-gy)/res); cv2.line(im,(0,y),(W,y),(225,225,255),1); cv2.putText(im,str(gy),(2,y-2),cv2.FONT_HERSHEY_SIMPLEX,0.32,(0,0,200),1)
cv2.imwrite(out,im)
