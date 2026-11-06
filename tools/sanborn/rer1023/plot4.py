try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np, cv2
from shapely.geometry import shape
SP=_ws.DATA
E0,N0,E1,N1,res=[float(v) for v in sys.argv[1:6]]; out=sys.argv[6]
W,H=int((E1-E0)/res),int((N1-N0)/res); im=np.full((H,W,3),255,np.uint8)
def P(c): return np.array([(int((q[0]-E0)/res),int((N1-q[1])/res)) for q in c],np.int32)
B=json.load(open(SP+'deckpage/basin.json'))
for f in B['features']:
    p=f['properties']
    if p['layer']=='block':
        g=shape(f['geometry'])
        for pg in getattr(g,'geoms',[g]): cv2.fillPoly(im,[P(pg.exterior.coords)],(232,228,220) if p.get('set')!='mv' else (205,232,205))
for f in B['features']:
    p=f['properties']
    if p['layer']=='street': cv2.polylines(im,[P(f['geometry']['coordinates'])],False,(200,200,200),max(1,int(p.get('width_m',10)/res)),cv2.LINE_AA)
C=json.load(open(SP+'deckpage/context.json')); T=json.load(open(SP+'deckpage/tracks.json'))
for p in C['plats']:
    if p['sys']=='rer': cv2.fillPoly(im,[P(p['c'])],(120,200,250))
for f in T['features']:
    g=f['geometry']
    if g['type']=='LineString' and f['properties'].get('layer') in ('apex','lower'): cv2.polylines(im,[P(g['coordinates'])],False,(60,60,60) if f['properties']['layer']=='apex' else (200,60,160),1,cv2.LINE_AA)
for t in C['tracks']:
    if t['sys']=='rer': cv2.polylines(im,[P(t['c'])],False,(0,110,230) if t['line']=='A' else (150,40,150),1,cv2.LINE_AA)

S_=json.load(open(SP+'deckpage/structures.json'))
for f in S_['features']:
    if f['properties'].get('layer')=='struct':
        g=shape(f['geometry'])
        for pg in getattr(g,'geoms',[g]): cv2.polylines(im,[P(pg.exterior.coords)],True,(0,140,255),1,cv2.LINE_AA)
for f in T['features']:
    if 'R5' in f['properties'].get('name','') and f['geometry']['type']=='LineString': cv2.polylines(im,[P(f['geometry']['coordinates'])],False,(0,0,255),2,cv2.LINE_AA)
for r in C['rer_struct']:
    if r['c']: cv2.polylines(im,[P(r['c'])],False,(0,200,0),1,cv2.LINE_AA)
for m in C['rer_marks']:
    x,y=P([m['p']])[0]
    if 0<x<W and 0<y<H: cv2.circle(im,(x,y),3,(0,0,200),-1); cv2.putText(im,m['label'][:60],(x+5,y-3),cv2.FONT_HERSHEY_SIMPLEX,0.33,(0,0,160),1)
step=50 if (E1-E0)<1000 else (100 if (E1-E0)<2500 else 500)
for gx in range(int(E0//step*step),int(E1)+1,step):
    x=int((gx-E0)/res); cv2.line(im,(x,0),(x,H),(225,225,255),1); cv2.putText(im,str(gx),(x+2,12),cv2.FONT_HERSHEY_SIMPLEX,0.32,(0,0,200),1)
for gy in range(int(N0//step*step),int(N1)+1,step):
    y=int((N1-gy)/res); cv2.line(im,(0,y),(W,y),(225,225,255),1); cv2.putText(im,str(gy),(2,y-2),cv2.FONT_HERSHEY_SIMPLEX,0.32,(0,0,200),1)
cv2.imwrite(out,im); print(im.shape)
