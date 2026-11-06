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
        for pg in getattr(g,'geoms',[g]): cv2.fillPoly(im,[P(pg.exterior.coords)],(235,225,210) if p.get('set')!='mv' else (200,235,200))
for f in B['features']:
    p=f['properties']
    if p['layer']=='street':
        c=P(f['geometry']['coordinates']); cv2.polylines(im,[c],False,(170,170,170),max(1,int(p.get('width_m',10)/res)),cv2.LINE_AA)
        if len(sys.argv)>7 and p.get('name') and len(c)>1: m=c[len(c)//2]; cv2.putText(im,p['name'][:14],(int(m[0]),int(m[1])),cv2.FONT_HERSHEY_SIMPLEX,0.32,(90,90,90),1)
T=json.load(open(SP+'deckpage/tracks.json'))
for f in T['features']:
    g=f['geometry']
    if g['type']=='LineString' and f['properties'].get('layer') in ('apex','lower'): cv2.polylines(im,[P(g['coordinates'])],False,(60,60,60) if f['properties']['layer']=='apex' else (200,60,160),1,cv2.LINE_AA)
C=json.load(open(SP+'deckpage/context.json')); ED=json.load(open(SP+'dbread2/deck/layout.json'))['transit']
for f in C['rer']:
    c=ED[f['id']]['c'] if f['id'] in ED and isinstance(ED[f['id']].get('c'),list) else f['c']
    cv2.polylines(im,[P(c)],False,(40,140,240) if 'A' in f['lines'] else (160,40,160),2,cv2.LINE_AA)
BJ=json.load(open(SP+'rer1023/ben_1021.json'))
for k,v in BJ.items():
    if k.endswith('stn'): x,y=P([v])[0]; cv2.circle(im,(x,y),7,(0,0,255),2); continue
    cv2.polylines(im,[P(v)],False,(0,0,255) if 'Spur' not in k else (0,170,255),2,cv2.LINE_AA)
X=json.load(open(SP+sys.argv[8])) if len(sys.argv)>8 else {}
for k,v in X.items():
    if isinstance(v,list) and v and isinstance(v[0],list): cv2.polylines(im,[P(v)],False,(0,120,0),2,cv2.LINE_AA)
step=100 if (E1-E0)<1600 else 500
for gx in range(int(E0//step*step),int(E1)+1,step):
    x=int((gx-E0)/res); cv2.line(im,(x,0),(x,H),(220,220,255),1); cv2.putText(im,str(gx),(x+2,12),cv2.FONT_HERSHEY_SIMPLEX,0.35,(0,0,200),1)
for gy in range(int(N0//step*step),int(N1)+1,step):
    y=int((N1-gy)/res); cv2.line(im,(0,y),(W,y),(220,220,255),1); cv2.putText(im,str(gy),(2,y-2),cv2.FONT_HERSHEY_SIMPLEX,0.35,(0,0,200),1)
cv2.imwrite(out,im); print(im.shape)
