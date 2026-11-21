"""Side-by-side pictures of plate-44 area maps under several settings, with Ben's blocks (the truth) drawn on top.

    python pic44.py VARIANT[,VARIANT...] [--crop x0,y0,x1,y1] [--scale 0.25] [--tag NAME] [--root maps]

Each panel: the scan, P(block) > 0.5 tinted green, P(line) > 0.5 red, Ben's 55 block rings (streetmap/22-44.json) in
magenta, and the outline step's blocks (bench/runs/VARIANT/outlines.json) in blue. Writes pics/44_TAG.jpg.
"""
import json, os, sys
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
vs = a[0].split(','); sc = float(opt('--scale', 0.25)); root = opt('--root', 'maps'); tag = opt('--tag', '_'.join(vs))
full = cv2.imread(SP + 'cufp/22-44.jpg'); H, W = full.shape[:2]
x0, y0, x1, y1 = [int(v) for v in opt('--crop', f'0,0,{W},{H}').split(',')]
base = cv2.resize(full[y0:y1, x0:x1], None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA); h, w = base.shape[:2]
ben = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))['blocks']
P = lambda pts: ((np.asarray(pts, float) - [x0, y0]) * sc).round().astype(np.int32)
panels = []
for v in vs:
    pa = cv2.resize(cv2.imread(HERE + f'{root}/{v}/44_area.png', 0), (W, H), interpolation=cv2.INTER_LINEAR)[y0:y1, x0:x1]
    pl = cv2.imread(HERE + f'{root}/{v}/44_lines.png', 0)[y0:y1, x0:x1]
    pa = cv2.resize(pa, (w, h), interpolation=cv2.INTER_LINEAR) > 127; pl = cv2.resize(pl, (w, h), interpolation=cv2.INTER_AREA) > 60
    im = base.astype(np.float32) * 0.75 + 60; im[pa] = im[pa] * 0.65 + np.array([60, 200, 60], np.float32) * 0.35; im[pl] = (40, 40, 230); im = im.clip(0, 255).astype(np.uint8)
    for b in ben: cv2.polylines(im, [P(b['ring'])], True, (200, 0, 200), 2, cv2.LINE_AA)
    of = HERE + f'bench/runs/{v}/outlines.json'
    for poly in (json.load(open(of, encoding='utf8')) if os.path.exists(of) else []):
        cv2.polylines(im, [P([s['a'] for s in poly])], True, (230, 120, 0), 2, cv2.LINE_AA)
    cv2.rectangle(im, (0, 0), (16 + 12 * len(v), 26), (255, 255, 255), -1); cv2.putText(im, v, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2, cv2.LINE_AA)
    panels += [im, np.full((h, 6, 3), 255, np.uint8)]
os.makedirs(HERE + 'pics', exist_ok=True); cv2.imwrite(HERE + f'pics/44_{tag}.jpg', np.hstack(panels[:-1]), [cv2.IMWRITE_JPEG_QUALITY, 88]); print(HERE + f'pics/44_{tag}.jpg')
