"""Draw the glyph candidates and words of extract_glyphs.py on a window of a plate, for looking.

    cd data/sanborn
    python -B bench_2026-11-25/text/shapes/scripts/show_words.py N X0 Y0 X1 Y1 OUT.jpg [labels.npz]

Boxes: grey = lone glyph, coloured = in a word (colour per word); a short line from each glyph shows its reading
direction. With labels.npz (from classify.py) the predicted character is written beside each glyph.
"""
import os, sys
import numpy as np
import cv2

N = sys.argv[1]; x0, y0, x1, y1 = (int(v) for v in sys.argv[2:6]); out = sys.argv[6]
D = np.load(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'glyphs', f'{N}.npz'))
im = cv2.imread(f'cufp/22-{N}.jpg')[y0:y1, x0:x1]
c = (im * 0.6 + 255 * 0.4).astype(np.uint8)
rng = np.random.default_rng(1); col = rng.integers(0, 200, (D['word'].max() + 1, 3))
pred = None
if len(sys.argv) > 7:
    P = np.load(sys.argv[7], allow_pickle=True); pred = dict(zip(map(int, P['idx']), P['char']))
for k, (bx, by, bw, bh) in enumerate(D['bbox']):
    if bx + bw < x0 or bx > x1 or by + bh < y0 or by > y1: continue
    cc = (150, 150, 150) if D['wsize'][k] < 2 else tuple(int(v) for v in col[D['word'][k]])
    cv2.rectangle(c, (bx - x0, by - y0), (bx + bw - x0, by + bh - y0), cc, 1)
    cx, cy = D['cen'][k]; a = D['angle'][k]
    cv2.line(c, (int(cx - x0), int(cy - y0)), (int(cx - x0 + 12 * np.cos(a)), int(cy - y0 + 12 * np.sin(a))), (0, 0, 255), 2)
    if pred is not None and k in pred:
        cv2.putText(c, str(pred[k]), (bx - x0, by - y0 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 0, 0), 2)
cv2.imwrite(out, c, [cv2.IMWRITE_JPEG_QUALITY, 90])
