"""Cut one region round each tie crossing from each plate's scan (Ben's PNGs; the LoC scans for the vol. 1 halves; Ben's
GeoTIFF for 35N, the image the picks were read on) and render an overview with the original-pixel grid. Read only."""
import json, os, sys
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

REPO = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D'
sys.path.insert(0, REPO + '/tools/sanborn')
import _ws  # noqa
sys.path.insert(0, _ws.CODE + 'cuf'); sys.path.insert(0, _ws.CODE + 'sbg')
import plates as PL  # noqa
from sb import find  # noqa

HERE = os.path.dirname(os.path.abspath(__file__))
REG = HERE + '/regions'; os.makedirs(REG, exist_ok=True)
T = json.load(open(HERE + '/ties15.json', encoding='utf8'))


def scan(pid):
    n = pid[3:]
    if pid == '22-35N':
        return _ws.ext('/mnt/user-data/uploads/35_northern_CUF.tif')
    if pid == '22-38':
        return _ws.ext('/mnt/user-data/uploads/38.png')
    if n in ('34L', '34R', '37L', '37R', '16R'):
        return find(pid)
    return PL.PNGPATH.get(n, _ws.ext(f'/mnt/user-data/uploads/PNG/{n}.png'))


jobs = {}
for e in T:
    for pid, d in e['plates'].items():
        o = np.array([d['old_pick']['x'], d['old_pick']['y']]); q = np.array(d['other_plate_here_px'])
        ok = np.all(np.isfinite(q)) and np.all(q > -1e5)
        c = (o + q) / 2 if ok else o
        half = max(1000, (np.hypot(*(o - q)) / 2 + 700) if ok else 1000)
        jobs[f"t{e['n']:02d}_{pid[3:]}"] = dict(tie=e['n'], plate=pid, streets=[e['street_1'], e['street_2']], center=c.tolist(), half=float(half), scan=scan(pid))
by_plate = {}
for j, v in jobs.items():
    by_plate.setdefault(v['plate'], []).append(j)
meta = {}
for pid, js in by_plate.items():
    im = Image.open(jobs[js[0]]['scan']); im.load()
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA'); bg = Image.new('RGBA', im.size, (255, 255, 255, 255)); bg.alpha_composite(im); im = bg
    im = im.convert('RGB'); W, H = im.size
    for j in js:
        v = jobs[j]; cx, cy = v['center']; h = v['half']
        x0, y0 = max(0, int(cx - h)), max(0, int(cy - h)); x1, y1 = min(W, int(cx + h)), min(H, int(cy + h))
        im.crop((x0, y0, x1, y1)).save(f'{REG}/{j}.png')
        meta[j] = dict(v, box=[x0, y0, x1, y1], size=[W, H])
        print(j, pid, [x0, y0, x1, y1], flush=True)
json.dump(meta, open(HERE + '/regions.json', 'w', encoding='utf8', newline='\n'), indent=1)
