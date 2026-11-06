"""1912 City Topographic Survey helper (georeferenced, EPSG:26916 UTM metres).
  python3 r12.py render E0 N0 E1 N1 OUT.jpg     render a window with a grid labelled in UTM metres (E right, N up)
  python3 r12.py check AREA E0 N0 E1 N1 OUT.jpg draw the picks saved in picks12/AREA.json on a window
Coordinates are UTM 16N metres (E, N). Windows of 150-400 m read best; the survey is 0.5 m per pixel."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import sys, os, json
import numpy as np, rasterio
from rasterio.windows import from_bounds
from PIL import Image, ImageDraw, ImageFont
VRT = _ws.ext('/mnt/user-data/outputs/1912_georef/1912_Survey_Mosaic.vrt')
HERE = _ws.data_dir(os.path.dirname(os.path.abspath(__file__)))
try: FNT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 13)
except: FNT = ImageFont.load_default()
def render(E0, N0, E1, N1, out, picks=None, maxpx=1300):
    d = rasterio.open(VRT); w = from_bounds(E0, N0, E1, N1, d.transform)
    a = d.read([1, 2, 3], window=w, boundless=True, fill_value=255)
    im = Image.fromarray(np.moveaxis(a, 0, -1).astype(np.uint8))
    W, H = im.size; s = min(maxpx / max(W, H), 3.0); im = im.resize((max(1, int(W * s)), max(1, int(H * s))), Image.LANCZOS)
    dr = ImageDraw.Draw(im); span = max(E1 - E0, N1 - N0)
    step = 100 if span > 600 else (50 if span > 250 else (20 if span > 100 else 10))
    px = lambda E, N: ((E - E0) / (E1 - E0) * im.size[0], (N1 - N) / (N1 - N0) * im.size[1])
    for gx in np.arange(np.ceil(E0 / step) * step, E1, step):
        X = px(gx, N0)[0]; major = gx % (step * 5) == 0
        dr.line([(X, 0), (X, im.size[1])], fill=(255, 0, 0) if major else (255, 150, 150), width=1); dr.text((X + 2, 2), str(int(gx)), fill=(200, 0, 0), font=FNT)
    for gy in np.arange(np.ceil(N0 / step) * step, N1, step):
        Y = px(E0, gy)[1]; major = gy % (step * 5) == 0
        dr.line([(0, Y), (im.size[0], Y)], fill=(255, 0, 0) if major else (255, 150, 150), width=1); dr.text((2, Y + 2), str(int(gy)), fill=(200, 0, 0), font=FNT)
    for p in picks or []:
        X, Y = px(p['E'], p['N']); dr.ellipse([X - 6, Y - 6, X + 6, Y + 6], outline=(0, 0, 255), width=3)
        dr.text((X + 7, Y - 8), f"{p['a'][:12]}/{p['b'][:12]}", fill=(0, 0, 200), font=FNT)
    im.save(out, quality=90); print('saved', out, 'grid step', step, 'm')
if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'render': render(*map(float, sys.argv[2:6]), sys.argv[6])
    elif c == 'check':
        P = json.load(open(os.path.join(HERE, 'picks12', sys.argv[2] + '.json')))
        render(*map(float, sys.argv[3:7]), sys.argv[7], picks=P.get('intersections', []))
