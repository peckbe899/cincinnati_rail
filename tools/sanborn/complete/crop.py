"""Reader tool: render part of a job's region with a pixel grid labelled in ORIGINAL plate pixels (as sbg/sb.py render).
Reads JOBS_DIR/jobs.json and JOBS_DIR/regions/<job>.jpg (tools/sanborn/complete/prep.py); JOBS_DIR is the environment
variable of that name, else this file's folder.

    python crop.py JOB OUT.jpg                    # the whole region
    python crop.py JOB x0 y0 x1 y1 OUT.jpg        # a zoom, box in ORIGINAL plate pixels
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
HERE = os.environ.get('JOBS_DIR', os.path.dirname(os.path.abspath(__file__)))
M = json.load(open(HERE + '/jobs.json', encoding='utf8'))
try:
    FNT = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 15)
except Exception:
    FNT = ImageFont.load_default()


def render(job, box, out, maxpx=1400):
    m = M[job]; ox, oy, ex, ey = m['box']
    im = Image.open(f'{HERE}/regions/{job}.jpg').convert('RGB')
    x0, y0, x1, y1 = box or (ox, oy, ex, ey)
    x0, y0, x1, y1 = max(x0, ox), max(y0, oy), min(x1, ex), min(y1, ey)
    c = im.crop((x0 - ox, y0 - oy, x1 - ox, y1 - oy)); s = min(maxpx / max(c.size), 2.0)
    c = c.resize((max(1, int(c.size[0] * s)), max(1, int(c.size[1] * s))), Image.LANCZOS); d = ImageDraw.Draw(c)
    span = max(x1 - x0, y1 - y0); step = 500 if span > 2500 else (200 if span > 1000 else (100 if span > 400 else (50 if span > 150 else 10)))
    for gx in range((x0 // step + 1) * step, x1, step):
        X = (gx - x0) * s; d.line([(X, 0), (X, c.size[1])], fill=(255, 0, 0) if gx % (step * 5) == 0 else (255, 140, 140), width=1)
        d.text((X + 2, 2), str(gx), fill=(200, 0, 0), font=FNT)
    for gy in range((y0 // step + 1) * step, y1, step):
        Y = (gy - y0) * s; d.line([(0, Y), (c.size[0], Y)], fill=(255, 0, 0) if gy % (step * 5) == 0 else (255, 140, 140), width=1)
        d.text((2, Y + 2), str(gy), fill=(200, 0, 0), font=FNT)
    c.save(out, quality=90)
    print('saved', out, 'box', [x0, y0, x1, y1], 'scale', round(s, 3), 'region', m['box'])


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) == 6:
        render(a[0], tuple(int(float(v)) for v in a[1:5]), a[5])
    else:
        render(a[0], None, a[1])
