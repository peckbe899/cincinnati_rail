"""Show what today's rule calls text (ink_bins bin 8) on crops of a plate.
Reads unet_data/<plate>_bins.png (bin codes 0-9 or colours) and the scan. Writes pics/<plate>_bins_<name>.jpg:
left the scan, right the scan with bin 8 in magenta and every other ink bin in its bin colour (faded).
Usage: python -B bins_overlay.py 44 name:x0,y0,x1,y1 ..."""
import os, sys, json, cv2, numpy as np
R = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D'
O = os.path.join(R, 'data/sanborn/bench_2026-11-25/text/research/pics')
plate = sys.argv[1]
im = cv2.imread(os.path.join(R, f'data/sanborn/cufp/22-{plate}.jpg'))
b = cv2.imread(os.path.join(R, f'data/sanborn/unet_data/{plate}_bins.png'), cv2.IMREAD_UNCHANGED)
meta = json.load(open(os.path.join(R, f'data/sanborn/unet_data/{plate}_bins.json')))
print('bins png', b.shape, b.dtype, 'scan', im.shape)
if b.ndim == 3:   # colour coded: map colours back to codes
    code = np.zeros(b.shape[:2], np.uint8)
    for k, v in meta['bins'].items():
        r, g, bl = v['rgb']
        code[(b[..., 2] == r) & (b[..., 1] == g) & (b[..., 0] == bl)] = int(k)
else:
    code = b
print('codes present', np.unique(code))
for a in sys.argv[2:]:
    n, bb = a.split(':')
    x0, y0, x1, y1 = map(int, bb.split(','))
    c = im[y0:y1, x0:x1].copy()
    k = code[y0:y1, x0:x1]
    ov = (c * 0.55 + 255 * 0.45).astype(np.uint8)
    for kk, v in meta['bins'].items():
        r, g, bl = v['rgb']
        m = k == int(kk)
        ov[m] = (bl, g, r)
    cv2.imwrite(os.path.join(O, f'{plate}_bins_{n}.jpg'), np.hstack([c, ov]), [cv2.IMWRITE_JPEG_QUALITY, 90])
