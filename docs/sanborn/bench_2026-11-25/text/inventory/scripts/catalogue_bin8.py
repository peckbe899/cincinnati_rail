"""Which bin ink_bins gave the text pixels of each catalogue example (the kinds and scales the truth crops lack:
KEY, title, scale notes, adjoining sheet numbers, 200 and 400 ft lettering, the heavy tint of 54A).
The text pixels are the automatic ones of wordpix.word_pixels (snapped box less straight lines), not hand-checked:
an estimate. python -B catalogue_bin8.py -> measure/catalogue_bin8.json"""
import os, json, math
import numpy as np, cv2
from common import INV, window, bins, jdump
from wordpix import word_pixels
from measure import parse_catalogue

NAMES = {0: 'no ink', 1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text', 9: 'not sorted'}
rows = []; agg = {}
for r in parse_catalogue():
    x1, y1, x2, y2, h = r['geo']; L = math.hypot(x2 - x1, y2 - y1); P = int(L / 2 + 3 * h + 120); cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    img, lab, ink, (wx0, wy0, wx1, wy1) = window(r['plate'], int(cx - P), int(cy - P), int(cx + P), int(cy + P))
    w = word_pixels(ink, (wx0, wy0), r['geo'], r['flags']); bx0, by0, bx1, by1 = w['sub']
    B = bins(r['plate'])[wy0 + by0:wy0 + by1, wx0 + bx0:wx0 + bx1]
    t = w['text']; n = int(t.sum())
    if n < 10: continue
    cnt = np.bincount(B[t], minlength=10)
    share = {NAMES[k]: round(cnt[k] / n, 3) for k in range(10) if cnt[k]}
    rows.append(dict(plate=r['plate'], kind=r['kind'], reading=r['reading'], text_px=n, bin8_share=round(cnt[8] / n, 3), bins=share))
    a = agg.setdefault(r['kind'], [0, 0, []]); a[0] += int(cnt[8]); a[1] += n; a[2].append(f"{r['plate']}:{r['reading'][:20]}={cnt[8] / n:.2f}")
jdump(dict(note='share of each catalogue example\'s (automatic) text pixels in each bin of unet_data/N_bins.png. Estimate (text pixels not hand-checked). Made by catalogue_bin8.py',
           by_kind={k: dict(bin8_share=round(v[0] / max(1, v[1]), 3), examples=v[2]) for k, v in sorted(agg.items())}, rows=rows),
      os.path.join(INV, 'measure', 'catalogue_bin8.json'))
for k, v in sorted(agg.items()): print(k, round(v[0] / max(1, v[1]), 3), v[2])
