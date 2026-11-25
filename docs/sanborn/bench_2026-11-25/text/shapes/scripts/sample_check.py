"""A random sample of plate-44 glyphs that the hold-out reader calls digits, for checking by eye (25 Nov 2026).

    python -B bench_2026-11-25/text/shapes/scripts/sample_check.py      (from data/sanborn)

Reader: model_no44.npz (classify.py --holdout 44: no plate-44 glyph in its training set), all classes, no context,
no cutting: what a plate-wide pass would say glyph by glyph. Every glyph of 12-40 px on plate 44 is read; 10 glyphs
are drawn at random (seed 1) from those read as each digit (100 in all). look/check44_digits_0/1.png show each one as
a tile of the scan around it (44 px around its centre at 3.4x, the glyph boxed in red) with the reading in the corner,
one row per digit.
The count of wrong tiles is done by eye and written into the findings, not by this script.
"""
import os, sys
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from read import Reader, HERE  # noqa: E402
from cluster import features  # noqa: E402
from classify import knn  # noqa: E402


def main():
    R = Reader(os.path.join(HERE, 'model_no44.npz'))
    D = np.load(os.path.join(HERE, 'glyphs', '44.npz')); mx = D['hw'].max(1); q = np.nonzero((mx >= 12) & (mx < 40))[0]
    Z = ((features(D['imgs'][q], D['hw'][q]) - R.mu) @ R.V).astype(np.float32)
    b, s, d = knn(R.Ztr, R.ytr, Z); ch = R.classes[b]
    im = cv2.imread('cufp/22-44.jpg'); rng = np.random.default_rng(1); rows = []; picked = {}
    print('plate 44, glyphs 12-40 px:', len(q), '| read as digits:', int(np.isin(ch, list('0123456789')).sum()),
          '| per digit:', {c: int((ch == c).sum()) for c in '0123456789'}, '| junk', int((ch == 'junk').sum()))
    for dg in '0123456789':
        idx = q[ch == dg]; pk = rng.choice(idx, min(10, len(idx)), replace=False); picked[dg] = pk.tolist(); tiles = []
        for k in pk:
            x, y, w, h = D['bbox'][k]; cx, cy = x + w // 2, y + h // 2; r = 22
            t = im[max(0, cy - r):cy + r, max(0, cx - r):cx + r].copy()
            cv2.rectangle(t, (x - max(0, cx - r), y - max(0, cy - r)), (x + w - max(0, cx - r), y + h - max(0, cy - r)), (0, 0, 255), 1)
            t = cv2.resize(t, (146, 146), interpolation=cv2.INTER_CUBIC)
            cv2.putText(t, dg, (3, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 0, 0), 2)
            tiles.append(np.pad(t, ((2, 2), (2, 2), (0, 0)), constant_values=255))
        while len(tiles) < 10: tiles.append(np.full((150, 150, 3), 255, np.uint8))
        rows.append(np.hstack(tiles))
    for i in range(0, 10, 5):
        cv2.imwrite(os.path.join(HERE, 'look', f'check44_digits_{i // 5}.png'), np.vstack(rows[i:i + 5]))
    import json; json.dump(dict(note=__doc__, picked=picked), open(os.path.join(HERE, 'look', 'check44_digits.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
