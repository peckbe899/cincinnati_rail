"""The Deck's viaducts, each a selection of its own (Ben, 28 October): writes hub/sites/deck/viaducts.json (Deck UTM).

Parts (sel id: what it is, where it comes from):
- north_arch: the north arch viaduct, APEx lower deck (the Deck's polygon within 12 m of an APEx track)
- wh_sc: RER A, Western Hills to South Cumminsville (the rest of the Deck's north arch viaduct polygon, and the route's
  elevated stretches in the Rail Profiles)
- cut_arch, cut_kentucky, cut_cardinal, cut_cvgx: the CUT south approach, the arch viaduct from W 9th to the Cardinal
  crossing and its three branches south of it (APEx Kentucky to the APEx bridge, the Cardinal branch, the CVG Express),
  split by the nearest track
- cw_upper: the Cincinnati Western viaduct upper deck (RER D and the APEx Indianapolis pair; named for the Roll Hill
  tunnel), from the Profiles context's upper deck
- cw_lower: the Cincinnati Western viaduct lower deck (R5), the Deck's R5 tracks on the lower level
- westwood, northgate, northside: RER A's Westwood branch, the Northgate line (the Colerain branch, west of the
  Northside branch) and the Northside viaduct (the line through Northside toward Oxford): the elevated stretches of
  those routes in the Rail Profiles, as the 3D build has them (6.45 m either side of the line: half a 4.5 m track pair
  and the 4.2 m deck edge)
- cno: the C&O viaduct (the C&O pair's viaduct and the TRIMET C&O viaduct)

Usage: python3 tools/viaduct_parts.py [HARNESS_OUT]   (default hub/work/harness_out.json; the hub's 3D build runs it)
"""
import json
import os
import sys

import numpy as np
from shapely.geometry import LineString, Point, mapping, shape
from shapely.ops import unary_union

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
OUT = os.path.join(ROOT, 'hub', 'sites', 'deck', 'viaducts.json')   # the repo copy; the hub writes its own with --out
HALF = 2.25 + 4.2
ELEV_ROUTES = {'westwood': ('RER_A_westwood', 'RER A Westwood'), 'northgate': ('RER_A_colerain', 'RER A Northgate (Colerain branch)'),
               'northside': ('RER_A_wyoming', 'Northside viaduct (RER A, the Oxford line)'), 'wh_sc': ('RER_A_cumminsville', 'RER A Western Hills to South Cumminsville')}
NAMES = {'north_arch': 'North arch viaduct (APEx lower deck)', 'cut_arch': 'CUT south approach: arch viaduct, W 9th to the Cardinal crossing',
         'cut_kentucky': 'CUT south approach: APEx Kentucky', 'cut_cardinal': 'CUT south approach: Cardinal branch', 'cut_cvgx': 'CUT south approach: CVG Express',
         'cw_upper': 'Cincinnati Western viaduct, upper deck (RER D, APEx Indianapolis)', 'cw_lower': 'Cincinnati Western viaduct, lower deck (R5)',
         'cno': 'C&O viaduct', **{k: v[1] for k, v in ELEV_ROUTES.items()}}


def main():
    import make_profile_context as mpc
    B = mpc.build()
    S, T, stru = B['S'], B['T'], B['stru']
    by = {st['short']: st for st in S}
    raw = {f['properties']['name']: shape(f['geometry']) for f in json.load(open(os.path.join(ROOT, 'data', 'deck', 'structures.json')))['features']
           if f['properties'].get('layer') == 'struct'}
    parts = {k: [] for k in NAMES}
    # the north arch viaduct: APEx part, and RER A's Western Hills - South Cumminsville viaduct (the rest of the polygon)
    na = raw['North arch viaduct']
    parts['north_arch'].append(stru['North arch viaduct'])
    parts['wh_sc'].append(na.difference(stru['North arch viaduct'].buffer(0.5)))
    # the CUT south approach: the arch part, then south of the Cardinal crossing by the nearest track family
    parts['cut_arch'].append(by['CUT south arch viaduct']['geom'])
    fam = {'cut_kentucky': ('APEx Kentucky',), 'cut_cardinal': ('Cardinal branch', 'APEx Cardinal'), 'cut_cvgx': ('Track 15', 'Track 16', 'CVG Express')}
    lines = {k: unary_union([LineString(f['geometry']['coordinates']) for f in T['features'] if f['geometry']['type'] == 'LineString'
                             and (f['properties'].get('name') or '').startswith(v) and 'tunnel' not in (f['properties'].get('name') or '')]) for k, v in fam.items()}
    south = by['CUT south approach (viaduct)']['geom']
    cells = {k: [] for k in fam}
    xs = np.arange(south.bounds[0], south.bounds[2] + 2, 2.0)
    ys = np.arange(south.bounds[1], south.bounds[3] + 2, 2.0)
    from shapely.geometry import box
    for x in xs:
        for y in ys:
            p = Point(x + 1, y + 1)
            if not south.contains(p):
                continue
            k = min(lines, key=lambda k: lines[k].distance(p))
            cells[k].append(box(x, y, x + 2, y + 2))
    for k, c in cells.items():
        if c:
            parts[k].append(unary_union(c).intersection(south).buffer(0.01).buffer(-0.01))
    # the Cincinnati Western viaduct: the upper deck (Profiles context) and R5 on the lower level
    parts['cw_upper'].append(by['Indianapolis and D upper deck']['geom'])
    r5 = [LineString(f['geometry']['coordinates']) for f in T['features'] if (f['properties'].get('name') or '').startswith('R5') and f['geometry']['type'] == 'LineString']
    if r5:
        parts['cw_lower'].append(unary_union([l.buffer(3.0, cap_style=2) for l in r5]))
    # the C&O viaduct
    parts['cno'] += [raw[n] for n in ('C&O pair: viaduct', 'C&O viaduct (TRIMET line, to the C&O bridge)') if n in raw]
    # RER A's viaducts: the elevated stretches of each route (as the 3D build has them)
    hf = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'hub', 'work', 'harness_out.json')
    H = json.load(open(hf))['profiles'] if os.path.exists(hf) else {}
    for k, (lid, _) in ELEV_ROUTES.items():
        if lid not in H:
            continue
        d = json.load(open(os.path.join(ROOT, 'data', 'profile', 'rer', 'lines', lid + '.json')))
        p = np.array(d['path'], float)
        E, N = mpc.TO_UTM.transform(p[:, 1], p[:, 2])
        line = LineString(np.c_[E, N])
        dv = np.concatenate([[0], np.cumsum(np.hypot(np.diff(E), np.diff(N)))])
        runs, cur = [], None
        for c, z, t, *_ in H[lid]['samples']:
            if t == 'elevated':
                if cur and c - cur[1] <= 60:
                    cur[1] = c
                else:
                    cur = [c, c]
                    runs.append(cur)
        from shapely.ops import substring
        for a, b in runs:
            if b - a >= 40:
                da, db = np.interp([a, b], p[:, 0], dv)
                parts[k].append(substring(line, da, db).buffer(HALF, cap_style=2))
    feats = []
    for k, gs in parts.items():
        g = unary_union([x for x in gs if not x.is_empty])
        if g.is_empty:
            continue
        g = g.simplify(0.3)
        feats.append({'type': 'Feature', 'properties': {'layer': 'viaduct_part', 'sel': k, 'name': NAMES[k], 'area_m2': round(g.area)},
                      'geometry': {'type': g.geom_type, 'coordinates': json.loads(json.dumps(mapping(g)['coordinates'], default=float), parse_float=lambda s: round(float(s), 2))}})
    out = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == '--out' and i + 1 < len(sys.argv)), OUT)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({'type': 'FeatureCollection', 'about': __doc__.split('\n\n')[0], 'features': feats}, open(out, 'w'), separators=(',', ':'))
    print(f'{len(feats)} viaduct parts -> {out}: ' + ', '.join(f"{f['properties']['sel']} {f['properties']['area_m2']} m2" for f in feats))


if __name__ == '__main__':
    main()
