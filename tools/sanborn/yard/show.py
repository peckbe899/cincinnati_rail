try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import shape
S = _ws.DATA
E0, E1, N0, N1, res = [float(v) for v in sys.argv[1:6]]; out = sys.argv[6]; files = sys.argv[7].split(',')
W, H = int((E1 - E0) / res), int((N1 - N0) / res)
im = Image.new('RGB', (W, H), (250, 250, 247)); d = ImageDraw.Draw(im, 'RGBA')
P = lambda c: [((x - E0) / res, (N1 - y) / res) for x, y in c]
def poly(g, fill=None, outline=None, w=1):
    for gg in getattr(g, 'geoms', [g]):
        if gg.geom_type == 'Polygon':
            d.polygon(P(gg.exterior.coords), fill=fill, outline=outline, width=w)
            for r in gg.interiors: d.polygon(P(r.coords), fill=(250, 250, 247, 255) if fill else None, outline=outline, width=w)
def line(g, col, w=1):
    for gg in getattr(g, 'geoms', [g]):
        if gg.geom_type == 'LineString': d.line(P(gg.coords), fill=col, width=w)
D = json.load(open(S + 'deckpage/deck.json'))
for f in D['features']:
    p = f['properties']
    if p.get('layer') == 'deck': poly(shape(f['geometry']), outline=(0, 0, 0, 200), w=2)
    if p.get('layer') == 'boulevard': poly(shape(f['geometry']), outline=(120, 120, 120, 150), w=1)
# MILLVALE
for f in json.load(open(S + 'deckpage/basin.json'))['features']:
    p = f['properties']
    if p.get('layer') == 'street' and p.get('set') == 'mv': line(shape(f['geometry']), (150, 150, 150, 200), 2)
ST = json.load(open(S + 'deckpage/structures.json'))
for f in ST['features']:
    if f['properties'].get('layer') == 'struct': poly(shape(f['geometry']), fill=(255, 140, 0, 40), outline=(220, 110, 0, 200), w=1)
CL = {'in': (220, 30, 30), 'under': (40, 150, 60), 'over': (40, 90, 220), 'unset': (130, 130, 130)}
for fn in files:
    for f in json.load(open(S + fn))['features']:
        p = f['properties']; g = shape(f['geometry']); L = p['layer']
        if L == 'yard_limit': poly(g, fill=(255, 230, 0, 40), outline=(160, 120, 0, 255), w=3)
        elif L == 'yard_today': poly(g, outline=(0, 160, 220, 200), w=2)
        elif L == 'yard_hist': poly(g, fill=(150, 80, 200, 50), outline=(130, 60, 180, 255), w=2)
        elif L == 'ud_box': c = CL[p.get('cls', 'unset')]; poly(g, fill=c + (70,), outline=c + (230,), w=1)
        elif L == 'ud_line': c = CL[p.get('cls', 'unset')]; line(g, c + (255,), 2 if p.get('kind') != 'metro' else 1)
        elif L == 'yard_fan': poly(g, fill=(90, 47, 208, 40), outline=(90, 47, 208, 200), w=1)
        elif L == 'yard_track': line(g, (60, 20, 170, 255) if p.get('kind') == 'yard' else (200, 60, 140, 255), 1)
        elif L == 'yard_lead': line(g, (0, 0, 0, 255), 3)
        elif L in ('deck_col', 'deck_cell'): pass
import math
for e in range(int(math.ceil(E0 / 100) * 100), int(E1) + 1, 100):
    x = (e - E0) / res; d.line([(x, 0), (x, H)], fill=(0, 0, 0, 40)); d.text((x + 2, 2), str(e)[-4:], fill=(0, 0, 0, 255))
for n in range(int(math.ceil(N0 / 100) * 100), int(N1) + 1, 100):
    y = (N1 - n) / res; d.line([(0, y), (W, y)], fill=(0, 0, 0, 40)); d.text((2, y + 2), str(n)[-5:], fill=(0, 0, 0, 255))
im.save(out, quality=90); print(W, H)
