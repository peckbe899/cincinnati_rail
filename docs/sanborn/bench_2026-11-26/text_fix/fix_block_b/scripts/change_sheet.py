"""Contact sheet of blockfix changes: scan | changes (red = new text, yellow = new shared, grey = other ink) per number.
    python -B .../scripts/change_sheet.py RUN_DIR BASE_DIR OUT.png N [N ...] [--offlist] [--min PX] [--max K] [--seed S]
--offlist keeps only numbers not on the survey lists (analyze_nums.py must have run). H windows are skipped."""
import sys, os, json, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np, cv2
import bfcommon as C
a = sys.argv[1:]
def opt(k, d):
    global a
    if k in a: i = a.index(k); v = a[i + 1]; a = a[:i] + a[i + 2:]; return v
    return d
mn = int(opt('--min', 0)); mx = int(opt('--max', 60)); seed = opt('--seed', None); off = '--offlist' in a; a = [x for x in a if x != '--offlist']
rd, bd, out, plates = a[0], a[1], a[2], a[3:]
items = []
for N in plates:
    T = json.load(open(os.path.join(rd, f'{N}_text.json'))); ch = [c for c in T['changes'] if not C.in_hwin(N, c['box'], 60)]
    lab = None
    if off:
        rows = [r for r in json.load(open(os.path.join(rd, 'nums_features.json'))) if r['plate'] == N]; lab = [r['lab'] for r in rows]
    for i, c in enumerate(ch):
        if c['to_text'] + c['to_shared'] < mn: continue
        if off and lab[i] == 1: continue
        items.append((N, c))
if seed is not None: random.Random(int(seed)).shuffle(items)
items = items[:mx]; tiles = []; cache = {}
for N, c in items:
    if N not in cache: cache.clear(); cache[N] = (cv2.imread(f'cufp/22-{N}.jpg'), cv2.imread(os.path.join(bd, f'{N}_text.png'), 0), cv2.imread(os.path.join(rd, f'{N}_text.png'), 0))
    im, b0, b1 = cache[N]; bx = [int(v) for v in c['box']]; cx, cy = (bx[0] + bx[2]) // 2, (bx[1] + bx[3]) // 2; r = 60
    X0, Y0 = max(0, cx - r), max(0, cy - r); X1, Y1 = X0 + 2 * r, Y0 + 2 * r
    s = im[Y0:Y1, X0:X1]; o = np.full(s.shape, 255, np.uint8); o[b1[Y0:Y1, X0:X1] > 0] = (190, 190, 190)
    d = b1[Y0:Y1, X0:X1] != b0[Y0:Y1, X0:X1]; o[d & (b1[Y0:Y1, X0:X1] == 2)] = (0, 0, 255); o[d & (b1[Y0:Y1, X0:X1] == 4)] = (0, 200, 230)
    o[np.isin(b0[Y0:Y1, X0:X1], (2, 3)) & ~d] = (220, 150, 220)
    t = np.concatenate([s, o], 1); t = cv2.resize(t, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_NEAREST)
    cv2.putText(t, f"{N} {c['reading']} +{c['to_text']}", (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 200), 1); tiles.append(t)
cols = 5; h, w = tiles[0].shape[:2]; rows = (len(tiles) + cols - 1) // cols; S = np.full((rows * (h + 2), cols * (w + 4), 3), 0, np.uint8)
for i, t in enumerate(tiles): r_, c_ = divmod(i, cols); S[r_ * (h + 2):r_ * (h + 2) + h, c_ * (w + 4):c_ * (w + 4) + w] = t
cv2.imwrite(out, S); print(len(tiles), 'tiles', S.shape)
