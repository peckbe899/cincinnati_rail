"""Ditto completeness sweep (sealed cross-check): in every opened ditto window of both halves, isolated pairs of small
elongated ink pieces (each 5-30 px, 4-12 px across, long side at least 1.6 times the short side, sizes within 2.5 times,
centres 3-12 px apart, no other ink within 5 px) that no ditto word of the merged truth covers. A pointer only: every candidate is looked at on pics/dsweep_*.png (scan, 6x).
    cd data/sanborn
    python -B .../ditto_sweep.py"""
import os, sys, json
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import FINAL, window, jdump
AN = os.path.join(FINAL, 'annot'); crops = json.load(open(os.path.join(FINAL, 'crops.json'), encoding='utf8'))
wins = [(p, w, 'A') for r, p, w in json.load(open(os.path.join(AN, 'selection_A', 'ditto_round_robin.json'))) if r <= 3]
for p, d in json.load(open(os.path.join(AN, 'selection_B', 'selection.json')))['ditto'].items():
    wins += [(p, w, 'B') for w in d['windows'][:4 if p == '92' else 6]]
dit = {}
for tid, c in crops.items():
    for w in json.load(open(os.path.join(FINAL, f'{tid}_words.json'), encoding='utf8'))['words']:
        if w['kind'] == 'ditto': dit.setdefault(c['plate'], []).append(w['aabb'])
cands = []
for p, (x0, y0, x1, y1), half in wins:
    im, _, ink, (wx0, wy0, _, _) = window(p, x0, y0, x1, y1)
    n, lb, st, cen = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
    def elong(i):
        ys, xs = np.nonzero(lb[st[i][1]:st[i][1] + st[i][3], st[i][0]:st[i][0] + st[i][2]] == i)
        (_, _), (a_, b_), _ = cv2.minAreaRect(np.stack([xs, ys], 1).astype(np.float32)); return max(a_, b_) / max(1.0, min(a_, b_))
    small = [i for i in range(1, n) if 5 <= st[i][4] <= 30 and 4 <= max(st[i][2], st[i][3]) <= 12]
    for i in small:
        for j in small:
            if j <= i or not (3 <= np.hypot(*(cen[i] - cen[j])) <= 12): continue
            if max(st[i][4], st[j][4]) > 2.5 * min(st[i][4], st[j][4]) or elong(i) < 1.6 or elong(j) < 1.6: continue
            bx = [min(st[i][0], st[j][0]), min(st[i][1], st[j][1]), max(st[i][0] + st[i][2], st[j][0] + st[j][2]), max(st[i][1] + st[i][3], st[j][1] + st[j][3])]
            ring = lb[max(0, bx[1] - 5):bx[3] + 5, max(0, bx[0] - 5):bx[2] + 5]
            if set(np.unique(ring)) - {0, i, j}: continue          # isolated: no other ink within 5 px
            bx = [bx[0] + wx0, bx[1] + wy0, bx[2] + wx0, bx[3] + wy0]
            if any(not (bx[2] < d[0] - 3 or bx[0] > d[2] + 3 or bx[3] < d[1] - 3 or bx[1] > d[3] + 3) for d in dit.get(p, [])): continue
            if any(c['plate'] == p and abs(c['box'][0] - bx[0]) < 8 and abs(c['box'][1] - bx[1]) < 8 for c in cands): continue
            cands.append(dict(plate=p, half=half, win=[x0, y0, x1, y1], box=[int(v) for v in bx], pair=True))
jdump(cands, os.path.join(HERE, '..', 'checks', 'ditto_sweep.json'))
cells = []
for k, c in enumerate(cands):
    b = c['box']; cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
    im, _, _, _ = window(c['plate'], cx - 20, cy - 16, cx + 20, cy + 16)
    z = cv2.resize(im, None, fx=5, fy=5, interpolation=cv2.INTER_NEAREST)
    t = np.full((z.shape[0] + 14, 210, 3), 255, np.uint8); t[14:14 + z.shape[0], :z.shape[1]] = z
    cv2.putText(t, f"{k}:{c['plate']} {cx},{cy}", (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (120, 0, 0), 1); cells.append(t)
cols = 12
for s0 in range(0, len(cells), 96):
    cs = cells[s0:s0 + 96]; rows = [cs[i:i + cols] for i in range(0, len(cs), cols)]
    H = sum(max(c.shape[0] for c in r) + 4 for r in rows); out = np.full((H, cols * 214, 3), 255, np.uint8); y = 0
    for r in rows:
        x = 0
        for c in r: out[y:y + c.shape[0], x:x + c.shape[1]] = c; x += 214
        y += max(c.shape[0] for c in r) + 4
    cv2.imwrite(os.path.join(HERE, '..', 'pics', f'dsweep_{s0 // 96:02d}.png'), out)
print(len(wins), 'windows,', len(cands), 'candidates')
