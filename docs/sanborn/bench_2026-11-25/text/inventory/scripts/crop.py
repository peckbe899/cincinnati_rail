"""Crop a full-size window of a plate, optionally beside its ink_bins sorting (bin 8 magenta, other ink grey).
python -B crop.py PLATE X0 Y0 X1 Y1 OUT.jpg [--bins] [--scale S] [--grid G]
--bins   put the bins picture under the crop (text bin magenta, block line green, lot orange, pipe navy, sewer teal, rail red/blue)
--grid G draw a grid line every G full px with its coordinate, for reading positions off the picture"""
import os, sys, cv2, numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))   # data/sanborn
COL = {1: (0, 150, 0), 2: (0, 140, 255), 3: (120, 70, 20), 4: (0, 0, 230), 5: (255, 150, 0), 6: (160, 0, 0), 7: (160, 170, 0), 8: (255, 0, 255), 9: (120, 120, 120)}
_cache = {}

def plate(p):
    if p not in _cache: _cache[p] = cv2.imread(os.path.join(ROOT, 'cufp', f'22-{p}.jpg'))
    return _cache[p]

def bins(p):
    k = 'b' + p
    if k not in _cache: _cache[k] = cv2.imread(os.path.join(ROOT, 'unet_data', f'{p}_bins.png'), 0)
    return _cache[k]

def bins_pic(b):
    c = np.full(b.shape + (3,), 255, np.uint8)
    for k, v in COL.items(): c[b == k] = v
    return c

def grid(c, x0, y0, g, s):
    h, w = c.shape[:2]
    for x in range((x0 // g + 1) * g, x0 + int(w / s), g):
        X = int((x - x0) * s); cv2.line(c, (X, 0), (X, h), (255, 200, 0), 1); cv2.putText(c, str(x), (X + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 0, 0), 1)
    for y in range((y0 // g + 1) * g, y0 + int(h / s), g):
        Y = int((y - y0) * s); cv2.line(c, (0, Y), (w, Y), (255, 200, 0), 1); cv2.putText(c, str(y), (2, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 0, 0), 1)
    return c

def crop(p, x0, y0, x1, y1, scale=1.0, with_bins=False, g=0):
    im = plate(p)[y0:y1, x0:x1].copy()
    parts = [im]
    if with_bins: parts.append(bins_pic(bins(p)[y0:y1, x0:x1]))
    out = []
    for c in parts:
        if scale != 1.0: c = cv2.resize(c, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_NEAREST)
        if g: c = grid(c, x0, y0, g, scale)
        out.append(c)
    return np.vstack(out) if (x1 - x0) >= (y1 - y0) else np.hstack(out)

if __name__ == '__main__':
    a = sys.argv; p = a[1]; x0, y0, x1, y1 = map(int, a[2:6]); out = a[6]
    s = float(a[a.index('--scale') + 1]) if '--scale' in a else 1.0
    g = int(a[a.index('--grid') + 1]) if '--grid' in a else 0
    cv2.imwrite(out, crop(p, x0, y0, x1, y1, s, '--bins' in a, g), [cv2.IMWRITE_JPEG_QUALITY, 90])
