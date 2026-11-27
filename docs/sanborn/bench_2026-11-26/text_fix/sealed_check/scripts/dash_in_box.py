"""Dash check (sealed cross-check): text pieces inside a word box that look like a dash of a line running along the word.
    cd data/sanborn
    python -B .../dash_in_box.py [--out FILE.json]
For every word, the 8-connected pieces of its text pixels (truth 2) are fitted with a rotated rectangle. A piece is a
suspect when it is long and thin (long side 12 px or more, at least 4 times the short side), runs within 25 degrees of the
reading direction, and its centre lies in the outer third of the box across the reading direction (a hyphen sits in the
middle). Each suspect is looked at by eye."""
import os, sys, json, math, argparse
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import FINAL, jdump
ap = argparse.ArgumentParser(); ap.add_argument('--out', default=os.path.join(HERE, '..', 'checks', 'dash_in_box.json')); a = ap.parse_args()
crops = json.load(open(os.path.join(FINAL, 'crops.json'), encoding='utf8')); out = []
for tid, c in crops.items():
    X0, Y0, X1, Y1 = c['win']; M = cv2.imread(os.path.join(FINAL, f'{tid}_mask.png'), 0)
    W = json.load(open(os.path.join(FINAL, f'{tid}_words.json'), encoding='utf8'))['words']
    for w in W:
        pm = np.zeros(M.shape, np.uint8); cv2.fillPoly(pm, [np.round(np.array(w['poly']) - [X0, Y0]).astype(np.int32)], 1)
        t = ((M == 2) & (pm > 0)).astype(np.uint8)
        n, lb, st, _ = cv2.connectedComponentsWithStats(t, connectivity=8)
        ang = math.radians(w['angle']); u = np.array([math.cos(ang), math.sin(ang)]); v = np.array([-u[1], u[0]])
        P = np.array(w['poly']); ctr = P.mean(0)
        for i in range(1, n):
            if st[i][4] < 12: continue
            ys, xs = np.nonzero(lb == i)
            (cx, cy), (rw, rh), ra = cv2.minAreaRect(np.stack([xs, ys], 1).astype(np.float32))
            L, S = max(rw, rh), max(1.0, min(rw, rh))
            if L < 12 or L < 4 * S: continue
            da = math.radians(ra if rw >= rh else ra + 90); d = np.array([math.cos(da), math.sin(da)])
            if abs(d @ u) < math.cos(math.radians(25)): continue
            across = (np.array([cx + X0, cy + Y0]) - ctr) @ v
            if abs(across) < w['height'] / 6: continue
            out.append(dict(crop=tid, plate=c['plate'], check='dash', box=[int(xs.min() + X0), int(ys.min() + Y0), int(xs.max() + X0 + 1), int(ys.max() + Y0 + 1)],
                            px=int(st[i][4]), word=w['id'], reading=w['reading'], kind=w['kind']))
jdump(dict(suspects=out), a.out)
from collections import Counter
print(len(out), Counter(s['crop'] for s in out).most_common(20))
