"""Zoomed view of a window of a sealed plate (scan only), with full-plate px ticks, for reading by eye.
python -B view.py PLATE X0 Y0 X1 Y1 SCALE OUT.jpg [--grid STEP] [--ink]
--grid STEP: faint grid lines every STEP full px (default: 100 at scale<2, 50 at 2-4, 20 above).
--ink: show the ink mask (L<140 on paper) as black on white instead of the scan."""
import os, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import window


def render(p, x0, y0, x1, y1, sc, step=None, ink=False):
    im, lab, ink_m, (x0, y0, x1, y1) = window(p, x0, y0, x1, y1)
    if ink: im = np.where(ink_m[..., None], 0, 255).astype(np.uint8).repeat(3, 2) if ink_m.ndim == 2 else im
    t = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST if sc >= 2 else cv2.INTER_CUBIC)
    step = step or (100 if sc < 2 else 50 if sc < 4 else 20 if sc < 7 else 10)
    M = 34
    out = np.full((t.shape[0] + M, t.shape[1] + M + 4, 3), 255, np.uint8); out[M:, M:M + t.shape[1]] = t
    for gx in range((x0 // step + 1) * step, x1, step):
        X = int((gx - x0) * sc) + M
        out[M:, X] = (out[M:, X].astype(int) * 0.7 + np.array([255, 120, 0]) * 0.3).astype(np.uint8)
        cv2.putText(out, str(gx), (X - 14, 12 if (gx // step) % 2 else 26), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (200, 0, 0), 1)
    for gy in range((y0 // step + 1) * step, y1, step):
        Y = int((gy - y0) * sc) + M
        out[Y, M:] = (out[Y, M:].astype(int) * 0.7 + np.array([255, 120, 0]) * 0.3).astype(np.uint8)
        cv2.putText(out, str(gy), (0, Y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 0, 0), 1)
    return out


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    p = a[0]; x0, y0, x1, y1 = map(int, a[1:5]); sc = float(a[5]); out = a[6]
    step = int(sys.argv[sys.argv.index('--grid') + 1]) if '--grid' in sys.argv else None
    if step: a = a  # noqa
    cv2.imwrite(out, render(p, x0, y0, x1, y1, sc, step, '--ink' in sys.argv), [cv2.IMWRITE_JPEG_QUALITY, 92])
