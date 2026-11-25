"""Crop a region of a 1922 Sanborn plate scan, with a coordinate grid, for reading by eye.

usage: python -B crop.py PLATE x0 y0 x1 y1 OUT.png [scale] [grid_px]
Coordinates are full-scan pixels. The grid lines and their labels are drawn in red
every grid_px pixels (default 100) so a read can be placed on the plate.
"""
import sys
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
ROOT = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/cufp/'


def crop(plate, x0, y0, x1, y1, out, scale=1.0, grid=100):
    im = Image.open(f'{ROOT}22-{plate}.jpg').convert('RGB')
    c = im.crop((x0, y0, x1, y1))
    if scale != 1.0:
        c = c.resize((int((x1 - x0) * scale), int((y1 - y0) * scale)), Image.LANCZOS)
    if grid:
        d = ImageDraw.Draw(c)
        gx = (x0 // grid + 1) * grid
        while gx < x1:
            X = (gx - x0) * scale
            d.line([(X, 0), (X, c.size[1])], fill=(255, 0, 0), width=1)
            d.text((X + 2, 2), str(gx), fill=(255, 0, 0))
            gx += grid
        gy = (y0 // grid + 1) * grid
        while gy < y1:
            Y = (gy - y0) * scale
            d.line([(0, Y), (c.size[0], Y)], fill=(255, 0, 0), width=1)
            d.text((2, Y + 2), str(gy), fill=(255, 0, 0))
            gy += grid
    c.save(out)


if __name__ == '__main__':
    a = sys.argv
    crop(a[1], *map(int, a[2:6]), a[6], float(a[7]) if len(a) > 7 else 1.0, int(a[8]) if len(a) > 8 else 100)
