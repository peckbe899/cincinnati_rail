try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# 1922 Sanborn plates on the page's own 1922 layer (tiles_22). For each plate: its image (RGB(A)), a mask of its mapped area at
# 1/8 scale, and the world -> image-pixel map.
#   22-34L, 22-34R, 22-37L, 22-37R, 22-16R : the vol. 1 halves that were the underlay in tiles_n until 2026-10-20 (lph/tf22_cw.json,
#            affine; mapped-area polygons as in lph/tiles_n.py POLY22)
#   22-35N : Ben's georeferenced GeoTIFF, used as he made it (checked against 30 unchanged crossings: 3.1 m rms)
#   22-38  : Ben's raw scan (png), fitted to unchanged OSM crossings (cuf38/fit38.py -> cuf38/model38.npz); Ben's GeoTIFF only seeded it
import os, sys, json, numpy as np, cv2
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'cuf'); sys.path.insert(0, _ws.CODE + 'lph'); sys.path.insert(0, _ws.CODE + 'sbg')
import common as C
from PIL import Image; Image.MAX_IMAGE_PIXELS = None

TF22 = json.load(open(SP + 'lph/tf22_cw.json'))
POLY22 = {
    '22-34L': [(90, 90), (6175, 90), (6175, 6000), (4400, 6000), (4400, 6750), (90, 6750)],
    '22-37L': [(100, 60), (6272, 60), (6272, 7470), (100, 7470)],
    '22-37R': [(0, 60), (3500, 60), (3500, 2200), (5400, 2200), (5400, 4100), (3300, 4100), (3300, 7470), (0, 7470)],
    '22-34R': [(0, 90), (4800, 90), (4800, 700), (6009, 700), (6009, 7700), (1000, 7700), (1000, 6000), (0, 6000)],
    '22-16R': [(0, 0), (5050, 0), (5039, 356), (4890, 1273), (4750, 2128), (4514, 3494), (4429, 4081), (4285, 5076), (4065, 6636), (3950, 7796), (0, 7796)],
}
_gp = {}
def _half(k):
    def img():
        from sb import find
        im = cv2.imread(find(k), cv2.IMREAD_COLOR)[:, :, ::-1]
        a = np.zeros(im.shape[:2], np.uint8); cv2.fillPoly(a, [np.array(POLY22[k], np.int32)], 255)
        return np.dstack([im, a])
    M = SP + f'cuf_cw/{k[3:]}/model.npz'      # 2026-10-22: refitted to unchanged OSM crossings (cuf_cw/fit.py); the affine only if no model
    def inv(E, N):
        if os.path.exists(M):
            if k not in _gp: _gp[k] = dict(np.load(M))
            g = _gp[k]; E = np.asarray(E, float); N = np.asarray(N, float)
            fx = ((E - g['E0']) / g['step']).astype(np.float32); fy = ((g['N1'] - N) / g['step']).astype(np.float32)
            px = cv2.remap(g['px'].astype(np.float32), fx, fy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=-1e6)
            py = cv2.remap(g['py'].astype(np.float32), fx, fy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=-1e6)
            return px, py
        import mosn; return mosn.inv(TF22[k[3:]], np.asarray(E, float), np.asarray(N, float))
    return dict(id=k, img=img, inv=inv, ok=lambda: True)

def img35():
    import rasterio; r = rasterio.open(_ws.ext('/mnt/user-data/uploads/35_northern_CUF.tif')); return np.moveaxis(r.read(), 0, -1)
def inv35(E, N): return C.ben2px(E, N)

M38 = SP + 'cuf38/model38.npz'
def img38(): return np.array(Image.open(_ws.ext('/mnt/user-data/uploads/38.png')).convert('RGBA'))
_g38 = None
def inv38(E, N):
    """world -> png pixel, bilinear lookup in the inverse grid written by fit38.py"""
    global _g38
    if _g38 is None: _g38 = dict(np.load(M38))
    g = _g38; E = np.asarray(E, float); N = np.asarray(N, float)
    fx = ((E - g['E0']) / g['step']).astype(np.float32); fy = ((g['N1'] - N) / g['step']).astype(np.float32)
    px = cv2.remap(g['px'].astype(np.float32), fx, fy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=-1e6)
    py = cv2.remap(g['py'].astype(np.float32), fx, fy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=-1e6)
    return px, py

PLATES = [_half(k) for k in POLY22] + [dict(id='22-35N', img=img35, inv=inv35, ok=lambda: True),
                                       dict(id='22-38', img=img38, inv=inv38, ok=lambda: os.path.exists(M38))]

PNGPATH = {'82A': _ws.ext('/mnt/user-data/uploads/82A.png'), '83A': _ws.ext('/mnt/user-data/uploads/83A.png'), '75': _ws.ext('/mnt/user-data/uploads/75.png'), '76': _ws.ext('/mnt/user-data/uploads/76_1.png'), '26A': _ws.ext('/mnt/user-data/uploads/PNG/26a.png'), '26B': _ws.ext('/mnt/user-data/uploads/PNG/26b.png')}   # 2026-10-25: Price Hill 26a/26b; 2026-10-23: Norwood plates, uploaded outside PNG/
# 2026-10-21: plates 66-70 (Corryville, Avondale, the Zoo, Woodburn, Evanston): Ben's scans fitted by cufp/fit.py -> cufp/N/model.npz
def _plate(n):
    M = SP + f'cufp/{n}/model.npz'
    def img(): return np.array(Image.open(PNGPATH.get(n, _ws.ext(f'/mnt/user-data/uploads/PNG/{n}.png'))).convert('RGBA'))
    def inv(E, N):
        if n not in _gp: _gp[n] = dict(np.load(M))
        g = _gp[n]; E = np.asarray(E, float); N = np.asarray(N, float)
        fx = ((E - g['E0']) / g['step']).astype(np.float32); fy = ((g['N1'] - N) / g['step']).astype(np.float32)
        px = cv2.remap(g['px'].astype(np.float32), fx, fy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=-1e6)
        py = cv2.remap(g['py'].astype(np.float32), fx, fy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=-1e6)
        return px, py
    return dict(id=f'22-{n}', img=img, inv=inv, ok=lambda: os.path.exists(M))
PLATES += [_plate(n) for n in ('66', '67', '68', '69', '70', '82A', '83A', '75', '76', '26A', '26B', '29', '31', '33', '25', '28', '39', '40')]   # 26A, 26B, 29 Price Hill; 31, 33 Fairmount (2026-10-25); 25, 28 Price Hill (2026-11-08)
