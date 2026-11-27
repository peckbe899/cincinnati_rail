"""Close zoom of a targeted truth crop: scan left, truth right (dev_block, 26 Nov 2026). Scan and truth only.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/dev_block/scripts/tz.py DB09 x0 y0 x1 y1 [--scale 8] [--name N]

Truth colours: text red, not text blue, don't care orange (outside the scope pale), paper faded scan; 10 px grid.
Writes dev_block/pics/check/tz_DB##_NAME.png."""
import os, sys, json
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from common import plate_img  # noqa: E402
from zoom import gridded  # noqa: E402

a = sys.argv; tid = a[1]; x0, y0, x1, y1 = [int(v) for v in a[2:6]]
sc = float(a[a.index('--scale') + 1]) if '--scale' in a else 8.0; name = a[a.index('--name') + 1] if '--name' in a else f'{x0}_{y0}'
TR = os.path.join(DB, 'truth'); c = json.load(open(os.path.join(TR, 'crops.json'), encoding='utf8'))[tid]
X0, Y0, X1, Y1 = c['win']; M = cv2.imread(os.path.join(TR, f'{tid}_mask.png'), 0)
im = plate_img(c['plate'])[y0:y1, x0:x1].copy()
t = np.full((y1 - y0, x1 - x0), 255, np.uint8)
ax0, ay0, ax1, ay1 = max(x0, X0), max(y0, Y0), min(x1, X1), min(y1, Y1)
t[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0] = M[ay0 - Y0:ay1 - Y0, ax0 - X0:ax1 - X0]
o = (im.astype(np.float32) * 0.35 + 255 * 0.65).astype(np.uint8)
for v, col in {1: (200, 90, 0), 2: (0, 0, 230), 3: (0, 160, 255)}.items(): o[t == v] = col
A = gridded(im, x0, y0, sc); B = gridded(o, x0, y0, sc)
f = os.path.join(DB, 'pics', 'check', f'tz_{tid}_{name}.png'); cv2.imwrite(f, np.hstack([A, np.full((A.shape[0], 6, 3), 255, np.uint8), B])); print(f)
