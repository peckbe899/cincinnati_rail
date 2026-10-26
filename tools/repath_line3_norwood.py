"""Line 3's Norwood end onto the Deck's Metro 3 route (Ben, Deck Version 111: terminus at Norwood
frame s 4,585-4,707, o +38, beside the north edge of the track field; ruling of 2026-10-26).

Applied on 2026-10-26: the first 783.1 m follow the Deck route (data/deck/context.json piece
M-L3-720291-4337966), which replaced 924.0 m of the old path, so every chainage past the rejoin
moved by -140.9 m (line 25,245.0 m; Norwood Central at c 60.6). Re-sampled ground, recomputed
crossings on the new piece, shifted crossings everywhere else, plan networks and rails table.
The saved profile (data/profile/alignments/Line_3.json) was shifted in the page database and
exported. This script records the method; it refuses to run again on the re-pathed line.

    python tools/repath_line3_norwood.py
"""
# --- shared helpers (paths, projections, chainage on a Profiles line path, the map 3 ground) ---
import json, math, sys
from pathlib import Path
import numpy as np
from pyproj import Transformer
from shapely.geometry import LineString, Point
import rasterio
from rasterio.windows import Window
ROOT = Path(__file__).resolve().parent.parent
SITE, DECK = str(ROOT / "data" / "profile"), str(ROOT / "data" / "deck")
ORIG = SITE
VRT = str(ROOT / "data" / "profile" / "dem" / "map3_profile_dem_dm.vrt")
TO_UTM = Transformer.from_crs(4326, 26916, always_xy=True)
TO_LL = Transformer.from_crs(26916, 4326, always_xy=True)
def jload(p): return json.load(open(p, encoding='utf8'))
def jsave(p, d, indent=None):
    with open(p, 'w', encoding='utf8') as f: json.dump(d, f, ensure_ascii=False, indent=indent, separators=(',', ':') if indent is None else None)
class Path:
    """A Profiles line path: vertices [c, lon, lat] -> UTM polyline with chainage mapping."""
    def __init__(self, path):
        self.cv = np.array([p[0] for p in path], float)
        self.xy = np.array([TO_UTM.transform(p[1], p[2]) for p in path])
        self.L = LineString(self.xy)
        seg = np.hypot(*np.diff(self.xy, axis=0).T); self.dv = np.concatenate([[0], np.cumsum(seg)])
    def c_of_d(self, d): return float(np.interp(d, self.dv, self.cv))
    def d_of_c(self, c): return float(np.interp(c, self.cv, self.dv))
    def chain(self, pt): return self.c_of_d(self.L.project(Point(pt)))
    def at(self, c): p = self.L.interpolate(self.d_of_c(c)); return (p.x, p.y)

_ds = rasterio.open(VRT)
def sample(xy, mode='bilinear'):
    """xy: array (n,2) UTM 16N (EPSG:26916). Returns metres (NaN for nodata)."""
    xy = np.asarray(xy, float)
    col = (xy[:, 0] - 695000.0) / 2.0 - 0.5; row = (4350000.0 - xy[:, 1]) / 2.0 - 0.5
    c0, r0 = int(np.floor(col.min())) - 2, int(np.floor(row.min())) - 2
    c1, r1 = int(np.ceil(col.max())) + 3, int(np.ceil(row.max())) + 3
    a = _ds.read(1, window=Window(c0, r0, c1 - c0, r1 - r0)).astype(float)
    a[a == -32768] = np.nan
    cc, rr = col - c0, row - r0
    if mode == 'nearest':
        return a[np.round(rr).astype(int), np.round(cc).astype(int)] / 10
    i, j = np.floor(rr).astype(int), np.floor(cc).astype(int); fr, fc = rr - i, cc - j
    v = (a[i, j] * (1 - fr) * (1 - fc) + a[i, j + 1] * (1 - fr) * fc + a[i + 1, j] * fr * (1 - fc) + a[i + 1, j + 1] * fr * fc)
    return v / 10

import glob, copy

_cur = jload(SITE + '/lines/Line_3.json')
_start = TO_UTM.transform(_cur['path'][0][1], _cur['path'][0][2])
_deck0 = [x for x in jload(DECK + '/context.json')['metro'] if x['id'] == 'M-L3-720291-4337966'][0]['c'][0]
if math.dist(_start, _deck0) < 1.0:
    sys.exit('Line 3 already starts on the Deck route; nothing to do')
ctx = jload(DECK + '/context.json')
piece = [x for x in ctx['metro'] if x['id'] == 'M-L3-720291-4337966'][0]['c']   # Deck route, terminus end first
L3 = jload(ORIG + '/lines/Line_3.json'); P = Path(L3['path'])
# rejoin: the first Deck vertex past 600 m that lies within 0.5 m of the Profiles path
acc, k_join = 0, None
for i in range(1, len(piece)):
    acc += math.dist(piece[i], piece[i - 1])
    if acc > 600 and P.L.distance(Point(piece[i])) < 0.5: k_join = i; break
new_xy = [tuple(q) for q in piece[:k_join + 1]]
d_new = sum(math.dist(new_xy[i], new_xy[i - 1]) for i in range(1, len(new_xy)))
c_join_old = P.chain(new_xy[-1])
DELTA = d_new - c_join_old
print(f'rejoin at Deck vertex {k_join}, new {d_new:.1f} m vs old {c_join_old:.1f} m: shift {DELTA:+.1f} m')
# new path vertices [c, lon, lat]
path = []; c = 0.0
for i, q in enumerate(new_xy):
    if i: c += math.dist(q, new_xy[i - 1])
    lon, lat = TO_LL.transform(*q); path.append([round(c, 1), round(lon, 7), round(lat, 7)])
for p in L3['path']:
    if p[0] > c_join_old + 0.05: path.append([round(p[0] + DELTA, 1), p[1], p[2]])
Lnew = round(L3['length_m'] + DELTA, 1)
NP = Path(path)
n = math.ceil(Lnew / L3['step_m']) + 1
cs = np.minimum(np.arange(n) * L3['step_m'], Lnew)
xy = np.array([NP.at(c) for c in cs])
g = sample(xy)
L3n = copy.deepcopy(L3)
L3n['path'] = path; L3n['length_m'] = Lnew
L3n['ground_dm'] = [None if not np.isfinite(v) else int(round(v * 10)) for v in g]
old_l = np.array([np.nan if v is None else v for v in L3['ground_dm_lidar']], float)
old_c = np.arange(len(old_l)) * L3['step_m']
lid = []
for i, c in enumerate(cs):
    if c >= d_new: v = np.interp(c - DELTA, old_c, old_l); lid.append(None if not np.isfinite(v) else int(round(v)))
    else: lid.append(L3n['ground_dm'][i])
L3n['ground_dm_lidar'] = lid
L3n['ground_note'] = L3['ground_note'] + f'; Norwood end re-pathed onto the Deck Metro 3 route (Ben, Version 111) for the first {d_new:.0f} m (2026-10-26), sampled from the same raster (ground_dm_lidar there repeats it)'
# stations: Norwood Central at the Deck's station point (Ben's terminus), the rest shifted
ptN = (720123.0, 4338042.0)
for s in L3n['stations']:
    if s['name'] == 'Norwood Central':
        c = NP.chain(ptN); x, y = NP.at(c); lon, lat = TO_LL.transform(x, y)
        s.update(c=round(c, 1), lon=round(lon, 7), lat=round(lat, 7), ground=round(float(sample([[x, y]])[0]), 2))
    else: s['c'] = round(s['c'] + DELTA, 1)
for r in L3n['rivers']: r['c0'] = round(r['c0'] + DELTA, 1); r['c1'] = round(r['c1'] + DELTA, 1)
for i, pc in enumerate(L3n['pieces']):
    if i: pc['c0'] = round(pc['c0'] + DELTA, 1)
    pc['c1'] = round(pc['c1'] + DELTA, 1)
# crossings: keep and shift those past the rejoin; find the new piece's crossings with every other line
newpiece = LineString(new_xy)
keep = [dict(x, c=round(x['c'] + DELTA, 1)) for x in L3['crossings'] if x['c'] > c_join_old]
added = []
files = sorted(glob.glob(ORIG + '/lines/*_*.json')) + sorted(glob.glob(ORIG + '/rer/lines/RER_*.json'))
out_files = {}
for fn in files:
    d = jload(fn)
    if d['id'] == 'Line_3': continue
    OP = Path(d['path']); rer = d['id'].startswith('RER_'); changed = False
    xs = []
    for x in d.get('crossings', []):
        if x.get('wid') == 'Line_3':
            changed = True
            if x['oc'] > c_join_old: xs.append(dict(x, oc=round(x['oc'] + DELTA, 1)))
            continue   # crossings on the replaced piece are recomputed below
        xs.append(x)
    hit = OP.L.intersection(newpiece)
    for p in getattr(hit, 'geoms', [hit]):
        if p.is_empty or p.geom_type != 'Point': continue
        c3, co = NP.chain((p.x, p.y)), OP.chain((p.x, p.y)); changed = True
        xs.append({'c': round(co, 1), 'wid': 'Line_3', 'oc': round(c3, 1), 'kind': 'metro', 'with': 'Line 3'})
        added.append({'c': round(c3, 1), 'wid': None if rer else d['id'], 'oc': None if rer else round(co, 1), 'kind': 'rer' if rer else 'metro', 'with': d['line']})
    if changed:
        d['crossings'] = sorted(xs, key=lambda x: x['c']); out_files[fn.replace(ORIG, SITE)] = d
for a in added:
    if a['kind'] == 'rer': a.pop('wid'); a.pop('oc')
L3n['crossings'] = sorted(keep + added, key=lambda x: x['c'])
print('new crossings on the re-pathed piece:', added)
out_files[SITE + '/lines/Line_3.json'] = L3n
for p, d in out_files.items(): jsave(p, d)
# index, plan networks, rails table
idx = jload(ORIG + '/lines/index.json')
for e in idx:
    if e['id'] == 'Line_3': e['length_m'] = Lnew
jsave(SITE + '/lines/index.json', idx)
for nf in ('/network.json', '/rer/network.json'):
    net = jload(ORIG + nf); pts = net['metro']['Line_3']
    rest = [q for q in pts if P.chain(TO_UTM.transform(*q)) > c_join_old + 1]
    head = [[round(v, 5) for v in TO_LL.transform(*q)] for q in LineString(new_xy).simplify(1.0).coords]
    net['metro']['Line_3'] = head + rest; jsave(SITE + nf, net)
mr = jload(ORIG + '/rer/metro_rails.json'); r3 = mr['Line_3']; r3['length_m'] = Lnew
cN = [s for s in L3n['stations'] if s['name'] == 'Norwood Central'][0]['c']
for s in r3['stations']: s['c'] = cN if s['name'] == 'Norwood Central' else round(s['c'] + DELTA, 1)
jsave(SITE + '/rer/metro_rails.json', mr)
print('shift',  {'delta': round(DELTA, 1), 'c_join_old': round(c_join_old, 1), 'c_join_new': round(d_new, 1), 'norwood_c': cN, 'length_m': Lnew})
print('Norwood Central now at c', cN, 'length', Lnew)
