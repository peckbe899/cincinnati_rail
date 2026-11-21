"""Score what the editor would show on plate 44 against Ben's street map (streetmap/22-44.json).

    python -B score44.py TAG OUTLINES_JSON [LINES_PNG] [AREA_PNG]
"""
import json, sys
import numpy as np
import cv2
from shapely.geometry import Polygon
import evallib as E

TAG, OJ = sys.argv[1], sys.argv[2]; LP = sys.argv[3] if len(sys.argv) > 3 else None; AP = sys.argv[4] if len(sys.argv) > 4 else None
T = E.truth('44'); W, H = T['size']
ben_all = [(l['a'], l['b']) for l in T['lines']]
ben_in = [(l['a'], l['b']) for l in T['lines'] if l['kind'] != 'sheet_edge']
ben_blocks = [Polygon(b['ring']) for b in T['blocks']]
res = dict(tag=TAG)

# what blocks_noguide.py step 4 writes (N_edges.json) and the editor then shows (clean + the sheet's outline)
polys = json.load(open(OJ, encoding='utf8')); edges = []
for poly in polys:
    for s in poly:
        if s['state'] == 'short' or s.get('paper_edge'): continue
        edges.append(dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange'))
shown = E.clean(edges); sh = E.sheet('44', W, H)
seg = lambda L: [(e['a'], e['b']) for e in L]
res['n_edges_json'] = len(edges); res['n_shown_lines'] = len(shown); res['n_green'] = sum(e['state'] == 'green' for e in shown); res['n_sheet_lines'] = len(sh)
for tol in (4.0, 8.0):
    k = f'tol{int(tol)}'
    # recall of Ben's interior street sides by the network's lines; precision of the network's lines against all of Ben's lines
    r_in = E.line_scores(seg(shown), ben_in, tol)
    r_all = E.line_scores(seg(shown), ben_all, tol)
    r_ed = E.line_scores(seg(shown) + seg(sh), ben_all, tol)
    g = [e for e in shown if e['state'] == 'green']; o = [e for e in shown if e['state'] != 'green']
    res[k] = dict(recall_interior=r_in['recall'], precision=r_all['precision'], editor_with_sheet_recall_all=r_ed['recall'], editor_with_sheet_precision=r_ed['precision'],
                  green_precision=E.line_scores(seg(g), ben_all, tol)['precision'], orange_precision=E.line_scores(seg(o), ben_all, tol)['precision'] if o else None,
                  shown_len=r_all['pred_len'], ben_len_all=r_all['truth_len'], ben_len_interior=r_in['truth_len'],
                  recall_by_kind={kd: E.line_scores(seg(shown), [(l['a'], l['b']) for l in T['lines'] if l['kind'] == kd], tol)['recall'] for kd in ('printed', 'drawn', 'sheet_edge')})

# edit-cost proxy at 4 px: shown lines Ben would delete (< 50% of their length on one of his lines), his lines he would
# have to draw (< 50% of their length covered), and the length involved
P, Pd, Pi = E.sample(seg(shown), 2.0); Q, Qd, Qi = E.sample(ben_all, 2.0)
pm = E.matched(P, Pd, Q, Qd, 4.0, 20.0); qm = E.matched(Q, Qd, P, Pd, 4.0, 20.0)
fp = [k for k in range(len(shown)) if (Pi == k).any() and pm[Pi == k].mean() < 0.5]
fn = [k for k in range(len(ben_all)) if (Qi == k).any() and qm[Qi == k].mean() < 0.5]
res['edit_cost_tol4'] = dict(shown_lines_to_delete=len(fp), shown_lines_kept=len(shown) - len(fp), ben_lines_to_draw=len(fn), ben_lines=len(ben_all),
                             ben_lines_to_draw_excluding_sheet=sum(1 for k in fn if T['lines'][k]['kind'] != 'sheet_edge'))
# blocks: (a) the outline polygons the networks assert; (b) what the editor lines close into (street_map.py's rule)
rings = []
for poly in polys:
    pts = [s['a'] for s in poly]
    if len(pts) >= 3:
        p = Polygon(pts); p = p if p.is_valid else p.buffer(0)
        if p.area > 0: rings.append(p)
m_out, ious = E.block_match(rings, ben_blocks); res['blocks_outline_polys'] = m_out
closed = E.polys_from_lines(seg(shown) + seg(sh)); m_cl, _ = E.block_match(closed, ben_blocks); res['blocks_closed_by_editor_lines'] = m_cl
# Ben's own lines closed the same way, as a check that the rule gives 55
res['check_ben_lines_close_into'] = len(E.polys_from_lines(ben_all))
res['per_ben_block_best_iou'] = [round(float(x), 3) for x in ious]

if LP:
    pl = cv2.imread(LP, 0) > 127
    res['line_map_vs_ben'] = {f'tol{t}': E.map_scores(pl, ben_all, W, H, t) for t in (3, 4)}
if AP:
    pa = cv2.imread(AP, 0); h, w = pa.shape
    tb = np.zeros((h, w), np.uint8)
    for b in T['blocks']: cv2.fillPoly(tb, [(np.array(b['ring']) / 2).round().astype(np.int32)], 1)
    alpha = cv2.resize(np.load(E.SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (w, h)) > 0.5
    lab = cv2.imread(E.U + '44_label.png', 0); pr = pa > 127; m = alpha
    iou = lambda a, b: float((a & b).sum() / max(1, (a | b).sum()))
    res['area_vs_ben'] = dict(accuracy_on_paper=round(float((pr[m] == (tb[m] == 1)).mean()), 4), iou_block=round(iou(pr & m, (tb == 1) & m), 4), iou_street=round(iou(~pr & m, (tb == 0) & m), 4))
    sc = lab != 255
    res['area_vs_label'] = dict(accuracy=round(float((pr[sc] == (lab[sc] == 1)).mean()), 4), iou_street=round(iou(~pr & sc, (lab == 0) & sc), 4))
print(json.dumps(res, indent=1))
json.dump(res, open(f'out/score44_{TAG}.json', 'w'), indent=1)
