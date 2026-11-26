"""missed.py H1: QA of a built held-out crop. Lists the ink pieces (ink less straight runs of 41 px, 8-connected)
that are glyph-sized, hold no text or don't-care pixel and lie outside every word box, so each can be looked at:
a missed glyph, or a dash, hook, dot or outline stub (not text). Writes work/<crop>_missed.jpg tiles (1.5x) with
those pieces in blue and numbered, and work/<crop>_missed.json. Uses the scan and the hand mask only."""
import sys, os, json, math, cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_heldout import window, straight_runs, CROPS, HO, WORK
cid = sys.argv[1]
c = CROPS[cid]; X0, Y0, X1, Y1 = c['win']
img, ink, _ = window(c['plate'], X0, Y0, X1, Y1)
M = cv2.imread(os.path.join(os.path.dirname(HO), 'heldout', f'{cid}_mask.png'), 0)
W = json.load(open(os.path.join(os.path.dirname(HO), 'heldout', f'{cid}_words.json'), encoding='utf8'))['words']
boxes = np.zeros(M.shape, np.uint8)
for w in W:
    q = np.round(np.array(w['poly']) - [X0, Y0]).astype(np.int32); cv2.fillPoly(boxes, [q], 1)
boxes = cv2.dilate(boxes, np.ones((5, 5), np.uint8))
rest = ink & ~(cv2.dilate(straight_runs(ink, 41).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
n, lb, st, cen = cv2.connectedComponentsWithStats(rest.astype(np.uint8), connectivity=8)
out = []
for i in range(1, n):
    x, y, w, h, a = st[i]
    if a < 12 or max(w, h) < 6 or max(w, h) > 80: continue
    m = lb[y:y + h, x:x + w] == i
    if (M[y:y + h, x:x + w][m] >= 2).any(): continue
    if boxes[y:y + h, x:x + w][m].mean() > 0.3: continue
    out.append(dict(id=len(out) + 1, x=int(x + X0), y=int(y + Y0), w=int(w), h=int(h), area=int(a)))
json.dump(out, open(os.path.join(WORK, f'{cid}_missed.json'), 'w'), indent=0)
print(cid, len(out), 'glyph-sized pieces outside every word box')
v = (img * 0.35 + 255 * 0.65).astype(np.uint8); v[M == 1] = (150, 150, 150); v[M == 2] = (0, 0, 230); v[M == 3] = (0, 200, 255)
for o in out:
    x, y = o['x'] - X0, o['y'] - Y0
    sub = lb[y:y + o['h'], x:x + o['w']]; idx = sub[sub > 0]
    k = np.bincount(idx).argmax() if len(idx) else 0
    v[y:y + o['h'], x:x + o['w']][sub == k] = (255, 60, 0)
P = 25; big = cv2.copyMakeBorder(v, P, P, P, P, cv2.BORDER_CONSTANT, value=(255, 255, 255))
for r, ty in enumerate(range(0, Y1 - Y0, 500)):
    for q, tx in enumerate(range(0, X1 - X0, 500)):
        t = cv2.resize(big[ty:ty + 550, tx:tx + 550], None, fx=1.5, fy=1.5, interpolation=cv2.INTER_NEAREST)
        for o in out:
            px, py = (o['x'] - X0 - tx + P) * 1.5, (o['y'] - Y0 - ty + P) * 1.5
            if -10 < px < t.shape[1] and -10 < py < t.shape[0]:
                cv2.putText(t, str(o['id']), (int(px), int(py) - 2), 0, 0.38, (200, 0, 0), 1)
        for gx in range(((X0 + tx - P) // 100 + 1) * 100, X0 + tx - P + 550, 100):
            Xp = int((gx - X0 - tx + P) * 1.5); cv2.putText(t, str(gx), (Xp + 2, 11), 0, 0.35, (0, 120, 0), 1); t[:8, Xp] = (0, 120, 0)
        for gy in range(((Y0 + ty - P) // 100 + 1) * 100, Y0 + ty - P + 550, 100):
            Yp = int((gy - Y0 - ty + P) * 1.5); cv2.putText(t, str(gy), (2, Yp - 2), 0, 0.35, (0, 120, 0), 1); t[Yp, :8] = (0, 120, 0)
        cv2.imwrite(os.path.join(WORK, f'{cid}_missed_{r}{q}.jpg'), t, [cv2.IMWRITE_JPEG_QUALITY, 90])
