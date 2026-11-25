"""Overlay of a finder output in a window. python -B <this> N FINDER_PNG OUT.jpg X0 Y0 X1 Y1 [scale]
Colours: magenta glyph/cluster, blue stroke or dot taken in by a glyph, orange lone stroke, grey line ink, green other ink."""
import sys, os
sys.dont_write_bytecode = True
import numpy as np, cv2
a = sys.argv; N, F, OUT = a[1], a[2], a[3]; x0, y0, x1, y1 = (int(v) for v in a[4:8]); s = float(a[8]) if len(a) > 8 else 1.0
COLOR = {1: (170, 170, 170), 2: (220, 0, 220), 3: (255, 120, 0), 4: (0, 160, 255), 5: (0, 150, 0)}
im = cv2.imread(f'cufp/22-{N}.jpg')[y0:y1, x0:x1]; code = cv2.imread(F, 0)[y0:y1, x0:x1]
c = (im * 0.25 + 255 * 0.75).astype(np.uint8)
for v, col in COLOR.items(): c[code == v] = col
if s != 1: c = cv2.resize(c, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
cv2.imwrite(OUT, c, [cv2.IMWRITE_JPEG_QUALITY, 90])
