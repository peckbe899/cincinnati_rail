"""Intersections between named streets in OSM (and the demolished 1912 streets of the traced basin layer)."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import json, sys, os, collections, numpy as np, pickle
sys.path.insert(0,(_ws.CODE + 'sbg'))
from names import key, base
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import unary_union
from shapely.strtree import STRtree
SP=_ws.DATA
ROADS={'residential','secondary','primary','tertiary','unclassified','service','pedestrian','living_street','trunk','secondary_link','primary_link','tertiary_link','construction'}
def lines_osm():
    G=collections.defaultdict(list)
    for f in json.load(open(SP+'basin/osm_basin.geojson'))['features']:
        p=f['properties']; n=p.get('name')
        if not n or p.get('highway') not in ROADS: continue
        G[key(n)].append(LineString(f['geometry']['coordinates']))
    return G
def lines_1912():
    G=collections.defaultdict(list)
    for f in json.load(open(SP+'deckpage/basin.json'))['features']:
        p=f['properties']
        if p.get('layer')!='street' or not p.get('name'): continue
        if p.get('geom_src')=='OSM centreline': continue
        G[key(p['name'])].append(LineString(f['geometry']['coordinates']))
    return G
def inters(G, tol=0.5):
    keys=list(G); geoms=[unary_union(G[k]) for k in keys]
    tree=STRtree(geoms); out=collections.defaultdict(list)
    for i,g in enumerate(geoms):
        for j in tree.query(g.buffer(tol)):
            j=int(j)
            if j<=i: continue
            x=g.intersection(geoms[j].buffer(tol)) if tol>0 else g.intersection(geoms[j])
            if x.is_empty: continue
            pts=[]
            for part in getattr(x,'geoms',[x]):
                c=part.centroid; pts.append((c.x,c.y))
            # cluster within 40 m
            cl=[]
            for p in pts:
                for c in cl:
                    if np.hypot(p[0]-c[0][0],p[1]-c[0][1])<40: c.append(p); break
                else: cl.append([p])
            k=tuple(sorted((keys[i],keys[j])))
            for c in cl: out[k].append(tuple(np.mean(c,axis=0)))
    return out
if __name__=='__main__':
    O=inters(lines_osm()); print('osm pairs',len(O))
    T=inters(lines_1912()); print('1912 pairs',len(T))
    pickle.dump(dict(osm=dict(O),t12=dict(T)),open('fit/osmx.pkl','wb'))
