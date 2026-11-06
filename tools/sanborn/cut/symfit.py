try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, math, numpy as np
from shapely.geometry import shape
from shapely.affinity import affine_transform, rotate
from shapely.ops import unary_union
from scipy.optimize import minimize
S=_ws.DATA
D=json.load(open(S+'deckpage/deck.json'));B=json.load(open(S+'deckpage/basin.json'))
def get(F,layers,east=None):
    out=[]
    for f in F['features']:
        p=f['properties']
        if p.get('layer') in layers:
            g=shape(f['geometry'])
            if g.geom_type.startswith('Line'): g=g.buffer(1.0)
            out.append(g)
    return unary_union(out)
def mirror(g,ang,x0,y0):
    a=math.radians(ang); c,s=math.cos(2*a),math.sin(2*a)
    # reflect about line through (x0,y0) at angle a
    return affine_transform(g,[c,s,s,-c, x0-c*x0-s*y0, y0-s*x0+c*y0])
def fit(g,ang0,x0,y00):
    def f(v):
        m=mirror(g,v[0],x0,v[1]); return g.symmetric_difference(m).area
    r=minimize(f,[ang0,y00],method='Nelder-Mead',options={'xatol':1e-3,'fatol':1})
    return r.x, r.fun, g.area
bld=get(D,['cut_building'])
print('building',fit(bld,-3.8,712905,bld.centroid.y),bld.centroid)
pl=get(B,['cut_plaza','cut_lincoln','cut_lawn','cut_terrace','cut_walk'])
pl2=get(B,['cut_lawn','cut_walk','cut_terrace'])
print('plaza group',fit(pl,-3.0,713150,4331857))
print('lawns walks',fit(pl2,-3.0,713150,4331857))
rd=get(B,['cut_road'])
print('roads',fit(rd,-3.0,713150,4331857))
