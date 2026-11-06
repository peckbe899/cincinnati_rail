try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import sys, json, numpy as np
from shapely.geometry import LineString, Point, shape
from scipy.spatial import cKDTree
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'trunk3'); sys.path.insert(0, _ws.CODE + 'trunk2')
import build as B, north as N
from creek_up import WAT_UP as WAT
opt = sys.argv[1] if len(sys.argv) > 1 else 'B'
L = B.build(opt); FR = N.FR
def resamp(c, step):
    c = np.asarray(c); d = np.r_[0, np.cumsum(np.hypot(*np.diff(c, axis=0).T))]; t = np.arange(0, d[-1], step); return np.c_[np.interp(t, d, c[:, 0]), np.interp(t, d, c[:, 1])]
def radii(c, chord=30.0):
    p = resamp(c, chord / 2); a, b, cc = p[:-2], p[1:-1], p[2:]
    ab = np.hypot(*(b - a).T); bc = np.hypot(*(cc - b).T); ac = np.hypot(*(cc - a).T)
    cr = np.abs((b - a)[:, 0] * (cc - a)[:, 1] - (b - a)[:, 1] * (cc - a)[:, 0]); return b, ab * bc * ac / (2 * cr + 1e-12)
print('== minimum radius (30 m chord) per line, and stretches under 1,500 m')
for k, v in L.items():
    if k.startswith('_') or v['kind'] == 'ref': continue
    b, R = radii(v['c']); low = R < 1500; segs = []; j = 0
    while j < len(R):
        if low[j]:
            j0 = j
            while j < len(R) and low[j]: j += 1
            m = j0 + int(np.argmin(R[j0:j])); segs.append('%.0f at %s' % (R[m], b[m].round(0)))
        j += 1
    print('%-22s min %6.0f | %s' % (k, R.min(), '; '.join(segs[:6])))
print('== throat match (Norwood Central tracks start at frame s 4,150)')
NW = json.load(open(SP + 'deckpage/norwood.json'))
for f in NW['features']:
    nm = f['properties'].get('name') or ''
    if f['geometry']['type'] == 'LineString' and any(t in nm for t in ('through track', 'T4 ', 'T2 ', 'T9', 'T10')) and 'Waynesville' not in nm:
        q = np.array(f['geometry']['coordinates'][0][:2]); best = min(((np.hypot(*(np.asarray(v['c'][-1]) - q)), k) for k, v in L.items() if not k.startswith('_') and v['kind'] != 'ref'))
        print('  %-45s nearest end %-22s %.2f m' % (nm[:45], best[1], best[0]))
print('== B stations', [(a, round(b), c, round(d, 1)) for a, b, c, d, _ in L['_bst']])
print('== same-level spacing under 4.3 m (TV over ORR/APEx in the crossing span excluded)')
s_lo, s_hi = 3420, 3720
pts = {}
for k, v in L.items():
    if k.startswith('_') or v['kind'] == 'ref': continue
    p = resamp(v['c'], 1.0); pts[k] = p
names = list(pts)
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        a, b = pts[names[i]], pts[names[j]]; Tq = cKDTree(b); dd, ii = Tq.query(a, distance_upper_bound=4.3); ok = np.isfinite(dd)
        if not ok.any(): continue
        sv = np.array([FR.nw_so(q)[0] for q in a[ok]])
        tvx = ('TV' in names[i]) != ('TV' in names[j]) and not ('TV' in names[i] and 'TV' in names[j])
        keep = ~((sv > s_lo) & (sv < s_hi)) if tvx else np.ones(len(sv), bool)
        if keep.any(): print('  %s / %s: %d pts, min %.2f m, at %s' % (names[i], names[j], keep.sum(), dd[ok][keep].min(), a[ok][keep][0].round(0)))
print('== Mill Creek (open) crossings / near passes')
for k, v in L.items():
    if k.startswith('_') or v['kind'] == 'ref': continue
    g = LineString(v['c'])
    if g.intersects(WAT): X = g.intersection(WAT); print('  %s crosses the open creek, %.0f m of track over water' % (k, X.length))
print('== highways the branch crosses (hwy data centre lines)')
HW = json.load(open(SP + 'hwy/data.json')); HO = HW['origin']
for q in HW['segs']:
    hl = LineString(np.array(q['c']) + HO)
    for k in ('Norwood 1', 'X2 1', 'B SB', 'ORR 2', 'TV 1 (inbound, T10)'):
        X = LineString(L[k]['c']).intersection(hl)
        if not X.is_empty:
            for pnt in getattr(X, 'geoms', [X]): print('  %s crosses %s %s (%s) at %s' % (k, q['r'], q.get('a'), q.get('t'), np.round(pnt.coords[0], 0)))
