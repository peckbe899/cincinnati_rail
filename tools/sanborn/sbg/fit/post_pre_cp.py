"""Clip the Sanborn-built streets to the basin (outside the deck and the CUT forecourt), cut the blocks, write the page layer."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import json, os, sys, collections, numpy as np
from shapely.geometry import LineString, Polygon, MultiPolygon, shape, mapping, Point
from shapely.ops import unary_union, polygonize
from shapely.strtree import STRtree
HERE = _ws.data_dir(os.path.dirname(os.path.abspath(__file__)))
SP = _ws.DATA
FT = 0.3048
SUFFIX = os.environ.get('SBG_SUFFIX', '')
D = json.load(open(os.path.join(HERE, f'streets_raw{SUFFIX}.json'))); F = D['feats']
deckF = json.load(open(SP + 'deckpage/deck.json'))['features']
deck = [shape(f['geometry']) for f in deckF if f['properties'].get('layer') == 'deck'][0].buffer(0)
old = json.load(open(SP + 'deckpage/basin.json'))['features']
fore = [f for f in old if f['properties'].get('layer') == 'we_forecourt']
foreG = unary_union([shape(f['geometry']) for f in fore]) if fore else Polygon()
oldB = [shape(f['geometry']).buffer(0) for f in old if f['properties'].get('layer') == 'block']
oldU = unary_union(oldB); hull = oldU.convex_hull.buffer(50)
parks = [(shape(f['geometry']).buffer(0), f['properties'].get('name')) for f in old if f['properties'].get('layer') == 'block' and f['properties'].get('type') == 'park']
cut = unary_union([deck, foreG])
EXTRA_PARKS = [(Point(q['E'], q['N']).buffer(3), q['name']) for q in json.load(open(os.path.join(HERE, '..', 'osmchk', 'pick_fix.json'))).get('parks', [])]
# ---------------------------------------------------------------- streets
S = []
for f in F:
    g = LineString(f['coords']).difference(cut)
    for part in getattr(g, 'geoms', [g]):
        if part.is_empty or part.geom_type != 'LineString' or part.length < 6: continue
        S.append(dict(f, geom=part))
# cuts from the OSM check (osmchk/cuts.json): links through 1904 buildings that the picks do not support
CUTS = json.load(open(os.path.join(HERE, '..', 'osmchk', 'cuts.json')))
from shapely.ops import substring
def apply_cuts(S, verbose=True):
    ncut = 0
    for c in CUTS:
        if c['mode'] == 'link': probe = Point(*c['at'])
        else: probe = LineString(c['at']).interpolate(0.5, normalized=True)
        cand = [(s_['geom'].distance(probe), k) for k, s_ in enumerate(S) if s_['name'] == c['name']]
        if not cand or min(cand)[0] > 6:
            if verbose: print('cut not found', c['name'], c['at'])
            continue
        k = min(cand)[1]; g = S[k]['geom']; cs = list(g.coords)
        if c['mode'] == 'link':
            d = g.project(probe); acc_ = 0; seg = len(cs) - 2
            for i in range(len(cs) - 1):
                l_ = Point(cs[i]).distance(Point(cs[i + 1]))
                if acc_ + l_ >= d: seg = i; break
                acc_ += l_
            parts = [cs[:seg + 1], cs[seg + 1:]]
        else:
            d1, d2 = sorted((g.project(Point(*c['at'][0])), g.project(Point(*c['at'][1]))))
            parts = [list(substring(g, 0, d1).coords) if d1 > 0.5 else [], list(substring(g, d2, g.length).coords) if d2 < g.length - 0.5 else []]
        new = [dict(S[k], geom=LineString(q)) for q in parts if len(q) >= 2 and LineString(q).length >= 6]
        S = S[:k] + new + S[k + 1:]; ncut += 1
    if verbose: print('cuts applied', ncut, 'of', len(CUTS))
    return S
S = apply_cuts(S)
# ---------------------------------------------------------------- streets that follow OSM (Ben, 2026-10-11): Central Parkway, Eggleston Ave (with Lockport), Reading Rd
sys.path.insert(0, _ws.code_dir(HERE))
from osmfollow import ways as _ways, centreline as _centreline, bridge as _bridge
_OSMP = SP + 'basin/osm_basin.geojson'
HULL = unary_union(oldB).convex_hull.buffer(20)
FOLLOW = [
    dict(id='parkway', osm={'Central Parkway', 'West Central Parkway', 'East Central Parkway'}, replace=lambda n: 'central parkway' in n.lower(),
         absorb={'West Plum Street', 'East Plum Street'}, width=150.0, extent='hull', bridge=True),
    dict(id='reading', osm={'Reading Road'}, replace=lambda n: n == 'Reading Road', extent='old'),
    dict(id='eggleston', osm={'Eggleston Avenue'}, replace=lambda n: n in ('Eggleston Avenue', 'Lockport Avenue'), extent='old'),
]
NEWLINES = []
def follow_osm(S, verbose=True):
    for fo in FOLLOW:
        old = [x for x in S if fo['replace'](x['name'])]
        W = _ways(_OSMP, fo['osm']); OT = STRtree([g for _, g in W])
        new = []
        CL = [g for g, _, _, _ in _centreline(W)]
        if fo.get('bridge'):
            n0 = len(CL); CL = _bridge(CL)
            if verbose: print('follow', fo['id'], 'centreline pieces joined across turns', n0, '->', len(CL))
        for g in CL:
            nm = sorted(fo['osm'])[0]
            if fo['extent'] == 'old':
                near = [x for x in old if x['geom'].distance(g) < 60]
                if not near: continue
                ds = [g.project(Point(c)) for x in near for c in x['geom'].coords]
                d0, d1 = max(0, min(ds) - 5), min(g.length, max(ds) + 5)
                if d1 - d0 < 10: continue
                g = substring(g, d0, d1)
            else:
                g = g.intersection(HULL).difference(deck)
            for part in getattr(g, 'geoms', [g]):
                if part.geom_type != 'LineString' or part.length < 30: continue
                n_ = max(1, int(part.length // 15)); segs = []
                for i in range(n_):
                    sg = substring(part, part.length * i / n_, part.length * (i + 1) / n_); m = sg.interpolate(0.5, normalized=True)
                    if fo.get('width'):
                        j = int(OT.nearest(m)); nm2 = W[j][0]; ft = fo['width']; how = 'printed'; sh = []
                    else:
                        cand = sorted(((x['geom'].distance(m), k) for k, x in enumerate(old)), key=lambda t: t[0])
                        if cand and cand[0][0] < 45: x = old[cand[0][1]]; nm2, ft, how, sh = x['name'], x['ft'], x['how'], x['sheets']
                        else: nm2, ft, how, sh = nm, float(np.median([x['ft'] for x in old])) if old else 40.0, 'default', []
                    segs.append((sg, nm2, ft, how, sh))
                cur = None
                for sg, nm2, ft, how, sh in segs:
                    if cur and cur[1] == nm2 and cur[2] == ft: cur[0].extend(list(sg.coords)[1:])
                    else:
                        if cur: new.append(cur)
                        cur = [list(sg.coords), nm2, ft, how, sh]
                if cur: new.append(cur)
        if not new:
            if verbose: print('follow', fo['id'], 'no OSM line found'); continue
        newg = unary_union([LineString(c) for c, *_ in new])
        S = [x for x in S if not fo['replace'](x['name'])]
        if fo.get('absorb'):
            band = newg.buffer(fo['width'] * FT / 2 + 6)
            keep = []
            for x in S:
                if x['name'] in fo['absorb'] and x['geom'].intersection(band).length > 0.6 * x['geom'].length: continue
                if x['name'] in fo['absorb']:
                    rest = x['geom'].difference(band)
                    for q in getattr(rest, 'geoms', [rest]):
                        if q.geom_type == 'LineString' and q.length >= 8: keep.append(dict(x, geom=q))
                    continue
                keep.append(x)
            S = keep
        for c, nm2, ft, how, sh in new:
            S.append(dict(key=nm2.lower(), name=nm2, coords=c, ft=float(ft), how=how, kind='we_street', sheets=sh, geom=LineString(c), geom_src='OSM centreline (Ben: follow OSM)'))
            if verbose: NEWLINES.append(LineString(c))
        if verbose: print('follow', fo['id'], 'replaced', len(old), 'pieces with', len(new))
    return S
S = follow_osm(S)
# streets that ended on a replaced line: move their ends onto the new centreline
_NL = unary_union(NEWLINES); _nmoved = 0
for x in S:
    if x.get('geom_src', '').startswith('OSM centreline'): continue
    cs = list(x['geom'].coords)
    for e_ in (0, -1):
        p = np.array(cs[e_]); q = np.array(cs[1 if e_ == 0 else -2])
        if _NL.distance(Point(p)) > 25 or np.hypot(*(p - q)) < 1: continue
        d = (p - q) / np.hypot(*(p - q)); ray = LineString([q, p + d * 30])
        xx = _NL.intersection(ray)
        pts = [xx] if xx.geom_type == 'Point' else [t for t in getattr(xx, 'geoms', []) if t.geom_type == 'Point']
        if not pts: continue
        best = min(pts, key=lambda t: Point(p).distance(t))
        if Point(p).distance(best) < 25 and Point(q).distance(best) > 2: cs[e_] = (best.x + d[0] * 0.3, best.y + d[1] * 0.3); _nmoved += 1
    x['geom'] = LineString(cs)
print('ends moved onto the OSM-following streets', _nmoved)

# remove parallel duplicates (same street read under two names, or a jog piece also read under the plain name)
S.sort(key=lambda s: -s['geom'].length)
from shapely.strtree import STRtree
def ang(a, b):
    # angle between piece a and the stretch of b alongside it (local direction, so a bent b still counts as parallel)
    ca = np.array(a.coords); va = ca[-1] - ca[0]; va = va / (np.hypot(*va) + 1e-9)
    m = a.interpolate(0.5, normalized=True); t = b.project(m)
    p0 = np.array(b.interpolate(max(0, t - 6)).coords[0]); p1 = np.array(b.interpolate(min(b.length, t + 6)).coords[0])
    vb = p1 - p0; vb = vb / (np.hypot(*vb) + 1e-9)
    return np.degrees(np.arccos(min(1, abs(va @ vb))))
def axis_dev(g, q):
    # how far the overlap q turns from g's own heading around it (a jog link turns, a street's body does not)
    t0, t1 = sorted((g.project(Point(q.coords[0])), g.project(Point(q.coords[-1]))))
    a = np.array(g.interpolate(max(0, t0 - 40)).coords[0]); b = np.array(g.interpolate(min(g.length, t1 + 40)).coords[0])
    cq = np.array(q.coords); vq = cq[-1] - cq[0]; va = b - a
    if np.hypot(*va) < 1e-6 or np.hypot(*vq) < 1e-6: return 0.0
    return float(np.degrees(np.arccos(min(1, abs(va @ vq) / (np.hypot(*va) * np.hypot(*vq))))))
# where two pieces run on top of each other: a jog link of one street lying along another street is cut from the jogging
# street; one street read twice keeps the longer reading
_T = STRtree([x['geom'] for x in S]); CUT = collections.defaultdict(list)
for i, x in enumerate(S):
    for j in _T.query(x['geom'].buffer(5)):
        j = int(j)
        if j <= i: continue
        g, h = x['geom'], S[j]['geom']
        ov = g.intersection(h.buffer(4, cap_style=2))
        parts = [q for q in getattr(ov, 'geoms', [ov]) if q.geom_type == 'LineString' and q.length > 12 and ang(q, h) < 12]
        if not parts: continue
        ov2 = h.intersection(g.buffer(4, cap_style=2))
        parts2 = [q for q in getattr(ov2, 'geoms', [ov2]) if q.geom_type == 'LineString' and q.length > 12]
        dg = max(axis_dev(g, q) for q in parts); dh = max((axis_dev(h, q) for q in parts2), default=0)
        if dg > 25 >= dh: CUT[i] += parts            # the overlap is g's jog link lying along h
        elif dh > 25 >= dg: CUT[j] += parts2         # the overlap is h's jog link lying along g
        else: CUT[i if g.length <= h.length else j] += (parts if g.length <= h.length else parts2)   # one street read twice: the shorter goes
acc = []
for i, x in enumerate(S):
    g = x['geom']
    if CUT[i]: g = g.difference(unary_union([q.buffer(0.3, cap_style=2) for q in CUT[i]]))
    for part in getattr(g, 'geoms', [g]):
        if part.geom_type == 'LineString' and part.length >= 12: acc.append(dict(x, geom=part))
print('street pieces', len(S), '->', len(acc), 'after duplicate removal; from', len(F))
S = acc
# ---------------------------------------------------------------- blocks
FL = follow_osm(apply_cuts([dict(name=f['name'], kind=f['kind'], ft=f['ft'], how=f['how'], sheets=f['sheets'], geom=LineString(f['coords'])) for f in F], verbose=False), verbose=False)
lines = [s['geom'] for s in S if s['kind'] == 'we_street'] + [f['geom'] for f in FL if f['kind'] == 'we_street']
net = unary_union(lines)
faces = [p for p in polygonize(net) if p.area > 80]
print('faces', len(faces))
bands = unary_union([s['geom'].buffer(max(s['ft'] * FT, 2.5) / 2, cap_style=2, join_style=2, mitre_limit=3) for s in S])
blocks = []
for p in faces:
    if p.intersection(deck).area > 0.5 * p.area: continue
    inside = hull.contains(p.representative_point())
    cov = p.intersection(oldU).area / p.area if inside else None
    if inside and cov < 0.30 and not any(p.intersects(pg) for pg, _ in EXTRA_PARKS): continue
    if not inside and p.area > 25000: continue
    q = p.difference(bands).difference(cut)
    for part in getattr(q, 'geoms', [q]):
        if part.geom_type != 'Polygon' or part.area < 120: continue
        if part.buffer(-2.0).is_empty: continue
        part = part.simplify(0.25, preserve_topology=True)
        typ, name = 'building', ''
        for pg, nm in parks:
            if part.intersection(pg).area > 0.5 * part.area: typ, name = 'park', nm
        for pg, nm in EXTRA_PARKS:
            if part.intersects(pg): typ, name = 'park', nm
        blocks.append(dict(geom=part, type=typ, name=name))
print('blocks', len(blocks), collections.Counter(b['type'] for b in blocks))
# ---------------------------------------------------------------- write
def r1(c): return [round(c[0], 1), round(c[1], 1)]
out = []
for i, s in enumerate(sorted(S, key=lambda s: (s['kind'], s['name']))):
    w = s['ft'] * FT
    out.append(dict(type='Feature', properties=dict(layer='street', id=f'SB{i + 1:04d}', name=s['name'], kind=s['kind'], width_m=round(w, 2), width_ft=s['ft'],
                    width_src=s['how'], side='', src='Sanborn 1904', sheets=', '.join(map(str, s['sheets'])), geom_src=s.get('geom_src', 'Sanborn intersections'), **({'check': s['check']} if s.get('check') else {})),
                    geometry=dict(type='LineString', coordinates=[r1(c) for c in s['geom'].coords])))
for i, b in enumerate(blocks):
    g = b['geom']
    out.append(dict(type='Feature', properties=dict(layer='block', id=f'SBB{i + 1:04d}', type=b['type'], area_m2=int(round(g.area)), name=b['name'], src='Sanborn 1904'),
                    geometry=dict(type='Polygon', coordinates=[[r1(c) for c in g.exterior.coords]] + [[r1(c) for c in h.coords] for h in g.interiors])))
for f in fore:
    f = json.loads(json.dumps(f)); f['properties']['src'] = 'Sanborn 1904'; out.append(f)
fc = dict(type='FeatureCollection', crs='EPSG:26916',
          source='1904 Sanborn atlas (vols. 1-3), 154 sheets georeferenced in one joint fit on street intersections; streets as straight runs between the picked intersections at the printed widths; blocks cut from the spaces between the streets',
          features=out)
json.dump(fc, open(os.path.join(HERE, f'basin_sanborn{SUFFIX}.json'), 'w'), separators=(',', ':'))
L = sum(s['geom'].length for s in S)
print('wrote', len(out), 'features; street length %.1f km' % (L / 1000), 'named streets', len({s['name'] for s in S if s['name']}))
