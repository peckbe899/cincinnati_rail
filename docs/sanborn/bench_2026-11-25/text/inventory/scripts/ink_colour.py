"""Is any lettering printed in a colour other than black? Counts, per plate, the ink (L < 140 of 255, ink_bins' rule)
that is reddish, bluish or yellowish (Lab a* or b* beyond +-20), its share of all ink, and the size of its 8-connected
pieces; and the paper and tint colour for comparison. Writes measure/ink_colour.json and a picture of the largest
coloured-ink pieces (measure/ink_colour_<plate>.jpg, up to 24 tiles) to look at.
python -B ink_colour.py"""
import os, json
import numpy as np, cv2
from common import INV, plate_img, paper, jdump

OUT = os.path.join(INV, 'measure')
res = {}
for p in ['44', '1A', '5', '90', '30', '60B', '47', '54A']:
    im = plate_img(p); lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB); pa = paper(p)
    L = lab[..., 0]; a = lab[..., 1].astype(np.int16) - 128; b = lab[..., 2].astype(np.int16) - 128
    ink = (L < 140) & pa
    red = ink & (a > 20); blue = ink & (b < -20); yel = ink & (b > 20) & ~red
    r = dict(ink_px=int(ink.sum()), red_ink_px=int(red.sum()), blue_ink_px=int(blue.sum()), yellow_ink_px=int(yel.sum()),
             ink_L_med=round(float(np.median(L[ink])) * 100 / 255, 1), ink_a_med=float(np.median(a[ink])), ink_b_med=float(np.median(b[ink])),
             paper_L_med=round(float(np.median(L[pa & ~ink][::97])) * 100 / 255, 1), paper_a_med=float(np.median(a[pa & ~ink][::97])), paper_b_med=float(np.median(b[pa & ~ink][::97])))
    tiles = []
    for name, m in (('red', red), ('blue', blue)):
        n, lb, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
        A = st[1:, 4]; r[f'{name}_pieces_ge20px'] = int((A >= 20).sum()); r[f'{name}_largest_px'] = int(A.max()) if len(A) else 0
        for k in (np.argsort(-A)[:12] + 1 if len(A) else []):
            x, y, w, h, _ = st[k]; c = 40
            t = im[max(0, y - c):y + h + c, max(0, x - c):x + w + c]
            s = min(1.0, 200 / max(t.shape[:2])); t = cv2.resize(t, None, fx=s, fy=s)
            card = np.full((216, 210, 3), 255, np.uint8); card[16:16 + t.shape[0], :t.shape[1]] = t
            cv2.putText(card, f'{name} {x},{y} {st[k, 4]}px', (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 0, 0), 1); tiles.append(card)
    if tiles:
        rows = [np.hstack(tiles[i:i + 6] + [np.full((216, 210, 3), 255, np.uint8)] * (6 - len(tiles[i:i + 6]))) for i in range(0, len(tiles), 6)]
        cv2.imwrite(os.path.join(OUT, f'ink_colour_{p}.jpg'), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])
    res[p] = r; print(p, r)
jdump(dict(note='coloured ink (a* > 20 red, b* < -20 blue, b* > 20 yellow) among the dark pixels; Lab medians in L 0-100, a b -128..127. Made by ink_colour.py. Measured.', plates=res),
      os.path.join(OUT, 'ink_colour.json'))
