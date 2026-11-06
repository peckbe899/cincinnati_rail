try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Composite views of the deck: 1904 Sanborn (and 1922), OSM rail (today), deck outline, structures, tracks.
import json, sys, os
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import shape
S = _ws.DATA
E0, E1, N0, N1 = [float(v) for v in sys.argv[1:5]]; res = float(sys.argv[5]); tset = sys.argv[6]; out = sys.argv[7]
W, H = int((E1 - E0) / res), int((N1 - N0) / res)
base = Image.new('RGB', (W, H), (245, 245, 240))
idx = json.load(open(S + f'deckpage/{tset}/index.json')); T = idx['size']
for tx, ty in idx['tiles']:
    if tx > E1 or tx + T < E0 or ty > N1 or ty + T < N0: continue
    p = S + f'deckpage/{tset}/{tx}_{ty}.webp'
    if not os.path.exists(p): continue
    im = Image.open(p).convert('RGBA'); s = int(T / res)
    im = im.resize((s, s), Image.LANCZOS)
    x = int((tx - E0) / res); y = int((N1 - (ty + T)) / res)
    base.paste(im, (x, y), im)
d = ImageDraw.Draw(base, 'RGBA')
P = lambda c: [((x - E0) / res, (N1 - y) / res) for x, y in c]
def poly(g, fill=None, outline=None, w=2):
    for gg in getattr(g, 'geoms', [g]):
        if gg.geom_type == 'Polygon': d.polygon(P(gg.exterior.coords), fill=fill, outline=outline, width=w)
def line(c, col, w=2): d.line(P(c), fill=col, width=w)
layers = sys.argv[8].split(',') if len(sys.argv) > 8 else ['deck', 'osm', 'struct', 'tracks']
D = json.load(open(S + 'deckpage/deck.json'))
if 'deck' in layers:
    for f in D['features']:
        if f['properties'].get('layer') == 'deck': poly(shape(f['geometry']), outline=(200, 0, 0, 255), w=3)
        if f['properties'].get('layer') == 'street' and f['properties'].get('name', '').startswith('New street W'): line(f['geometry']['coordinates'], (200, 0, 200, 255), 4)
if 'osm' in layers:
    for f in json.load(open(S + 'yard/osm_rail_deck.json'))['features']:
        p = f['properties']; col = (0, 120, 255, 200) if p.get('railway') == 'rail' else (0, 200, 255, 140)
        line(f['geometry']['coordinates'], col, 2)
if 'struct' in layers:
    for f in json.load(open(S + 'deckpage/structures.json'))['features']:
        if f['properties'].get('layer') == 'struct': poly(shape(f['geometry']), fill=(255, 140, 0, 50), outline=(255, 120, 0, 220), w=2)
if 'tracks' in layers:
    T2 = json.load(open(S + 'deckpage/tracks.json'))
    for f in T2['features']:
        if f['geometry']['type'] == 'LineString' and f['properties'].get('layer') in ('apex', 'lower', 'passing'): line(f['geometry']['coordinates'], (0, 0, 0, 160), 1)
    C = json.load(open(S + 'deckpage/context.json'))
    for t in C['tracks']:
        line(t['c'], (0, 150, 0, 170) if t['sys'] == 'rer' else (150, 0, 150, 120), 1)
if 'grid' in layers:
    import math
    for e in range(int(math.ceil(E0/50)*50), int(E1)+1, 50):
        x=(e-E0)/res; d.line([(x,0),(x,H)], fill=(0,0,0,90 if e%100 else 160), width=1)
        if e%100==0: d.text((x+2,2), str(e)[-4:], fill=(0,0,0,255))
    for n in range(int(math.ceil(N0/50)*50), int(N1)+1, 50):
        y=(N1-n)/res; d.line([(0,y),(W,y)], fill=(0,0,0,90 if n%100 else 160), width=1)
        if n%100==0: d.text((2,y+2), str(n)[-5:], fill=(0,0,0,255))
base.save(out, quality=88)
print(W, H)
