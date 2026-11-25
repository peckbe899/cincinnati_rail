"""verify (25 Nov 2026): tiles of a truth crop for looking: text ink red, non-text ink blue, don't care orange, paper = scan
faded. Optional second layer: the finder's verdict on the same pixels (--finder): text called non-text = blue in the truth
but magenta-boxed... kept simple: a side-by-side of truth (left) and finder (right) colouring.

    cd data/sanborn; python -B bench_2026-11-25/text/verify/scripts/truth_tiles.py T1 [--finder] [--tile 750 500] [--scale 1.0]
Writes verify/pics/truth_T#_rRcC.jpg."""
import json, os, sys
import numpy as np, cv2
T = os.path.join(os.getcwd(), 'bench_2026-11-25', 'text'); V = os.path.join(T, 'verify')
tid = sys.argv[1]; fin = '--finder' in sys.argv
tw, th = (int(sys.argv[sys.argv.index('--tile') + 1]), int(sys.argv[sys.argv.index('--tile') + 2])) if '--tile' in sys.argv else (750, 500)
sc = float(sys.argv[sys.argv.index('--scale') + 1]) if '--scale' in sys.argv else 1.0
c = json.load(open(os.path.join(T, 'inventory', 'truth', 'crops.json')))[tid]; N = c['plate']; x0, y0, x1, y1 = c['win']
im = cv2.imread(f'cufp/22-{N}.jpg')[y0:y1, x0:x1]; t = cv2.imread(os.path.join(T, 'inventory', 'truth', f'{tid}_mask.png'), 0)
def paint(lbl, cols):
    o = (im.astype(np.float32) * 0.35 + 255 * 0.65).astype(np.uint8)
    for v, col in cols.items(): o[lbl == v] = col
    return o
A = paint(t, {1: (200, 90, 0), 2: (0, 0, 230), 3: (0, 160, 255)})
if fin:
    f = cv2.imread(os.path.join(T, 'finder', 'out', f'{N}_finder.png'), 0)[y0:y1, x0:x1]
    # finder vs truth: green = finder text on truth non-text (false text), magenta = truth text the finder missed
    B = paint(t, {1: (200, 150, 120), 2: (150, 150, 255), 3: (180, 220, 255)})
    ft = np.isin(f, (2, 3, 4)); B[ft & (t == 1)] = (0, 170, 0); B[~ft & (t == 2)] = (200, 0, 200); B[ft & (t == 2)] = (0, 0, 200)
H, W = t.shape
for r, yy in enumerate(range(0, H, th)):
    for cc, xx in enumerate(range(0, W, tw)):
        a = A[yy:yy + th, xx:xx + tw]
        if fin: a = np.hstack([a, np.full((a.shape[0], 6, 3), 255, np.uint8), B[yy:yy + th, xx:xx + tw]])
        if sc != 1.0: a = cv2.resize(a, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
        cv2.putText(a, f'{tid} x{x0 + xx} y{y0 + yy}', (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
        cv2.imwrite(os.path.join(V, 'pics', f'truth_{tid}_{"fin_" if fin else ""}r{r}c{cc}.jpg'), a, [cv2.IMWRITE_JPEG_QUALITY, 90])
print('ok', tid, H, W)
