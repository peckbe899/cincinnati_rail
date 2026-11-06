try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json,sys
sys.path.insert(0,(_ws.CODE + 'yard'))
exec(open((_ws.CODE + 'yard/build4.py')).read().split("# ---------------- receiving yard")[0])
RECV = fil([(712170.0, 4336150.0), (712110.0, 4335800.0), (712090.0, 4335450.0), (712110.0, 4335150.0), (712200.0, 4334850.0), (712350.0, 4334580.0), (712500.0, 4334330.0), (712570.0, 4334170.0), (712575.0, 4334080.0)], 900)
fN = CurveFrame(RECV); xs = lat_range(-90, 90)
sN, bN = tree_local(xs); sS, bS = tree_local([-x for x in xs])
feats=[]
for x in xs[::3]:
    t0, t1 = bN[x], fN.L - bS[-x]
    body = LineString(fN.poly([(x, t0), (x, t1)], 10)); d = body.difference(ROOM)
    print(x, round(t0), round(t1), 'outside m', round(d.length), [[round(v) for v in g.bounds] for g in getattr(d,'geoms',[d]) if g.length>3][:3])
