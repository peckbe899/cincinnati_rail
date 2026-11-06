try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Union Terminal, its train concourse, the plaza and the former Lincoln Park from the architects' plot plan of 1 June 1931
# (HABS OH-705, sheet 1; Ben, 2026-10-15). cutplan/trace.py traces them on the scan and fits them by five street crossings
# (cutplan/georef.py, affine, residuals 0.5-1.1 m). Run after deck_gen.py / add22.py --install: it rewrites deckpage/deck.json
# (cut_building, cut_concourse) and deckpage/basin.json (the open east forecourt becomes cut_plaza and cut_lincoln).
import json
from shapely.geometry import Polygon, mapping
S = _ws.DATA
N = json.load(open(S + 'cutplan/cut1931_utm.json'))
SRC = 'Plot plan, Cincinnati Union Terminal, 1 June 1931 (HABS OH-705, sheet 1)'
r = lambda g: json.loads(json.dumps(mapping(g.simplify(0.05)), default=float))
bld = Polygon(N['building']).union(Polygon(N['rotunda'])).buffer(0)
deck = json.load(open(S + 'deckpage/deck.json'))
deck['features'] = [f for f in deck['features'] if f['properties'].get('layer') != 'cut_concourse']
for f in deck['features']:
    if f['properties'].get('layer') == 'cut_building':
        f['geometry'] = r(bld); f['properties'].update(name='Union Terminal', src=SRC, area_m2=round(bld.area))
deck['features'].append(dict(type='Feature', properties=dict(layer='cut_concourse', name='Train concourse (1933)', src=SRC, area_m2=round(Polygon(N['concourse']).area)), geometry=r(Polygon(N['concourse']))))
json.dump(deck, open(S + 'deckpage/deck.json', 'w'))
basin = json.load(open(S + 'deckpage/basin.json'))
basin['features'] = [f for f in basin['features'] if f['properties'].get('layer') not in ('we_forecourt', 'cut_plaza', 'cut_lincoln')]
pl = Polygon(N['plaza']).difference(bld).buffer(0); lp = Polygon(N['lincoln_park'])
basin['features'].append(dict(type='Feature', properties=dict(layer='cut_plaza', name='Terminal plaza (1933)', src=SRC, area_m2=round(pl.area)), geometry=r(pl)))
basin['features'].append(dict(type='Feature', properties=dict(layer='cut_lincoln', name='Former Lincoln Park: the terminal approach (1933)', src=SRC, area_m2=round(lp.area)), geometry=r(lp)))
json.dump(basin, open(S + 'deckpage/basin.json', 'w'))
print('building', round(bld.area), 'plaza', round(pl.area), 'Lincoln Park', round(lp.area), 'concourse', round(Polygon(N['concourse']).area))
