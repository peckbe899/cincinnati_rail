try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
SP=_ws.DATA
x0,y0,x1,y1=map(float,sys.argv[1:5]); out=sys.argv[5]
T=json.load(open(SP+'deckpage/tracks.json'))['features']
fig,ax=plt.subplots(figsize=(12,12*(y1-y0)/(x1-x0)))
col={'apex':'#16252a','lower':'#b0207a','passing':'#777','bridge':'#999'}
for f in T:
    p=f['properties']; g=f['geometry']
    if g['type']=='LineString':
        c=g['coordinates']; ax.plot([q[0] for q in c],[q[1] for q in c],color=col.get(p['layer'],'c'),lw=0.8)
    elif g['type']=='Point' and p.get('label'):
        ax.plot(*g['coordinates'],'o',ms=3,color='r'); ax.text(g['coordinates'][0],g['coordinates'][1],p['label'][:60],fontsize=6)
try:
    Cx=json.load(open(SP+'deckpage/context.json'))
    for t in Cx['tracks']:
        if t['sys']=='rer' and t['line'] in ('B','D','B D'): ax.plot([q[0] for q in t['c']],[q[1] for q in t['c']],color='#2a7ab0',lw=0.8)
    for t in Cx['plats']:
        if t['sys']=='rer': ax.fill([q[0] for q in t['c']],[q[1] for q in t['c']],color='#2a7ab0',alpha=0.4)
except Exception as e: print(e)
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); plt.savefig(out,dpi=90)
