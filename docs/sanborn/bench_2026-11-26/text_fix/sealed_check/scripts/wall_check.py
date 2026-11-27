"""Wall check for the full crops (sealed cross-check): text pixels inside a word box that lie on a straight run which goes
on outside the box as not-text ink for 10 px or more (the wall of a small building, or a lot line, crossing the word).
    cd data/sanborn
    python -B .../wall_check.py [crops...] [--out FILE.json]
Per word and per direction (36 directions), ink on a straight run of 15 px or more is found by an opening; a run piece
that holds text pixels of the box and reaches 10 px or more beyond the box (box grown by 10 px) is a suspect. For each
suspect, a NOTTEXT strip is proposed from a line fit of the run pixels inside the box grown by 3 px (width = run
thickness + 2, at most 6). Nothing is changed here; every proposal is looked at on pics/wallchk_*.png."""
import os, sys, json, math, argparse
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import FINAL, window, jdump
ap = argparse.ArgumentParser(); ap.add_argument('crops', nargs='*'); ap.add_argument('--out', default=os.path.join(HERE, '..', 'checks', 'wall_check.json')); a = ap.parse_args()
crops = json.load(open(os.path.join(FINAL, 'crops.json'), encoding='utf8'))
ids = a.crops or [k for k, c in crops.items() if c.get('kind') == 'full']
out = []


def in_rect(xs, ys, cx, cy, L, h, ang):
    t = math.radians(ang); u = (math.cos(t), math.sin(t)); v = (-math.sin(t), math.cos(t))
    dx, dy = xs - cx, ys - cy; al = dx * u[0] + dy * u[1]; ac = dx * v[0] + dy * v[1]
    return (np.abs(al) <= L / 2) & (np.abs(ac) <= h / 2)


for tid in ids:
    c = crops[tid]; X0, Y0, X1, Y1 = c['win']; P = 40
    _, _, ink, (wx0, wy0, _, _) = window(c['plate'], X0 - P, Y0 - P, X1 + P, Y1 + P)
    M = np.full(ink.shape, 9, np.uint8); M[Y0 - wy0:Y1 - wy0, X0 - wx0:X1 - wx0] = cv2.imread(os.path.join(FINAL, f'{tid}_mask.png'), 0)
    W = json.load(open(os.path.join(FINAL, f'{tid}_words.json'), encoding='utf8'))['words']
    yy, xx = np.mgrid[0:ink.shape[0], 0:ink.shape[1]]
    for w in W:
        if w['kind'] in ('block', 'street', 'owner', 'ditto'): continue
        p = np.array(w['poly']) - [wx0, wy0]; cx, cy = p.mean(0); L, h, ang = w['length'], w['height'], w['angle']
        R = int(L / 2 + h / 2 + 30); bx0, by0 = max(0, int(cx - R)), max(0, int(cy - R)); bx1, by1 = min(ink.shape[1], int(cx + R)), min(ink.shape[0], int(cy + R))
        sub = ink[by0:by1, bx0:bx1]; X = xx[by0:by1, bx0:bx1].astype(float); Y = yy[by0:by1, bx0:bx1].astype(float); T = M[by0:by1, bx0:bx1]
        box = in_rect(X, Y, cx, cy, L + 1, h + 1, ang); far = ~in_rect(X, Y, cx, cy, L + 20, h + 20, ang)
        if not (box & (T == 2)).any(): continue
        u8 = cv2.morphologyEx(sub.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
        hit = np.zeros(sub.shape, bool)
        for i in range(36):
            t = math.pi * i / 36; k = np.zeros((15, 15), np.uint8); d = np.array([math.cos(t), math.sin(t)]) * 7
            cv2.line(k, tuple(np.round(7 - d).astype(int).tolist()), tuple(np.round(7 + d).astype(int).tolist()), 1, 1)
            run = (cv2.morphologyEx(u8, cv2.MORPH_OPEN, k) > 0) & sub
            n, lb = cv2.connectedComponents(run.astype(np.uint8), connectivity=8)
            if n < 2: continue
            reach = np.bincount(lb.ravel(), (far & (T == 1)).ravel(), minlength=n) >= 6
            txt = np.bincount(lb.ravel(), (box & (T == 2)).ravel(), minlength=n) >= 6
            ok = reach & txt; ok[0] = False
            hit |= ok[lb] & box & (T == 2)
        if hit.sum() < 6: continue
        ys, xs = np.nonzero(hit)
        out.append(dict(crop=tid, plate=c['plate'], check='wall', word=w['id'], reading=w['reading'], kind=w['kind'], px=int(hit.sum()),
                        box=[int(xs.min() + bx0 + wx0), int(ys.min() + by0 + wy0), int(xs.max() + bx0 + wx0 + 1), int(ys.max() + by0 + wy0 + 1)]))
jdump(dict(suspects=out), a.out)
print(len(out), 'suspects', sum(s['px'] for s in out), 'text px on wall runs')
