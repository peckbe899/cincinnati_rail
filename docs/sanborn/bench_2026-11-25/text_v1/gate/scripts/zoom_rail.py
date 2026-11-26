"""Zoom on a plate spot: scan | finder3 mask (text magenta, line grey, shared cyan, other green) | bins before | bins after
(railroad red, streetcar orange, text magenta, rest grey) with Ben's tracks in blue. Reads only; writes gate/pics/.
    cd data/sanborn; python -B .../zoom_rail.py N X Y HALF SCALE RUN NAME"""
import json, sys, numpy as np
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
N, X, Y, S, sc, run, name = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]), sys.argv[6], sys.argv[7]
x0, y0, x1, y1 = X - S, Y - S, X + S, Y + S
scan = np.array(Image.open(f'cufp/22-{N}.jpg').crop((x0, y0, x1, y1)).convert('RGB'))
m = np.array(Image.open(f'bench_2026-11-25/text_v1/classifier/out/finder3/{N}_text.png').crop((x0, y0, x1, y1)))
def paint(code, cols):
    o = np.full(code.shape + (3,), 255, np.uint8)
    for v, c in cols.items(): o[code == v] = c
    return o
MC = {1: (150, 150, 150), 2: (220, 0, 220), 3: (220, 0, 220), 4: (0, 190, 220), 5: (0, 150, 0)}
BC = {1: (150, 150, 150), 2: (150, 150, 150), 3: (150, 150, 150), 4: (230, 0, 0), 5: (255, 140, 0), 6: (150, 150, 150), 7: (150, 150, 150), 8: (220, 0, 220), 9: (150, 150, 150)}
H = 'bench_2026-11-25/text_v1/handoff/runs/bins/'
bb = np.array(Image.open(H + f'{run}_before.png').crop((x0, y0, x1, y1))); ba = np.array(Image.open(H + f'{run}_after.png').crop((x0, y0, x1, y1)))
P = [scan, paint(m, MC), paint(bb, BC), paint(ba, BC)]
ben = json.load(open(f'picks22_guided/22-{N}/rail_ben.json'))['tracks']
ims = []
for k, p in enumerate(P):
    im = Image.fromarray(p)
    if k > 1:
        d = ImageDraw.Draw(im)
        for t in ben: d.line([(px - x0, py - y0) for px, py in t['pts']], fill=(0, 0, 255), width=1)
    ims.append(im.resize((int(im.width * sc), int(im.height * sc)), Image.NEAREST))
out = Image.new('RGB', (sum(i.width for i in ims) + 18, ims[0].height), (0, 0, 0)); x = 0
for i in ims: out.paste(i, (x, 0)); x += i.width + 6
out.save(f'bench_2026-11-25/text_v1/gate/pics/{name}.jpg', quality=90); print(name)
