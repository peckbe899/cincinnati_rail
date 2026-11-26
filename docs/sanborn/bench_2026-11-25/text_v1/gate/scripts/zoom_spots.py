"""Zoom on plate spots: scan | finder v1 | finder2 | finder3 text (magenta = text 2/3 (v1: 2/3/4), grey = line, cyan = shared,
green = other) with Ben's tracks in blue. Reads only; writes gate/pics/NAME.jpg.
    cd data/sanborn; python -B .../zoom_spots.py N HALF SCALE NAME X,Y [X,Y ...]"""
import json, sys, numpy as np
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
N, S, sc, name = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
pts = [tuple(int(v) for v in p.split(',')) for p in sys.argv[5:]]
B = 'bench_2026-11-25/'
M = [(B + f'text/finder/out/{N}_finder.png', (2, 3, 4)), (B + f'text_v1/finder2/out/final/{N}_text.png', (2, 3)), (B + f'text_v1/classifier/out/finder3/{N}_text.png', (2, 3))]
scan = Image.open(f'cufp/22-{N}.jpg'); masks = [Image.open(p) for p, _ in M]
ben = json.load(open(f'picks22_guided/22-{N}/rail_ben.json'))['tracks'] if N in ('44', '5', '1A') else []
rows = []
for X, Y in pts:
    box = (X - S, Y - S, X + S, Y + S); tiles = [scan.crop(box).convert('RGB')]
    for (p, codes), m in zip(M, masks):
        c = np.array(m.crop(box)); o = np.full(c.shape + (3,), 255, np.uint8)
        o[c == 1] = (150, 150, 150); o[c == 5] = (0, 150, 0); o[c == 4] = (0, 190, 220); o[np.isin(c, codes)] = (220, 0, 220)
        im = Image.fromarray(o); d = ImageDraw.Draw(im)
        for t in ben: d.line([(px - box[0], py - box[1]) for px, py in t['pts']], fill=(0, 0, 255), width=1)
        tiles.append(im)
    tiles = [t.resize((int(t.width * sc), int(t.height * sc)), Image.NEAREST) for t in tiles]
    row = Image.new('RGB', (sum(t.width for t in tiles) + 6 * 3, tiles[0].height), (0, 0, 0)); x = 0
    for t in tiles: row.paste(t, (x, 0)); x += t.width + 6
    ImageDraw.Draw(row).text((3, 3), f'{X},{Y}', fill=(255, 0, 0)); rows.append(row)
out = Image.new('RGB', (rows[0].width, sum(r.height + 6 for r in rows)), (0, 0, 0)); y = 0
for r in rows: out.paste(r, (0, y)); y += r.height + 6
out.save(f'bench_2026-11-25/text_v1/gate/pics/{name}.jpg', quality=90); print(name)
