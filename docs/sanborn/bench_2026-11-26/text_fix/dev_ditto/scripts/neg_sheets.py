"""Contact sheets of the negative candidates (negatives/choose/candidates.json), scan only (dev_ditto, 26 Nov 2026).
Each cell: the 64 x 64 px window centred on the candidate at x5, a 10 px grid, a cyan cross at the centre, the cid.
python -B neg_sheets.py  -> negatives/choose/sheet_NN.png (20 cells each)"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from zoom import zoom, DD
OUT = os.path.join(DD, 'negatives', 'choose')
SRC = sys.argv[1] if len(sys.argv) > 1 else 'candidates.json'; TAG = 'sheet' if SRC == 'candidates.json' else 'sheet2'
C = [d for d in json.load(open(os.path.join(OUT, SRC)))['draws'] if d['verdict'] == 'candidate']
cells = []
for d in C:
    x, y = d['centre']; G = zoom(d['plate'], x - 32, y - 32, x + 32, y + 32, 5, 10, False)
    X, Y = 34 + 32 * 5, 34 + 32 * 5; cv2.line(G, (X - 8, Y), (X - 3, Y), (230, 190, 0), 1); cv2.line(G, (X + 3, Y), (X + 8, Y), (230, 190, 0), 1)
    cv2.line(G, (X, Y - 8), (X, Y - 3), (230, 190, 0), 1); cv2.line(G, (X, Y + 3), (X, Y + 8), (230, 190, 0), 1)
    Cc = np.full((G.shape[0] + 14, G.shape[1], 3), 255, np.uint8); Cc[14:] = G
    cv2.putText(Cc, f"{d['cid']} {d['sampler']} {d['plate']} {x},{y}", (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1)
    cells.append(Cc)
CW = max(c.shape[1] for c in cells); CH = max(c.shape[0] for c in cells); cols = 5
for s in range(0, len(cells), 20):
    part = cells[s:s + 20]; rows = (len(part) + cols - 1) // cols
    S = np.full((rows * (CH + 4), cols * (CW + 4), 3), 180, np.uint8)
    for i, c in enumerate(part):
        r, cc = divmod(i, cols); S[r * (CH + 4):r * (CH + 4) + c.shape[0], cc * (CW + 4):cc * (CW + 4) + c.shape[1]] = c
    S = cv2.resize(S, None, fx=0.75, fy=0.75, interpolation=cv2.INTER_AREA)
    f = os.path.join(OUT, f'{TAG}_{s // 20 + 1:02d}.png'); cv2.imwrite(f, S); print(f, S.shape)
