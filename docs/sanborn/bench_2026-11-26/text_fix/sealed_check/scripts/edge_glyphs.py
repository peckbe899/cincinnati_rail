"""Edge-glyph check for targeted crops (sealed cross-check): glyph-sized ink pieces cut by the scope edge.
    cd data/sanborn
    python -B .../edge_glyphs.py [--truth DIR] [--out FILE.json]
For each targeted crop, the 8-connected ink pieces of the whole crop window (not cut at the scope) that lie partly inside
and partly outside the scope, are glyph-sized (at most 70 px across, 900 px) and have no text pixel inside the scope.
Such a piece is often the end of a word the builder did not type because most of it lies outside the scope; its
in-scope pixels are then scored as non-text ink. Lines and dashes show up too; every hit is looked at by eye."""
import os, sys, json, argparse
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import FINAL, window, jdump
ap = argparse.ArgumentParser(); ap.add_argument('--truth', default=FINAL); ap.add_argument('--out', default=os.path.join(HERE, '..', 'checks', 'edge_glyphs.json')); a = ap.parse_args()
crops = json.load(open(os.path.join(a.truth, 'crops.json'), encoding='utf8')); out = []
for tid in sorted(crops, key=lambda k: (crops[k]['plate'], k)):
    c = crops[tid]
    if c.get('kind') != 'targeted': continue
    X0, Y0, X1, Y1 = c['win']; M = cv2.imread(os.path.join(a.truth, f'{tid}_mask.png'), 0)
    R = json.load(open(os.path.join(a.truth, f'{tid}_words.json'), encoding='utf8'))
    _, _, ink, _ = window(c['plate'], X0, Y0, X1, Y1)
    S = np.zeros(M.shape, bool)
    for r in R['scope']: S[max(0, r[1] - Y0):max(0, r[3] - Y0 + 1), max(0, r[0] - X0):max(0, r[2] - X0 + 1)] = True
    n, lb, st, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
    for i in range(1, n):
        x, y, w, h, ar = st[i]
        if max(w, h) > 70 or ar > 900 or ar < 4: continue
        sub = lb[y:y + h, x:x + w] == i; s = S[y:y + h, x:x + w][sub]
        if s.all() or not s.any(): continue
        L = M[y:y + h, x:x + w][sub][s]
        if (L == 2).any() or not (L == 1).any(): continue
        out.append(dict(crop=tid, plate=c['plate'], check='edge_glyph', box=[int(x + X0), int(y + Y0), int(x + w + X0), int(y + h + Y0)], px=int(ar), in_scope_nontext=int((L == 1).sum())))
jdump(dict(suspects=out), a.out)
from collections import Counter
print(len(out), 'edge pieces;', Counter(s['crop'][:2] for s in out), 'in-scope non-text px', sum(s['in_scope_nontext'] for s in out))
