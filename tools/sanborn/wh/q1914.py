"""Black ink of the 1914 USGS 1:62,500 quads (West and East Cincinnati), for dating OSM roads: was there a road here in 1914?"""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import rasterio, numpy as np
from pyproj import Transformer
from scipy.ndimage import binary_dilation
Q = _ws.ext('/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/USGS_Historical/')
FILES = ['OH_West Cincinnati_226552_1914_62500_geo.tif', 'OH_East Cincinnati_224939_1914_62500_geo.tif']
class Quad:
    def __init__(self, f, r_m=25):
        self.r = rasterio.open(Q + f); a = self.r.read()
        R, G, B = a[0].astype(int), a[1].astype(int), a[2].astype(int)
        mx = np.maximum(np.maximum(R, G), B); mn = np.minimum(np.minimum(R, G), B)
        self.ink = (mx < 110) & (mx - mn < 45)                         # dark and grey: black culture ink (roads, buildings, rails, lettering)
        k = int(round(r_m / self.r.res[0])); yy, xx = np.mgrid[-k:k + 1, -k:k + 1]
        self.near = binary_dilation(self.ink, structure=(xx * xx + yy * yy) <= k * k)
        self.t = Transformer.from_crs(26916, self.r.crs, always_xy=True)
    def hit(self, pts):
        x, y = self.t.transform(pts[:, 0], pts[:, 1]); rows, cols = rasterio.transform.rowcol(self.r.transform, x, y)
        rows, cols = np.asarray(rows), np.asarray(cols); ok = (rows >= 0) & (rows < self.near.shape[0]) & (cols >= 0) & (cols < self.near.shape[1])
        h = np.full(len(pts), -1); h[ok] = self.near[rows[ok], cols[ok]]; return h
def quads(r_m=25): return [Quad(f, r_m) for f in FILES]
def score(QS, g, step=10.0):
    d = np.arange(0, g.length + 0.01, step); P = np.array([g.interpolate(s).coords[0] for s in d])
    best = np.full(len(P), -1)
    for q in QS: best = np.maximum(best, q.hit(P))
    v = best[best >= 0]
    return (float(v.mean()) if len(v) else None), best
