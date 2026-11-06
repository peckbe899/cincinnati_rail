import json, sys
sys.path.insert(0, '.')
from zipkit import *
from PIL import Image, ImageDraw, ImageFont
cands = [('A. Two long yards end to end,\n   extra tracks in the wide parts', 'zs_series2_0-2400-5350.json'),
         ('B. Two lanes side by side,\n   leads outside, staggered', 'zs_zipper_0_2700_1350_0.json'),
         ('C. Four yards end to end', 'zs_series_0-1350-2700-4050-5350.json')]
E0, E1, N0, N1 = 711850, 712750, 4330820, 4336700; res = 3.2
W, H = int((E1 - E0) / res), int((N1 - N0) / res)
try: font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 15); big = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 17)
except Exception: font = big = None
canvas = Image.new('RGB', (W * 3 + 80, H + 90), 'white'); D = ImageDraw.Draw(canvas)
for k, (name, fn) in enumerate(cands):
    L = [LineString(c) for c in json.load(open(fn))]
    g = fp(L); ox = 20 + k * (W + 20); oy = 70
    P = lambda cs: [(ox + (x - E0) / res, oy + (N1 - y) / res) for x, y in cs]
    D.polygon(P(A.exterior.coords), outline=(190, 110, 0), fill=(255, 246, 225))
    for gg in getattr(g, 'geoms', [g]): D.polygon(P(gg.exterior.coords), fill=(214, 204, 250))
    for l in L: D.line(P(l.coords), fill=(70, 30, 180), width=1)
    D.text((ox, 4), name, fill='black', font=font)
    D.text((ox, 44), '%.1f ha' % (g.area / 1e4), fill=(70, 30, 180), font=big)
    for n in (4331000, 4332000, 4333000, 4334000, 4335000, 4336000):
        y = oy + (N1 - n) / res; D.line([(ox, y), (ox + 8, y)], fill='gray'); D.text((ox + 10, y - 8), 'N %d' % (n % 100000), fill='gray', font=font)
canvas.save('orientation_study.png'); print(canvas.size)
