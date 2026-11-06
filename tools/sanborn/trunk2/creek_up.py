try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Mill Creek is decked and underground south-west (downstream) of Albone Street (Ben, 25 October 2026): keep only the open creek upstream of Albone.
import json, numpy as np
from pyproj import Transformer
from shapely.geometry import shape, box, Point, LineString
from shapely.ops import transform, unary_union, linemerge, substring
TRf = Transformer.from_crs(4326, 26916, always_xy=True)
W = json.load(open(_ws.ext('/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/OSM/water.geojson')))
Bx = box(711000, 4334000, 717500, 4340500)
ALB = Point(713015.0, 4337300.0)                     # where Albone Street meets the creek (its two pieces end on the bank)
lines, polys = [], []
for f in W['features']:
    g = transform(TRf.transform, shape(f['geometry']))
    if not g.intersects(Bx): continue
    if f['properties'].get('name') == 'Mill Creek':
        if g.geom_type in ('LineString', 'MultiLineString'): lines.append(g)
        else: polys.append(g)
    elif f['properties'].get('water') == 'river' or f['properties'].get('waterway') == 'riverbank': polys.append(g)      # Mill Creek's bank polygons
    elif g.geom_type in ('Polygon', 'MultiPolygon') and g.area > 1500: polys.append(('other', g))
M = linemerge(unary_union(lines)); parts = list(getattr(M, 'geoms', [M]))
up = []
for ln in parts:
    if ln.distance(ALB) < 40:
        d = ln.project(ALB); a = substring(ln, 0, d); b = substring(ln, d, ln.length)
        # upstream = the piece reaching further north-east
        ka = max(np.asarray(a.coords)[:, 0] + np.asarray(a.coords)[:, 1]); kb = max(np.asarray(b.coords)[:, 0] + np.asarray(b.coords)[:, 1])
        up.append(a if ka > kb else b)
    else:
        c = np.asarray(ln.coords)
        if (c[:, 0].mean() - ALB.x) + (c[:, 1].mean() - ALB.y) > 0: up.append(ln)
OPEN_LINE = unary_union(up)
DECKED_LINE = M.difference(OPEN_LINE.buffer(0.5))                 # the decked, underground creek south-west of Albone
WAT_UP = unary_union([OPEN_LINE.buffer(8)] + [g.intersection(OPEN_LINE.buffer(60)) for g in polys if not isinstance(g, tuple)] + [g[1] for g in polys if isinstance(g, tuple)])
if __name__ == '__main__':
    print('pieces', len(parts), 'open length %.0f m' % OPEN_LINE.length)
    json.dump({'creek_open': [list(map(list, np.asarray(l.coords))) for l in getattr(OPEN_LINE, 'geoms', [OPEN_LINE])]}, open((_ws.DATA + 'trunk2/millcreek_open.json'), 'w'))
