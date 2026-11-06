try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np, cv2
SP=_ws.DATA
E0,N0,E1,N1,res=[float(v) for v in sys.argv[1:6]]; out=sys.argv[6]
W,H=int((E1-E0)/res),int((N1-N0)/res); im=np.full((H,W,3),255,np.uint8)
P=lambda c: np.array([(int((x-E0)/res),int((N1-y)/res)) for x,y in c[:][:] for _ in [0]],np.int32)
def P(c): return np.array([(int((q[0]-E0)/res),int((N1-q[1])/res)) for q in c],np.int32)
B=json.load(open(SP+'deckpage/basin.json'))
for f in B['features']:
    p=f['properties']
    if p['layer']=='street':
        col=(150,150,150) if p.get('set')!='mv' else (90,160,90)
        cv2.polylines(im,[P(f['geometry']['coordinates'])],False,col,max(1,int(p.get('width_m',10)/res/2)),cv2.LINE_AA)
T=json.load(open(SP+'deckpage/tracks.json'))
for f in T['features']:
    g=f['geometry']
    if g['type']=='LineString' and f['properties'].get('layer') in ('apex','lower'): cv2.polylines(im,[P(g['coordinates'])],False,(60,60,60),1,cv2.LINE_AA)
C=json.load(open(SP+'deckpage/context.json')); ED=json.load(open(SP+'dbread2/deck/layout.json'))['transit']
COL={'A':(40,120,230),'B':(200,80,40),'D':(160,40,160),'E':(40,160,40),'C':(0,180,180)}
for f in C['rer']:
    c=ED[f['id']]['c'] if f['id'] in ED and isinstance(ED[f['id']].get('c'),list) else f['c']
    col=COL.get(f['lines'][0],(0,0,0)); cv2.polylines(im,[P(c)],False,col,2,cv2.LINE_AA)
for s in C['rer_stations']:
    x,y=P([s['p']])[0]; cv2.circle(im,(x,y),5,(0,0,0),2); cv2.putText(im,s['name'][:18],(x+6,y-4),cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,0,0),1)
BJ=json.load(open(SP+'rer1023/ben_1021.json'))
for k,v in BJ.items():
    if k.endswith('stn'): x,y=P([v])[0]; cv2.circle(im,(x,y),7,(0,0,255),2); continue
    cv2.polylines(im,[P(v)],False,(0,0,255) if 'Spur' not in k else (0,140,255),2,cv2.LINE_AA)
for gx in range(int(E0//500*500),int(E1)+1,500):
    x=int((gx-E0)/res); cv2.line(im,(x,0),(x,H),(220,220,255),1); cv2.putText(im,str(gx),(x+2,12),cv2.FONT_HERSHEY_SIMPLEX,0.35,(0,0,200),1)
for gy in range(int(N0//500*500),int(N1)+1,500):
    y=int((N1-gy)/res); cv2.line(im,(0,y),(W,y),(220,220,255),1); cv2.putText(im,str(gy),(2,y-2),cv2.FONT_HERSHEY_SIMPLEX,0.35,(0,0,200),1)
cv2.imwrite(out,im); print(im.shape)
