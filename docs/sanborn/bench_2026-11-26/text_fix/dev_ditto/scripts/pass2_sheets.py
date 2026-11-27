"""Sheets for the second-pass completeness aid, part b (dev_ditto, 26 Nov 2026; scan only).
pics/pairs/pass2b.json holds (made by the inline rule recorded in truth/README.md): 'pairs2' = two tiny pieces (3-30 px,
sides <= 8) 3-10 px apart, joint box <= 14 px, no other ink within 2 px; 'singles' = one separate piece of 12-60 px,
sides <= 12, no other ink within 4 px. Both skip ditto words already in the truth and the pairs of pairs.json.
python -B pass2_sheets.py -> pics/pairs/p2_<kind>_NN.png (42 cells, 40 x 40 px at 4x; ids Q### / S###)"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from zoom import zoom, DD
O = os.path.join(DD, 'pics', 'pairs'); J = json.load(open(os.path.join(O, 'pass2b.json')))
for kind, tag, rows in (('pairs2', 'Q', J['pairs2']), ('singles', 'S', [q for q in J['singles'] if q['scale'] in (200, 400)])):
    cells = []
    for i, q in enumerate(rows):
        q['id'] = f'{tag}{i + 1:03d}'; x, y = q['centre']; G = zoom(q['plate'], x - 20, y - 20, x + 20, y + 20, 4, 10, False)
        Cc = np.full((G.shape[0] + 13, G.shape[1], 3), 255, np.uint8); Cc[13:] = G
        cv2.putText(Cc, f"{q['id']} {q['plate']}#{q['rank']} {x},{y}", (2, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 0, 0), 1); cells.append(Cc)
    CW = max(c.shape[1] for c in cells); CH = max(c.shape[0] for c in cells); cols = 7
    for s in range(0, len(cells), 42):
        part = cells[s:s + 42]; nr = (len(part) + cols - 1) // cols
        S = np.full((nr * (CH + 3), cols * (CW + 3), 3), 180, np.uint8)
        for i, c in enumerate(part):
            r, cc = divmod(i, cols); S[r * (CH + 3):r * (CH + 3) + c.shape[0], cc * (CW + 3):cc * (CW + 3) + c.shape[1]] = c
        cv2.imwrite(os.path.join(O, f'p2_{kind}_{s // 42 + 1:02d}.png'), S); print(kind, s // 42 + 1, S.shape)
json.dump(J, open(os.path.join(O, 'pass2b.json'), 'w'), indent=0)
