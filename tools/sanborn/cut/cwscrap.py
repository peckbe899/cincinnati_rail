try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben (18 October): scrap every street between Spring Grove Ave and Beekman St, Hopple St and Dreman St (cut at those streets),
# except Geringer St and J1 (they box in the viaduct), to rethink the Manhattan-style layout. Dry run unless --apply.
import json, sys, shutil
from shapely.geometry import shape, LineString, Point, mapping
from shapely.ops import unary_union, polygonize
S = _ws.DATA
D = json.load(open(S + 'deckpage/deck.json')); B = json.load(open(S + 'deckpage/basin.json')); P = json.load(open(S + 'deckpage/plots.json'))
LAY = json.load(open(S + 'plots/live5/deck/layout.json')); ED = LAY['streets']
FE = D['features'] + B['features']
SF = {f['properties']['id']: f for f in FE if f['properties'].get('layer') == 'street'}
def C(i): return [tuple(q) for q in (ED.get(i, {}).get('c') or SF[i]['geometry']['coordinates'])]
BOUND = ['S22014', 'SB0779', 'SB0778', 'SBW002', 'SBW001', 'SB0650', 'SB0934', 'SB0937', 'SB0938', 'SB0935']
KEEP = set(BOUND) | {'SB0736', 'S056'}
def ext(c, d=40):
    import numpy as np
    a, b = np.array(c[0]), np.array(c[1]); y, z = np.array(c[-2]), np.array(c[-1])
    return LineString([tuple(a + (a - b) / np.linalg.norm(a - b) * d)] + c[1:-1] + [tuple(z + (z - y) / np.linalg.norm(z - y) * d)])
faces = list(polygonize(unary_union([ext(C(i)) for i in BOUND])))
reg = [g for g in faces if g.contains(Point(712100, 4335700))][0]
print('region', round(reg.area), [round(v) for v in reg.bounds])
out = {'remove': [], 'cut': []}
for i, f in SF.items():
    if i in KEEP or ED.get(i, {}).get('del'): continue
    l = LineString(C(i))
    if not l.intersects(reg): continue
    inside = l.intersection(reg).length
    if inside < 1: continue
    if inside > l.length - 1: out['remove'].append(i)
    else: out['cut'].append((i, round(inside), round(l.length)))
print('remove', len(out['remove']), sorted((i, SF[i]['properties'].get('name')) for i in out['remove']))
print('cut', out['cut'], [SF[i]['properties'].get('name') for i, _, _ in out['cut']])
print('edited in db:', [i for i in out['remove'] + [c[0] for c in out['cut']] if i in ED])
blocks = [f['properties']['id'] for f in FE if f['properties'].get('layer') == 'block' and f.get('geometry') and shape(f['geometry']).representative_point().within(reg)]
print('blocks', len(blocks), 'held in db:', [b for b in blocks if b in LAY.get('blocks', {})])
txt = json.dumps(LAY.get('plotOps', [])) + json.dumps(list(LAY.get('plots', {})))
print('lot edits in db:', [b for b in blocks if '"' + b + '-' in txt][:20])
json.dump(dict(region=mapping(reg), **out, blocks=blocks), open(S + 'cut/cwscrap_plan.json', 'w'), default=float)
