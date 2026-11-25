"""Numbered sheets of a random sample of single-glyph candidates, for labelling by eye.
Reads out/glyphs_<plate>.npz (from glyph_cluster.py). Picks N at random (seed 7), writes
pics/label_<plate>_<s>.png (60 per sheet, 10 x 6, each shown 2x with 6 px of context, the piece itself outlined)
and out/label_sample_<plate>.json (index -> component box). Usage: python -B label_sheets.py 44 240"""
import os, sys, json, cv2, numpy as np
R = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D'
B = os.path.join(R, 'data/sanborn/bench_2026-11-25/text/research')
plate, N = sys.argv[1], int(sys.argv[2])
d = np.load(os.path.join(B, f'out/glyphs_{plate}.npz'))
boxes = d['boxes']
scan = cv2.imread(os.path.join(R, f'data/sanborn/cufp/22-{plate}.jpg'))
pick = np.random.default_rng(7).choice(len(boxes), N, replace=False)
json.dump({'plate': plate, 'pick': pick.tolist(), 'boxes': boxes[pick].tolist()},
          open(os.path.join(B, f'out/label_sample_{plate}.json'), 'w'))
cell = 120
for s in range(0, N, 60):
    sheet = np.full((6 * (cell + 18), 10 * cell, 3), 255, np.uint8)
    for j, g in enumerate(pick[s:s + 60]):
        x, y, w, h = boxes[g]
        c = scan[max(0, y - 6):y + h + 6, max(0, x - 6):x + w + 6].copy()
        cv2.rectangle(c, (6 - 1, 6 - 1), (6 + w, 6 + h), (0, 0, 255), 1)
        sc = min((cell - 6) / c.shape[0], (cell - 6) / c.shape[1], 2.0)
        c = cv2.resize(c, (int(c.shape[1] * sc), int(c.shape[0] * sc)), interpolation=cv2.INTER_CUBIC)
        r, q = divmod(j, 10)
        X, Y = q * cell, r * (cell + 18)
        cv2.putText(sheet, str(s + j), (X + 2, Y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 0, 0), 1)
        sheet[Y + 16:Y + 16 + c.shape[0], X + 2:X + 2 + c.shape[1]] = c
    cv2.imwrite(os.path.join(B, f'pics/label_{plate}_{s // 60}.png'), sheet)
