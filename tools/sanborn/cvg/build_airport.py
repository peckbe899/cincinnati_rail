try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# CVG from Ben's CVG Layout.kmz (2026-10-16): runways are centre lines, drawn 150 ft (45.72 m) wide; terminals and hubs are buildings;
# the other polygons are general areas. Output deckpage/airport.json (EPSG:26916).
import json, math
from shapely.geometry import LineString, Polygon, mapping
S = _ws.DATA
K = json.load(open(S + 'cvgkmz/cvg_kmz.json'))['CVG_Layout.kml']
W = 150 * 0.3048
R = lambda g: json.loads(json.dumps(mapping(g), default=lambda v: round(float(v), 2)))
def r2(c): return [[round(x, 2), round(y, 2)] for x, y in c]
F = []
BUILD = ('Terminal', 'Hub')
for r in K:
    nm = r['name'].replace('Hanger', 'Hangar')
    if r['kind'] == 'line':
        g = LineString(r['c']); poly = g.buffer(W / 2, cap_style='flat')
        a = math.degrees(math.atan2(r['c'][1][0] - r['c'][0][0], r['c'][1][1] - r['c'][0][1])) % 360
        F.append(dict(type='Feature', properties=dict(layer='cvg_runway', name=nm, length_m=round(g.length), length_ft=round(g.length / 0.3048 / 10) * 10, width_m=round(W, 2),
                                                      bearing=round(a, 1), src='CVG Layout.kmz (centre line), 150 ft wide'),
                       geometry=dict(type='Polygon', coordinates=[r2(poly.exterior.coords)])))
        F.append(dict(type='Feature', properties=dict(layer='cvg_runway_cl', name=nm), geometry=dict(type='LineString', coordinates=r2(r['c']))))
    elif r['kind'] == 'poly':
        g = Polygon(r['c']).buffer(0)
        layer = 'cvg_building' if any(b in nm for b in BUILD) else 'cvg_area'
        F.append(dict(type='Feature', properties=dict(layer=layer, name=nm, area_m2=round(g.area), src='CVG Layout.kmz'), geometry=dict(type='Polygon', coordinates=[r2(g.exterior.coords)])))
json.dump(dict(crs='EPSG:26916', src='CVG Layout.kmz (Ben, 16 October 2026)', features=F), open(S + 'deckpage/airport.json', 'w'))
for f in F:
    p = f['properties']; print(p['layer'], p['name'], p.get('length_m', ''), p.get('length_ft', ''), p.get('area_m2', ''), p.get('bearing', ''))
