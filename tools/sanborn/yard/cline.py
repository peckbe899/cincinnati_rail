# centreline of Ben's buildable area, as a smooth spine (curves R >= 800 where possible)
import json, math
from shapely.geometry import shape, LineString, Point
import sys; sys.path.insert(0, '.')
from ygen import CurveFrame
A = shape(json.load(open('ben_area.json'))['geometry'])
# first pass: horizontal cut midpoints
pts = []
for n in range(4330880, 4336640, 50):
    g = LineString([(711000, n), (714000, n)]).intersection(A)
    q = max(getattr(g, 'geoms', [g]), key=lambda z: z.length); pts.append(((q.bounds[0] + q.bounds[2]) / 2, n))
line = LineString(pts)
for it in range(4):   # recentre along normals
    f = CurveFrame(list(line.simplify(20).coords)); new = []
    for t in range(0, int(f.L) + 1, 50):
        c = f.W(0, t); u = f._ut(t); nrm = (-u[1], u[0])
        seg = LineString([(c[0] - nrm[0] * 400, c[1] - nrm[1] * 400), (c[0] + nrm[0] * 400, c[1] + nrm[1] * 400)]).intersection(A)
        parts = [z for z in getattr(seg, 'geoms', [seg]) if z.length > 1]
        if not parts: continue
        z = min(parts, key=lambda z: z.distance(Point(c)))
        a, b = z.coords[0], z.coords[-1]; new.append(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
    line = LineString(new).simplify(5)
f = CurveFrame(list(line.coords))
out = []
for t in range(0, int(f.L) + 1, 100):
    c = f.W(0, t); u = f._ut(t); nrm = (-u[1], u[0])
    seg = LineString([(c[0] - nrm[0] * 400, c[1] - nrm[1] * 400), (c[0] + nrm[0] * 400, c[1] + nrm[1] * 400)]).intersection(A)
    parts = [z for z in getattr(seg, 'geoms', [seg]) if z.length > 1]
    z = min(parts, key=lambda z: z.distance(Point(c))) if parts else None
    out.append((t, [round(v) for v in c], round(z.length) if z else 0, round(math.degrees(math.atan2(u[0], u[1])) % 360)))
for o in out: print(o)
json.dump(list(line.coords), open('cline.json', 'w'))
print('length', round(f.L))
