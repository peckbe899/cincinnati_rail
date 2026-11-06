try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# APEx out to the region bounds (Ben, 2026-10-15: Erlanger, CVG Terminal 1, Eastgate, Aviation). Run after tracks_gen4.py.
# The APEx Routes.kmz lines inside the region box are drawn as they are, each shared corridor once; where they meet the detailed
# CUT approach tracks they leave from the end of that bundle (a tangent-matched join), and inside the detailed area they are left
# out. Tracks: four on a corridor that two or more Tier 1 routes share (the quad-track bridge's Kentucky trunk, the north trunk
# to the Vandalia/Norwood split) unless it continues a two-track bundle; two elsewhere. Track centres 4.5 m: drawing values.
import json, math, zipfile
import numpy as np
from xml.etree import ElementTree as ET
from pyproj import Transformer
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union, substring
S = _ws.DATA
OUT = S + 'deckpage/tracks.json'
REG = box(699000, 4320800, 736900, 4347000)
T = Transformer.from_crs(4326, 26916, always_xy=True)
NS = '{http://www.opengis.net/kml/2.2}'
TJ = json.load(open(OUT)); TJ['features'] = [f for f in TJ['features'] if f['properties'].get('kind') not in ('region', 'region_station')]
# ---------------------------------------------------------------- KMZ lines in the box
z = zipfile.ZipFile(_ws.ext('/mnt/user-data/uploads/Documents--_Personal--_Cincinnati Rail/APEx Routes.kmz'))
root = ET.fromstring(z.read([n for n in z.namelist() if n.endswith('.kml')][0]))
lines, stations = [], []
def walk(el, path):
    for ch in el:
        tag = ch.tag.replace(NS, '')
        if tag in ('Folder', 'Document'):
            nm = ch.find(NS + 'name'); walk(ch, path + [nm.text if nm is not None else '?'])
        elif tag == 'Placemark':
            nm = ch.find(NS + 'name'); nm = (nm.text or '').strip() if nm is not None else ''
            tier = next((p for p in path if p.startswith('Tier')), ''); grp = path[path.index(tier) + 1] if tier and path.index(tier) + 1 < len(path) else ''
            for l in ch.iter(NS + 'LineString'):
                cs = [T.transform(*map(float, c.split(',')[:2])) for c in l.find(NS + 'coordinates').text.split()]
                g = LineString(cs)
                if len(cs) >= 2 and g.intersects(REG):
                    x = g.intersection(REG)
                    for p in getattr(x, 'geoms', [x]):
                        if p.geom_type == 'LineString' and p.length > 50: lines.append(dict(name=nm, grp=grp, tier=tier, g=p))
            for pt in ch.iter(NS + 'Point'):
                x, y = T.transform(*map(float, pt.find(NS + 'coordinates').text.split(',')[:2]))
                if REG.contains(Point(x, y)) and 'Union Terminal' not in nm and not any(s[0] == nm for s in stations): stations.append((nm, x, y))
walk(root, [])
# ---------------------------------------------------------------- shared corridors once (as the RER pieces in build_transit)
lines.sort(key=lambda o: -o['g'].length)
pieces = []
for o in lines:
    rest = o['g']; tag = (o['tier'], o['grp'])
    for q in list(pieces):
        shared = q['g'].intersection(o['g'].buffer(30))
        if shared.length < 100: continue
        pieces.remove(q)
        for g_, gs in ((shared, q['groups'] | {tag}), (q['g'].difference(o['g'].buffer(30)), q['groups'])):
            for r_ in getattr(g_, 'geoms', [g_]):
                if r_.geom_type == 'LineString' and r_.length > 100: pieces.append(dict(g=r_, groups=set(gs), names=set(q['names']) | ({o['name']} if g_ is shared else set())))
        rest = rest.difference(q['g'].buffer(30))
    for r_ in getattr(rest, 'geoms', [rest]):
        if r_.geom_type == 'LineString' and r_.length > 100: pieces.append(dict(g=r_, groups={tag}, names={o['name']}))
# merge pieces that meet end to end with the same groups (shapely splits leave short breaks)
from shapely.ops import linemerge
merged = {}
for q in pieces: merged.setdefault((frozenset(q['groups'])), []).append(q)
pieces = []
def _snap(gs, tol=6.0):   # pull line ends that nearly meet onto one point, so they merge
    pts = []
    for g in gs:
        for e in (g.coords[0], g.coords[-1]):
            if not any(math.dist(e, p) < tol for p in pts): pts.append(e)
    def sn(e): return min(pts, key=lambda p: math.dist(e, p)) if any(math.dist(e, p) < tol for p in pts) else e
    return [LineString([sn(g.coords[0])] + list(g.coords)[1:-1] + [sn(g.coords[-1])]) for g in gs]
for gs, qs in merged.items():
    m = linemerge(_snap([q['g'] for q in qs]))
    for r_ in getattr(m, 'geoms', [m]):
        if r_.length > 100: pieces.append(dict(g=r_, groups=set(gs), names=set().union(*[q['names'] for q in qs])))
# ---------------------------------------------------------------- the detailed approach tracks: left out inside, joined at their ends
det = [f for f in TJ['features'] if f['properties'].get('layer') == 'apex' and f['properties'].get('kind') != 'cvg' and f['geometry']['type'] == 'LineString']
cover = unary_union([LineString(f['geometry']['coordinates']).buffer(120) for f in det] + [box(712600, 4331500, 712950, 4332300)])   # the KMZ strays up to about 60 m from the designed approaches
CUT = Point(712762, 4331890)
ends = []
for f in det:
    c = f['geometry']['coordinates']
    for i, j in ((0, 1), (-1, -2)):
        q = Point(c[i])
        if q.distance(CUT) > 1200:
            d = np.subtract(c[i], c[j if j > 0 else len(c) + j]); d = d / (np.linalg.norm(d) or 1); ends.append((np.array(c[i]), d))
bundles = []
for p, d in ends:
    for b in bundles:
        if np.linalg.norm(b['p'] - p) < 30: b['pts'].append(p); b['dirs'].append(d); break
    else: bundles.append(dict(p=p, pts=[p], dirs=[d]))
for b in bundles: b['p'] = np.mean(b['pts'], axis=0); b['d'] = np.mean(b['dirs'], axis=0); b['d'] /= np.linalg.norm(b['d']); b['n'] = len(b['pts'])
print('bundles', [(b['p'].round(), b['n']) for b in bundles])
def bez(a, ta, b, tb, k=0.4, n=40):
    a, b, ta, tb = map(np.asarray, (a, b, ta, tb)); L = np.linalg.norm(b - a); c0, c1 = a + ta * k * L, b - tb * k * L
    t = np.linspace(0, 1, n)[:, None]; return [tuple(p) for p in (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * c0 + 3 * (1 - t) * t * t * c1 + t ** 3 * b]
out = []
for q in pieces:
    g = q['g'].difference(cover)
    for r_ in getattr(g, 'geoms', [g]):
        if r_.geom_type != 'LineString' or r_.length < 300: continue
        c = list(r_.coords); bn = None
        for flip in (False, True):
            cc = c[::-1] if flip else c
            for b in bundles:
                if np.linalg.norm(np.array(cc[0]) - b['p']) < 400:
                    L = LineString(cc); s = min(350.0, 0.4 * L.length); pj = L.interpolate(s); pk = L.interpolate(s + 5)
                    tb = np.subtract(pk.coords[0], pj.coords[0]); tb = tb / np.linalg.norm(tb)
                    cc = bez(b['p'], b['d'], pj.coords[0], tb) + list(substring(L, s, L.length).coords)[1:]; bn = b; break
            if bn: c = cc; break
        t1 = sum(1 for t, _ in q['groups'] if t == 'Tier 1')
        n = 4 if t1 >= 2 and not (bn and bn['n'] == 2) else 2
        out.append(dict(c=c, n=n, groups=q['groups'], names=q['names'], joined=bool(bn)))
R = lambda c: [[round(x, 1), round(y, 1)] for x, y in c]
for o in out:
    g = LineString(o['c']).simplify(0.3); offs = [-2.25, 2.25] if o['n'] == 2 else [-6.75, -2.25, 2.25, 6.75]
    route = ', '.join(sorted(g_ for t, g_ in o['groups'] if t == 'Tier 1')) or ', '.join(sorted(g_ for _, g_ in o['groups']))
    for k, d in enumerate(offs):
        h = g.offset_curve(d, quad_segs=8, join_style='round')
        for hh in getattr(h, 'geoms', [h]):
            ky = min(q[1] for q in o['c']) < 4330300 and o['joined']        # the Kentucky trunk from Ludlow: tunnelled through the hills (Ben)
            TJ['features'].append(dict(type='Feature', properties=dict(layer='apex', kind='region', name=f'APEx {route} ({k + 1} of {o["n"]})' + (', tunnel' if ky else ''),
                                       note='APEx Routes.kmz line as drawn (' + ', '.join(sorted(o['names'])) + '); track count and spacing are drawing values' +
                                            ('; in tunnel through the hills from Ludlow (Ben), portals toward Erlanger not set' if ky else ''), **({'state': 'tunnel'} if ky else {})),
                                       geometry=dict(type='LineString', coordinates=R(hh.coords))))
for nm, x, y in stations:
    lab = nm.replace('Cincinnati-', '').replace(' Station', '') + ' (APEx)'
    TJ['features'].append(dict(type='Feature', properties=dict(layer='marker', kind='region_station', name=nm, label=lab, anchor='left' if x > 728000 else 'right'), geometry=dict(type='Point', coordinates=[round(x, 1), round(y, 1)])))
TJ['summary']['region'] = dict(box=[699000, 4320800, 736900, 4347000], apex_pieces=len(out), apex_km=round(sum(LineString(o['c']).length for o in out) / 1000, 1),
                               four_track_km=round(sum(LineString(o['c']).length for o in out if o['n'] == 4) / 1000, 1), stations=[s[0] for s in stations])
json.dump(TJ, open(OUT, 'w'))
for o in out: print(o['n'], 'joined' if o['joined'] else '      ', round(LineString(o['c']).length), sorted(o['groups']), sorted(o['names'])[:4])
print(TJ['summary']['region'])
