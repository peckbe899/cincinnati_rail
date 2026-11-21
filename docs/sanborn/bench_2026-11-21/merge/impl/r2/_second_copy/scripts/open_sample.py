"""merge/impl/r2: what do the plain outlines (blocks whose ring cannot be closed, kept with PLAIN_KEEP) add to the
editor's lines on the 104 unplaced plates? Counts, and a random sample of their exported sides to judge by eye.

    python -B open_sample.py TAG [N_SAMPLE]    reads r2/plates_TAG/ -> r2/open_sample_TAG.json, r2/pics/open_TAG_K.jpg

Each sample is drawn uniformly by length (seed 0) from the exported sides (step 4) of plain outlines, plates other than
44. A crop is 700 x 700 full px round the side's middle, shown at 0.6: the side in thick green (green) or orange, the
rest of its outline thin red, the other exported lines thin blue. The verdicts are written by hand into
r2/open_verdicts.json after looking (estimates, small sample).
"""
import json, os, sys
import numpy as np
import cv2
import common as C
TAG = sys.argv[1]; NS = int(sys.argv[2]) if len(sys.argv) > 2 else 30; D = C.IMPL + f'plates_{TAG}/'
BN = C.step4_mod(); rows = []; tot = dict(plates=0, open_polys=0, open_blocks=0, exported=0, exported_len=0.0, green=0, green_len=0.0)
for n in sorted(os.listdir(D)):
    if not os.path.exists(D + n + '/outlines.json'): continue
    P = json.load(open(D + n + '/outlines.json')); op = [p for p in P if any(s['state'] == 'short' for s in p)]
    if not op: continue
    tot['plates'] += 1; tot['open_polys'] += len(op); tot['open_blocks'] += sum(1 for p in op if not p[0].get('hole'))
    for i, p in enumerate(op):
        for e in BN.step4([p]):
            L = float(np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1])); tot['exported'] += 1; tot['exported_len'] += L
            if e['state'] == 'green': tot['green'] += 1; tot['green_len'] += L
            rows.append(dict(plate=n, poly=i, hole=bool(p[0].get('hole')), a=e['a'], b=e['b'], state=e['state'], len=round(L)))
tot['exported_len'] = round(tot['exported_len']); tot['green_len'] = round(tot['green_len'])
pool = [r for r in rows if r['plate'] != '44']; rng = np.random.default_rng(0); w = np.array([r['len'] for r in pool], float)
pick = sorted(rng.choice(len(pool), size=min(NS, len(pool)), replace=False, p=w / w.sum()).tolist())
S = [dict(i=k, **pool[j]) for k, j in enumerate(pick)]
os.makedirs(C.IMPL + 'pics', exist_ok=True); tiles = []
for s in S:
    n = s['plate']; im = cv2.imread(C.DATA + f'cufp/22-{n}.jpg'); H, W = im.shape[:2]; m = (np.array(s['a']) + np.array(s['b'])) / 2
    x0, y0 = int(np.clip(m[0] - 350, 0, max(0, W - 700))), int(np.clip(m[1] - 350, 0, max(0, H - 700))); c = im[y0:y0 + 700, x0:x0 + 700].copy()
    q = lambda p: (int(round(p[0] - x0)), int(round(p[1] - y0)))
    for e in json.load(open(D + n + '/outlines.json'))[0:0]: pass
    E = BN.step4(json.load(open(D + n + '/outlines.json')))
    for e in E: cv2.line(c, q(e['a']), q(e['b']), (255, 120, 0), 2, cv2.LINE_AA)
    poly = [p for p in json.load(open(D + n + '/outlines.json')) if any(t['state'] == 'short' for t in p)][s['poly']]
    for t in poly: cv2.line(c, q(t['a']), q(t['b']), (0, 0, 220), 2, cv2.LINE_AA)
    cv2.line(c, q(s['a']), q(s['b']), (0, 170, 0) if s['state'] == 'green' else (0, 140, 255), 6, cv2.LINE_AA)
    c = cv2.resize(c, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA)
    cv2.putText(c, f"#{s['i']} {n} {s['state']} {s['len']}px{' hole' if s['hole'] else ''}", (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2, cv2.LINE_AA)
    tiles.append(c)
for k in range(0, len(tiles), 6):
    row = tiles[k:k + 6] + [np.full_like(tiles[0], 255)] * (6 - len(tiles[k:k + 6]))
    cv2.imwrite(C.IMPL + f'pics/open_{TAG}_{k // 6}.jpg', np.vstack([np.hstack(row[0:3]), np.hstack(row[3:6])]), [cv2.IMWRITE_JPEG_QUALITY, 85])
json.dump(dict(totals=tot, by_plate={n: sum(1 for r in rows if r['plate'] == n) for n in sorted({r['plate'] for r in rows})}, sample=S), open(C.IMPL + f'open_sample_{TAG}.json', 'w'), indent=1)
print(tot); print('sample', len(S), 'from', len(pool), 'sides')
