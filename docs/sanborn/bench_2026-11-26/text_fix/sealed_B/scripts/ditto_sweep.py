"""Completeness aid for the ditto windows (scan only, my own rule, never a finder): in every opened random window, find
small isolated ink pieces (8-connected ink, 4-70 px of ink, at most 14 px across, nothing else within 4 px) that have
a partner of the same kind within 12 px (a tick pair), or are a lone short tick 6-14 px long; drop those already inside a
typed ditto box (grown 6 px); write a contact sheet of the rest at 4x for a look by eye.
python -B ditto_sweep.py OUT.jpg   (reads annot/selection.json rounds 1-3, plate 92 rounds 1-4, and the typed D crops)"""
import os, sys, json
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import INV, window

sel = json.load(open(os.path.join(INV, 'truth', 'annot', 'selection.json'), encoding='utf8'))
crops = json.load(open(os.path.join(INV, 'truth', 'crops.json'), encoding='utf8'))
typed = []
for k, c in crops.items():
    if c.get('target') != 'ditto': continue
    for w in json.load(open(os.path.join(INV, 'truth', f'{k}_words.json'), encoding='utf8'))['words']:
        if w['kind'] == 'ditto': typed.append((c['plate'], w['aabb']))
panels = []; n_all = 0
for p, v in sel['ditto'].items():
    wins = v['windows'][:4] if p == '92' else v['windows'][:6]
    for wi, w in enumerate(wins):
        im, _, ink, (x0, y0, _, _) = window(p, *w)
        n, lb, st, cen = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
        small = [i for i in range(1, n) if 4 <= st[i, 4] <= 70 and max(st[i, 2], st[i, 3]) <= 14]
        big = (np.isin(lb, small, invert=True) & ink)
        bigd = cv2.dilate(big.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
        iso = [i for i in small if not bigd[lb == i].any()]
        C = {i: cen[i] for i in iso}
        cand = set()
        for i in iso:
            for j in iso:
                if i < j and np.hypot(*(C[i] - C[j])) <= 12 and min(st[i, 4], st[j, 4]) >= 6: cand.add(i); cand.add(j)
            if '--lone' in sys.argv and max(st[i, 2], st[i, 3]) >= 6: cand.add(i)
        for i in sorted(cand):
            gx, gy = int(C[i][0]) + x0, int(C[i][1]) + y0
            if any(tp == p and a[0] - 6 <= gx <= a[2] + 6 and a[1] - 6 <= gy <= a[3] + 6 for tp, a in typed): continue
            if any(abs(gx - q[1]) < 10 and abs(gy - q[2]) < 10 and q[0] == p for q in [t[1] for t in panels]): continue
            n_all += 1
            a0, b0 = gx - 18, gy - 18
            crop = window(p, a0, b0, gx + 18, gy + 18)[0]
            t = cv2.resize(crop, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
            t = cv2.copyMakeBorder(t, 14, 0, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            cv2.putText(t, f'{p}w{wi + 1} {gx},{gy}', (1, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 160), 1)
            panels.append((t, (p, gx, gy)))
print(n_all, 'candidates')
cols = 10; rows = []
for i in range(0, len(panels), cols):
    r = [q[0] for q in panels[i:i + cols]]; h = max(x.shape[0] for x in r)
    r = [cv2.copyMakeBorder(x, 0, h - x.shape[0], 0, 4, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for x in r]
    rows.append(np.hstack(r))
if rows:
    W = max(r.shape[1] for r in rows)
    cv2.imwrite(sys.argv[1], np.vstack([cv2.copyMakeBorder(r, 0, 4, 0, W - r.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r in rows]), [cv2.IMWRITE_JPEG_QUALITY, 90])
for q in panels: print(q[1])
