"""Second look for missed text (dev_block, 26 Nov 2026): every piece of ink the truth calls NOT text (1) inside a scope
that is glyph-sized (8-70 px across) and is not a long straight run is cut out on a contact sheet, scan beside truth.
Scan and truth only (no finder, no bin 8), as text_v1/truth-fix/scripts/blue_glyphs.py.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/dev_block/scripts/blue_check.py [DB01 ...]
Writes dev_block/pics/check/blue_sheet_K.png and prints the pieces."""
import os, sys, json
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from common import plate_img  # noqa: E402

TR = os.path.join(DB, 'truth'); C = json.load(open(os.path.join(TR, 'crops.json'), encoding='utf8'))
ids = [a for a in sys.argv[1:] if a.startswith('DB')] or sorted(C)
cells = []
for t in ids:
    c = C[t]; X0, Y0, X1, Y1 = c['win']; M = cv2.imread(os.path.join(TR, f'{t}_mask.png'), 0)
    n, lb, st, _ = cv2.connectedComponentsWithStats((M == 1).astype(np.uint8), connectivity=8)
    im = plate_img(c['plate'])[Y0:Y1, X0:X1]
    for i in range(1, n):
        x, y, w, h, a = st[i]
        ext = max(w, h)
        if ext < 8 or ext > 70 or a < 20: continue
        # straight thin runs (line stubs) are skipped: fill ratio of the bounding box low and one side thin
        if min(w, h) <= 6: continue
        pad = 12; xa, ya, xb, yb = max(0, x - pad), max(0, y - pad), min(M.shape[1], x + w + pad), min(M.shape[0], y + h + pad)
        A = im[ya:yb, xa:xb]; T = M[ya:yb, xa:xb]
        o = (A.astype(np.float32) * 0.35 + 255 * 0.65).astype(np.uint8)
        for v, col in {1: (200, 90, 0), 2: (0, 0, 230), 3: (0, 160, 255)}.items(): o[T == v] = col
        o[(lb[ya:yb, xa:xb] == i)] = (200, 0, 200)
        k = 3.0
        P = np.hstack([cv2.resize(A, None, fx=k, fy=k, interpolation=cv2.INTER_NEAREST), np.full((int(A.shape[0] * k), 4, 3), 255, np.uint8), cv2.resize(o, None, fx=k, fy=k, interpolation=cv2.INTER_NEAREST)])
        P = cv2.copyMakeBorder(P, 14, 2, 2, 2, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        cv2.putText(P, f'{t} {X0 + x},{Y0 + y} {w}x{h}', (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 0), 1)
        cells.append(P); print(t, X0 + x, Y0 + y, w, h, a)
if cells:
    CW = max(p.shape[1] for p in cells); CH = max(p.shape[0] for p in cells); cols = max(1, 1500 // (CW + 4)); per = cols * max(1, 1500 // (CH + 4))
    for s in range(0, len(cells), per):
        part = cells[s:s + per]; rows = (len(part) + cols - 1) // cols
        G = np.full((rows * (CH + 4), cols * (CW + 4), 3), 220, np.uint8)
        for i, P in enumerate(part):
            r, q = divmod(i, cols); G[r * (CH + 4):r * (CH + 4) + P.shape[0], q * (CW + 4):q * (CW + 4) + P.shape[1]] = P
        f = os.path.join(DB, 'pics', 'check', f'blue_sheet_{s // per}.png'); cv2.imwrite(f, G); print(f, G.shape)
