"""Second-pass completeness aid for the ditto search, scan only (dev_ditto, 26 Nov 2026).

    cd data/sanborn; python -B bench_2026-11-26/text_fix/dev_ditto/scripts/pairfind.py [--ranks 6]

After the eye pass, a plain rule lists every PAIR of small separate ink pieces in the looked-at windows (ranks 1-6 of
choose/windows.json on every plate): both 3-60 px, box sides <= 12 px, centres 3-14 px apart, the pair's
joint box 16 px or less, and NO other ink within 4 px of the joint box (an isolated pair; v2 of this aid: without the
isolation rule it listed 1424 pairs, mostly broken figures). Pairs already inside a
truth ditto word box are skipped. Each pair is shown at 5x (40 x 40 px around it) on pics/pairs/sheet_<scale>_NN.png
with its number; the list goes to pics/pairs/pairs.json. Every pair is then judged by eye (ditto or not) and new dittos
are added to the truth with the rest of their window. Never reads a finder output or bins."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import window
from zoom import zoom, DD
from scipy.spatial import cKDTree

OUT = os.path.join(DD, 'pics', 'pairs'); os.makedirs(OUT, exist_ok=True)
ranks = int(sys.argv[sys.argv.index('--ranks') + 1]) if '--ranks' in sys.argv else 6
W = json.load(open(os.path.join(DD, 'choose', 'windows.json')))
T = os.path.join(DD, 'truth'); C = json.load(open(os.path.join(T, 'crops.json'))); boxes = {}
for k, c in C.items():
    f = os.path.join(T, f'{k}_words.json')
    if os.path.exists(f):
        for w in json.load(open(f))['words']:
            if w['kind'] == 'ditto': boxes.setdefault(c['plate'], []).append(w['aabb'])
pairs = []
for p, d in W.items():
    for w in d['windows'][:ranks]:
        x0, y0, x1, y1 = w['win']; _, _, ink, (wx0, wy0, _, _) = window(p, x0, y0, x1, y1)
        n, lb, st, cen = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
        ok = [k for k in range(1, n) if 3 <= st[k, 4] <= 60 and max(st[k, 2], st[k, 3]) <= 12]
        if len(ok) < 2: continue
        P = np.array([cen[k] for k in ok]); prs = cKDTree(P).query_pairs(14)
        for i, j in sorted(prs):
            dd = float(np.hypot(*(P[i] - P[j])))
            if dd < 3: continue
            ki, kj = ok[i], ok[j]
            bx0 = min(st[ki, 0], st[kj, 0]); by0 = min(st[ki, 1], st[kj, 1]); bx1 = max(st[ki, 0] + st[ki, 2], st[kj, 0] + st[kj, 2]); by1 = max(st[ki, 1] + st[ki, 3], st[kj, 1] + st[kj, 3])
            if max(bx1 - bx0, by1 - by0) > 16: continue
            sub = lb[max(0, by0 - 4):by1 + 4, max(0, bx0 - 4):bx1 + 4]
            if np.any((sub > 0) & (sub != ki) & (sub != kj)): continue
            cx, cy = (P[i] + P[j]) / 2 + [wx0, wy0]
            if any(b[0] - 3 <= cx <= b[2] + 3 and b[1] - 3 <= cy <= b[3] + 3 for b in boxes.get(p, [])): continue
            pairs.append(dict(plate=p, scale=d['scale'], rank=w['rank'], centre=[int(cx), int(cy)], dist=round(dd, 1)))
# merge pairs within 6 px of each other (a pair of pairs)
keep = []
for q in pairs:
    if any(r['plate'] == q['plate'] and abs(r['centre'][0] - q['centre'][0]) <= 6 and abs(r['centre'][1] - q['centre'][1]) <= 6 for r in keep): continue
    keep.append(q)
for i, q in enumerate(keep): q['pid'] = f'P{i + 1:03d}'
json.dump(keep, open(os.path.join(OUT, 'pairs.json'), 'w'), indent=1)
for sc in (100, 200, 400):
    qs = [q for q in keep if q['scale'] == sc]; cells = []
    for q in qs:
        x, y = q['centre']; G = zoom(q['plate'], x - 20, y - 20, x + 20, y + 20, 5, 10, False)
        Cc = np.full((G.shape[0] + 14, G.shape[1], 3), 255, np.uint8); Cc[14:] = G
        cv2.putText(Cc, f"{q['pid']} {q['plate']}#{q['rank']} {x},{y}", (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 0), 1); cells.append(Cc)
    if not cells: continue
    CW = max(c.shape[1] for c in cells); CH = max(c.shape[0] for c in cells); cols = 6
    for s in range(0, len(cells), 30):
        part = cells[s:s + 30]; rows = (len(part) + cols - 1) // cols
        S = np.full((rows * (CH + 4), cols * (CW + 4), 3), 180, np.uint8)
        for i, c in enumerate(part):
            r, cc = divmod(i, cols); S[r * (CH + 4):r * (CH + 4) + c.shape[0], cc * (CW + 4):cc * (CW + 4) + c.shape[1]] = c
        S = cv2.resize(S, None, fx=0.8, fy=0.8, interpolation=cv2.INTER_AREA)
        cv2.imwrite(os.path.join(OUT, f'sheet_{sc}_{s // 30 + 1:02d}.png'), S)
    print(sc, len(qs), 'pairs')
