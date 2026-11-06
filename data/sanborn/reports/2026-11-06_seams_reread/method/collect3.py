"""Round 3 (Ben, 6 November): collate the two reads of the 37L/37R gutter controls and the 33/34R, 34R/38 tie crossings,
classify each (confirmed / moved / wrong match / unresolved), write data/sanborn/picks22_reread/<plate>/r3_*.json and
data/sanborn/reports/2026-11-06_seams_reread/round3.json."""
import collections, json, os, re, sys
import numpy as np

REPO = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D'
sys.path.insert(0, REPO + '/tools/sanborn')
import _ws, seams as S  # noqa
from names import key, base  # noqa
from shapely.geometry import shape, Point  # noqa
from shapely.ops import unary_union, nearest_points  # noqa
SP = _ws.DATA
HERE = os.path.dirname(os.path.abspath(__file__))
JOBS = json.load(open(HERE + '/jobs3.json', encoding='utf8'))
T = {e['n']: e for e in json.load(open(SP + 'reports/2026-11-06_seams_reread/ties15.json', encoding='utf8'))}
R = collections.defaultdict(list)
for g in ('Cr1', 'Cr2', 'Dr1', 'Dr2'):
    for q in json.load(open(f'{HERE}/reads/{g}.json', encoding='utf8')):
        R[q['job']].append(dict(q, reader=g))
# OSM crossings of a pair of names, as cufp/fit.py finds them
OL = collections.defaultdict(list)
for fn in ('lph/osm_north.geojson', 'basin/osm_basin.geojson', 'lph/osm_east.geojson', 'lph/osm_norwood.geojson', 'lph/osm_west.geojson'):
    for f in json.load(open(SP + fn))['features']:
        nm = f['properties'].get('name')
        if nm and f['geometry']['type'] == 'LineString':
            g = shape(f['geometry']); OL[key(nm)].append(g); OL['B:' + base(key(nm))].append(g)
U = {k: unary_union(v) for k, v in OL.items()}
src = open(_ws.CODE + 'cufp/fit.py', encoding='utf8').read()
ns = dict(key=key); exec(re.search(r"^ALIAS = \{.*?\}\.items\(\)\}", src, re.S | re.M).group(0), ns); ALIAS = ns['ALIAS']
lines = lambda k: U.get(ALIAS.get(k, k)) or U.get('B:' + base(ALIAS.get(k, k)))


def osm_pts(na, nb):
    la, lb = lines(key(na)), lines(key(nb))
    if la is None or lb is None:
        return []
    x = la.intersection(lb); pts = [g for g in getattr(x, 'geoms', [x]) if g.geom_type == 'Point'] if not x.is_empty else []
    if not pts:
        a, b = nearest_points(la, lb)
        if a.distance(b) < 3: pts = [Point((a.x + b.x) / 2, (a.y + b.y) / 2)]
    return [np.array([p.x, p.y]) for p in pts]


slug = lambda s: re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')
W = {}
rows = []
for job, v in JOBS.items():
    p = v['plate']; W.setdefault(p, S.plate_world(p)); F = W[p]
    reads = R[job]; found = [q for q in reads if q.get('found') and q.get('x') is not None]
    spread = float(np.hypot(found[0]['x'] - found[1]['x'], found[0]['y'] - found[1]['y'])) if len(found) == 2 else None
    new = None
    if len(found) == 2 and spread <= S.DUP_PX:
        new = [float(np.mean([q['x'] for q in found])), float(np.mean([q['y'] for q in found]))]
    elif len(found) == 1:
        new = [float(found[0]['x']), float(found[0]['y'])]
    Po = np.array(F(*v['old'])); O = np.array(v['osm']) if v.get('osm') else None
    others = osm_pts(*v['streets'])
    rec = dict(round=3, job=job, kind=v['kind'], plate=p, crossing=' & '.join(v['streets']), reads=reads,
               two_reads_spread_px=None if spread is None else round(spread, 1),
               old_pick=dict(x=v['old'][0], y=v['old'][1], E=round(float(Po[0]), 2), N=round(float(Po[1]), 2)),
               osm_match=None if O is None else dict(E=float(O[0]), N=float(O[1]), from_old_m=round(float(np.hypot(*(Po - O))), 2)),
               osm_crossings_of_these_names=[dict(E=round(float(c[0]), 1), N=round(float(c[1]), 1)) for c in others])
    if v['kind'] == 'control':
        rec['control_index'] = v['control_index']
    else:
        rec['tie'] = v['tie']
    if new is None:
        cls, why = 'unresolved', 'not found, or the two reads differ by more than 60 px'
    else:
        Pn = np.array(F(*new)); d = float(np.hypot(*(Pn - Po)))
        rec['new_pick'] = dict(x=round(new[0], 1), y=round(new[1], 1), E=round(float(Pn[0]), 2), N=round(float(Pn[1]), 2),
                               moved_px=round(float(np.hypot(new[0] - v['old'][0], new[1] - v['old'][1])), 1), moved_m=round(d, 2))
        dO = None if O is None else float(np.hypot(*(Pn - O)))
        if O is not None:
            rec['osm_match']['from_new_m'] = round(dO, 2)
        for c in rec['osm_crossings_of_these_names']:
            c['from_new_m'] = round(float(np.hypot(Pn[0] - c['E'], Pn[1] - c['N'])), 1)
        better = [c for c in others if (O is None or np.hypot(*(c - O)) > 3) and dO is not None and np.hypot(*(Pn - c)) < dO - 1]
        if better:
            cls, why = 'wrong match', f'another OSM crossing of the same names is {min(np.hypot(*(Pn - c)) for c in better):.1f} m from the new pick, the matched one {dO:.1f} m'
        elif d <= 5:
            cls, why = 'confirmed', f'new pick {d:.1f} m from the old' + ('' if dO is None else f'; {dO:.1f} m from its OSM crossing (old {rec["osm_match"]["from_old_m"]:.1f})')
        else:
            cls, why = 'moved', f'new pick {d:.1f} m from the old (two reads {spread:.0f} px apart)' + ('' if dO is None else f'; {dO:.1f} m from its OSM crossing (old {rec["osm_match"]["from_old_m"]:.1f})')
    rec.update(classification=cls, why=why)
    folder = SP + f'picks22_reread/{p}'; os.makedirs(folder, exist_ok=True)
    fn = f"r3_{job}_{slug(v['streets'][0])}__{slug(v['streets'][1])}.json"
    json.dump(rec, open(f'{folder}/{fn}', 'w', encoding='utf8', newline='\n'), indent=1)
    rows.append(dict(job=job, plate=p, kind=v['kind'], crossing=rec['crossing'], classification=cls, why=why,
                     moved_m=rec.get('new_pick', {}).get('moved_m'), spread_px=rec['two_reads_spread_px'],
                     osm_from_old_m=None if O is None else rec['osm_match']['from_old_m'],
                     osm_from_new_m=None if O is None or new is None else rec['osm_match'].get('from_new_m'),
                     record=f'picks22_reread/{p}/{fn}'))
    print(f"{job:10s} {p:7s} {rec['crossing']:36s} {cls:12s} {why}")
json.dump(rows, open(SP + 'reports/2026-11-06_seams_reread/round3.json', 'w', encoding='utf8', newline='\n'), indent=1)
