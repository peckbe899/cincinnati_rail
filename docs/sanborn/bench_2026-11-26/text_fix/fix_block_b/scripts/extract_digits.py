"""Cut real block-number figures out of the 12 dev plates, using dev_block's survey lists (position + reading) only.
Candidates inside a dev truth window (grown 60 px) or an H window (grown 50 px) are skipped, so no scored window is used.
Reads only the scan and paper mask (no finder output, no truth mask).

    cd data/sanborn
    python -B .../scripts/extract_digits.py OUT.npz [plates...]

Per figure kept: plate, fold, digit, the full-res ink crop round its box (+6 px), its thick-core component mask, height.
A number is kept only when the thick ink near the survey point splits into exactly as many upright figure-sized
pieces, side by side, as the reading has figures (so crossed or merged figures are mostly left out)."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np, cv2
import bfcommon as C

out = sys.argv[1]; plates = sys.argv[2:] or C.FOLD['A'] + C.FOLD['B']
crops = C.dev_crops(); E5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
rec = []; log = []
for N in plates:
    im, paper = C.load_scan(N); H, W = im.shape[:2]
    L = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0]; fold = 'A' if N in C.FOLD['A'] else 'B'
    wins = [c['win'] for c in crops.values() if c['plate'] == N]
    for x, y, r, note in C.candidates(N):
        b = (x - 130, y - 110, x + 130, y + 110)
        if C.in_hwin(N, b, 50) or any(b[0] < w[2] + 60 and b[2] > w[0] - 60 and b[1] < w[3] + 60 and b[3] > w[1] - 60 for w in wins):
            log.append((N, x, y, r, 'skip window')); continue
        digs = [ch for ch in r if ch.isdigit()]
        if not digs or len(digs) != len(r): log.append((N, x, y, r, 'not plain digits')); continue
        X0, Y0, X1, Y1 = max(0, b[0]), max(0, b[1]), min(W, b[2]), min(H, b[3])
        ink = ((L[Y0:Y1, X0:X1] < 140) & paper[Y0:Y1, X0:X1]).astype(np.uint8)
        K = cv2.morphologyEx(ink, cv2.MORPH_OPEN, E5)
        n, lb, st, cen = cv2.connectedComponentsWithStats(K, connectivity=8)
        ok = [i for i in range(1, n) if 34 <= st[i, 3] <= 85 and 5 <= st[i, 2] <= 70 and st[i, 4] >= 120]
        if not ok: log.append((N, x, y, r, 'no piece')); continue
        px, py = x - X0, y - Y0
        a = min(ok, key=lambda i: np.hypot(cen[i, 0] - px, cen[i, 1] - py))
        if np.hypot(cen[a, 0] - px, cen[a, 1] - py) > 90: log.append((N, x, y, r, 'far')); continue
        ha = st[a, 3]; ch = [a]
        def mates(i, side):
            best = None
            for j in ok:
                if j in ch: continue
                if abs(st[j, 3] - ha) > 0.2 * ha: continue
                ov = min(st[i, 1] + st[i, 3], st[j, 1] + st[j, 3]) - max(st[i, 1], st[j, 1])
                if ov < 0.7 * min(st[i, 3], st[j, 3]): continue
                gap = (st[j, 0] - (st[i, 0] + st[i, 2])) if side > 0 else (st[i, 0] - (st[j, 0] + st[j, 2]))
                if -3 <= gap <= 0.45 * ha and (best is None or gap < best[0]): best = (gap, j)
            return best
        for side in (1, -1):
            cur = a
            while True:
                m = mates(cur, side)
                if m is None: break
                ch.append(m[1]) if side > 0 else ch.insert(0, m[1]); cur = m[1]
        ch = sorted(ch, key=lambda i: st[i, 0])
        if len(ch) != len(digs): log.append((N, x, y, r, f'{len(ch)} pieces')); continue
        for d, i in zip(digs, ch):
            bx, by, bw, bh = st[i, :4]; g = 6
            x0, y0, x1, y1 = max(0, bx - g), max(0, by - g), min(ink.shape[1], bx + bw + g), min(ink.shape[0], by + bh + g)
            rec.append(dict(plate=N, fold=fold, digit=d, reading=r, x=int(X0 + bx), y=int(Y0 + by), w=int(bw), h=int(bh),
                            ink=ink[y0:y1, x0:x1].copy(), comp=(lb[y0:y1, x0:x1] == i).astype(np.uint8), off=(int(bx - x0), int(by - y0))))
        log.append((N, x, y, r, 'ok'))
    print(N, sum(1 for q in rec if q['plate'] == N), 'figures', flush=True)
np.save(out, np.array(rec, dtype=object), allow_pickle=True)
json.dump(log, open(out.replace('.npy', '_log.json'), 'w'))
from collections import Counter
print(Counter(q['digit'] for q in rec)); print(Counter(l[4].split()[0] if 'pieces' not in l[4] else 'pieces' for l in log))
