"""Zoom pictures of the scan for writing annotations (dev_block, 26 Nov 2026). Scan only.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/dev_block/scripts/zoom.py PLATE X Y [--half 130] [--scale 3] [--name NAME] [--ink]

Writes dev_block/pics/zoom/NAME.png: the scan round (X, Y) (full-plate px) at `scale`, a faint grid every 10 px, labelled
every 50 px in full-plate px. --ink: right half shows the ink (L < 140 on the paper) in black on white, for counting px."""
import os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.normpath(os.path.join(HERE, '..'))
ROOT = os.path.normpath(os.path.join(DB, '..', '..', '..'))
sys.path.insert(0, HERE)
SEALED = set('6 9 52 56 58 63 35 38 41 66 71 76 84 88 46 92'.split())
_c = {}


def opt(n, d):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def plate(N):
    assert N not in SEALED
    if N not in _c: _c[N] = cv2.imread(os.path.join(ROOT, 'cufp', f'22-{N}.jpg'))
    return _c[N]


def gridded(im, x0, y0, sc, col=(0, 0, 160)):
    A = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
    h, w = im.shape[:2]
    for gx in range((x0 // 10 + 1) * 10, x0 + w, 10):
        X = int((gx - x0) * sc); A[:, X] = (A[:, X].astype(int) * 3 // 4 + np.array(col) // 4).astype(np.uint8) if gx % 50 else (A[:, X].astype(int) // 3 + np.array(col) * 2 // 3).astype(np.uint8)
    for gy in range((y0 // 10 + 1) * 10, y0 + h, 10):
        Y = int((gy - y0) * sc); A[Y, :] = (A[Y, :].astype(int) * 3 // 4 + np.array(col) // 4).astype(np.uint8) if gy % 50 else (A[Y, :].astype(int) // 3 + np.array(col) * 2 // 3).astype(np.uint8)
    for gx in range((x0 // 50 + 1) * 50, x0 + w, 50): cv2.putText(A, str(gx), (int((gx - x0) * sc) + 2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 200), 1)
    for gy in range((y0 // 50 + 1) * 50, y0 + h, 50): cv2.putText(A, str(gy), (2, int((gy - y0) * sc) - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 200), 1)
    return A


def ink_of(N, x0, y0, x1, y1):
    from common import window
    _, _, ink, _ = window(N, x0, y0, x1, y1); return ink


if __name__ == '__main__':
    N, X, Y = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    hf = int(opt('--half', '130')); sc = float(opt('--scale', '3')); name = opt('--name', f'{N}_{X}_{Y}')
    im = plate(N); H, W = im.shape[:2]
    x0, y0, x1, y1 = max(0, X - hf), max(0, Y - hf), min(W, X + hf), min(H, Y + hf)
    A = gridded(im[y0:y1, x0:x1], x0, y0, sc)
    if '--ink' in sys.argv:
        k = ink_of(N, x0, y0, x1, y1); B = np.where(k[..., None], 0, 255).astype(np.uint8).repeat(3, 2)
        A = np.hstack([A, np.full((A.shape[0], 6, 3), 255, np.uint8), gridded(B, x0, y0, sc)])
    os.makedirs(os.path.join(DB, 'pics', 'zoom'), exist_ok=True)
    f = os.path.join(DB, 'pics', 'zoom', f'{name}.png'); cv2.imwrite(f, A); print(f, A.shape)
