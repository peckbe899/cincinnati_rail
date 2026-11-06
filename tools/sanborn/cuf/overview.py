try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# rebuild tiles_n/overview.webp (2 m) from the tiles (as tiles_ext*.py do at the end)
import json, os
from PIL import Image
SP = _ws.DATA; OUT = SP + 'deckpage/tiles_n/'; T, RES = 512, 0.25; NP = int(T / RES)
order = [tuple(t) for t in json.load(open(OUT + 'index.json'))['tiles']]
ex = [min(t[0] for t in order), min(t[1] for t in order), max(t[0] for t in order) + T, max(t[1] for t in order) + T]
sc = int(2.0 / RES); W, H = int((ex[2] - ex[0]) / 2.0), int((ex[3] - ex[1]) / 2.0)
ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
for tx, ty in order:
    fn = OUT + f'{tx}_{ty}.webp'
    if not os.path.exists(fn): continue
    t = Image.open(fn).convert('RGBA').resize((NP // sc, NP // sc), Image.LANCZOS)
    ov.paste(t, (int((tx - ex[0]) / 2.0), int((ex[3] - ty - T) / 2.0)), t)
ov.save(OUT + 'overview.webp', quality=70, method=4)
json.dump(dict(E0=ex[0], N0=ex[1], E1=ex[2], N1=ex[3], res=2), open(OUT + 'overview.json', 'w')); print('overview', W, H, ex)
