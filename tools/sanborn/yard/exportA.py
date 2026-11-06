try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, math, sys
sys.path.insert(0, (_ws.CODE + 'yard'))
from shapely.geometry import shape, mapping, LineString, Point
from shapely.ops import unary_union
from lv import deck_z, yard_z, S
from zipkit import fp, radii, A
R = json.load(open(S + 'yard/A.json'))
SEG = [(y, k, LineString(c)) for y, k, c in R['SEG']]; LEADS = [(n, LineString(c)) for n, c in R['LEADS']]
Y = json.load(open(S + 'deckpage/yard_v140.json'))
F = [f for f in Y['features'] if f['properties']['layer'] not in ('yard_track', 'yard_lead', 'yard_xing', 'yard_fan', 'yard_mark')]
for f in F:
    if f['properties']['layer'] == 'yard_limit':
        f['geometry'] = mapping(A); f['properties']['name'] = 'Buildable area (Ben, 27 October)'
        f['properties']['note'] = 'Between the arch viaduct, RER and Mill Creek; %.1f ha' % (A.area / 1e4)
def addf(layer, g, **p):
    p['layer'] = layer; F.append({'type': 'Feature', 'properties': p, 'geometry': mapping(g)})
NOTES = {'North yard': 'From the Palace north to the north end of the area; one long yard, full width, compound ladders at each end (master 14.3°, groups 7.15°, No. 8 turnouts); extra tracks branch off its outer tracks where the area widens',
         'South yard': 'From the south throat (where the departure line and the fan lead leave) north to the Palace; one long yard, full width, compound ladders at each end',
         'South fan (stub, to the river)': 'CVG-type stub fan in the lower left, for unloading; lead off the departure line at yard level; stub ends at the area’s south edge'}
for name, note in NOTES.items():
    ls = [l for y, k, l in SEG if y == name]
    if not ls: continue
    g = fp(ls); ntr = sum(1 for y, k, l in SEG if y == name and k in ('track', 'stub')); nst = sum(1 for y, k, l in SEG if y == name and k == 'stub')
    addf('yard_fan', g, name=name, area_m2=round(g.area), tracks=ntr, stubs=nst, floor=[round(yard_z(g.bounds[3]), 1), round(yard_z(g.bounds[1]), 1)], note=note)
for y, k, l in SEG: addf('yard_track', l, yard=y, kind='stub' if k == 'stub' else ('throat' if k == 'throat' else 'yard'))
LN = {'Lead between the yards': 'Straight lead joining the south yard’s north throat to the north yard’s south throat',
      'Lead to the north': 'From the north yard’s north throat to the north end of the area; its route on beyond is not set',
      'Departure line and freight ramp to the CS bridge': 'From the south yard’s south throat at yard level, then its own ramp at %.2f%% along the east side onto the Cincinnati Southern bridge tracks by No. 10 turnouts; curves of 450 m radius' % (R['grade'] * 100),
      'South fan lead': 'Off the departure line at yard level by a No. 8 turnout, curves of 300 m radius, to the fan’s throat'}
for n, g in LEADS: addf('yard_lead', g, name=n, length_m=round(g.length), note=LN[n])
for nm, x, y, z, dz, how in R['xings']:
    if how == 'cut or bridge': addf('yard_xing', Point(x, y), name=nm, rail=z, deck=dz, label=nm + ': ramp %.1f m, deck %.1f m' % (z, dz))
for nn in range(4331000, 4336700, 500):
    ii = LineString([(711000, nn), (714000, nn)]).intersection(A)
    xs_ = [g.bounds for g in getattr(ii, 'geoms', [ii]) if not g.is_empty]
    if xs_: addf('yard_mark', Point(max(xs_, key=lambda b: b[2] - b[0])[2] - 8, nn), deck=round(deck_z(nn), 1), floor=round(yard_z(nn), 1))
def r(c): return [r(v) for v in c] if isinstance(c[0], (list, tuple)) else [round(c[0], 1), round(c[1], 1)]
for f in F:
    g = json.loads(json.dumps(f['geometry'])); f['geometry'] = g
    if g['type'] == 'GeometryCollection': continue
    g['coordinates'] = r(g['coordinates']) if g['type'] != 'Point' else [round(g['coordinates'][0], 1), round(g['coordinates'][1], 1)]
FC = {'type': 'FeatureCollection', 'crs': 'EPSG:26916', 'footprint_ha': round(R['footprint'] / 1e4, 1), 'note': 'Yards under the deck, draft 6 (27 October 2026): layout A in Ben’s buildable area: two long yards end to end with extra tracks where the area widens, a CVG-type stub fan in the lower left, the departure line and freight ramp up the east side to the CS bridge. Track spacing 4.5 m (the real yard), No. 8 turnouts in the yard and No. 10 at the bridge, compound ladders (14.3/7.15 deg). Footprint measured like today’s yard (tracks + 3 m, gaps under 24 m closed).', 'features': F}
json.dump(FC, open(S + 'deckpage/yard.json', 'w'), separators=(',', ':'))
print('written', len(F), 'footprint', FC['footprint_ha'])
