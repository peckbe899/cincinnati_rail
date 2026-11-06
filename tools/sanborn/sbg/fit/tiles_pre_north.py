"""Warp the georeferenced basin Sanborn sheets into 512 m webp tiles at 0.25 m (plus a 2 m overview).
Each frame keeps the area around its own picked streets (hull of its picks, buffered); where frames overlap the
pixel goes to the frame it is deepest inside, so seams fall near the shared streets. Deck sheets are left to the deck tiles."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import json, os, sys, collections, numpy as np, cv2
from PIL import Image
HERE = _ws.data_dir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, _ws.code_dir(HERE)); sys.path.insert(0, _ws.code_dir(os.path.dirname(HERE)))
from load import load, frame_of, DECK
from shapely.geometry import MultiPoint, Polygon, box, shape
from shapely.ops import unary_union
from shapely import affinity
SP = _ws.DATA
SB = os.path.dirname(HERE)
OUT = os.path.join(SB, 'tiles_b'); os.makedirs(OUT, exist_ok=True)
RES, T = 0.25, 512
NP = int(T / RES)
P = {k: np.array(v) for k, v in json.load(open(os.path.join(HERE, 'tf.json'))).items()}
SZ = {int(k): v[0] for k, v in json.load(open(os.path.join(HERE, 'sizes.json'))).items()}
def sheet_of(fr): return int(''.join(c for c in fr if c.isdigit()))
def M_t(p):
    if len(p) == 6: return np.array([[p[0], p[1]], [p[2], p[3]]]), np.array([p[4], p[5]])
    a, c, tx, ty = p; return np.array([[a, c], [c, -a]]), np.array([tx, ty])
R, O = load()
pts = collections.defaultdict(list)
for r in R:
    if r['fr']: pts[r['fr']].append((r['x'], r['y']))
for o in O:
    if o['typ'] == 'alleys':
        for k in ('1', '2'):
            fr = frame_of(o['s'], o.get('part'), o['y' + k])
            if fr: pts[fr].append((o['x' + k], o['y' + k]))
    elif o['typ'] in ('bends', 'ends'):
        fr = frame_of(o['s'], o.get('part'), o['y'])
        if fr: pts[fr].append((o['x'], o['y']))
deck_polys = unary_union([Polygon(s['poly']) for s in json.load(open(SP + 'deckpage/sheets.json')) if not s.get('basin')])
regions = {}
for fr, pp in pts.items():
    s = sheet_of(fr)
    if fr not in P or s in DECK or len(pp) < 2: continue
    W, H = SZ[s]; buf = 330 if s < 200 else 560
    hull = MultiPoint(pp).convex_hull.buffer(buf, join_style=2).intersection(box(40, 40, W - 40, H - 40))
    M, t = M_t(P[fr])
    wpoly = affinity.affine_transform(hull, [M[0, 0], M[0, 1], M[1, 0], M[1, 1], t[0], t[1]])
    regions[fr] = wpoly
print('frames for tiles', len(regions))
allr = unary_union(list(regions.values()))
E0, N0, E1, N1 = allr.bounds
tx0, ty0 = int(np.floor(E0 / T) * T), int(np.floor(N0 / T) * T)
tiles = []
cache = collections.OrderedDict()
def img(s):
    if s in cache: cache.move_to_end(s); return cache[s]
    a = cv2.imread(os.path.join(SB, 'small', f's{s}.jpg'), cv2.IMREAD_COLOR)
    cache[s] = a
    while len(cache) > 10: cache.popitem(last=False)
    return a
over = np.zeros((int((np.ceil(N1 / T) * T - ty0) / 2), int((np.ceil(E1 / T) * T - tx0) / 2), 4), np.uint8)
for ty in range(ty0, int(np.ceil(N1 / T) * T), T):
    for tx in range(tx0, int(np.ceil(E1 / T) * T), T):
        tb = box(tx, ty, tx + T, ty + T)
        frs = [f for f, g in regions.items() if g.intersects(tb)]
        if not frs: continue
        best = np.full((NP, NP), -1.0, np.float32); rgb = np.zeros((NP, NP, 3), np.uint8)
        for fr in frs:
            s = sheet_of(fr); f = 2 if s < 200 else 4
            M, t = M_t(P[fr]); Mi = np.linalg.inv(M)
            # dst pixel (j, i) -> world (tx + (j+.5)RES, ty+T - (i+.5)RES) -> page -> small
            A = np.array([[RES, 0], [0, -RES]]); b = np.array([tx + 0.5 * RES, ty + T - 0.5 * RES])
            L = Mi @ A / f; c = Mi @ (b - t) / f
            warp = cv2.warpAffine(img(s), np.c_[L, c].astype(np.float64), (NP, NP), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_CONSTANT)
            g = regions[fr].intersection(tb)
            mask = np.zeros((NP, NP), np.uint8)
            for part in getattr(g, 'geoms', [g]):
                if part.geom_type != 'Polygon' or part.is_empty: continue
                q = np.array(part.exterior.coords); q = np.c_[(q[:, 0] - tx) / RES, (ty + T - q[:, 1]) / RES]
                cv2.fillPoly(mask, [np.round(q).astype(np.int32)], 1)
            if not mask.any(): continue
            # depth inside the region: distance transform on a padded mask so tile edges do not count as region edges
            pad = 600
            big = np.zeros((NP + 2 * pad, NP + 2 * pad), np.uint8)
            gb = regions[fr].intersection(box(tx - pad * RES, ty - pad * RES, tx + T + pad * RES, ty + T + pad * RES))
            for part in getattr(gb, 'geoms', [gb]):
                if part.geom_type != 'Polygon' or part.is_empty: continue
                q = np.array(part.exterior.coords); q = np.c_[(q[:, 0] - tx) / RES + pad, (ty + T - q[:, 1]) / RES + pad]
                cv2.fillPoly(big, [np.round(q).astype(np.int32)], 1)
            dist = cv2.distanceTransform(big, cv2.DIST_L2, 5)[pad:pad + NP, pad:pad + NP]
            sel = (mask > 0) & (dist > best)
            best[sel] = dist[sel]; rgb[sel] = warp[sel]
        alpha = (best > 0).astype(np.uint8) * 255
        # leave the deck sheets to the deck tiles
        g = deck_polys.intersection(tb)
        if not g.is_empty:
            dm = np.zeros((NP, NP), np.uint8)
            for part in getattr(g, 'geoms', [g]):
                if part.geom_type != 'Polygon': continue
                q = np.array(part.exterior.coords); q = np.c_[(q[:, 0] - tx) / RES, (ty + T - q[:, 1]) / RES]
                cv2.fillPoly(dm, [np.round(q).astype(np.int32)], 1)
            alpha[dm > 0] = 0
        if alpha.max() == 0: continue
        alpha = cv2.GaussianBlur(alpha, (5, 5), 0)
        rgba = np.dstack([rgb[..., ::-1], alpha])
        Image.fromarray(rgba, 'RGBA').save(os.path.join(OUT, f'{tx}_{ty}.webp'), quality=72, method=4)
        tiles.append([tx, ty])
        # overview at 2 m
        sm = cv2.resize(rgba, (T // 2, T // 2), interpolation=cv2.INTER_AREA)
        oy = over.shape[0] - (ty - ty0) // 2 - T // 2; ox = (tx - tx0) // 2
        over[oy:oy + T // 2, ox:ox + T // 2] = sm
        print('tile', tx, ty, len(frs), flush=True)
json.dump(dict(size=T, res=RES, tiles=tiles), open(os.path.join(OUT, 'index.json'), 'w'))
Image.fromarray(over, 'RGBA').save(os.path.join(OUT, 'overview.webp'), quality=70, method=4)
json.dump(dict(E0=tx0, N0=ty0, E1=tx0 + over.shape[1] * 2, N1=ty0 + over.shape[0] * 2, res=2), open(os.path.join(OUT, 'overview.json'), 'w'))
print('tiles', len(tiles))
