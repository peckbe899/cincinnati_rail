try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# add plates to deckpage/tiles_22 without re-rendering the rest (2026-10-25: the full render ran out of memory with every plate's tiles held at once).
# usage: python3 cuf/tiles22_add.py 22-26A 22-26B 22-29
# Tiles touched by the given plates are rendered among themselves by depth (deepest inside its plate wins, as tiles22.py does) and laid
# under what an existing tile already shows (the old plates keep their pixels). Then the index and the overview are rebuilt from disk.
import json, os, sys, numpy as np, cv2
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'cuf'); import plates as PL
from PIL import Image
from scipy import ndimage as ndi
OUT = SP + 'deckpage/tiles_22/'; T, RES = 512, 0.25; NP = int(T / RES)
IDS = sys.argv[1:]
PS = [P for P in PL.PLATES if P['id'] in IDS and P['ok']()]
foot = {}
for P in PS:
    IM = P['img'](); h, w = IM.shape[:2]
    gx, gy = np.meshgrid(np.arange(700000, 725000, 16.0), np.arange(4324000, 4342000, 16.0))
    px, py = P['inv'](gx, gy); px = np.asarray(px); py = np.asarray(py)
    okk = (px >= 0) & (py >= 0) & (px < w - 1) & (py < h - 1)
    a = np.zeros_like(okk); a[okk] = IM[py[okk].astype(int), px[okk].astype(int), 3] > 0
    foot[P['id']] = sorted({(int(e // T * T), int(n // T * T)) for e, n in zip(gx[a], gy[a])}); del IM
    print(P['id'], 'tiles', len(foot[P['id']]))
tiles = sorted(set(t for v in foot.values() for t in v))
jj, ii = np.meshgrid(np.arange(NP), np.arange(NP))
cache = {}
def plate(P):
    if P['id'] not in cache:
        cache.clear(); IM = P['img']()
        cache[P['id']] = (IM, ndi.distance_transform_edt(IM[::8, ::8, 3] > 127).astype(np.float32) * 8)
    return cache[P['id']]
# one tile at a time (memory): render each plate that touches it
order = {P['id']: P for P in PS}
for k, (tx, ty) in enumerate(tiles):
    E = tx + (jj + 0.5) * RES; N = ty + T - (ii + 0.5) * RES
    new = np.zeros((NP, NP, 4), np.uint8); bd = np.zeros((NP, NP), np.float32)
    for pid in IDS:
        if pid not in order or (tx, ty) not in foot[pid]: continue
        IM, D8 = plate(order[pid]); qx, qy = order[pid]['inv'](E, N)
        rgba = cv2.remap(IM, np.asarray(qx, np.float32), np.asarray(qy, np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        rgba[..., 3] = np.where(rgba[..., 3] > 127, 255, 0).astype(np.uint8)
        d = cv2.remap(D8, np.asarray(qx, np.float32) / 8, np.asarray(qy, np.float32) / 8, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        take = (rgba[..., 3] > 0) & (d > bd); new[take] = rgba[take]; bd[take] = d[take]
    fn = OUT + f'{tx}_{ty}.webp'
    if os.path.exists(fn):
        old = np.array(Image.open(fn).convert('RGBA')); keep = old[..., 3] > 0; new[keep] = old[keep]
    if (new[..., 3] > 0).any(): Image.fromarray(new, 'RGBA').save(fn, quality=72, method=4)
print('tiles written', len(tiles))
keep = sorted([[int(a), int(b)] for a, b in (f[:-5].split('_') for f in os.listdir(OUT) if f.endswith('.webp') and f[0].isdigit())], key=lambda t: (t[1], t[0]))
json.dump(dict(size=T, res=RES, tiles=keep), open(OUT + 'index.json', 'w'))
ex = [min(t[0] for t in keep), min(t[1] for t in keep), max(t[0] for t in keep) + T, max(t[1] for t in keep) + T]
sc = int(2.0 / RES); W, H = int((ex[2] - ex[0]) / 2.0), int((ex[3] - ex[1]) / 2.0); ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
for tx, ty in keep:
    t = Image.open(OUT + f'{tx}_{ty}.webp').convert('RGBA').resize((NP // sc, NP // sc), Image.LANCZOS); ov.paste(t, (int((tx - ex[0]) / 2.0), int((ex[3] - ty - T) / 2.0)), t)
ov.save(OUT + 'overview.webp', quality=70, method=4); json.dump(dict(E0=ex[0], N0=ex[1], E1=ex[2], N1=ex[3], res=2), open(OUT + 'overview.json', 'w'))
print('tiles_22', len(keep), 'overview', W, H, ex)
