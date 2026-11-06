try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Cut the streets at the CUT platform deck and in the fans (arch viaduct, Relief log 10l.19) at the platform deck edges.
# The platform deck is unbroken (Ben, 26 October): the street is cut at both deck edges, nothing passes under.
# West piece keeps the id; the east piece becomes <id>E; the part inside the deck is dropped.
# Uses the live layout geometry where Ben has edited a street ('c'), and rewrites those live entries to the west piece.
# Idempotent: skips any id whose <id>E already exists. Reads/writes deckpage/deck.json, basin.json; layout in/out by argv.
import json, sys
from shapely.geometry import shape, LineString, Point
from shapely.ops import substring
S = _ws.DATA
# street id -> structure it is cut at
CUTS = {'SB0623': 'CUT platform deck', 'S030': 'CUT platform deck', 'SB0775': 'CUT platform deck', 'SB0799': 'CUT platform deck',  # Courtland, Clark, Hopkins, Kenner
        # fans (Ben, 26 October): only the important streets keep going under (W Liberty, Court, Richmond, W 9th)
        'SB0718': 'North arch viaduct', 'SB0962': 'North arch viaduct', 'SB1021': 'North arch viaduct',               # Flint, Wade, Wilstach
        'S031': 'CUT approach viaduct (south)', 'SB0738': 'CUT approach viaduct (south)'}                              # Oehler, Gest
IDS = list(CUTS)
lay_in, lay_out = sys.argv[1], sys.argv[2]
LJ = json.load(open(lay_in)); LD = LJ.get('data', LJ); st = LD['streets']
POLY = {f['properties']['name']: shape(f['geometry']) for f in json.load(open(S + 'deckpage/structures.json'))['features'] if f['properties'].get('name') in set(CUTS.values())}
files = {fn: json.load(open(S + f'deckpage/{fn}.json')) for fn in ('deck', 'basin')}
r = lambda c: [[round(x, 2), round(y, 2)] for x, y in c]
for fn, D in files.items():
    have = {f['properties']['id'] for f in D['features'] if f['properties'].get('layer') == 'street'}
    out = []
    for f in D['features']:
        p = f['properties']; out.append(f)
        if p.get('layer') != 'street' or p['id'] not in IDS or p['id'] + 'E' in have: continue
        live = st.get(p['id']) or {}
        L = LineString(live.get('c') or f['geometry']['coordinates'])
        I = L.intersection(POLY[CUTS[p['id']]])
        pts = [q for g in getattr(I, 'geoms', [I]) for q in g.coords]
        d = [min(L.project(Point(q)) for q in pts), max(L.project(Point(q)) for q in pts)]   # whole span across the structure
        a, m, b = substring(L, 0, d[0]), substring(L, d[0], d[1]), substring(L, d[1], L.length)
        if a.coords[0][0] > b.coords[-1][0]: a, b = b, a     # a = west piece
        f['geometry']['coordinates'] = r(a.coords)
        if live.get('c'): live['c'] = r(a.coords); st[p['id']] = live
        if b.length > 1: out.append({'type': 'Feature', 'properties': dict(p, id=p['id'] + 'E'), 'geometry': {'type': 'LineString', 'coordinates': r(b.coords)}})
        print(fn, p['id'], p.get('name'), 'west %.1f  cut %.1f  east %.1f m' % (a.length, m.length, b.length))
    D['features'] = out
for fn, D in files.items():
    json.dump(D, open(S + f'deckpage/{fn}.json', 'w'), separators=(',', ':'))
json.dump(LD, open(lay_out, 'w'))
