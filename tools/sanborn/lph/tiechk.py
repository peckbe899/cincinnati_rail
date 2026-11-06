try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# same-name crossings read on two sheets: world distance between the two readings (new vol-3 frames against everything)
import json, glob, collections, sys, numpy as np
SP=_ws.DATA
sys.path.insert(0,_ws.CODE+'sbg')
from names import key2
T={}
for fn in ('sbg/fit/tf.json','lph/tf_all.json','lph/tf_ext.json','lph/tf_ext2.json','lph/tf_ext3.json'): T.update(json.load(open(SP+fn)))
def ap(p,x,y):
    if len(p)==6: return np.array([p[0]*x+p[1]*y+p[4], p[2]*x+p[3]*y+p[5]])
    a,c,tx,ty=p; return np.array([a*x+c*y+tx, c*x-a*y+ty])
NEW=set(json.load(open(SP+'lph/tf_ext3.json')))
W=collections.defaultdict(list)
for f in glob.glob(SP+'sbg/picks/s*.json'):
    d=json.load(open(f)); s=d.get('sheet') or f.split('/s')[-1].split('.')[0]
    for p in d.get('intersections',[]):
        fr=f"{s}{p['part'][0]}" if p.get('part') else str(s)
        if fr not in T: continue
        a,b=key2(p['a']),key2(p['b'])
        if not a or not b or a==b: continue
        W[tuple(sorted((a,b)))].append((fr, ap(T[fr],p['x'],p['y'])))
out=[]
for k,v in W.items():
    for i in range(len(v)):
        for j in range(i+1,len(v)):
            if v[i][0]==v[j][0] or not ({v[i][0],v[j][0]}&NEW): continue
            d=float(np.hypot(*(v[i][1]-v[j][1])))
            out.append((round(d,1),k,v[i][0],v[j][0]))
out.sort(reverse=True)
for o in out[:int(sys.argv[1]) if len(sys.argv)>1 else 30]: print(o)
print('pairs',len(out),'over 8 m',sum(o[0]>8 for o in out))
