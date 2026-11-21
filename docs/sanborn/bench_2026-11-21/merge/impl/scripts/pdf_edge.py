"""merge/impl: the map-edge fix on the 24 uncut PDF sheets at 200 ft: lines kept and lost against outline-nesting (21 Nov 2026).

    python -B pdf_edge.py      -> merge/impl/pdf_edge.json, merge/impl/pdf_edge/N_edge.jpg

Lines are step 4's (what N_edges.json holds):
  batch    unet_data/N_edges.json (the batch)
  nesting  outline-nesting/runs_plates/final/N/outlines.json, its step 4 (drop short and paper_edge)
  merged   merge/impl/plates/N/outlines.json, the staged step 4 (blocks_noguide.step4)
A line of one set is 'in' another when at least half of its length (1 px samples) has a line of the other within 6 px
and 20 degrees (verify-outline-nesting/lost_lines.py's rule). Where a line lies, by its middle, against the map ground
(merged: plates/N/N_mapground.png, made live by map_area.py; nesting used visual-pdf/maparea_check/N_mask8.png, and the
two are compared): off_map, edge_band (on the map ground but within 40 px of its edge), on_map.
Reported per sheet and in total:
  - the batch lines nesting lost in the edge band (verify-outline-nesting: 201 lines, 64k px) and how many merged has back
  - merged lines not in nesting (kept by the fix) and nesting lines not in merged (lost), by place
  - merged sides along the map edge that are not paper_edge, by state (kept by step 4, or dropped as 'not on a line')
"""
import json, os
import numpy as np
import cv2
from scipy.spatial import cKDTree
import common as C
BN = C.step4_mod()
PDF200 = '19 20 21 22 23 24 27 30 32 36 41 42 72 73 74 77 78 79 81 86 88 89 90 91'.split()
NEST = C.DATA + 'bench_2026-11-21/outline-nesting/runs_plates/final/'; MASKS = C.DATA + 'bench_2026-11-21/visual-pdf/maparea_check/'
O = C.IMPL + 'pdf_edge/'; os.makedirs(O, exist_ok=True)
L = lambda e: float(np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1]))
step4_old = lambda polys: [dict(a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange') for p in polys for s in p if not (s['state'] == 'short' or s.get('paper_edge'))]


def samples(segs):
    P, Dv, I = [], [], []
    for i, e in enumerate(segs):
        a, b = np.asarray(e['a'], float), np.asarray(e['b'], float); l = np.hypot(*(b - a))
        if l < 1: continue
        t = np.linspace(0, 1, max(2, int(l))); P.append(a + np.outer(t, b - a)); Dv.append(np.tile((b - a) / l, (len(t), 1))); I.append(np.full(len(t), i))
    if not P: return np.zeros((0, 2)), np.zeros((0, 2)), np.zeros(0, int)
    return np.vstack(P), np.vstack(Dv), np.concatenate(I)


def found_in(X, Y):
    """share of each line of X with a line of Y within 6 px and 20 degrees"""
    xp, xd, xi = samples(X); yp, yd, _ = samples(Y)
    if not len(xp) or not len(yp): return np.zeros(len(X))
    tr = cKDTree(yp); ok = np.zeros(len(xp), bool)
    for k, nb in enumerate(tr.query_ball_point(xp, 6.0)):
        if nb and np.max(np.abs(yd[nb] @ xd[k])) >= np.cos(np.radians(20)): ok[k] = True
    return np.bincount(xi, ok, minlength=len(X)) / np.maximum(np.bincount(xi, minlength=len(X)), 1)


res = {}; T = {}
for n in PDF200:
    polys = json.load(open(C.IMPL + f'plates/{n}/outlines.json', encoding='utf8')); M = BN.step4(polys)
    Nn = step4_old(json.load(open(NEST + f'{n}/outlines.json', encoding='utf8'))); Bt = json.load(open(C.U + f'{n}_edges.json', encoding='utf8'))
    m8 = cv2.imread(C.IMPL + f'plates/{n}/{n}_mapground.png', 0) > 127; c8 = cv2.imread(MASKS + f'{n}_mask8.png', 0) > 127
    inner = cv2.erode(m8.astype(np.uint8), np.ones((11, 11), np.uint8)) > 0       # 5 px at 1/8 = 40 full px
    def where(e):
        m = ((np.array(e['a']) + np.array(e['b'])) / 2 / 8).astype(int); y, x = min(m8.shape[0] - 1, max(0, m[1])), min(m8.shape[1] - 1, max(0, m[0]))
        return 'off_map' if not m8[y, x] else ('edge_band' if not inner[y, x] else 'on_map')
    tally = lambda lines, sel: {w: [sum(1 for e, s in zip(lines, sel) if s and where(e) == w), round(sum(L(e) for e, s in zip(lines, sel) if s and where(e) == w))] for w in ('off_map', 'edge_band', 'on_map')}
    bt_in_n = found_in(Bt, Nn) >= 0.5; bt_in_m = found_in(Bt, M) >= 0.5; m_in_n = found_in(M, Nn) >= 0.5; n_in_m = found_in(Nn, M) >= 0.5
    lost_edge = [bool(not a and where(e) == "edge_band") for e, a in zip(Bt, bt_in_n)]
    back = [bool(l and b) for l, b in zip(lost_edge, bt_in_m)]
    # merged sides along the map edge (middle in the edge band), not paper_edge: their states
    sides = [s for p in polys for s in p if not s.get('paper_edge') and where(s) == 'edge_band']
    st = {}
    for s in sides: k = s['state']; st.setdefault(k, [0, 0]); st[k][0] += 1; st[k][1] += round(L(s))
    r = dict(mask_same_as_nesting=bool((m8 == c8).all()), mask_px_differ=int((m8 != c8).sum()), batch_lines=len(Bt), nesting_lines=len(Nn), merged_lines=len(M),
             batch_lost_by_nesting_in_edge_band=[sum(lost_edge), round(sum(L(e) for e, l in zip(Bt, lost_edge) if l))],
             of_those_back_in_merged=[sum(back), round(sum(L(e) for e, b in zip(Bt, back) if b))],
             merged_not_in_nesting=tally(M, ~m_in_n), nesting_not_in_merged=tally(Nn, ~n_in_m), merged_all=tally(M, np.ones(len(M), bool)), nesting_all=tally(Nn, np.ones(len(Nn), bool)),
             merged_edge_band_sides_by_state=st)
    res[n] = r
    for k, v in r.items():
        if isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v): T.setdefault(k, [0, 0]); T[k][0] += v[0]; T[k][1] += v[1]
        elif isinstance(v, dict) and k != 'merged_edge_band_sides_by_state':
            for w, (c, l) in v.items(): T.setdefault(f'{k}.{w}', [0, 0]); T[f'{k}.{w}'][0] += c; T[f'{k}.{w}'][1] += l
        elif k == 'merged_edge_band_sides_by_state':
            for w, (c, l) in v.items(): T.setdefault(f'edge_band_sides.{w}', [0, 0]); T[f'edge_band_sides.{w}'][0] += c; T[f'edge_band_sides.{w}'][1] += l
        elif k in ('batch_lines', 'nesting_lines', 'merged_lines'): T[k] = T.get(k, 0) + v
    T['sheets_mask_same'] = T.get('sheets_mask_same', 0) + r['mask_same_as_nesting']
    print(n, r['mask_same_as_nesting'], r['batch_lost_by_nesting_in_edge_band'], r['of_those_back_in_merged'], 'merged not in nesting', r['merged_not_in_nesting'], 'nesting not in merged', r['nesting_not_in_merged'], flush=True)
    if n in ('90', '79', '89', '30'):   # a picture: map edge white, merged lines green (orange), nesting lines it does not have blue
        im = (cv2.imread(C.DATA + f'cufp/22-{n}.jpg', cv2.IMREAD_REDUCED_COLOR_8) * 0.6 + 90).astype(np.uint8); mm = cv2.resize(m8.astype(np.uint8), (im.shape[1], im.shape[0]), interpolation=cv2.INTER_NEAREST)
        cv2.drawContours(im, cv2.findContours(mm, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)[0], -1, (255, 255, 255), 2)
        for e, ok in zip(Nn, n_in_m):
            if not ok: cv2.line(im, (int(e['a'][0] / 8), int(e['a'][1] / 8)), (int(e['b'][0] / 8), int(e['b'][1] / 8)), (255, 80, 0), 3, cv2.LINE_AA)
        for e, ok in zip(M, m_in_n): cv2.line(im, (int(e['a'][0] / 8), int(e['a'][1] / 8)), (int(e['b'][0] / 8), int(e['b'][1] / 8)), (0, 150, 0) if ok else (0, 140, 255), 2 if ok else 3, cv2.LINE_AA)
        cv2.imwrite(O + f'{n}_edge.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 85])
json.dump(dict(total=T, per_sheet=res), open(C.IMPL + 'pdf_edge.json', 'w'), indent=1); print(json.dumps(T, indent=1))
