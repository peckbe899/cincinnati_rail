try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, math
from PIL import Image, ImageDraw
from shapely.geometry import shape
S = _ws.DATA
E0, E1, N0, N1, res = [float(v) for v in sys.argv[1:6]]; out = sys.argv[6]
W, H = int((E1 - E0) / res), int((N1 - N0) / res)
im = Image.new('RGB', (W, H), (252, 252, 250)); d = ImageDraw.Draw(im, 'RGBA')
P = lambda c: [((x - E0) / res, (N1 - y) / res) for x, y in c]
D = json.load(open(S + 'deckpage/deck.json'))
for f in D['features']:
    if f['properties'].get('layer') == 'deck':
        for g in shape(f['geometry']).geoms: d.polygon(P(g.exterior.coords), outline=(200, 0, 0, 160), width=2)
for f in json.load(open(S + 'deckpage/structures.json'))['features']:
    if f['properties'].get('layer') == 'struct':
        g = shape(f['geometry'])
        for gg in getattr(g, 'geoms', [g]): d.polygon(P(gg.exterior.coords), fill=(255, 150, 0, 35))
for f in json.load(open(S + 'yard/osm_rail_deck.json'))['features']:
    p = f['properties']; g = shape(f['geometry'])
    if p.get('railway') != 'rail': col, w = (180, 180, 180, 150), 1
    elif p.get('usage') == 'main': col, w = (220, 0, 0, 255), 3
    elif p.get('service') == 'yard': col, w = (0, 90, 220, 230), 1
    elif p.get('service') == 'crossover': col, w = (0, 160, 0, 255), 2
    else: col, w = (120, 0, 160, 230), 2
    for gg in getattr(g, 'geoms', [g]): d.line(P(gg.coords), fill=col, width=w)
for e in range(int(math.ceil(E0 / 100) * 100), int(E1) + 1, 100):
    x = (e - E0) / res; d.line([(x, 0), (x, H)], fill=(0, 0, 0, 30)); d.text((x + 2, 2), str(e)[-4:], fill=(0, 0, 0, 255))
for n in range(int(math.ceil(N0 / 100) * 100), int(N1) + 1, 100):
    y = (N1 - n) / res; d.line([(0, y), (W, y)], fill=(0, 0, 0, 30)); d.text((2, y + 2), str(n)[-5:], fill=(0, 0, 0, 255))
im.save(out, quality=90)
