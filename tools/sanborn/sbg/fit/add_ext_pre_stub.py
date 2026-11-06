try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
# Ben (18 October): streets and blocks for newly georeferenced 1904 sheets, added to the page's basin layer without renumbering
# anything already there. Streets come from a build.py run that includes the new frames (streets_raw<SUFFIX>.json); only pieces on
# the new sheets that the basin layer does not already have are kept. A street that continues from the existing layer is joined
# to it exactly: its end is moved onto the existing street of the same name (or, failing that, onto the street it meets).
# Blocks: faces of the joined network on the new sheets, minus the street bands and the existing blocks.
#   python3 add_ext.py SUFFIX SET PREFIX SHEETS [--install]
import json, sys, os, collections, numpy as np
from shapely.geometry import LineString, Point, Polygon, shape, mapping
from shapely.ops import unary_union, polygonize, nearest_points, substring
from shapely.strtree import STRtree
HERE = _ws.data_dir(os.path.dirname(os.path.abspath(__file__))); SP = _ws.DATA
sys.path.insert(0, _ws.code_dir(os.path.dirname(HERE))); from names import key2
FT = 0.3048
SUFFIX, SET, PREFIX = sys.argv[1], sys.argv[2], sys.argv[3]
NEW = {s.strip() for s in sys.argv[4].split(',')}
INSTALL = '--install' in sys.argv
import re
_re = re.compile(r'^(west|east|north|south) ')
def base(n): k = key2(n) or ''; return _re.sub('', k.split(' | ')[0])
F = json.load(open(os.path.join(HERE, f'streets_raw{SUFFIX}.json')))['feats']
BJ = json.load(open(SP + 'deckpage/basin.json'))
SH = json.load(open(SP + 'deckpage/sheets.json'))
deck = [shape(f['geometry']) for f in json.load(open(SP + 'deckpage/deck.json'))['features'] if f['properties'].get('layer') == 'deck'][0].buffer(0)
NEWCOV = unary_union([Polygon(e['poly']) for e in SH if e['sheet'] in NEW and '1904' in e['vol']]).buffer(0)
OLDS = [f for f in BJ['features'] if f['properties']['layer'] == 'street' and f['properties'].get('set') != SET]      # a reinstall replaces its own set
OLDG = [LineString(f['geometry']['coordinates']) for f in OLDS]
OLDB = unary_union([shape(f['geometry']).buffer(0) for f in BJ['features'] if f['properties']['layer'] == 'block' and f['properties'].get('set') != SET])
OT = STRtree(OLDG)
oldbase = [base(f['properties']['name']) if f['properties']['name'] else None for f in OLDS]
# ---------------------------------------------------------------- new pieces
def ang(a, b):
    ca = np.array(a.coords); va = ca[-1] - ca[0]; va = va / (np.hypot(*va) + 1e-9)
    m = a.interpolate(0.5, normalized=True); t = b.project(m)
    p0 = np.array(b.interpolate(max(0, t - 6)).coords[0]); p1 = np.array(b.interpolate(min(b.length, t + 6)).coords[0]); vb = p1 - p0; vb = vb / (np.hypot(*vb) + 1e-9)
    return np.degrees(np.arccos(min(1, abs(va @ vb))))
pieces = []
def fixname(n):      # a street known only from ends and bends comes out of build.py under its bare key ('section'): spell it out
    if n and (n[0].isdigit() or n.lower().startswith('unnamed')): return ''      # descriptive alley labels ('10 ft alley', 'unnamed alley (...)') are unnamed
    if n and n == n.lower(): n = n.title() + ('' if any(n.endswith(x) for x in (' street', ' avenue', ' alley', ' place', ' road')) else ' Street')
    return n
for f in F:
    f = dict(f, name=fixname(f['name']))
    if not ({str(s) for s in f['sheets']} & NEW): continue
    g = LineString(f['coords']).difference(deck)
    bk = base(f['name']) if f['name'] else None
    near = [int(j) for j in OT.query(g.buffer(8))]
    same = [OLDG[j] for j in near if bk and oldbase[j] == bk]
    if same: g = g.difference(unary_union(same).buffer(6, cap_style=2))
    for part in getattr(g, 'geoms', [g]):
        if part.is_empty or part.geom_type != 'LineString' or part.length < 10: continue
        # an unnamed or differently named reading of a street already drawn: dropped where it runs along it
        alongs = [OLDG[j] for j in OT.query(part.buffer(6)) if OLDG[int(j)].distance(part) < 6]
        if alongs:
            ov = part.intersection(unary_union([a.buffer(6, cap_style=2) for a in alongs])).length
            if ov > 0.6 * part.length and any(ang(part, a) < 15 for a in alongs): continue
        if not NEWCOV.buffer(30).intersects(part): continue
        pieces.append(dict(f, geom=part, bk=bk))
# ---------------------------------------------------------------- join continuing streets
njoin = nT = 0
for p in pieces:
    cs = list(p['geom'].coords)
    for e in (0, -1):
        q = Point(cs[e]); inner = Point(cs[1 if e == 0 else -2])
        cand = [(OLDG[int(j)].distance(q), int(j)) for j in OT.query(q.buffer(14))]
        cand = [c for c in cand if c[0] < 14]
        if not cand: continue
        same = [c for c in cand if p['bk'] and oldbase[c[1]] == p['bk']]
        if same:
            d, j = min(same); og = OLDG[j]
            # onto the existing street's nearer end if close, else onto its line
            ends = [Point(og.coords[0]), Point(og.coords[-1])]; de = [q.distance(t) for t in ends]
            t = ends[int(np.argmin(de))] if min(de) < 14 else nearest_points(og, q)[0]
            cs[e] = (t.x, t.y); njoin += 1
        else:
            d, j = min(cand)
            if d < 8:
                t = nearest_points(OLDG[j], q)[0]
                if t.distance(inner) > 2: cs[e] = (t.x, t.y); nT += 1
    p['geom'] = LineString(cs)
# second pass: an end left loose within 15 m of any street (new pieces included) is a T-junction the picks fell short of
nT2 = 0
for i, p in enumerate(pieces):
    cs = list(p['geom'].coords)
    others = [q['geom'] for k, q in enumerate(pieces) if k != i]
    for e in (0, -1):
        q = Point(cs[e]); inner = Point(cs[1 if e == 0 else -2])
        cand = [(g.distance(q), g) for g in others + [OLDG[int(j)] for j in OT.query(q.buffer(15))] if g.distance(q) < 15]
        if not cand or min(c[0] for c in cand) < 1.0: continue
        d, g = min(cand, key=lambda c: c[0])
        t = nearest_points(g, q)[0]
        if t.distance(inner) > 2: cs[e] = (t.x, t.y); nT2 += 1
    p['geom'] = LineString(cs)
print('new street pieces', len(pieces), 'joined to the same street', njoin, 'ends snapped onto a crossing street', nT, '+', nT2)
# ---------------------------------------------------------------- blocks
region = NEWCOV.buffer(10)
loc = [g for g, f in zip(OLDG, OLDS) if g.intersects(region.buffer(400))]
locw = [g for g, f in zip(OLDG, OLDS) if g.intersects(region.buffer(400)) and f['properties']['kind'] not in ('we_alley',) and 'alley' not in (f['properties'].get('kind') or '')]
net = unary_union(locw + [p['geom'] for p in pieces if p['kind'] == 'we_street'])
faces = [q for q in polygonize(net) if q.area > 80]
bands = unary_union([LineString(f['geometry']['coordinates']).buffer(max(f['properties']['width_m'], 2.5) / 2, cap_style=2, join_style=2, mitre_limit=3) for f in OLDS if LineString(f['geometry']['coordinates']).intersects(region.buffer(400))]
                    + [p['geom'].buffer(max(p['ft'] * FT, 2.5) / 2, cap_style=2, join_style=2, mitre_limit=3) for p in pieces])
blocks = []
for q in faces:
    if not NEWCOV.contains(q.representative_point()): continue
    if q.area > 25000: continue
    if q.intersection(OLDB).area > 0.3 * q.area: continue
    r = q.difference(bands).difference(OLDB).difference(deck)
    for part in getattr(r, 'geoms', [r]):
        if part.geom_type != 'Polygon' or part.area < 120 or part.buffer(-2.0).is_empty: continue
        blocks.append(part.simplify(0.25, preserve_topology=True))
print('faces', len(faces), 'new blocks', len(blocks))
# ---------------------------------------------------------------- write
def r1(c): return [round(c[0], 1), round(c[1], 1)]
out = []
for i, p in enumerate(sorted(pieces, key=lambda p: (p['kind'], p['name']))):
    w = p['ft'] * FT
    out.append(dict(type='Feature', properties=dict(layer='street', id=f'{PREFIX}{i + 1:04d}', name=p['name'], kind=p['kind'], width_m=round(w, 2), width_ft=p['ft'], width_src=p['how'], side='',
                    src='Sanborn 1904', sheets=', '.join(map(str, p['sheets'])), geom_src='Sanborn intersections', set=SET), geometry=dict(type='LineString', coordinates=[r1(c) for c in p['geom'].coords])))
for i, b in enumerate(blocks):
    out.append(dict(type='Feature', properties=dict(layer='block', id=f'{PREFIX}B{i + 1:04d}', type='building', area_m2=int(round(b.area)), name='', src='Sanborn 1904', set=SET),
                    geometry=dict(type='Polygon', coordinates=[[r1(c) for c in b.exterior.coords]] + [[r1(c) for c in h.coords] for h in b.interiors])))
json.dump(dict(type='FeatureCollection', features=out), open(os.path.join(HERE, f'ext_{SET}.json'), 'w'))
print('wrote', len(out), 'features to', f'ext_{SET}.json', '; named streets:', sorted({p['name'] for p in pieces if p['name']}))
if INSTALL:
    BJ['features'] = [f for f in BJ['features'] if f['properties'].get('set') != SET] + out
    json.dump(BJ, open(SP + 'deckpage/basin.json', 'w'), separators=(',', ':'))
    print('installed into deckpage/basin.json')
