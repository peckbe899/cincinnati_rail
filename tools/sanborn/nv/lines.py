"""Collect every rail line in the north corridor (CUT to St. Bernard/Ivorydale) from the APEx KMZ, Cincinnati Rail.kmz and TRIMET 3D."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import re, json, numpy as np
from pyproj import Transformer
from shapely.geometry import LineString, box, mapping
SP=_ws.DATA
T=Transformer.from_crs(4326,26916,always_xy=True)
BOX=box(710500,4331500,717500,4342500)
out=[]
def parse(fn, src):
    s=open(fn,encoding='utf-8',errors='ignore').read()
    # walk folders to keep a path
    tokens=re.finditer(r'<Folder>|</Folder>|<Placemark>.*?</Placemark>|<name>(.*?)</name>',s,re.S)
    path=[]; pend=False
    for m in tokens:
        t=m.group(0)
        if t=='<Folder>': path.append('?'); pend=True; continue
        if t=='</Folder>': path.pop() if path else None; continue
        if t.startswith('<name>'):
            if pend and path: path[-1]=m.group(1); pend=False
            continue
        nm=re.search(r'<name>(.*?)</name>',t); nm=nm.group(1) if nm else ''
        for co in re.findall(r'<LineString>.*?<coordinates>(.*?)</coordinates>',t,re.S):
            pts=[tuple(map(float,c.split(',')[:3])) if c.count(',')>=2 else tuple(map(float,c.split(',')[:2]))+(None,) for c in co.split() if c.count(',')>=1]
            xy=[T.transform(p[0],p[1]) for p in pts]
            if len(xy)<2: continue
            g=LineString(xy)
            if not g.intersects(BOX): continue
            out.append(dict(src=src, folder='/'.join(path[-3:]), name=nm, c=[[round(x,1),round(y,1)] for x,y in g.coords], z=[p[2] for p in pts]))
parse(SP+'kmz_apex/doc.kml','APEx')
parse(SP+'kmz/cr.kml','CR')
for k,v in json.load(open(SP+'cut/trimet3d.json')).items():
    a=np.array(v); g=LineString(a[:,:2])
    if g.intersects(BOX): out.append(dict(src='TRIMET3D',folder='3D',name=k,c=[[round(x,1),round(y,1)] for x,y in a[:,:2]],z=[round(float(z),2) for z in a[:,2]]))
json.dump(out,open(SP+'nv/lines.json','w'))
from collections import Counter
for o in out:
    g=LineString(o['c']).intersection(BOX)
    if o['src']=='CR' and 'Line' in o['folder'] and 'RER' not in o['folder']: continue
    print(o['src'],'|',o['folder'],'|',o['name'],'|',round(g.length),[round(v) for v in g.bounds])
