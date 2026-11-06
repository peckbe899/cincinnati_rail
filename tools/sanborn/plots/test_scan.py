import sys, json, numpy as np, time
sys.path.insert(0, '.')
from frontage import Faces, scan, scan2
from common import Tiles
from shapely.geometry import Point, LineString
from shapely.geometry.polygon import orient
from PIL import Image, ImageDraw
F = Faces(); T = Tiles()
cx, cy, half = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
sel = [b for b in F.blocks if b['g'].intersects(Point(cx, cy).buffer(half))]
print('blocks', len(sel))
# render tile crop
res = 0.25; W = int(2 * half / res)
X0, Y1 = cx - half, cy + half
xs = X0 + (np.arange(W) + 0.5) * res; ys = Y1 - (np.arange(W) + 0.5) * res
XX, YY = np.meshgrid(xs, ys); lum = T.sample(XX.ravel(), YY.ravel()).reshape(W, W)
im = Image.fromarray(np.nan_to_num(lum, nan=255).astype(np.uint8)).convert('RGB'); d = ImageDraw.Draw(im)
def px(x, y): return ((x - X0) / res, (Y1 - y) / res)
t0 = time.time(); allc = []
for b in sel:
    g = b['g']; parts = list(getattr(g, 'geoms', [g]))
    for pg in parts:
        ring = list(orient(pg, 1.0).exterior.coords)
        d.line([px(*q) for q in ring], fill=(0, 120, 255), width=2)
        smp = F.classify(ring)
        for x, y, tx, ty, lab in smp:
            col = (0, 170, 0) if lab and lab != 'alley' else ((255, 140, 0) if lab == 'alley' else (160, 160, 160))
            d.point(px(x, y), fill=col)
        for r in F.runs(smp):
            c, Ln, _ = scan2(T, r); allc.append((Ln, len(c)))
            L = LineString(r['pts'])
            for s in c:
                p = L.interpolate(s); q = L.interpolate(min(L.length, s + 0.5)); o = L.interpolate(max(0, s - 0.5)); tx, ty = q.x - o.x, q.y - o.y; m = np.hypot(tx, ty); nx, ny = -ty / m, tx / m
                d.line([px(p.x, p.y), px(p.x + nx * 10, p.y + ny * 10)], fill=(255, 0, 0), width=2)
            gaps = np.diff(c) if len(c) > 1 else []
            print(b['id'], r['street'], 'L', round(Ln), 'cands', len(c), 'gaps med', round(float(np.median(gaps)), 1) if len(gaps) else '-')
print('time', round(time.time() - t0, 1))
im.save(sys.argv[4])
