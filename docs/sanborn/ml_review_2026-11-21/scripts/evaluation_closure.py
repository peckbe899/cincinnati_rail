"""How many of Ben's blocks would the editor lines close into, if line ends were allowed to reach further (tol px)?"""
import json, sys, numpy as np, evallib as E
from shapely.geometry import Polygon
OJ = sys.argv[1]; T = E.truth('44'); W, H = T['size']; ben = [Polygon(b['ring']) for b in T['blocks']]
polys = json.load(open(OJ)); edges = [dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange') for p in polys for s in p if s['state'] != 'short' and not s.get('paper_edge')]
shown = E.clean(edges); sh = E.sheet('44', W, H); seg = [(e['a'], e['b']) for e in shown + sh]
allp = [(s['a'], s['b']) for p in polys for s in p] + [(e['a'], e['b']) for e in sh]
out = {}
for tol in (1.5, 5, 10, 20, 40):
    m, _ = E.block_match(E.polys_from_lines(seg, tol), ben); m2, _ = E.block_match(E.polys_from_lines(allp, tol), ben)
    out[tol] = dict(editor_lines=m, with_short_pieces=m2)
    print(tol, 'editor lines:', {k: m[k] for k in ('pred_polys', 'iou_gt_0_8', 'iou_gt_0_9', 'median_best_iou')}, '| incl. short pieces:', {k: m2[k] for k in ('pred_polys', 'iou_gt_0_8', 'iou_gt_0_9')})
json.dump(out, open(OJ.replace('_outlines.json', '_closure.json'), 'w'), indent=1)
