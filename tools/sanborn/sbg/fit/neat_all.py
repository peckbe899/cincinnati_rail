"""Neatline boxes for all basin sheets (deck method) and half-resolution copies for warping."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import json, sys, os, numpy as np
from PIL import Image
from scipy import ndimage as ndi
Image.MAX_IMAGE_PIXELS = None
HERE = _ws.data_dir(os.path.dirname(os.path.abspath(__file__)))
SZ = json.load(open(os.path.join(HERE, 'sizes.json')))
def neat(im, band=0.10):
    H, W = im.shape; paper = im > 60; dark = (im < 120) & paper
    bw, bh = int(W * band), int(H * band)
    def peak(prof, lo, hi):
        p = ndi.uniform_filter1d(prof.astype(float), 3); seg = p[lo:hi]; k = np.argmax(seg); return lo + k, seg[k]
    cs = dark[int(H * .2):int(H * .8)].sum(0); rs = dark[:, int(W * .2):int(W * .8)].sum(1)
    xl, vl = peak(cs, 0, bw); xr, vr = peak(cs, W - bw, W); yt, vt = peak(rs, 0, bh); yb, vb = peak(rs, H - bh, H)
    return [int(xl), int(yt), int(xr), int(yb)], [round(vl / (H * .6), 2), round(vt / (W * .6), 2), round(vr / (H * .6), 2), round(vb / (W * .6), 2)]
out = {}
for s, (size, path) in SZ.items():
    s = int(s)
    im = Image.open(path).convert('RGB'); W, H = im.size
    f = 2 if 200 > s else 4
    sm = im.resize((W // f, H // f), Image.LANCZOS); sm.save(os.path.join(os.path.dirname(HERE), 'small', f's{s}.jpg'), quality=88)
    g = np.asarray(sm.convert('L')).astype(np.int16)
    b, v = neat(g); out[s] = dict(box=[c * f for c in b], strength=v, f=f)
    print(s, out[s], flush=True)
json.dump(out, open(os.path.join(HERE, 'neat.json'), 'w'), indent=0)
