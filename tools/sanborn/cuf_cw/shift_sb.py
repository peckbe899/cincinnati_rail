try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# 2026-10-22: the 1904 street and block layer of the north (set SB, from the 13 October north build, sbg/fit/post.py) is not rebuilt by
# cuf/rebuild_streets.sh, and rebuilding it renumbers every SB street (Ben's names, deletions and redraws are keyed by those ids).
# So the SB streets, SBB blocks and their plots are moved by exactly the change in their frames' placement (lph/tps_v98.pkl -> lph/tps.pkl),
# sampled over each bent frame's page, ids untouched.
import json, sys, pickle, os, numpy as np
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'lph'); sys.path.insert(0, _ws.CODE + 'sbg')
import mosn, tps
from scipy.spatial import cKDTree
from matplotlib.path import Path
from PIL import Image
from sb import find
Image.MAX_IMAGE_PIXELS = None
TF = {}
for fn in ('lph/tf_all.json', 'lph/tf_ext.json', 'lph/tf_ext2.json', 'lph/tf_ext3.json'): TF.update(json.load(open(SP + fn)))
PX = {}
for fn in ('lph/panels_ext.json', 'lph/panels_ext2.json', 'lph/panels_ext3.json'): PX.update(json.load(open(SP + fn)))
OLD = pickle.load(open(SP + 'lph/tps_v98.pkl', 'rb')); NEW = pickle.load(open(SP + 'lph/tps.pkl', 'rb'))
FR = open(SP + 'cuf_cw/frames_all.txt').read().strip().split(',')
def pagepts(f, step=16):
    sh = ''.join(ch for ch in f if ch.isdigit())
    im = np.asarray(Image.open(find(int(sh))).convert('RGB')); pm, pd = mosn.page_mask(int(sh), im)
    ys, xs = np.nonzero(pm[::step, ::step]); xs = xs * float(step) * 8; ys = ys * float(step) * 8; q = np.c_[xs, ys]; keep = np.ones(len(q), bool)
    if f in PX: keep &= Path(np.array(PX[f])).contains_points(q)
    for s in PX:
        if s != f and ''.join(ch for ch in s if ch.isdigit()) == sh: keep &= ~Path(np.array(PX[s])).contains_points(q)
    return xs[keep], ys[keep]
def place(M, f, E, N):
    if f in M: dE, dN = tps.disp(f, E, N, M); return E + dE, N + dN
    return E, N
P0, DL = [], []
for f in FR:
    if f not in TF: continue
    xs, ys = pagepts(f)
    if not len(xs): continue
    E, N = mosn.ap(TF[f], xs, ys); e0, n0 = place(OLD, f, E, N); e1, n1 = place(NEW, f, E, N)
    d = np.c_[e1 - e0, n1 - n0]; P0.append(np.c_[e0, n0]); DL.append(d)
    m = np.hypot(*d.T)
    if m.max() > 0.3: print(f'{f:5s} samples {len(xs):5d} move median {np.median(m):4.1f} max {m.max():4.1f}')
P0 = np.vstack(P0); DL = np.vstack(DL); T = cKDTree(P0)
def delta(q):
    q = np.asarray(q, float); out = np.zeros_like(q)
    for i, p in enumerate(q):
        idx = T.query_ball_point(p, 30.0)
        if not idx: continue
        d = np.hypot(*(P0[idx] - p).T); w = 1 / (d + 5); out[i] = (DL[idx] * w[:, None]).sum(0) / w.sum()
    return out
if __name__ == '__main__':
    B = json.load(open(SP + 'deckpage/basin.json')); moved = {'street': 0, 'block': 0}; mx = 0
    def mv(c):
        global mx
        a = np.array(c, float); d = delta(a); mx = max(mx, float(np.hypot(*d.T).max()) if len(d) else 0); return [[round(x, 2), round(y, 2)] for x, y in a + d], float(np.hypot(*d.T).max()) if len(d) else 0
    for f in B['features']:
        p = f['properties']; g = f['geometry']
        if p.get('src') != 'Sanborn 1904' or p.get('set') not in (None, ''): continue
        if p['layer'] == 'street' and p['id'].startswith('SB') and g['type'] == 'LineString':
            c, m = mv(g['coordinates'])
            if m > 0.05: g['coordinates'] = c; moved['street'] += 1
        elif p['layer'] == 'block' and p['id'].startswith('SBB'):
            if g['type'] == 'Polygon':
                rs = [mv(r) for r in g['coordinates']]
                if max(m for _, m in rs) > 0.05: g['coordinates'] = [c for c, _ in rs]; moved['block'] += 1
            elif g['type'] == 'MultiPolygon':
                ps = [[mv(r) for r in poly] for poly in g['coordinates']]
                if max(m for poly in ps for _, m in poly) > 0.05: g['coordinates'] = [[c for c, _ in poly] for poly in ps]; moved['block'] += 1
    json.dump(B, open(SP + 'deckpage/basin.json', 'w'), separators=(',', ':'))
    print('moved', moved, 'largest move', round(mx, 1), 'm')
    # plots of SB blocks
    SBB = {f['properties']['id'] for f in B['features'] if f['properties']['layer'] == 'block' and f['properties']['id'].startswith('SBB') and f['properties'].get('set') in (None, '')}
    PL = json.load(open(SP + 'deckpage/plots.json')); E0, N0 = PL['o']; npl = 0
    for row in PL['plots']:
        if row[1] not in SBB: continue
        newr = []; ch = False
        for a in row[6]:
            x, y = a[0], a[1]; pts = [[E0 + x / 10, N0 + y / 10]]
            for i in range(2, len(a), 2): x += a[i]; y += a[i + 1]; pts.append([E0 + x / 10, N0 + y / 10])
            d = delta(pts); 
            if np.hypot(*d.T).max() > 0.05: ch = True
            q = np.round((np.array(pts) + d - [E0, N0]) * 10).astype(int); enc = [int(q[0, 0]), int(q[0, 1])]
            for i in range(1, len(q)): enc += [int(q[i, 0] - q[i - 1, 0]), int(q[i, 1] - q[i - 1, 1])]
            newr.append(enc)
        if ch: row[6] = newr; npl += 1
    json.dump(PL, open(SP + 'deckpage/plots.json', 'w'), separators=(',', ':'))
    print('plots moved', npl)
