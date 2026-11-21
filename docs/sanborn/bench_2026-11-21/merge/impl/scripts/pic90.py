"""merge/impl: plate 90's ink bins after the change, as the editor colours them: an overview (1/6) and full-size crops.
    python -B pic90.py [X0,Y0 ...]   -> merge/impl/bins_sample/90_overview.jpg, 90_crop_X0_Y0.jpg (1600 x 1100, full res)
The editor's colours (ink_bins.COL): block line green, lot line light blue, building outline brown, railroad red,
streetcar orange, water pipe navy, sewer teal, text magenta, not sorted grey; the merged step's editor lines are not drawn."""
import sys, json
import numpy as np, cv2
import common as C
COL = {1: (0, 150, 0), 2: (255, 140, 0), 3: (20, 70, 120), 4: (0, 0, 230), 5: (0, 150, 255), 6: (160, 0, 0), 7: (160, 170, 0), 8: (255, 0, 255), 9: (120, 120, 120)}
n = '90'; im = cv2.imread(C.DATA + f'cufp/22-{n}.jpg'); A = cv2.imread(C.IMPL + f'bins_sample/{n}_after.png', 0)
v = (im * 0.35 + 255 * 0.65).astype(np.uint8)
for k, c in COL.items(): v[A == k] = c
cv2.imwrite(C.IMPL + f'bins_sample/{n}_overview.jpg', cv2.resize(v, None, fx=1 / 6, fy=1 / 6, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
for xy in sys.argv[1:]:
    x0, y0 = (int(t) for t in xy.split(',')); cv2.imwrite(C.IMPL + f'bins_sample/{n}_crop_{x0}_{y0}.jpg', v[y0:y0 + 1100, x0:x0 + 1600], [cv2.IMWRITE_JPEG_QUALITY, 90])
print('ok')
