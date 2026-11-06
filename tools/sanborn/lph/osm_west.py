try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# West (Price Hill) OSM extract for 1922 plates 26A, 26B, 29 (25 Oct 2026): same source as osm_north/osm_east
# (Historic_Topo/OSM/streets_all.geojson, Overpass 2026-10-07), projected to EPSG:26916, box E 703,500-713,500, N 4,327,500-4,334,500.
import json
from pyproj import Transformer
from shapely.geometry import shape, box, mapping
T = Transformer.from_crs(4326, 26916, always_xy=True)
SRC = _ws.ext('/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/OSM/streets_all.geojson')
B = box(703500, 4327500, 713500, 4334500); out = []
for f in json.load(open(SRC))['features']:
    g = f['geometry']
    if g['type'] != 'LineString': continue
    c = [T.transform(x, y) for x, y in g['coordinates']]
    s = shape({'type': 'LineString', 'coordinates': c})
    if not s.intersects(B): continue
    out.append({'type': 'Feature', 'properties': f['properties'], 'geometry': {'type': 'LineString', 'coordinates': [[round(x, 2), round(y, 2)] for x, y in c]}})
json.dump({'type': 'FeatureCollection', 'features': out}, open((_ws.DATA + 'lph/osm_west.geojson'), 'w'))
print(len(out))
