"""Mosaic of 1904 frames from a transform file, with OSM centrelines (red) and 1922 points (blue) overlaid.
  python3 mosn.py TF.json E0 N0 E1 N1 RES OUT.jpg [frames,comma,separated]
Each frame keeps the hull of its own picks buffered 90 m; overlaps go to the frame the pixel is deepest inside."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, pickle, collections, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from shapely.geometry import MultiPoint, box
from matplotlib.path import Path
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'sbg'); sys.path.insert(0, _ws.CODE + 'lph')
from sb import find
Image.MAX_IMAGE_PIXELS = None
def sheet_of(fr): return int(''.join(c for c in str(fr) if c.isdigit()))
def ap(p, x, y):
    if len(p) == 6: return p[0] * x + p[1] * y + p[4], p[2] * x + p[3] * y + p[5]
    a, c, tx, ty = p; return a * x + c * y + tx, c * x - a * y + ty
def inv(p, E, N):
    if len(p) == 4: a, c, tx, ty = p; M = np.array([[a, c], [c, -a]])
    else: M = np.array([[p[0], p[1]], [p[2], p[3]]]); tx, ty = p[4], p[5]
    Mi = np.linalg.inv(M); dE, dN = E - tx, N - ty
    return Mi[0, 0] * dE + Mi[0, 1] * dN, Mi[1, 0] * dE + Mi[1, 1] * dN
def frame_pts():
    d = pickle.load(open(SP + 'lph/obs_all.pkl', 'rb')); G = collections.defaultdict(list)
    for r in d['R']: G[r['fr']].append((r['x'], r['y']))
    return G
_MASK = {}
# panel frames: page boxes (x0, y0, x1, y1) kept / dropped, in page pixels
PANEL_KEEP = {'460u': [(0, 0, 99999, 4000)]}
PANEL_DROP = {'468m': [(3680, 5100, 99999, 99999)]}
def page_mask(sheet, im):
    """paper mask at 1/8 resolution (warp.py rule: bright paper, largest blob, holes filled, eroded); vol 1 cropped to the frame"""
    if sheet not in _MASK:
        a = im[::8, ::8].astype(np.float32).mean(-1); g = ndi.uniform_filter(a, 7); m = g > 55
        lab, n = ndi.label(m)
        if n > 1: sz = ndi.sum(m, lab, range(1, n + 1)); m = lab == (1 + np.argmax(sz))
        m = ndi.binary_fill_holes(m); m = ndi.binary_erosion(m, iterations=3)
        if sheet < 100:
            c = np.zeros_like(m); c[175 // 8:4585 // 8, 205 // 8:3935 // 8] = True; m &= c
        _MASK[sheet] = (m, ndi.distance_transform_edt(m))
    return _MASK[sheet]
def mosaic(TF, x0, y0, x1, y1, res, frames=None, buf=90, warpfn=None):
    W, H = int((x1 - x0) / res), int((y1 - y0) / res)
    jj, ii = np.meshgrid(np.arange(W), np.arange(H)); E = x0 + (jj + 0.5) * res; N = y1 - (ii + 0.5) * res
    acc = np.full((H, W, 3), 245, np.uint8); best = np.full((H, W), -1e9); FP = frame_pts(); win = box(x0, y0, x1, y1)
    for f in (frames or TF):
        if f not in TF or len(FP.get(f, [])) < 1: continue
        hp = MultiPoint([ap(TF[f], x, y) for x, y in FP[f]]).convex_hull.buffer(400)
        if not hp.intersects(win): continue
        im = np.asarray(Image.open(find(sheet_of(f))).convert('RGB')); pm, pd = page_mask(sheet_of(f), im)
        xa, ya = (warpfn(f, E.ravel(), N.ravel()) if warpfn else inv(TF[f], E.ravel(), N.ravel()))
        xa = xa.reshape(H, W); ya = ya.reshape(H, W)
        # panel frames: keep the part of the page near this frame's own picks
        if f in PANEL_KEEP or f in PANEL_DROP:
            near = np.zeros((H, W), bool) if f in PANEL_KEEP else np.ones((H, W), bool)
            for bx in PANEL_KEEP.get(f, []): near |= (xa >= bx[0]) & (ya >= bx[1]) & (xa < bx[2]) & (ya < bx[3])
            for bx in PANEL_DROP.get(f, []): near &= ~((xa >= bx[0]) & (ya >= bx[1]) & (xa < bx[2]) & (ya < bx[3]))
        elif f[-1].isalpha():
            near = Path(np.array(MultiPoint(FP[f]).convex_hull.buffer(700).exterior.coords)).contains_points(np.c_[xa.ravel(), ya.ravel()]).reshape(H, W)
        else: near = np.ones((H, W), bool)
        xi = np.clip((xa / 8).astype(int), 0, pm.shape[1] - 1); yi = np.clip((ya / 8).astype(int), 0, pm.shape[0] - 1)
        ok = (xa >= 0) & (ya >= 0) & (xa < im.shape[1]) & (ya < im.shape[0]) & near
        dep = np.where(ok, pd[yi, xi], 0); inside = ok & pm[yi, xi]
        m = inside & (dep > best)
        if not m.any(): continue
        x, y = xa[m], ya[m]
        for k in range(3): acc[..., k][m] = ndi.map_coordinates(im[..., k], [y, x], order=1, mode='constant', cval=245)
        best[m] = dep[m]; del im
    return acc
def overlay(img, x0, y0, x1, y1, osm=True, p22=True):
    im = Image.fromarray(img); dr = ImageDraw.Draw(im); W, H = im.size
    px = lambda e, n: ((e - x0) / (x1 - x0) * W, (y1 - n) / (y1 - y0) * H)
    if osm:
        for fn in ['basin/osm_basin.geojson', 'deck/osm_valley.geojson']:
            for f in json.load(open(SP + fn))['features']:
                g = f['geometry']
                if g['type'] != 'LineString' or not f['properties'].get('name'): continue
                c = g['coordinates']
                if max(p[0] for p in c) < x0 or min(p[0] for p in c) > x1 or max(p[1] for p in c) < y0 or min(p[1] for p in c) > y1: continue
                dr.line([px(*p) for p in c], fill=(230, 0, 0), width=1)
    if p22:
        from ref22 import ref
        for k, v in ref().items():
            for q in v:
                X, Y = px(*q)
                if 0 <= X < W and 0 <= Y < H: dr.ellipse([X - 5, Y - 5, X + 5, Y + 5], outline=(0, 0, 255), width=2)
    return im
if __name__ == '__main__':
    TF = json.load(open(sys.argv[1])); x0, y0, x1, y1, res = map(float, sys.argv[2:7])
    fr = sys.argv[8].split(',') if len(sys.argv) > 8 else None
    overlay(mosaic(TF, x0, y0, x1, y1, res, fr), x0, y0, x1, y1).save(sys.argv[7], quality=88)
