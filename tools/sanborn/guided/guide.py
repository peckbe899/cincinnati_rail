"""Guided reading, step 1: every crossing of two differently named streets on today's map that falls on plate N,
projected onto the scan through the plate's current model, with a crop box (randomly offset, so the crop centre does
not give the answer away). usage (from data/sanborn): guide.py N READ SEED [CROPDIR] -> picks22_guided/22-N/guide_READ.json and crops CROPDIR/READ/<id>.jpg (crops are not committed)"""
import sys, os, json, random, numpy as np
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')).replace(os.sep, '/') + '/'
sys.path.insert(0, ROOT + 'tools/sanborn/joint'); sys.path.insert(0, ROOT + 'tools/sanborn'); sys.path.insert(0, ROOT + 'tools/sanborn/sbg')
import _ws, jointlib as J, sb
from names import key
from scipy.interpolate import LinearNDInterpolator
from shapely.geometry import shape, box, Point
from shapely.strtree import STRtree
from PIL import Image; Image.MAX_IMAGE_PIXELS = None
N, READ, SEED = sys.argv[1], sys.argv[2], int(sys.argv[3]); SP = _ws.DATA; OUT = SP + f'picks22_guided/22-{N}/'; CROPS = (sys.argv[4].rstrip('/') + '/') if len(sys.argv) > 4 else OUT + 'crops/'; os.makedirs(OUT, exist_ok=True)
KEEP = {'primary', 'secondary', 'tertiary', 'residential', 'unclassified', 'living_street', 'trunk'}
A = np.load(SP + f'cufp/{N}/png_alpha_s4.npy'); H, W = A.shape[0] * 4, A.shape[1] * 4
gx, gy = np.meshgrid(np.linspace(-300, W + 300, 120), np.linspace(-300, H + 300, 95)); P0 = np.c_[gx.ravel(), gy.ravel()]
Wd = J.world_many(f'22-{N}', P0, 'complete'); inv = LinearNDInterpolator(Wd, P0); B = box(*Wd.min(0), *Wd.max(0))
L, seen = [], set()
for f in ('lph/osm_north.geojson', 'basin/osm_basin.geojson', 'lph/osm_east.geojson', 'lph/osm_norwood.geojson', 'lph/osm_west.geojson'):
    for ft in json.load(open(SP + f, encoding='utf8'))['features']:
        p, g = ft['properties'], ft['geometry']
        if not g or 'Line' not in g['type'] or p.get('highway') not in KEEP or not p.get('name'): continue
        s = shape(g)
        if not s.intersects(B) or s.wkb in seen: continue
        seen.add(s.wkb)
        for l in (s.geoms if s.geom_type.startswith('Multi') else [s]): L.append((p['name'], l))
tree = STRtree([l for _, l in L]); X = []
for i, (na, la) in enumerate(L):
    for j in tree.query(la):
        nb, lb = L[j]
        if j <= i or key(na) == key(nb) or not la.intersects(lb): continue
        it = la.intersection(lb)
        for pt in (it.geoms if hasattr(it, 'geoms') else [it]):
            if pt.geom_type != 'Point': continue
            k = tuple(sorted((key(na), key(nb))))
            if any(k == x['k'] and Point(x['E'], x['N']).distance(pt) < 8 for x in X): continue
            X.append(dict(k=k, a=na, b=nb, E=pt.x, N=pt.y, la=i, lb=j))
def px(E, Nn): return inv(np.array([[E, Nn]]))[0]
def way(l, pt):                       # direction of a street on the plate at the crossing, in words
    t = l.project(pt); a = l.interpolate(max(0, t - 15)); b = l.interpolate(min(l.length, t + 15))
    d = px(b.x, b.y) - px(a.x, a.y); ang = np.degrees(np.arctan2(-d[1], d[0])) % 180
    return 'left-right' if ang < 22.5 or ang >= 157.5 else ('lower-left to upper-right' if ang < 67.5 else ('up-down' if ang < 112.5 else 'upper-left to lower-right'))
rnd = random.Random(SEED); rows = []; os.makedirs(CROPS + READ, exist_ok=True)
for x in X:
    c = px(x['E'], x['N'])
    if np.isnan(c).any() or not (0 <= c[0] < W and 0 <= c[1] < H): continue
    yy, xx = int(c[1]) // 4, int(c[0]) // 4
    if A[max(0, yy - 15):yy + 15, max(0, xx - 15):xx + 15].max() == 0: continue      # more than 60 px off the plate (streets along the plate's edge count: 13 Nov, Mitchell Avenue on plate 80)
    pt = Point(x['E'], x['N'])
    rows.append(dict(id=f'{N}-{len(rows) + 1:03d}', a=x['a'], b=x['b'], E=round(x['E'], 2), N=round(x['N'], 2), pred=[round(float(c[0]), 1), round(float(c[1]), 1)],
                     a_runs=way(L[x['la']][1], pt), b_runs=way(L[x['lb']][1], pt)))
rows.sort(key=lambda r: (r['pred'][0] // 900, r['pred'][1]))
OLD = json.load(open(OUT + f'guide_{READ}.json')) if os.path.exists(OUT + f'guide_{READ}.json') else []     # a guide already written: its crossings keep their ids, only new ones are added
rows = [r for r in rows if not any(np.hypot(r['E'] - o['E'], r['N'] - o['N']) < 8 for o in OLD)]
for i, r in enumerate(rows): r['id'] = f'{N}-{len(OLD) + i + 1:03d}'
for r in rows:
    cx = int(min(max(r['pred'][0] + rnd.uniform(-70, 70), 300), W - 300)); cy = int(min(max(r['pred'][1] + rnd.uniform(-70, 70), 300), H - 300))
    r['box'] = [cx - 300, cy - 300, cx + 300, cy + 300]
    sb.render(f'22-{N}', tuple(r['box']), CROPS + READ + f'/{r["id"]}.jpg')
json.dump(OLD + rows, open(OUT + f'guide_{READ}.json', 'w'), indent=1)
print(N, READ, 'crossings on the plate', len(OLD) + len(rows), 'new', [r['id'] for r in rows])
