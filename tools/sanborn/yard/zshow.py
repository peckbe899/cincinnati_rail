import json, sys, math
sys.path.insert(0, '.')
from zipkit import *
from PIL import Image, ImageDraw
L = [LineString(c) for c in json.load(open(sys.argv[1]))]
print('lines', len(L), 'outside room:', sum(1 for l in L if l.difference(ROOM0.buffer(0.5)).length > 1), 'min R %.0f' % min(radii(list(l.coords)) for l in L))
x = 0
for i, a in enumerate(L):
    for b in L[i + 1:]:
        if a.crosses(b):
            g = a.intersection(b); pts = getattr(g, 'geoms', [g])
            if any(Point(a.coords[0]).distance(p) > 1 and Point(a.coords[-1]).distance(p) > 1 and Point(b.coords[0]).distance(p) > 1 and Point(b.coords[-1]).distance(p) > 1 for p in pts): x += 1
print('true crossings', x)
E0, E1, N0, N1 = 711850, 712750, 4330850, 4336700; res = 2.6
W, H = int((E1 - E0) / res), int((N1 - N0) / res)
im = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(im)
P = lambda cs: [((x - E0) / res, (N1 - y) / res) for x, y in cs]
d.polygon(P(A.exterior.coords), outline=(200, 120, 0))
for l in L: d.line(P(l.coords), fill=(60, 20, 170), width=1)
g = fp(L)
for gg in getattr(g, 'geoms', [g]): d.polygon(P(gg.exterior.coords), outline=(0, 160, 0))
im.save(sys.argv[2]); print('fp ha %.1f' % (g.area / 1e4))
