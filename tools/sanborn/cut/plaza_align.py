try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben (17 October): the CUT plaza (terrace, lawns, drives, walks, the former Lincoln Park) and the CUT west park were not aligned with the
# street grid or the real terminal. Rotate each group onto the grid of the streets on either side and centre it between them:
# the east plaza on Kenner and Hopkins east of the terminal (1904 lines), the west park on the deck's Kenner and Hopkins.
# Run after cut1931.py (and before or after fill_blocks.py). Marks deck.json 'aligned17'; will not run twice.
import json, math, sys, numpy as np
from shapely.geometry import shape, mapping, LineString, Point
from shapely.affinity import rotate, translate
S = _ws.DATA
D = json.load(open(S + 'deckpage/deck.json')); B = json.load(open(S + 'deckpage/basin.json'))
if D.get('aligned17'): sys.exit('already aligned')
r = lambda g: json.loads(json.dumps(mapping(g.simplify(0.05)), default=float))
ST = {f['properties']['id']: LineString(f['geometry']['coordinates']) for f in D['features'] + B['features'] if f['properties'].get('layer') == 'street'}
def brg(ids):   # mean direction (degrees, east = 0, within +-90) of the streets, length-weighted
    sx = sy = 0.0
    for i in ids:
        c = list(ST[i].coords); a, b = c[0], c[-1]; dx, dy = b[0] - a[0], b[1] - a[1]
        if dx < 0: dx, dy = -dx, -dy
        L = math.hypot(dx, dy); sx += dx; sy += dy
    return math.degrees(math.atan2(sy, sx))
def mid_y(x, north, south):   # midline between two streets at easting x
    def y_at(ids):
        for i in ids:
            g = ST[i]; v = g.intersection(LineString([(x, 4320000), (x, 4340000)]))
            if not v.is_empty: return v.y if v.geom_type == 'Point' else list(v.geoms)[0].y
        return None
    return (y_at(north) + y_at(south)) / 2
def axis_of(g):   # direction of the long side of the minimum rotated rectangle, within +-90
    c = list(g.minimum_rotated_rectangle.exterior.coords); e = max(((math.dist(c[i], c[i + 1]), c[i], c[i + 1]) for i in range(4)))
    dx, dy = e[2][0] - e[1][0], e[2][1] - e[1][1]
    if dx < 0: dx, dy = -dx, -dy
    return math.degrees(math.atan2(dy, dx))
bld = shape([f for f in D['features'] if f['properties'].get('layer') == 'cut_building'][0]['geometry'])
log = {}
# ---- east plaza (basin.json)
EL = ('cut_plaza', 'cut_lincoln', 'cut_road', 'cut_terrace', 'cut_lawn', 'cut_walk')
grid_e = brg(['SB0799', 'SB0775', 'SB0773'])
drv = [shape(f['geometry']) for f in B['features'] if f['properties'].get('layer') == 'cut_road' and 'driveway' in f['properties'].get('name', '')]
ax_e = sum(axis_of(g) for g in drv) / len(drv)
xe = bld.bounds[2]; pe = (xe, mid_y(xe + 110, ['SB0799'], ['SB0775']))
dth = grid_e - ax_e
moved = []
for f in B['features']:
    if f['properties'].get('layer') in EL:
        moved.append(f); f['_g'] = rotate(shape(f['geometry']), dth, origin=pe)
# centre between the streets: the two driveways' middle onto the midline at their easting
dg = [f['_g'] for f in moved if f['properties'].get('layer') == 'cut_road' and 'driveway' in f['properties'].get('name', '')]
cx = sum(g.centroid.x for g in dg) / len(dg); cy = sum(g.centroid.y for g in dg) / len(dg)
dy = mid_y(cx, ['SB0799'], ['SB0775']) - cy
for f in moved:
    g = translate(f.pop('_g'), 0, dy)
    if f['properties']['layer'] in ('cut_plaza', 'cut_road', 'cut_lawn') and f['properties'].get('kind') != 'ramp': g = g.difference(bld).buffer(0)
    f['geometry'] = r(g); f['properties']['aligned17'] = True
log['east'] = dict(grid=round(grid_e, 2), was=round(ax_e, 2), turned=round(dth, 2), pivot=[round(pe[0], 1), round(pe[1], 1)], shift_y=round(dy, 2), n=len(moved))
# ---- west park (deck.json)
grid_w = brg(['S012', 'S013'])
for f in D['features']:
    if f['properties'].get('layer') == 'cut_park':
        g = shape(f['geometry']); ax_w = axis_of(g); b = g.bounds; pw = (b[2], (b[1] + b[3]) / 2)
        g = rotate(g, grid_w - ax_w, origin=pw)
        dyw = mid_y(g.centroid.x, ['S013'], ['S012']) - g.centroid.y; g = translate(g, 0, dyw)
        f['geometry'] = r(g); f['properties']['aligned17'] = True
        log['west_park'] = dict(grid=round(grid_w, 2), was=round(ax_w, 2), turned=round(grid_w - ax_w, 2), shift_y=round(dyw, 2))
D['aligned17'] = log
json.dump(D, open(S + 'deckpage/deck.json', 'w')); json.dump(B, open(S + 'deckpage/basin.json', 'w'))
print(json.dumps(log))
