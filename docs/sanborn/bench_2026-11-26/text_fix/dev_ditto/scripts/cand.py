"""Contact sheet for deciding ditto marks by eye, scan only (dev_ditto, 26 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/dev_ditto/scripts/cand.py NAME PLATE:x:y[:label] [...] [--scale 6] [--half 30] [--cols 4]

Each cell: the scan round (x, y) +- half px at --scale with a 10 px grid; every separate ink piece (ink = L < 140 on the
paper, 8-connected) of 2-150 px that lies in the cell gets a thin cyan box and a number; the numbers, boxes (full-plate
px, x0 y0 x1 y1 inclusive) and pixel counts are printed and saved to pics/cand_<NAME>.json. Pieces joined to a line are
not boxed (they are part of a bigger piece). Writes pics/cand_<NAME>.png. Never reads a finder output or bins."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from zoom import zoom, DD
from common import window

a = sys.argv; name = a[1]
sc = float(a[a.index('--scale') + 1]) if '--scale' in a else 6
MAXA = int(a[a.index('--max') + 1]) if '--max' in a else 150
cols = int(a[a.index('--cols') + 1]) if '--cols' in a else 4
hd = int(a[a.index('--half') + 1]) if '--half' in a else 30
pts = [q for q in a[2:] if q.count(':') >= 2 and not q.startswith('--')]
cells, rec = [], []
for i, q in enumerate(pts):
    f = q.split(':'); p = f[0]; x, y = int(float(f[1])), int(float(f[2])); lab = f[3] if len(f) > 3 else ''
    x0, y0, x1, y1 = x - hd, y - hd, x + hd, y + hd
    G = zoom(p, x0, y0, x1, y1, sc, 10, False)
    _, _, ink, (wx0, wy0, _, _) = window(p, x0 - 40, y0 - 40, x1 + 40, y1 + 40)
    n, lb, st, cen = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
    pcs = []
    for k in range(1, n):
        bx, by, bw, bh, A = st[k]
        if not (2 <= A <= MAXA): continue
        X0, Y0 = bx + wx0, by + wy0
        if X0 + bw < x0 or X0 > x1 or Y0 + bh < y0 or Y0 > y1: continue
        j = len(pcs); pcs.append(dict(n=j, box=[int(X0), int(Y0), int(X0 + bw - 1), int(Y0 + bh - 1)], px=int(A)))
        P = 34
        cv2.rectangle(G, (P + int((X0 - x0) * sc) - 1, P + int((Y0 - y0) * sc) - 1), (P + int((X0 + bw - x0) * sc), P + int((Y0 + bh - y0) * sc)), (220, 180, 0), 1)
        cv2.putText(G, str(j), (P + int((X0 + bw - x0) * sc) + 1, P + int((Y0 - y0) * sc) + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 120, 0), 1)
    C = np.full((G.shape[0] + 16, G.shape[1], 3), 255, np.uint8); C[16:] = G
    cv2.putText(C, f'#{i} {p} {x},{y} {lab}', (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
    cells.append(C); rec.append(dict(cell=i, plate=p, x=x, y=y, label=lab, pieces=pcs))
    print(f'#{i} {p} {x},{y} {lab}: ' + '  '.join(f"{d['n']}:{d['box'][0]},{d['box'][1]}-{d['box'][2]},{d['box'][3]}/{d['px']}" for d in pcs))
CW = max(c.shape[1] for c in cells); CH = max(c.shape[0] for c in cells); rows = (len(cells) + cols - 1) // cols
S = np.full((rows * (CH + 4), min(cols, len(cells)) * (CW + 4), 3), 180, np.uint8)
for i, C in enumerate(cells):
    r, c = divmod(i, cols); S[r * (CH + 4):r * (CH + 4) + C.shape[0], c * (CW + 4):c * (CW + 4) + C.shape[1]] = C
f = os.path.join(DD, 'pics', 'cand', f'cand_{name}.png'); os.makedirs(os.path.dirname(f), exist_ok=True); cv2.imwrite(f, S)
json.dump(rec, open(f[:-4] + '.json', 'w'), indent=1); print(f, S.shape)
