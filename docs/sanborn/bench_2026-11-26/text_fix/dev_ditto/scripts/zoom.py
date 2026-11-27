"""Scan-only zoom with a coordinate grid, for reading ditto marks by eye (dev_ditto, 26 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/dev_ditto/scripts/zoom.py PLATE x0 y0 x1 y1 [--scale 3] [--grid 20] [--name NAME] [--ink]

Writes dev_ditto/pics/z_<NAME or PLATE_x0_y0>.png. Grid lines every --grid px (full-plate px), labelled every 5th
(or every 100 px). --ink paints the ink (L < 140 on the paper) dark so faint ticks show the same as in the masks.
Reads only cufp/22-N.jpg and the paper mask. Never a finder output or bins."""
import os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import window

DD = os.path.normpath(os.path.join(HERE, '..')); PICS = os.path.join(DD, 'pics')


def opt(a, name, d=None):
    return a[a.index(name) + 1] if name in a else d


def zoom(p, x0, y0, x1, y1, sc=3.0, grid=20, ink_paint=False, marks=()):
    img, lab, ink, (wx0, wy0, wx1, wy1) = window(p, x0, y0, x1, y1)
    c = img.copy()
    if ink_paint:
        c = (c * 0.45 + 255 * 0.55).astype(np.uint8); c[ink] = (img[ink] * 0.5).astype(np.uint8)
    t = cv2.resize(c, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST if sc >= 3 else cv2.INTER_LINEAR)
    H, W = t.shape[:2]
    P = 34; G = np.full((H + P, W + P, 3), 255, np.uint8); G[P:, P:] = t
    lab_every = 100 if grid >= 20 else 50
    for gx in range((wx0 // grid + 1) * grid, wx1, grid):
        X = int((gx - wx0) * sc) + P
        col = (0, 0, 220) if gx % lab_every == 0 else (240, 170, 170)
        G[P:, X] = (G[P:, X] * 0.55 + np.array(col) * 0.45).astype(np.uint8)
        if gx % lab_every == 0:
            cv2.putText(G, str(gx), (X - 14, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 200), 1)
        elif gx % (grid * 1) == 0 and sc >= 3:
            cv2.putText(G, str(gx % 100), (X - 6, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (150, 80, 80), 1)
    for gy in range((wy0 // grid + 1) * grid, wy1, grid):
        Y = int((gy - wy0) * sc) + P
        col = (0, 0, 220) if gy % lab_every == 0 else (240, 170, 170)
        G[Y, P:] = (G[Y, P:] * 0.55 + np.array(col) * 0.45).astype(np.uint8)
        if gy % lab_every == 0:
            cv2.putText(G, str(gy), (0, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 0, 200), 1)
        elif sc >= 3:
            cv2.putText(G, str(gy % 100), (8, Y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (150, 80, 80), 1)
    for (mx, my, txt) in marks:
        X = int((mx - wx0) * sc) + P; Y = int((my - wy0) * sc) + P
        cv2.circle(G, (X, Y), int(9 * sc), (255, 0, 200), 1); cv2.putText(G, txt, (X + int(9 * sc), Y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 200), 1)
    return G


if __name__ == '__main__':
    a = sys.argv; p = a[1]; x0, y0, x1, y1 = [int(v) for v in a[2:6]]
    sc = float(opt(a, '--scale', 3)); grid = int(opt(a, '--grid', 20)); name = opt(a, '--name', f'{p}_{x0}_{y0}')
    G = zoom(p, x0, y0, x1, y1, sc, grid, '--ink' in a)
    os.makedirs(PICS, exist_ok=True); f = os.path.join(PICS, f'z_{name}.png'); cv2.imwrite(f, G); print(f, G.shape)
