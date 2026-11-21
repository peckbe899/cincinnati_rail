"""Independent line checks on plate 44 (eval-2, eval-4, eval-9). Full-size, CPU, reads only.
All recalls here use ONE method (Ben's lines sampled every 1 px; a sample is found if a drawn pixel lies within TOL px,
Euclidean, no direction test), so the raw line map, the area boundary, the watershed boundary and the editor lines are
compared like for like. The editor lines are also scored with an exact point-to-segment distance + 20 degree direction test."""
import json, sys, gc
import numpy as np, cv2
from shapely.geometry import LineString
from shapely.strtree import STRtree
sys.path.insert(0, 'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/evaluation')
import evallib as E   # only clean() and sheet() (verified identical to edit_server.py's)
SP = E.SP; U = E.U
EV = 'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/evaluation/'
T = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8')); W, H = T['size']
ben_all = [(np.array(l['a'], float), np.array(l['b'], float)) for l in T['lines']]
ben_in = [(np.array(l['a'], float), np.array(l['b'], float)) for l in T['lines'] if l['kind'] != 'sheet_edge']
def samples(segs, step=1.0):
    out = []
    for a, b in segs:
        L = np.hypot(*(b - a)); m = max(1, int(np.ceil(L / step))); t = (np.arange(m) + 0.5) / m; out.append(a + np.outer(t, b - a))
    return np.vstack(out)
Qin = samples(ben_in); qx = np.clip(Qin[:, 0].round().astype(int), 0, W - 1); qy = np.clip(Qin[:, 1].round().astype(int), 0, H - 1)
def recall_of(mask, tol=4.0):
    d = cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5); r = float((d[qy, qx] <= tol).mean()); del d; return round(r, 4)
def boundary(m):
    return cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
alpha = cv2.resize(np.load(SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
# Ben's lines drawn as edgenet draws its target (3 px), for an edgenet-geometry precision
b3 = np.zeros((H, W), np.uint8)
for a, b in ben_all: cv2.line(b3, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), 1, 3)
near_b3 = cv2.dilate(b3, np.ones((7, 7), np.uint8)) > 0; del b3
b1 = np.zeros((H, W), np.uint8)
for a, b in ben_all: cv2.line(b1, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), 1, 1)
dB = cv2.distanceTransform((b1 == 0).astype(np.uint8), cv2.DIST_L2, 5); del b1
res = {}
runs = {'ng1': dict(lines=U + '44_lines_lines_ng1.png', area=U + '44_pred_area_ng1.png', bm=EV + 'out/44_ng1_blockmask.png', oj=EV + 'out/44_ng1_outlines.json'),
        'guided': dict(lines=U + '44_lines_lines_v2.png', area=U + '44_pred_edge_v1.png', bm=EV + 'out/44_guided_blockmask.png', oj=EV + 'out/44_guided_outlines.json')}
for k, r in runs.items():
    d = {}
    pl = cv2.imread(r['lines'], 0) > 127
    d['linemap_precision_vs_ben_edgenet_geometry'] = round(float(near_b3[pl].mean()), 4)
    d['linemap_precision_vs_ben_1px_tol3'] = round(float((dB[pl] <= 3).mean()), 4)
    d['linemap_precision_vs_ben_1px_tol4'] = round(float((dB[pl] <= 4).mean()), 4)
    d['recall_interior_tol4_raw_linemap'] = recall_of(pl); del pl; gc.collect()
    pa = cv2.resize(cv2.imread(r['area'], 0), (W, H), interpolation=cv2.INTER_LINEAR) > 127
    d['recall_interior_tol4_area_boundary'] = recall_of(boundary(pa & alpha)); del pa; gc.collect()
    bm = cv2.imread(r['bm'], 0); d['blockmask_shape'] = list(bm.shape)
    if bm.shape != (H, W): bm = cv2.resize(bm, (W, H), interpolation=cv2.INTER_NEAREST)
    bm = bm > 127
    d['recall_interior_tol4_watershed_boundary'] = recall_of(boundary(bm)); del bm; gc.collect()
    polys = json.load(open(r['oj']))
    allsides = [(np.array(s['a']), np.array(s['b'])) for p in polys for s in p]
    edges = [dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange') for p in polys for s in p if s['state'] != 'short' and not s.get('paper_edge')]
    shown = E.clean(edges)
    def rast(segs):
        m = np.zeros((H, W), np.uint8)
        for a, b in segs: cv2.line(m, tuple(np.round(np.asarray(a, float)).astype(int)), tuple(np.round(np.asarray(b, float)).astype(int)), 1, 1)
        return m > 0
    d['recall_interior_tol4_all_outline_sides_incl_short'] = recall_of(rast(allsides))
    d['recall_interior_tol4_editor_lines_no_dir'] = recall_of(rast([(e['a'], e['b']) for e in shown]))
    # exact distance + direction test for the editor lines
    S = [LineString([e['a'], e['b']]) for e in shown]; dirs = [np.subtract(e['b'], e['a']) / np.hypot(*np.subtract(e['b'], e['a'])) for e in shown]
    tree = STRtree(S); c20 = np.cos(np.radians(20))
    def rec_dir(segs):
        hit = tot = 0.0
        for a, b in segs:
            L = np.hypot(*(b - a)); dv = (b - a) / L; m = max(1, int(np.ceil(L / 2))); pts = a + np.outer((np.arange(m) + 0.5) / m, b - a)
            for p in pts:
                from shapely.geometry import Point
                P = Point(p); ok = False
                for j in tree.query(P.buffer(4.0)):
                    j = int(j)
                    if abs(dirs[j] @ dv) >= c20 and S[j].distance(P) <= 4.0: ok = True; break
                hit += ok; tot += 1
        return round(hit / tot, 4)
    d['recall_interior_tol4_editor_lines_exact_dir20'] = rec_dir(ben_in)
    # precision of the editor lines against all Ben lines (exact, with direction)
    BS = [LineString([tuple(a), tuple(b)]) for a, b in ben_all]; bd = [(b - a) / np.hypot(*(b - a)) for a, b in ben_all]; bt = STRtree(BS)
    from shapely.geometry import Point
    hit = tot = 0.0; ghit = gtot = 0.0
    for e in shown:
        a, b = np.array(e['a'], float), np.array(e['b'], float); L = np.hypot(*(b - a)); dv = (b - a) / L; m = max(1, int(np.ceil(L / 2)))
        for p in a + np.outer((np.arange(m) + 0.5) / m, b - a):
            P = Point(p); ok = any(abs(bd[int(j)] @ dv) >= c20 and BS[int(j)].distance(P) <= 4.0 for j in bt.query(P.buffer(4.0)))
            hit += ok; tot += 1
            if e['state'] == 'green': ghit += ok; gtot += 1
    d['precision_tol4_editor_lines_exact_dir20'] = round(hit / tot, 4); d['green_precision_tol4_exact_dir20'] = round(ghit / max(1, gtot), 4)
    d['n_shown'] = len(shown); d['n_green'] = sum(e['state'] == 'green' for e in shown)
    d['outline_polys'] = len(polys); d['short_pieces'] = sum(s['state'] == 'short' for p in polys for s in p)
    per = lambda keep: sum(np.hypot(*np.subtract(s['b'], s['a'])) for p in polys for s in p if keep(s))
    d['perimeter_share_kept_for_editor'] = round(per(lambda s: s['state'] != 'short' and not s.get('paper_edge')) / per(lambda s: True), 4)
    d['perimeter_share_short'] = round(per(lambda s: s['state'] == 'short') / per(lambda s: True), 4)
    res[k] = d; print(k, json.dumps(d), flush=True)
json.dump(res, open('v_lines.json', 'w'), indent=1)
