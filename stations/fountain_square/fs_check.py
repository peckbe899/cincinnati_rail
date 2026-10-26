"""Checks on fs_model: every flight starts and ends on a floor of its level, every elevator stands on a floor at each level it
serves, and no two flights or elevators overlap at a level they share."""
import numpy as np
from shapely.geometry import Point, box
from fs_model import *

def floor(level):
    return unary_union([p['geom'] for p in PARTS if p['level'] == level])

F = {lv: floor(lv) for lv in (-1, -1.5, -2, -3, -4)}
bad = 0
for i, f in enumerate(FLIGHTS):
    s, e = Point(f['start']), Point(f['end'])
    d = np.array(f['d'])
    s_in = Point(np.array(f['start']) - d * 0.8)        # just before the top edge
    e_in = Point(np.array(f['end']) + d * 0.8)          # just past the foot
    if f['top'] != 0 and not F[f['top']].buffer(0.3).contains(s_in):
        print('flight', i, f['kind'], f['top'], '->', f['bot'], 'top not on a floor at', f['top'], np.round(f['start'], 1)); bad += 1
    if not F[f['bot']].buffer(0.3).contains(e_in):
        print('flight', i, f['kind'], f['top'], '->', f['bot'], 'foot not on a floor at', f['bot'], np.round(f['end'], 1)); bad += 1
for i, l in enumerate(LIFTS):
    sq = box(l['xy'][0] - 1.25, l['xy'][1] - 1.25, l['xy'][0] + 1.25, l['xy'][1] + 1.25)
    for lv in l['levels']:
        if lv != 0 and not F[lv].buffer(0.3).contains(sq):
            print('lift', i, np.round(l['xy'], 1), 'not on a floor at', lv); bad += 1
# every flight's well (its opening in the floor at its top) lies inside that floor, so no opening bites the floor's edge
for i, f in enumerate(FLIGHTS):
    if f['top'] != 0:
        out = well(f).difference(F[f['top']].buffer(0.05)).area
        if out > 0.2:
            print('flight', i, f['kind'], f['top'], '->', f['bot'], np.round(f['start'], 1), 'well runs past the floor edge by %.1f m2' % out); bad += 1
# overlaps in plan between things that share a level band
items = [('flight %d %s %s->%s' % (i, f['kind'], f['top'], f['bot']), f['geom'], (Z[f['top']], Z[f['bot']])) for i, f in enumerate(FLIGHTS)]
items += [('lift %d' % i, box(l['xy'][0] - 1.25, l['xy'][1] - 1.25, l['xy'][0] + 1.25, l['xy'][1] + 1.25), (Z[l['levels'][0]], Z[l['levels'][-1]])) for i, l in enumerate(LIFTS)]
for a in range(len(items)):
    for b in range(a + 1, len(items)):
        na, ga, (ta, ba) = items[a]; nb, gb, (tb, bb) = items[b]
        if min(ba, bb) - max(ta, tb) > 0.3 and ga.intersection(gb).area > 0.3:
            print('overlap:', na, '&', nb, round(ga.intersection(gb).area, 1)); bad += 1
print('problems:', bad)
