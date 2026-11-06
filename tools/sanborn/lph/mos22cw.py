"""1922 plate halves -> world mosaic (UTM 16N) for a window, using lph/tf22_cw.json.
Each half keeps the hull of its own picks buffered 60 m; overlaps go to the half the pixel is deepest inside."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
from shapely.geometry import MultiPoint, Point
from matplotlib.path import Path
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'sbg')
from sb import find
Image.MAX_IMAGE_PIXELS = None
TF = json.load(open(SP + 'lph/tf22_cw.json'))
def ap(p, x, y):
    if len(p) == 6: return p[0] * x + p[1] * y + p[4], p[2] * x + p[3] * y + p[5]
    a, c, tx, ty = p; return a * x + c * y + tx, c * x - a * y + ty
def inv(p, E, N):
    if len(p) == 4: a, c, tx, ty = p; M = np.array([[a, c], [c, -a]])
    else: M = np.array([[p[0], p[1]], [p[2], p[3]]]); tx, ty = p[4], p[5]
    Mi = np.linalg.inv(M); dE, dN = E - tx, N - ty
    return Mi[0, 0] * dE + Mi[0, 1] * dN, Mi[1, 0] * dE + Mi[1, 1] * dN
def hull(h, buf=150):
    d = json.load(open(SP + f'sbg/picks22/s22-{h}.json'))
    pts = [ap(TF[h], p['x'], p['y']) for p in d['intersections'] if p.get('part') != 'inset']
    return MultiPoint(pts).convex_hull.buffer(buf)
def mosaic(x0, y0, x1, y1, res, halves=None, gray=False):
    W, H = int((x1 - x0) / res), int((y1 - y0) / res)
    jj, ii = np.meshgrid(np.arange(W), np.arange(H))
    E = x0 + (jj + 0.5) * res; N = y1 - (ii + 0.5) * res
    acc = np.full((H, W, 3), 240, np.uint8); best = np.full((H, W), -1e9)
    for h in (halves or TF):
        hp = hull(h)
        if not hp.intersects(Point((x0 + x1) / 2, (y0 + y1) / 2).buffer(max(x1 - x0, y1 - y0))): continue
        path = Path(np.array(hp.exterior.coords))
        inside = path.contains_points(np.c_[E.ravel(), N.ravel()]).reshape(H, W)
        if not inside.any(): continue
        # depth: distance to hull boundary
        dep = ndi.distance_transform_edt(inside) * res
        m = inside & (dep > best)
        if not m.any(): continue
        im = np.asarray(Image.open(find('22-' + h)).convert('RGB'))
        x, y = inv(TF[h], E[m], N[m])
        for k in range(3):
            acc[..., k][m] = ndi.map_coordinates(im[..., k], [y, x], order=1, mode='constant', cval=240)
        best[m] = dep[m]
        del im
    return acc
if __name__ == '__main__':
    a = list(map(float, sys.argv[1:6]))
    Image.fromarray(mosaic(*a)).save(sys.argv[6], quality=88)
