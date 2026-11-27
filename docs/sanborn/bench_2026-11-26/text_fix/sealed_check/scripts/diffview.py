"""Before/after pictures of a truth change (sealed cross-check): scan | old truth | new truth for every cluster of changed
pixels. python -B diffview.py OLD_DIR NEW_DIR TAG [crop ...] [--z 4] [--min 6] [--per 24] [--cols 4]
Colours as view.py: text red, not text dark grey, don't care orange, paper white; word boxes of the new truth magenta."""
import os, sys, json, argparse
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import window
ap = argparse.ArgumentParser(); ap.add_argument('old'); ap.add_argument('new'); ap.add_argument('tag'); ap.add_argument('crops', nargs='*')
ap.add_argument('--z', type=int, default=4); ap.add_argument('--min', type=int, default=6); ap.add_argument('--per', type=int, default=24); ap.add_argument('--cols', type=int, default=4)
a = ap.parse_args()
crops = json.load(open(os.path.join(a.new, 'crops.json'), encoding='utf8')) if os.path.exists(os.path.join(a.new, 'crops.json')) else json.load(open(os.path.join(a.old, 'crops.json'), encoding='utf8'))
ids = a.crops or [k for k in crops if os.path.exists(os.path.join(a.new, f'{k}_mask.png'))]


def colour(im, ink, T):
    c = (im * 0.3 + 255 * 0.7).astype(np.uint8); c[(T == 0) & ink] = (200, 200, 200)
    c[T == 1] = (70, 70, 70); c[T == 2] = (0, 0, 230); c[(T == 3) & ink] = (0, 170, 255); return c


cells = []; log = []
for tid in ids:
    c = crops[tid]; X0, Y0, X1, Y1 = c['win']
    A = cv2.imread(os.path.join(a.old, f'{tid}_mask.png'), 0); B = cv2.imread(os.path.join(a.new, f'{tid}_mask.png'), 0)
    d = (A != B)
    if not d.any(): continue
    W = json.load(open(os.path.join(a.new, f'{tid}_words.json'), encoding='utf8'))['words']
    n, lb, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(d.astype(np.uint8), np.ones((9, 9), np.uint8)), connectivity=8)
    for i in range(1, n):
        x, y, w, h, _ = st[i]; m = (lb == i) & d; k = int(m.sum())
        if k < a.min: continue
        x0, y0, x1, y1 = max(0, x - 10), max(0, y - 10), min(A.shape[1], x + w + 10), min(A.shape[0], y + h + 10)
        im, _, ink, _ = window(c['plate'], X0 + x0, Y0 + y0, X0 + x1, Y0 + y1)
        z = a.z if max(x1 - x0, y1 - y0) <= 90 else max(2, int(360 / max(x1 - x0, y1 - y0)))
        ps = [cv2.resize(im, None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)]
        for T in (A[y0:y1, x0:x1], B[y0:y1, x0:x1]):
            q = cv2.resize(colour(im, ink, T), None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
            for wd in W:
                P = (np.array(wd['poly']) - [X0 + x0, Y0 + y0]) * z
                if P[:, 0].max() < 0 or P[:, 1].max() < 0 or P[:, 0].min() > q.shape[1] or P[:, 1].min() > q.shape[0]: continue
                cv2.polylines(q, [np.round(P).astype(np.int32)], True, (255, 0, 200), 1)
            ps.append(q)
        t = np.full((ps[0].shape[0] + 16, sum(p.shape[1] for p in ps) + 8, 3), 255, np.uint8); xx = 0
        for p in ps: t[16:, xx:xx + p.shape[1]] = p; xx += p.shape[1] + 4
        lab = f'{len(cells)}:{tid} [{X0 + x0},{Y0 + y0}] {k}px'
        cv2.putText(t, lab, (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (120, 0, 0), 1); cells.append(t)
        log.append(dict(i=len(cells) - 1, crop=tid, box=[int(X0 + x0), int(Y0 + y0), int(X0 + x1), int(Y0 + y1)], px=k))
os.makedirs(os.path.join(HERE, '..', 'pics', 'diff'), exist_ok=True)
json.dump(log, open(os.path.join(HERE, '..', 'pics', 'diff', f'{a.tag}.json'), 'w'), indent=0)
for s0 in range(0, len(cells), a.per):
    cs = cells[s0:s0 + a.per]; rows = [cs[i:i + a.cols] for i in range(0, len(cs), a.cols)]
    cw = max(c.shape[1] for c in cs); H = sum(max(c.shape[0] for c in r) + 6 for r in rows)
    out = np.full((H, a.cols * (cw + 8), 3), 255, np.uint8); y = 0
    for r in rows:
        x = 0
        for c in r: out[y:y + c.shape[0], x:x + c.shape[1]] = c; x += cw + 8
        y += max(c.shape[0] for c in r) + 6
    p = os.path.join(HERE, '..', 'pics', 'diff', f'{a.tag}_{s0 // a.per:02d}.png'); cv2.imwrite(p, out); print(p, out.shape[1], 'x', out.shape[0])
print(len(cells), 'clusters')
