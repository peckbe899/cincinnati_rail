"""Assemble the 15 widest ties after the joint solve: old picks (each reader), OSM matches, the other plate's position
mapped into each plate, OSM crossings of the same names nearby. Writes ties15.json next to this script. Read only."""
import collections, csv, glob, json, os, re, sys
import numpy as np

REPO = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D'
sys.path.insert(0, REPO + '/tools/sanborn')
import _ws, seams as S  # noqa
SP = _ws.DATA
from names import key, base  # noqa
import plates as PL  # noqa
from shapely.geometry import shape, Point  # noqa
from shapely.ops import unary_union, nearest_points  # noqa

OUT = os.path.dirname(os.path.abspath(__file__))
T = list(csv.DictReader(open(SP + 'reports/2026-11-06_joint/ties.csv', encoding='utf8')))
T = sorted(T, key=lambda t: -float(t['after_m']))[:15]

# OSM lines, as cufp/fit.py builds them (all the files any plate used), with its alias table
OL = collections.defaultdict(list)
for fn in ('lph/osm_north.geojson', 'basin/osm_basin.geojson', 'lph/osm_east.geojson', 'lph/osm_norwood.geojson', 'lph/osm_west.geojson'):
    for f in json.load(open(SP + fn))['features']:
        nm = f['properties'].get('name')
        if nm and f['geometry']['type'] == 'LineString':
            g = shape(f['geometry']); OL[key(nm)].append(g); OL['B:' + base(key(nm))].append(g)
U = {k: unary_union(v) for k, v in OL.items()}
src = open(_ws.CODE + 'cufp/fit.py', encoding='utf8').read()
alias_src = re.search(r"^ALIAS = \{.*?\}\.items\(\)\}", src, re.S | re.M).group(0)
ns = dict(key=key); exec(alias_src, ns); ALIAS = ns['ALIAS']


def lines(k):
    k = ALIAS.get(k, k); return U.get(k) or U.get('B:' + base(k))


def osm_pts(na, nb):
    la, lb = lines(key(na)), lines(key(nb))
    if la is None or lb is None:
        return None
    x = la.intersection(lb); pts = [g for g in getattr(x, 'geoms', [x]) if g.geom_type == 'Point'] if not x.is_empty else []
    if not pts:
        a, b = nearest_points(la, lb)
        if a.distance(b) < 3: pts = [Point((a.x + b.x) / 2, (a.y + b.y) / 2)]
    return [(p.x, p.y) for p in pts]


def matches_file(pid):
    n = pid[3:]
    return {'22-35N': 'cuf/matches.json', '22-38': 'cuf38/matches38.json'}.get(pid) or (
        f'cufp/{n}/matches.json' if os.path.exists(SP + f'cufp/{n}/matches.json') else f'cuf_cw/{n}/matches.json')


# every plate's crossings (old models), and the individual reads behind them
PLATES = S.plate_ids()
CR = {p: S.plate_crossings(p)[0] for p in PLATES}
INV = {p['id']: p['inv'] for p in PL.PLATES}


def reads(pid, k, x, y):
    out = []
    for f in sorted(set(glob.glob(SP + f'sbg/picks22/s{pid}.json') + glob.glob(SP + f'sbg/picks22/s{pid}_*.json'))):
        for q in json.load(open(f, encoding='utf8')).get('intersections', []):
            if '?' in q['a'] + q['b'] or S.k2(q['a'], q['b']) != k:
                continue
            if np.hypot(q['x'] - x, q['y'] - y) < S.DUP_PX:
                out.append(dict(file=os.path.relpath(f, SP).replace('\\', '/'), a=q['a'], b=q['b'], x=q['x'], y=q['y'], kind=q.get('kind')))
    return out


def find(pid, sa, sb, E, N):
    k = S.k2(sa, sb)
    c = [r for r in CR[pid] if r['k'] == k]
    return min(c, key=lambda r: np.hypot(r['E'] - E, r['N'] - N)) if c else None


res = []
for n, t in enumerate(T, 1):
    a, b = t['a'], t['b']
    # the tie's crossing on each plate: same names, nearest pair (as the seam matching did)
    best = None
    for ra in [r for r in CR[a] if r['k'] == S.k2(t['street_1'], t['street_2'])]:
        for rb in [r for r in CR[b] if r['k'] == ra['k']]:
            d = float(np.hypot(ra['E'] - rb['E'], ra['N'] - rb['N']))
            if best is None or d < best[0]:
                best = (d, ra, rb)
    d, ra, rb = best
    entry = dict(n=n, tie=f'{a} / {b}', street_1=t['street_1'], street_2=t['street_2'], before_m=float(t['before_m']),
                 after_joint_m=float(t['after_m']), seam_old_m=round(d, 2), plates={})
    for me, other, r, o in ((a, b, ra, rb), (b, a, rb, ra)):
        M = json.load(open(SP + matches_file(me), encoding='utf8'))
        m = [q for q in M if tuple(sorted((base(key(q['a'])), base(key(q['b']))))) == r['k'] and np.hypot(q['x'] - r['x'], q['y'] - r['y']) < 80] if isinstance(M, list) else []
        px, py = INV[me](np.array([[o['E']]], np.float32), np.array([[o['N']]], np.float32))
        entry['plates'][me] = dict(old_pick=dict(x=r['x'], y=r['y'], E=round(r['E'], 2), N=round(r['N'], 2), readers=r['readers'], names=[r['a'], r['b']]),
                                   reads=reads(me, r['k'], r['x'], r['y']),
                                   osm_match=(dict(osm=m[0].get('osm'), why=m[0].get('why'), names=[m[0]['a'], m[0]['b']]) if m else None),
                                   other_plate_here_px=[float(np.ravel(px)[0]), float(np.ravel(py)[0])],
                                   same_names_on_plate=[dict(x=q['x'], y=q['y'], E=round(q['E'], 1), N=round(q['N'], 1),
                                                             d_m=round(float(np.hypot(q['E'] - r['E'], q['N'] - r['N'])), 1))
                                                        for q in CR[me] if q['k'] == r['k'] and q is not r])
    mid = ((ra['E'] + rb['E']) / 2, (ra['N'] + rb['N']) / 2)
    pts = osm_pts(t['street_1'], t['street_2'])
    entry['osm_same_names'] = None if pts is None else sorted(
        [dict(E=round(x, 1), N=round(y, 1), d_m=round(float(np.hypot(x - mid[0], y - mid[1])), 1)) for x, y in pts], key=lambda q: q['d_m'])
    res.append(entry)
json.dump(res, open(OUT + '/ties15.json', 'w', encoding='utf8', newline='\n'), indent=1)
for e in res:
    pa, pb = list(e['plates'])
    print(e['n'], e['tie'], e['street_1'], '&', e['street_2'], e['seam_old_m'],
          '| reads', len(e['plates'][pa]['reads']), len(e['plates'][pb]['reads']),
          '| osm', [(p, (e['plates'][p]['osm_match'] or {}).get('osm') is not None) for p in (pa, pb)],
          '| osm same names', [q['d_m'] for q in (e['osm_same_names'] or [])][:4],
          '| other picks', [q['d_m'] for p in (pa, pb) for q in e['plates'][p]['same_names_on_plate']])
