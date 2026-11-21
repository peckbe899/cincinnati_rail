"""merge/impl/r2: editor lines along the edge of the map ground on the uncut (PDF) sheets, round 2 against round 1 and
outline-nesting (B) (21 Nov 2026).

    python -B edge_pdf.py TAG     reads r2/plates_TAG/  -> r2/edge_pdf_TAG.json

For every PDF sheet among the 104: the exported lines (step 4) whose middle lies within 40 px INSIDE the edge of the map
ground (N_mapground.png of the round-2 run, 1/8 size; B and round 1 used the same map_area.py mask: merge/v-eye checked
the masks pixel-identical), count and length; and the lines within 40 px of the edge on either side.
  r2       plates_TAG/N/outlines.json, blocks_noguide.step4 (staged)
  round1   merge/impl/plates/N/outlines.json, the same step 4
  B        outline-nesting/runs_plates/final/N/outlines.json, B's own step 4 (drops short and paper_edge only)
The five sheets merge/v-eye judged by eye (90 30 23 21 47) are listed apart.
"""
import json, os, sys
import numpy as np
import cv2
import common as C
TAG = sys.argv[1]; D = C.IMPL + f'plates_{TAG}/'; BN = C.step4_mod()
B_DIR = C.DATA + 'bench_2026-11-21/outline-nesting/runs_plates/final/'
step4_B = lambda P: [s for p in P for s in p if not (s['state'] == 'short' or s.get('paper_edge'))]
L = lambda e: float(np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1]))
res = {}
for n in sorted(os.listdir(D)):
    mg = D + n + f'/{n}_mapground.png'
    if not os.path.exists(mg): continue
    m8 = cv2.imread(mg, 0) > 0; H, W = cv2.imread(C.DATA + f'cufp/22-{n}.jpg', cv2.IMREAD_REDUCED_GRAYSCALE_8).shape[:2]
    din = cv2.distanceTransform(np.pad(m8.astype(np.uint8), 1), cv2.DIST_L2, 5)[1:-1, 1:-1] * 8          # inside: distance to the map edge (full px, about)
    dout = cv2.distanceTransform(np.pad((~m8).astype(np.uint8), 1, constant_values=1), cv2.DIST_L2, 5)[1:-1, 1:-1] * 8
    sx, sy = m8.shape[1], m8.shape[0]
    def where(e):
        x, y = (e['a'][0] + e['b'][0]) / 2 / 8, (e['a'][1] + e['b'][1]) / 2 / 8; i, j = int(np.clip(y, 0, sy - 1)), int(np.clip(x, 0, sx - 1))
        return (m8[i, j] and din[i, j] <= 40), (din[i, j] <= 40 if m8[i, j] else dout[i, j] <= 40)
    row = {}
    for v, f, s4 in (('r2', D + n + '/outlines.json', BN.step4), ('round1', C.IMPL1 + f'plates/{n}/outlines.json', BN.step4), ('B', B_DIR + f'{n}/outlines.json', step4_B)):
        if not os.path.exists(f): continue
        E = s4(json.load(open(f, encoding='utf8'))); w = [where(e) for e in E]
        row[v] = dict(lines=len(E), len=round(sum(L(e) for e in E)), inside40=int(sum(bool(a) for a, _ in w)), inside40_len=round(sum(L(e) for e, (a, _) in zip(E, w) if a)),
                      inside40_orange=sum(1 for e, (a, _) in zip(E, w) if a and e['state'] != 'green'), band40=int(sum(bool(b) for _, b in w)), band40_len=round(sum(L(e) for e, (_, b) in zip(E, w) if b)))
    res[n] = row
tot = lambda names, v, k: sum(res[n][v][k] for n in names if v in res[n])
five = [n for n in ('90', '30', '23', '21', '47') if n in res]
S = {grp: {v: {k: tot(names, v, k) for k in ('lines', 'len', 'inside40', 'inside40_len', 'inside40_orange', 'band40', 'band40_len')} for v in ('r2', 'round1', 'B')}
     for grp, names in (('all PDF sheets (%d)' % len(res), list(res)), ('the five v-eye sheets', five))}
json.dump(dict(per_sheet=res, summary=S), open(C.IMPL + f'edge_pdf_{TAG}.json', 'w'), indent=1); print(json.dumps(S, indent=1))
