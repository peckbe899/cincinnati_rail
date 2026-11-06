try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
exec(open((_ws.CODE + 'yard/build1.py')).read().split("add('yard_limit', limit,")[0])
for N in (4335900, 4336100, 4336300, 4336500, 4336700, 4336900):
    L = LineString([(711500, N), (713300, N)])
    def iv(g):
        i = g.intersection(L); return [(round(x.bounds[0]), round(x.bounds[2])) for x in getattr(i, 'geoms', [i]) if not x.is_empty and x.length > 0]
    print(N, 'cand', iv(_cand), 'westCE', iv(_westCE), 'west', iv(_west), 'creek', iv(_creek), 'CE', iv(CE), 'limit', iv(limit))
