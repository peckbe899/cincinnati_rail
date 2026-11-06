try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# which 1904 frames on the page lie under plates 66-70: each frame's picks placed (as in cuf/x1904.py), counted inside each plate footprint
import json, sys, glob, pickle, os, numpy as np, collections
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'sbg'); sys.path.insert(0, _ws.CODE + 'cuf'); sys.path.insert(0, _ws.CODE + 'lph'); sys.path.insert(0, _ws.CODE + 'cufp')
import mosn, tps, fwdlib, rasterio.features
from shapely.geometry import shape, Polygon, Point
from pyproj import Transformer
TF = {}
for fn in ('lph/tf_all.json', 'lph/tf_ext.json', 'lph/tf_ext2.json', 'lph/tf_ext3.json'): TF.update(json.load(open(SP + fn)))
MOD = pickle.load(open(SP + 'lph/tps_pre1922.pkl', 'rb'))
W3857 = Transformer.from_crs(3857, 26916, always_xy=True)
def poly(x, y, deg):
    x = np.asarray(x, float) / 10000; y = np.asarray(y, float) / 10000
    return np.stack([x ** i * y ** j for i in range(deg + 1) for j in range(deg + 1 - i)], -1)
FP = {}
for n in ('66', '67', '68', '69', '70'):
    al = np.load(SP + f'cufp/{n}/png_alpha_s4.npy')[::2, ::2]
    pp = max([shape(g) for g, v in rasterio.features.shapes((al > 0).astype(np.uint8), mask=al > 0) if v == 1], key=lambda p: p.area)
    c = np.array(pp.exterior.coords) * 8
    if os.path.exists(SP + f'cufp/{n}/fwd.pkl'): W = fwdlib.world_many(n, c)
    elif os.path.exists(SP + f'cufp/{n}/png2tif.json'):
        G = json.load(open(SP + f'cufp/{n}/png2tif.json')); X = poly(c[:, 0], c[:, 1], 3); tx = X @ np.array(G['cx']); ty = X @ np.array(G['cy']); a = G['tif_transform']
        W = np.c_[W3857.transform(a[0] * (tx + .5) + a[2], a[4] * (ty + .5) + a[5])]
    else: continue
    FP[n] = Polygon(W).buffer(0)
    print(n, 'footprint', [int(v) for v in FP[n].bounds], round(FP[n].area / 1e4), 'ha')
hits = collections.defaultdict(dict)
for fr in TF:
    sh = ''.join(ch for ch in fr if ch.isdigit())
    fn = SP + f'sbg/picks/s{sh}.json'
    if not os.path.exists(fn): continue
    P = json.load(open(fn))['intersections']
    if not P: continue
    E, N = mosn.ap(TF[fr], np.array([p['x'] for p in P], float), np.array([p['y'] for p in P], float))
    for n, F in FP.items():
        k = sum(F.contains(Point(e, nn)) for e, nn in zip(E, N))
        if k: hits[fr][n] = k
for fr in sorted(hits, key=lambda s: int(''.join(ch for ch in s if ch.isdigit()))): print(fr, hits[fr])
json.dump({k: v for k, v in hits.items()}, open(SP + 'cufp/frames_under.json', 'w'))
