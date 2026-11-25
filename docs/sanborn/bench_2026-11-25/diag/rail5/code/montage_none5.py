"""Montage of the railroad tracks the rules make on plate 5 with NO ground (as the batch ran plates never placed on 21 Nov
morning) that the nets-ground run does not make; full-size crops, track in blue over the right half. diag/rail5, 25 Nov.
    cd data/sanborn; python -B bench_2026-11-25/diag/rail5/code/montage_none5.py RUN (orig_none | proposed_none)"""
import json, os, sys
import numpy as np, cv2
from scipy.spatial import cKDTree
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); run = sys.argv[1]
im = cv2.imread('cufp/22-5.jpg'); H, W = im.shape[:2]
T = [np.array(t['pts'], float) for t in json.load(open(os.path.join(ROOT, 'runs', run + '_tracks.json')))['tracks'] if t['kind'] == 'railroad']
ref = np.vstack([np.array(t['pts'], float) for t in json.load(open(os.path.join(ROOT, 'runs', 'orig_nets_tracks.json')))['tracks'] if t['kind'] == 'railroad'])
def samp(p, step=3):
    S = [a + np.linspace(0, 1, max(2, int(np.hypot(*(b - a)) / step) + 1))[:-1, None] * (b - a) for a, b in zip(p[:-1], p[1:])]; return np.vstack(S + [p[-1:]])
Sref = np.vstack([samp(np.array(t['pts'], float)) for t in json.load(open(os.path.join(ROOT, 'runs', 'orig_nets_tracks.json')))['tracks'] if t['kind'] == 'railroad']); K = cKDTree(Sref)
new = [p for p in T if (K.query(samp(p))[0] > 10).mean() > 0.5]
tiles = []; rec = []
for k, p in enumerate(sorted(new, key=lambda p: -np.hypot(*np.diff(p, axis=0).T).sum())):
    c = p.mean(0).astype(int); L = np.hypot(*np.diff(p, axis=0).T).sum()
    x0, y0 = max(0, c[0] - 200), max(0, c[1] - 110); x1, y1 = min(W, x0 + 400), min(H, y0 + 220)
    a = im[y0:y1, x0:x1].copy(); b = a.copy(); cv2.polylines(b, [np.round(p - [x0, y0]).astype(np.int32)], False, (255, 90, 0), 2)
    t = np.full((230, 810, 3), 255, np.uint8); t[:a.shape[0], :a.shape[1]] = a; t[:b.shape[0], 410:410 + b.shape[1]] = b
    cv2.putText(t, f'{k} L{int(L)} @{c[0]},{c[1]}', (5, 225), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 200), 1); tiles.append(t); rec.append(dict(k=k, len=round(float(L)), at=c.tolist()))
rows = [np.hstack(tiles[i:i + 2] + [np.full((230, 810, 3), 255, np.uint8)] * (2 - len(tiles[i:i + 2]))) for i in range(0, len(tiles), 2)]
for j in range(0, len(rows), 6): cv2.imwrite(os.path.join(ROOT, 'crops', f'{run}_extra_{j // 6}.png'), np.vstack(rows[j:j + 6]))
json.dump(rec, open(os.path.join(ROOT, 'crops', f'{run}_extra.json'), 'w'), indent=1); print(len(new), 'extra tracks', round(sum(r['len'] for r in rec)), 'px')
