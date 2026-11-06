try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
src = open((_ws.CODE + 'yard/build6.py')).read()
exec(src.split("xw = in_room(ROOM_W")[0])
fN = CurveFrame(SPW); fS = CurveFrame(SPW[::-1]); xs = lat_range(-90.0, 90.0)
sN, bN = FAN(xs); sS, bS = FAN([-x for x in xs])
for x in xs[::3]:
    t0, t1 = bN[x], fN.L - bS[-x]
    body = LineString(fN.poly([(x, t0), (x, max(t1, t0 + 1))], 10)); d = body.difference(ROOM_W)
    print(x, round(t0), round(t1), round(t1 - t0), 'out', round(d.length), [[round(v) for v in g.bounds] for g in getattr(d, 'geoms', [d]) if g.length > 3][:2])
print('spine L', round(fN.L))
