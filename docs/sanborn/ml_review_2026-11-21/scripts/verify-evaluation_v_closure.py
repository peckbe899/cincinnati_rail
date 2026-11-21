"""Independent check of the closure claim (eval-2): do the editor lines close into blocks?"""
import json, sys
import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union, polygonize, polygonize_full
sys.path.insert(0, 'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/evaluation')
import evallib as E

EV = 'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/evaluation/out/'
T = E.truth('44'); W, H = T['size']
ben = [Polygon(b['ring']) for b in T['blocks']]
for tag in ('ng1', 'guided'):
    polys = json.load(open(EV + f'44_{tag}_outlines.json'))
    edges = [dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange') for p in polys for s in p if s['state'] != 'short' and not s.get('paper_edge')]
    shown = E.clean(edges); sh = E.sheet('44', W, H)
    raw = [(e['a'], e['b']) for e in edges]
    segs = [(e['a'], e['b']) for e in shown + sh]
    for tol in (1.5, 10, 40):
        ext = []
        for a, b in segs:
            a = np.asarray(a, float); b = np.asarray(b, float); L = np.hypot(*(b - a))
            if L < 0.05: continue
            d = (b - a) / L; ext.append(LineString([a - d * tol, b + d * tol]))
        U = unary_union(ext)
        P = list(polygonize(U))
        big = [p for p in P if p.area >= 400]
        # how many of Ben's blocks have a polygon with IoU>0.8
        good = 0
        for bb in ben:
            best = max([bb.intersection(p).area / bb.union(p).area for p in big if p.intersects(bb)] or [0])
            good += best > 0.8
        print(tag, 'tol', tol, 'segments', len(ext), 'union type', U.geom_type, 'faces', len(P), 'faces>=400', len(big), 'ben IoU>0.8', good, flush=True)
    # raw edges (before clean): consecutive sides of one polygon share corners?
    for tol in (1.5,):
        ext = []
        for a, b in raw + [(e['a'], e['b']) for e in sh]:
            a = np.asarray(a, float); b = np.asarray(b, float); L = np.hypot(*(b - a))
            if L < 0.05: continue
            d = (b - a) / L; ext.append(LineString([a - d * tol, b + d * tol]))
        P = [p for p in polygonize(unary_union(ext)) if p.area >= 400]
        print(tag, 'raw N_edges (no clean) tol', tol, 'faces>=400', len(P))
    # how many outline polygons have NO short/paper-edge pieces (would survive whole)?
    whole = sum(1 for p in polys if all(s['state'] != 'short' and not s.get('paper_edge') for s in p))
    print(tag, 'outline polygons', len(polys), 'with no dropped piece', whole)
