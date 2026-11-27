"""Scan views for sealed builder A (26 Nov 2026). Reads only the scan cufp/22-N.jpg (and the paper mask for 'ink').
Never reads any finder output or bin.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/sealed_A/scripts/view.py zoom N x0 y0 x1 y1 SCALE OUT.png [--grid 10] [--ink]
    python -B bench_2026-11-26/text_fix/sealed_A/scripts/view.py quarter N OUTDIR [--tile 4000 3000] [--scale 0.25]

zoom: the scan window at SCALE with plate-px ticks every 50 px (labels every 100) and an optional faint grid.
      --ink paints the ink (L < 140 on the paper) dark blue over a faded scan, to see what the mask will hold.
quarter: the whole plate at 1/4 size in tiles (default 4000 x 3000 full px each), with plate-px labels every 500 px."""
import os, sys, math
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import plate_img, window

arg = sys.argv


def opt(name, n=1, d=None):
    if name not in arg: return d
    i = arg.index(name); v = arg[i + 1:i + 1 + n]; return v if n > 1 else v[0]


def zoom(N, x0, y0, x1, y1, sc, grid=0, ink=False):
    im, lab, ik, (x0, y0, x1, y1) = window(N, x0, y0, x1, y1)
    im = im.copy()
    if ink:
        o = (im.astype(np.float32) * 0.35 + 255 * 0.65).astype(np.uint8); o[ik] = (140, 30, 0); im = o
    A = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST if sc >= 1 else cv2.INTER_AREA)
    if grid:
        for gx in range((x0 // grid + 1) * grid, x1, grid):
            X = int((gx - x0) * sc); A[:, X] = (A[:, X].astype(int) * 3 // 4 + np.array([0, 0, 60])).astype(np.uint8)
        for gy in range((y0 // grid + 1) * grid, y1, grid):
            Y = int((gy - y0) * sc); A[Y, :] = (A[Y, :].astype(int) * 3 // 4 + np.array([0, 0, 60])).astype(np.uint8)
    for gx in range((x0 // 50 + 1) * 50, x1, 50):
        X = int((gx - x0) * sc); A[:8, X] = (0, 0, 255)
        if gx % 100 == 0: cv2.putText(A, str(gx), (X + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 200), 1)
    for gy in range((y0 // 50 + 1) * 50, y1, 50):
        Y = int((gy - y0) * sc); A[Y, :8] = (0, 0, 255)
        if gy % 100 == 0: cv2.putText(A, str(gy), (2, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 200), 1)
    return A


def quarter(N, outdir, tw=4000, th=3000, sc=0.25):
    im = plate_img(N); H, W = im.shape[:2]; os.makedirs(outdir, exist_ok=True); out = []
    for r, ty in enumerate(range(0, H, th)):
        for c, tx in enumerate(range(0, W, tw)):
            t = cv2.resize(im[ty:ty + th, tx:tx + tw], None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
            for gx in range((tx // 500) * 500, tx + tw, 500):
                if gx < tx or int((gx - tx) * sc) >= t.shape[1]: continue
                X = int((gx - tx) * sc); t[:, X] = (t[:, X].astype(int) // 2 + np.array([0, 0, 120])).astype(np.uint8)
                cv2.putText(t, str(gx), (X + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 200), 1)
            for gy in range((ty // 500) * 500, ty + th, 500):
                if gy < ty or int((gy - ty) * sc) >= t.shape[0]: continue
                Y = int((gy - ty) * sc); t[Y, :] = (t[Y, :].astype(int) // 2 + np.array([0, 0, 120])).astype(np.uint8)
                cv2.putText(t, str(gy), (2, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 200), 1)
            f = os.path.join(outdir, f'q_{N}_r{r}c{c}.png'); cv2.imwrite(f, t); out.append(f)
    print(N, 'plate', W, 'x', H, '->', len(out), 'tiles'); [print(' ', f) for f in out]


if __name__ == '__main__':
    if arg[1] == 'zoom':
        N = arg[2]; x0, y0, x1, y1 = [int(v) for v in arg[3:7]]; sc = float(arg[7]); out = arg[8]
        A = zoom(N, x0, y0, x1, y1, sc, int(opt('--grid', d='0')), '--ink' in arg)
        cv2.imwrite(out, A); print(out, A.shape)
    elif arg[1] == 'quarter':
        tw, th = [int(v) for v in opt('--tile', 2, ['4000', '3000'])]
        quarter(arg[2], arg[3], tw, th, float(opt('--scale', d='0.25')))
