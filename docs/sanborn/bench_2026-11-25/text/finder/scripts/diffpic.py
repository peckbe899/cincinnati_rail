"""Picture of where the finder and ink_bins' bin 8 agree and disagree, in a window (full size).

    cd data/sanborn
    python -B <this> N FINDER_PNG OUT.jpg X0 Y0 X1 Y1 [--ben]

Colours: magenta both call it text; blue finder text only; red bin 8 only, finder says line ink; orange bin 8 only,
finder says other ink; grey the rest of the ink. --ben draws Ben's lines (thin green)."""
import sys, os
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
a = sys.argv; N, F, OUT = a[1], a[2], a[3]; x0, y0, x1, y1 = (int(v) for v in a[4:8])
im = cv2.imread(f'cufp/22-{N}.jpg')[y0:y1, x0:x1]; code = cv2.imread(F, 0)[y0:y1, x0:x1]; bins = cv2.imread(f'unet_data/{N}_bins.png', 0)[y0:y1, x0:x1]
text = np.isin(code, (2, 3, 4)); b8 = bins == 8; ink = code > 0
c = (im * 0.25 + 255 * 0.75).astype(np.uint8)
c[ink] = (150, 150, 150); c[text & b8] = (220, 0, 220); c[text & ~b8] = (255, 90, 0); c[b8 & ~text & (code == 1)] = (0, 0, 230); c[b8 & ~text & (code == 5)] = (0, 150, 255)
if '--ben' in a:
    import benlines
    H, W = cv2.imread(F, 0).shape; m, _ = benlines.raster(N, W, H); c[m[y0:y1, x0:x1] > 0] = (0, 170, 0)
cv2.imwrite(OUT, c, [cv2.IMWRITE_JPEG_QUALITY, 90])
