"""Debug picture: pieces by kind in a window, re-running the finder on the window. python -B <this> N X0 Y0 X1 Y1 OUT.jpg [--ben]
Colours: glyph magenta, cluster purple, jog red, box cyan, stroke (text) blue, dash/line piece green, lone orange, eq teal,
other strokes olive, dots light grey, line ink grey; --ben: text within 3 px of Ben's lines yellow."""
import sys, os
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import finder
a = sys.argv; N = a[1]; win = tuple(int(v) for v in a[2:6]); OUT = a[6]
code, rec, (n, lb, F, k) = finder.run(N, win, None, False, None, verbose=False)
z = np.load  # noqa
im = cv2.imread(f'cufp/22-{N}.jpg')[win[1]:win[3], win[0]:win[2]]
c = (im * 0.25 + 255 * 0.75).astype(np.uint8)
c[code == 1] = (175, 175, 175)
col = dict(glyph=(220, 0, 220), cluster=(140, 0, 140), jog=(0, 0, 230), box=(230, 230, 0), stroke=(0, 120, 120), dot=(200, 200, 200), blob=(0, 0, 0), long=(80, 80, 0), eq=(160, 160, 0))
kc = np.zeros((n, 3), np.uint8)
for kk, cc in col.items(): kc[k == kk] = cc
m = lb > 0; c[m & (code > 0)] = kc[lb[m & (code > 0)]]
c[code == 3] = (255, 120, 0); c[code == 4] = (0, 160, 255)
if '--ben' in a:
    import benlines
    W, H = rec['size']; mm, _ = benlines.raster(N, W, H); mm = mm[win[1]:win[3], win[0]:win[2]]
    d = cv2.distanceTransform((mm == 0).astype(np.uint8), cv2.DIST_L2, 5)
    c[(d <= 3) & np.isin(code, (2, 3, 4))] = (0, 230, 255); c[(mm > 0) & (code == 0)] = (0, 200, 0)
cv2.imwrite(OUT, c, [cv2.IMWRITE_JPEG_QUALITY, 90]); print(rec['pieces'], rec['px'])
