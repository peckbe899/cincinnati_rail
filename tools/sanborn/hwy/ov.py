try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np, cv2
from shapely.geometry import shape, LineString, box
SP=_ws.DATA
E0,N0,E1,N1,res=[float(v) for v in sys.argv[1:6]]; out=sys.argv[6]
exec(open(_ws.CODE+'rer1023/plot4.py').read().split("for m in C['rer_marks']:")[0].replace("E0,N0,E1,N1,res=[float(v) for v in sys.argv[1:6]]; out=sys.argv[6]",""))
D=json.load(open(SP+'hwy/data.json')); O=D['origin']
ov=im.copy()
for sg in D['segs']:
    c=[(x+O[0],y+O[1]) for x,y in sg['c']]
    if not LineString(c).intersects(box(E0,N0,E1,N1)): continue
    w=sg.get('width') or 6
    col=(0,160,255) if sg['t']=='Boulevard' else (0,0,0) if sg['t']=='Tunnel' else (60,200,60) if 'APEx' in sg['t'] else (255,0,255) if 'BRT' in sg['t'] else (0,90,200)
    if 'BRT' in sg['t'] or 'APEx' in sg['t']: continue
    cv2.polylines(ov,[P(c)],False,col,max(1,int(w/res)),cv2.LINE_AA)
for l in D.get('lanes',[]):
    pass
im=cv2.addWeighted(ov,0.45,im,0.55,0)
for sg in D['segs']:
    c=[(x+O[0],y+O[1]) for x,y in sg['c']]
    if LineString(c).intersects(box(E0,N0,E1,N1)) and 'BRT' not in sg['t'] and 'APEx' not in sg['t']:
        cv2.polylines(im,[P(c)],False,(0,0,180),1,cv2.LINE_AA)
        m=c[len(c)//2]; x,y=P([m])[0]; cv2.putText(im,f"{sg['r']} {sg['a']}-{sg['b']} {sg['t']}",(x+4,y),cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,0,160),1)
for m in C['rer_marks']:
    x,y=P([m['p']])[0]
    if 0<x<W and 0<y<H: cv2.circle(im,(x,y),3,(0,0,200),-1); cv2.putText(im,m['label'][:50],(x+5,y-3),cv2.FONT_HERSHEY_SIMPLEX,0.3,(0,0,160),1)
cv2.imwrite(out,im)
