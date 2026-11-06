try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import sys; sys.path.insert(0,(_ws.CODE + 'yard'))
import ygen
from shapely.geometry import LineString, Point
def crossings(segs, body, extra=60):
    L = [LineString(p) for p in segs] + [LineString([(x, t), (x, t + extra)]) for x, t in body.items()]
    ends = [ (Point(l.coords[0]), Point(l.coords[-1])) for l in L]
    n = 0
    for i in range(len(L)):
        for j in range(i + 1, len(L)):
            g = L[i].intersection(L[j])
            if g.is_empty: continue
            for q in getattr(g, 'geoms', [g]):
                if q.geom_type != 'Point': continue
                if min(q.distance(e) for e in ends[i] + ends[j]) > 0.5: n += 1
    return n
if __name__ == '__main__':
    for fn in ('tree_local', 'spray_local'):
        for n in (64, 40, 20):
            xs = [round(-n * 4.5 / 2 + 4.5 * k, 2) for k in range(n)]
            s, b = getattr(ygen, fn)(xs); print(fn, n, 'crossings', crossings(s, b), 'max t', round(max(b.values())))
