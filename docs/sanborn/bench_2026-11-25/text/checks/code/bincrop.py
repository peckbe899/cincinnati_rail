"""Colour crop of an ink-bins map (unet_data/<P>_bins.png) beside the scan, for looking.
usage: python -B bincrop.py PLATE x0 y0 x1 y1 OUT.png [scale]"""
import sys, json
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
SB = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'


def bincrop(p, x0, y0, x1, y1, out, s=1.0):
    B = np.array(Image.open(f'{SB}unet_data/{p}_bins.png').crop((x0, y0, x1, y1)))
    leg = json.load(open(f'{SB}unet_data/{p}_bins.json'))['bins']
    rgb = np.full(B.shape + (3,), 255, np.uint8)
    for k, v in leg.items():
        rgb[B == int(k)] = v['rgb']
    scan = Image.open(f'{SB}cufp/22-{p}.jpg').convert('RGB').crop((x0, y0, x1, y1))
    a = Image.fromarray(rgb)
    w, h = scan.size
    c = Image.new('RGB', (w, 2 * h + 6), 'white'); c.paste(scan, (0, 0)); c.paste(a, (0, h + 6))
    if s != 1.0:
        c = c.resize((int(c.size[0] * s), int(c.size[1] * s)), Image.LANCZOS)
    c.save(out)


if __name__ == '__main__':
    a = sys.argv
    bincrop(a[1], *map(int, a[2:6]), a[6], float(a[7]) if len(a) > 7 else 1.0)
