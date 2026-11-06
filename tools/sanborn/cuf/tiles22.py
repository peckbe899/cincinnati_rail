try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# render the 1922 plates (cuf/plates.py) into deckpage/tiles_22: 512 m tiles at 0.25 m, transparent outside the plates, plus overview (2 m)
import json, os, sys, numpy as np, cv2
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'cuf'); import plates as PL
from PIL import Image
OUT = SP + 'deckpage/tiles_22/'; os.makedirs(OUT, exist_ok=True); T, RES = 512, 0.25; NP = int(T / RES)
acc = {}; dep = {}                                             # (tx, ty) -> RGBA array, depth (m inside its plate's mapped area)
from scipy import ndimage as ndi
for P in PL.PLATES:
    if not P['ok'](): print('skip', P['id']); continue
    IM = P['img'](); h, w = IM.shape[:2]
    D8 = ndi.distance_transform_edt(IM[::8, ::8, 3] > 127).astype(np.float32) * 8          # px inside the plate's mapped area
    # plate footprint in world: map a coarse ring of the image's opaque pixels -> find tiles by sampling a 16 m grid
    gx, gy = np.meshgrid(np.arange(705000, 725000, 16.0), np.arange(4326000, 4342000, 16.0))
    px, py = P['inv'](gx, gy); px = np.asarray(px); py = np.asarray(py)
    okk = (px >= 0) & (py >= 0) & (px < w - 1) & (py < h - 1)
    a = np.zeros_like(okk); a[okk] = IM[py[okk].astype(int), px[okk].astype(int), 3] > 0
    tiles = sorted({(int(e // T * T), int(n // T * T)) for e, n in zip(gx[a], gy[a])})
    print(P['id'], 'tiles', len(tiles))
    jj, ii = np.meshgrid(np.arange(NP), np.arange(NP))
    for tx, ty in tiles:
        E = tx + (jj + 0.5) * RES; N = ty + T - (ii + 0.5) * RES
        qx, qy = P['inv'](E, N)
        rgba = cv2.remap(IM, np.asarray(qx, np.float32), np.asarray(qy, np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        rgba[..., 3] = np.where(rgba[..., 3] > 127, 255, 0).astype(np.uint8)
        d = cv2.remap(D8, np.asarray(qx, np.float32) / 8, np.asarray(qy, np.float32) / 8, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        base = acc.get((tx, ty)); bd = dep.get((tx, ty))
        if base is None: base = np.zeros((NP, NP, 4), np.uint8); bd = np.zeros((NP, NP), np.float16)
        take = (rgba[..., 3] > 0) & (d > bd)                      # where plates overlap (gutters, plate edges) the one reaching deeper wins
        base[take] = rgba[take]; bd[take] = d[take].astype(np.float16); acc[(tx, ty)] = base; dep[(tx, ty)] = bd
    del IM
for f in os.listdir(OUT):
    if f.endswith('.webp'): os.remove(OUT + f)
keep = []
for (tx, ty), im in acc.items():
    if not (im[..., 3] > 0).any(): continue
    Image.fromarray(im, 'RGBA').save(OUT + f'{tx}_{ty}.webp', quality=72, method=4); keep.append([tx, ty])
keep.sort(key=lambda t: (t[1], t[0])); json.dump(dict(size=T, res=RES, tiles=keep), open(OUT + 'index.json', 'w'))
ex = [min(t[0] for t in keep), min(t[1] for t in keep), max(t[0] for t in keep) + T, max(t[1] for t in keep) + T]
sc = int(2.0 / RES); W, H = int((ex[2] - ex[0]) / 2.0), int((ex[3] - ex[1]) / 2.0); ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
for tx, ty in keep:
    t = Image.open(OUT + f'{tx}_{ty}.webp').convert('RGBA').resize((NP // sc, NP // sc), Image.LANCZOS); ov.paste(t, (int((tx - ex[0]) / 2.0), int((ex[3] - ty - T) / 2.0)), t)
ov.save(OUT + 'overview.webp', quality=70, method=4); json.dump(dict(E0=ex[0], N0=ex[1], E1=ex[2], N1=ex[3], res=2), open(OUT + 'overview.json', 'w'))
print('tiles_22', len(keep), 'overview', W, H, ex)
