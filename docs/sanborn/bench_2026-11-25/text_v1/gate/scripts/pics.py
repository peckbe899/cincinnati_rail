"""Gate pictures (26 Nov 2026): a method's text mask against the held-out truth, beside the scan.
    cd data/sanborn; python -B bench_2026-11-25/text_v1/gate/scripts/pics.py CROP METHOD [x0 y0 x1 y1 scale]
Colours on the error map: black = text found, RED = text missed, BLUE = non-text ink called text, light grey = non-text
ink left alone, yellow = don't care (any call). Window in crop px (default the whole crop); scale default 1.
Writes gate/pics/<CROP>_<METHOD>[_x0_y0].jpg: scan on the left, error map on the right. Reads only."""
import json, os, sys
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
B = 'bench_2026-11-25'
M = {'bin8': ('unet_data/{plate}_bins.png', (8,)), 'v1': (f'{B}/text/finder/out/{{plate}}_finder.png', (2, 3, 4)),
     'v2': (f'{B}/text_v1/finder2/out/final/{{plate}}_text.png', (2, 3)), 'v3': (f'{B}/text_v1/classifier/out/finder3/{{plate}}_text.png', (2, 3)),
     'v3ex': (f'{B}/text_v1/gate/out/v3ex/{{plate}}_text.png', (2, 3))}
TD = f'{B}/text_v1/truth-check/heldout_fixed'
a = sys.argv; cid, m = a[1], a[2]
crops = json.load(open(f'{TD}/crops.json')); c = crops[cid]; X0, Y0, X1, Y1 = c['win']
t = np.array(Image.open(f'{TD}/{cid}_mask.png'))
code = np.array(Image.open(M[m][0].replace('{plate}', c['plate'])))[Y0:Y1, X0:X1]
pred = np.isin(code, M[m][1])
scan = np.array(Image.open(f'cufp/22-{c["plate"]}.jpg').crop((X0, Y0, X1, Y1)).convert('RGB'))
w = [int(v) for v in a[3:7]] if len(a) > 6 else [0, 0, X1 - X0, Y1 - Y0]; sc = float(a[7]) if len(a) > 7 else 1.0
e = np.full(t.shape + (3,), 255, np.uint8)
e[t == 1] = (205, 205, 205); e[(t == 1) & pred] = (30, 90, 255)
e[t == 2] = (220, 0, 0); e[(t == 2) & pred] = (0, 0, 0)
e[t == 3] = (240, 200, 0)
sl = np.s_[w[1]:w[3], w[0]:w[2]]
L = Image.fromarray(scan[sl]); R = Image.fromarray(e[sl])
if sc != 1: L = L.resize((int(L.width * sc), int(L.height * sc)), Image.NEAREST); R = R.resize(L.size, Image.NEAREST)
out = Image.new('RGB', (L.width * 2 + 6, L.height), (255, 0, 255)); out.paste(L, (0, 0)); out.paste(R, (L.width + 6, 0))
os.makedirs(f'{B}/text_v1/gate/pics', exist_ok=True)
fn = f'{B}/text_v1/gate/pics/{cid}_{m}' + (f'_{w[0]}_{w[1]}' if len(a) > 6 else '') + '.jpg'
out.save(fn, quality=88); print(fn)
