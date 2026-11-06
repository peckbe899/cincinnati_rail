try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# RETIRED 2026-10-20: 1922 plates are drawn on their own layer (tiles_22, cuf/tiles22.py); tiles_n is 1904 only
# Ben 2026-10-20: inside the 1922 area (cuf/area_c22.json: plate footprint, east of West McMicken, north of Straight, west of Hopson) the
# page's Sanborn tiles show the 1922 plate 35 (north) as Ben georeferenced it, over whatever the 1904 sheets drew there. Run after any
# tiles_n rendering that touches the area (it reads each tile's '.pre_c22' copy if present, so it can be rerun safely).
import json, os, sys, shutil, numpy as np, cv2
from PIL import Image
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'cuf'); import common as C
from shapely.geometry import shape, box
from matplotlib.path import Path
import rasterio
Image.MAX_IMAGE_PIXELS = None
AREA = shape(json.load(open(SP + 'cuf/area_c22.json')))
r = rasterio.open(_ws.ext('/mnt/user-data/uploads/35_northern_CUF.tif')); IM = np.moveaxis(r.read(), 0, -1)      # RGBA, full size
OUT = SP + 'deckpage/tiles_n/'; T, RES = 512, 0.25; NP = int(T / RES)
idx = json.load(open(OUT + 'index.json')); have = {tuple(t) for t in idx['tiles']}
x0, y0, x1, y1 = AREA.bounds; todo = []
for tx in range(int(x0 // T * T), int(x1) + 1, T):
    for ty in range(int(y0 // T * T), int(y1) + 1, T):
        if AREA.intersects(box(tx, ty, tx + T, ty + T)): todo.append((tx, ty))
ap = Path(np.array(AREA.exterior.coords))
for tx, ty in todo:
    fn = OUT + f'{tx}_{ty}.webp'
    src = fn + '.pre_c22'
    if os.path.exists(fn) and not os.path.exists(src): shutil.copy(fn, src)
    base = np.array(Image.open(src).convert('RGBA')) if os.path.exists(src) else np.zeros((NP, NP, 4), np.uint8)
    jj, ii = np.meshgrid(np.arange(NP), np.arange(NP)); E = tx + (jj + 0.5) * RES; N = ty + T - (ii + 0.5) * RES
    inside = ap.contains_points(np.c_[E.ravel(), N.ravel()]).reshape(NP, NP)
    if not inside.any(): continue
    px, py = C.ben2px(E, N)
    rgba = cv2.remap(IM, px.astype(np.float32), py.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    take = inside & (rgba[:, :, 3] > 0)
    base[take] = rgba[take]; base[take, 3] = 255
    Image.fromarray(base, 'RGBA').save(fn, quality=72, method=4); have.add((tx, ty)); print('tile', tx, ty, int(take.sum()))
idx['tiles'] = sorted([list(t) for t in have], key=lambda t: (t[1], t[0])); json.dump(idx, open(OUT + 'index.json', 'w'))
