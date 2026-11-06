try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Union Terminal from the architects' drawings (Ben, 2026-10-15). Run after deck_gen.py / add22.py --install.
# - Building and train concourse: the first-floor plan (Ben's PNG of the HABS floor plans, left sheet), fitted to the 1931 plot plan by a
#   similarity on six building corners (cutfp/fp_trace.py, residuals 0.6-2.4 m), then to UTM by the plot plan's affine (cutplan/georef.py).
#   The concourse runs on west over the field to the west headhouse (Ben).
# - Plaza, former Lincoln Park and their roads, ramps, terrace, lawns and walks: the plot plan of 1 June 1931 (HABS OH-705, sheet 1),
#   cutplan/trace.py and cutplan/plaza_trace.py.
# - Streets: Dalton passes under the plaza (underpass SB0631U); President Place and Curran Street are gone (Ben).
import json
import numpy as np
from shapely.geometry import Polygon, LineString, box, shape, mapping
S = _ws.DATA
N = json.load(open(S + 'cutplan/cut1931_utm.json'))
FP = json.load(open(S + 'cutfp/fp_utm.json'))
PZ = json.load(open(S + 'cutplan/plaza_utm.json'))
SRC = 'Plot plan, Cincinnati Union Terminal, 1 June 1931 (HABS OH-705, sheet 1)'
SRC_FP = 'First-floor plan, Cincinnati Union Terminal (architects’ drawings, HABS), fitted to the 1931 plot plan'
r = lambda g: json.loads(json.dumps(mapping(g.simplify(0.05)), default=float))
bld = Polygon(FP['building']).buffer(0)
c = FP['concourse'][:4]                                              # PNG corners: (259,41) (314,41) (314,297) (259,297) = west-S, west-N, east-N, east-S
ax = np.subtract(c[2], c[1]); ax = ax / np.linalg.norm(ax)          # along the concourse, eastward
# Ben (15 October): the west headhouse moves east, to the freight passing track (2.5 m from its centre); the CUT west park follows it
FLD = json.load(open(S + 'cut/field1931.json')); _P0 = np.array(FLD['p0']); _D = np.array(FLD['dir']); _E = np.array(FLD['east'])
def _fpt(o, N): b0 = _P0 + _E * o; t = (N - b0[1]) / _D[1]; return b0 + _D * t
deck0 = json.load(open(S + 'deckpage/deck.json'))
_hh = [f for f in deck0['features'] if f['properties'].get('layer') == 'cut_headhouse'][0]; _hg = shape(_hh['geometry'])
if 'moved_m' not in _hh['properties']:
    HH_SHIFT = float(_fpt(FLD['off_m']['F'] - 2.5, (_hg.bounds[1] + _hg.bounds[3]) / 2)[0] - _hg.bounds[2])
else:
    HH_SHIFT = 0.0
HH_E = _hg.bounds[2] + HH_SHIFT - 1.0                                  # into the west headhouse's east face
def west_to(p): t = (HH_E - p[0]) / ax[0]; return tuple(np.array(p) + ax * t)
conc = Polygon([west_to(c[0]), west_to(c[1]), c[2], c[3]]).difference(bld).buffer(0)
deck = deck0
deck['features'] = [f for f in deck['features'] if f['properties'].get('layer') != 'cut_concourse']
from shapely.affinity import translate
for f in deck['features']:
    L = f['properties'].get('layer')
    if L == 'cut_headhouse' and HH_SHIFT:
        g = translate(shape(f['geometry']), xoff=HH_SHIFT); f['geometry'] = r(g); f['properties']['moved_m'] = round(HH_SHIFT, 1)
        f['properties']['note'] = f'moved {HH_SHIFT:.1f} m east to the freight passing track (Ben, 15 October)'
for f in deck['features']:
    L = f['properties'].get('layer')
    if L == 'cut_park' and HH_SHIFT:
        g = shape(f['geometry']); b = g.bounds
        g = g.union(box(b[2] - 1, b[1], b[2] + HH_SHIFT + 1, b[3])).buffer(0); f['geometry'] = r(g)
        if isinstance(deck.get('cut'), dict) and 'park_len_m' in deck['cut']: deck['cut']['park_len_m'] = round(deck['cut']['park_len_m'] + HH_SHIFT, 1)
    if L == 'cut_precinct' and HH_SHIFT:
        g = shape(f['geometry']); b = g.bounds
        g = g.difference(box(b[0] - 1, b[1] - 1, b[0] + HH_SHIFT, b[3] + 1)).buffer(0); f['geometry'] = r(g)
for f in deck['features']:
    if f['properties'].get('layer') == 'cut_building':
        f['geometry'] = r(bld); f['properties'].update(name='Union Terminal', src=SRC_FP, area_m2=round(bld.area), note='first floor: wings, concourse rotunda, front and the bus and cab ramp arms')
deck['features'].append(dict(type='Feature', properties=dict(layer='cut_concourse', name='Train concourse (1933), on to the west headhouse', src=SRC_FP,
                                                               area_m2=round(conc.area), length_m=round(float(np.dot(np.subtract(c[2], west_to(c[1])), ax)), 1)),
                         geometry=r(conc)))
json.dump(deck, open(S + 'deckpage/deck.json', 'w'))
basin = json.load(open(S + 'deckpage/basin.json'))
basin['features'] = [f for f in basin['features'] if f['properties'].get('layer') not in ('we_forecourt', 'cut_plaza', 'cut_lincoln', 'cut_road', 'cut_terrace', 'cut_lawn', 'cut_walk')]
pl = Polygon(N['plaza']).difference(bld).buffer(0); lp = Polygon(N['lincoln_park'])
basin['features'].append(dict(type='Feature', properties=dict(layer='cut_plaza', name='Terminal plaza (1933)', src=SRC, area_m2=round(pl.area)), geometry=r(pl)))
basin['features'].append(dict(type='Feature', properties=dict(layer='cut_lincoln', name='Former Lincoln Park: the terminal approach (1933)', src=SRC, area_m2=round(lp.area)), geometry=r(lp)))
for f in PZ['features']:
    g = shape(f['geometry'])
    if f['properties']['layer'] in ('cut_road', 'cut_lawn') and f['properties'].get('kind') != 'ramp': g = g.difference(bld).buffer(0)
    if g.is_empty: continue
    f['geometry'] = r(g); basin['features'].append(f)
# Streets (Ben, 15 October): Dalton Avenue runs on under the plaza in an underpass; President Place is gone, its land taken into the park;
# Curran Street, under the building and the plaza driveway, is not on the plan and goes too.
byid = {f['properties'].get('id'): f for f in basin['features']}
d0, d1 = byid['SB0631']['geometry']['coordinates'][-1], byid['SB0630']['geometry']['coordinates'][0]
pp = byid.get('SB0899')
if pp:
    strip = LineString(pp['geometry']['coordinates']).buffer(9.2, cap_style='flat')
    blk = byid['SBB0453']; bg = shape(blk['geometry']); bb = bg.bounds
    g2 = bg.union(strip.intersection(box(bb[0] - 30, bb[1], bb[2], bb[3]))).buffer(0.01).buffer(-0.01)
    blk['geometry'] = r(g2); blk['properties']['note'] = 'President Place taken into the park (1931 plot plan)'
basin['features'] = [f for f in basin['features'] if f['properties'].get('id') not in ('SB0899', 'SB0626', 'SB0631U')]
dp = dict(byid['SB0631']['properties']); dp.update(id='SB0631U', structure='underpass', width_m=10.8, width_ft=35.4, width_src='measured, 1931 plot plan (the underpass walls)',
          src='1931 plot plan', geom_src='the 1904 line, Hopkins to Kenner'); dp.pop('sheets', None)
basin['features'].append(dict(type='Feature', properties=dp, geometry=dict(type='LineString', coordinates=[d0, d1])))
json.dump(basin, open(S + 'deckpage/basin.json', 'w'))
print('headhouse moved', round(HH_SHIFT, 1), 'building', round(bld.area), 'concourse', round(conc.area), 'plaza', round(pl.area), 'Lincoln Park', round(lp.area), 'plaza features', len(PZ['features']))
