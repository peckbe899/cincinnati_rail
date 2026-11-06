"""Load all picks into flat records with frame ids (split sheets get u/l frames)."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import json, glob, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from names import key
HERE = _ws.data_dir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DECK=[33,34,35,47,57,58,67,68,69,77,201,202,211,212,221,222]
YSPLIT={13:2200,14:2200,31:2400,32:2500,111:2200,112:2250}
def is_loc(s): return 200<=int(s)<300
def frame_of(s,part,y):
    if s in YSPLIT or s==17:
        if part: return f'{s}{part[0]}'
        if s==17: return None
        return f'{s}u' if y<YSPLIT[s] else f'{s}l'
    return str(s)
def load():
    recs=[]; other=[]
    for f in glob.glob(os.path.join(HERE,'picks','s*.json')):
        d=json.load(open(f)); s=int(d.get('sheet') or f.split('/s')[-1].split('.')[0])
        for p in d.get('intersections',[]):
            fr=frame_of(s,p.get('part'),p['y'])
            recs.append(dict(s=s,fr=fr,a=p['a'],b=p['b'],ka=key(p['a']),kb=key(p['b']),x=float(p['x']),y=float(p['y']),kind=p.get('kind','cross')))
        for k in ('alleys','bends','ends','widths'):
            for q in d.get(k,[]):
                q=dict(q); q['s']=s; q['typ']=k; other.append(q)
    return recs, other
def pair(r): return tuple(sorted((r['ka'],r['kb'])))
if __name__=='__main__':
    R,O=load(); print(len(R),len(O)); import collections
    print(collections.Counter(r['fr'] for r in R if r['fr'] and not r['fr'].isdigit()))
