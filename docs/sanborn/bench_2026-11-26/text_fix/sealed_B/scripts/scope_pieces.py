"""Labelling aid for targeted crops: list the glyph-sized ink pieces inside each target's scope (grown by 6 px) that
no typed word covers, grouped into clusters (pieces closer than GAP px), with each cluster's box clipped to nothing
(full box, so a word reaching out of the scope is seen whole). Ink less straight runs of 61 px (the builder's peel).
Scan and my own typed words only. python -B scope_pieces.py CROP [CROP ...] [--gap 7]"""
import os, sys, json
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import INV, window, line_mask

GAP = int(sys.argv[sys.argv.index('--gap') + 1]) if '--gap' in sys.argv else 7
crops = json.load(open(os.path.join(INV, 'truth', 'crops.json'), encoding='utf8'))
for cid in [a for a in sys.argv[1:] if a.startswith('SB-')]:
    c = crops[cid]; X0, Y0, X1, Y1 = c['win']; p = c['plate']
    W = json.load(open(os.path.join(INV, 'truth', f'{cid}_words.json'), encoding='utf8'))['words']
    _, _, ink, (wx0, wy0, _, _) = window(p, X0 - 60, Y0 - 60, X1 + 60, Y1 + 60)
    ln = line_mask(ink, 61, nang=72)
    cand = ink & ~(cv2.dilate(ln.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
    cov = np.zeros(ink.shape, np.uint8)
    for w in W: cv2.fillPoly(cov, [np.round(np.array(w['poly']) - [wx0, wy0]).astype(np.int32)], 1)
    n, lb, st, _ = cv2.connectedComponentsWithStats(cand.astype(np.uint8), connectivity=8)
    covered = np.bincount(lb.ravel(), cov.ravel(), minlength=n) / np.maximum(1, st[:, 4])
    sc = np.zeros(ink.shape, bool)
    for w in W:
        if not w['target']: continue
        a = w['aabb']; pad = c.get('scope_pad', 25) + 6
        sc[max(0, a[1] - pad - wy0):a[3] + pad - wy0, max(0, a[0] - pad - wx0):a[2] + pad - wx0] = True
    insc = np.bincount(lb.ravel(), sc.ravel(), minlength=n) > 0
    keep = [i for i in range(1, n) if insc[i] and covered[i] < 0.5 and st[i, 4] >= 6 and max(st[i, 2], st[i, 3]) <= 70]
    m = np.isin(lb, keep).astype(np.uint8)
    g = cv2.dilate(m, np.ones((GAP, GAP), np.uint8))
    ng, glb, gst, _ = cv2.connectedComponentsWithStats(g, connectivity=8)
    print(f'== {cid} (plate {p}) uncovered clusters in scopes:')
    for j in range(1, ng):
        x, y, w_, h, _ = gst[j]; mm = (glb[y:y + h, x:x + w_] == j) & (m[y:y + h, x:x + w_] > 0)
        ys, xs = np.nonzero(mm)
        if len(xs) < 8: continue
        print(f'   x {xs.min() + x + wx0}-{xs.max() + x + wx0}  y {ys.min() + y + wy0}-{ys.max() + y + wy0}  ink {len(xs)}')
