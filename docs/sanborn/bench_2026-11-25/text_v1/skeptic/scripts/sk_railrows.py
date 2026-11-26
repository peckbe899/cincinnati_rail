"""Skeptic (26 Nov 2026): does the classifier's use of Ben's rail as training labels (200 'rail' junk rows from
picks22_guided/22-N/rail_ben.json on 44 and 5, weight 3) change finder3's mask where step 4 scores it?
Compares the shipped finder3 mask (classifier/out/finder3) with finder3 refitted WITHOUT those rows (skeptic/out/v3norail):
text px (codes 2,3) in the bands round Ben's tracks (railroad 14 px, streetcar 12 px, as finder2's check_lines_rail.py),
text pieces touching them, and the px that differ. Reads only; writes skeptic/out/railrows.json and a picture of the
differences in the bands.   cd data/sanborn; python -B .../sk_railrows.py"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
B = 'bench_2026-11-25/text_v1'; out = {}
for N in ('44', '5'):
    A = cv2.imread(f'{B}/classifier/out/finder3/{N}_text.png', cv2.IMREAD_UNCHANGED); Z = cv2.imread(f'{B}/skeptic/out/v3norail/{N}_text.png', cv2.IMREAD_UNCHANGED)
    ta, tz = np.isin(A, (2, 3)), np.isin(Z, (2, 3)); H, W = A.shape
    R = json.load(open(f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8'))
    r = dict(px_text_differ=int((ta != tz).sum()), text_shipped=int(ta.sum()), text_norail=int(tz.sum()))
    tiles = []
    for kind, tol in (('railroad', 14), ('streetcar', 12)):
        m = np.zeros((H, W), np.uint8)
        for t in R['tracks']:
            if t['kind'] == kind and len(t['pts']) > 1: cv2.polylines(m, [np.round(np.array(t['pts'])).astype(np.int32)], False, 1, 1)
        band = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * tol + 1, 2 * tol + 1))) > 0
        def pieces(t):
            n, lb = cv2.connectedComponents(t.astype(np.uint8), connectivity=8); return len(np.unique(lb[band & t]))
        d = band & (ta != tz)
        r[kind] = dict(text_in_band_shipped=int((band & ta).sum()), text_in_band_norail=int((band & tz).sum()),
                       pieces_shipped=pieces(ta), pieces_norail=pieces(tz), differ_in_band=int(d.sum()),
                       became_text_without_rail_rows=int((band & tz & ~ta).sum()), became_other_without_rail_rows=int((band & ta & ~tz).sum()))
        n, lb, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(d.astype(np.uint8), np.ones((7, 7), np.uint8)), connectivity=8)
        im = None
        for i in np.argsort(-st[1:, 4])[:8] + 1 if n > 1 else []:
            if im is None: im = cv2.imread(f'cufp/22-{N}.jpg')
            cx, cy = st[i, 0] + st[i, 2] // 2, st[i, 1] + st[i, 3] // 2; s = 40
            X0, Y0, X1, Y1 = max(0, cx - s), max(0, cy - s), min(W, cx + s), min(H, cy + s)
            def paint(t):
                o = (im[Y0:Y1, X0:X1] * 0.35 + 255 * 0.65).astype(np.uint8); o[t[Y0:Y1, X0:X1]] = (220, 0, 220); o[m[Y0:Y1, X0:X1] > 0] = (0, 160, 0); return o
            p = np.concatenate([im[Y0:Y1, X0:X1], paint(ta), paint(tz)], 1); p = cv2.resize(p, (480, 160), interpolation=cv2.INTER_NEAREST)
            cv2.putText(p, f'{N} {kind} {cx},{cy}', (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1); tiles.append(p)
    if tiles:
        cv2.imwrite(f'{B}/skeptic/pics/railrows_{N}.png', np.concatenate(tiles, 0))
    out[N] = r; print(N, json.dumps(r))
json.dump(out, open(f'{B}/skeptic/out/railrows.json', 'w'), indent=1)
