"""1950s USGS 1:24,000 contours (10 ft) mapped onto a 4 m LiDAR-grid crop: skeleton pixels with segment ids,
each sheet clipped to its own 7.5-minute neatline. Used by m3_rebuild.py."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, glob, cv2, rasterio, math
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
from pyproj import Transformer
X0, Y1, RES = 695000.0, 4350000.0, 4.0
TOLL = Transformer.from_crs('EPSG:26916', 'EPSG:4326', always_xy=True)
PREF = {'Covington': 1955, 'Newport': 1955}            # the 1950/1952 editions leave Ohio blank
def sheets():
    out = {}
    for f in sorted(glob.glob(_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/USGS_Historical*/*_24000_geo.tif"))):
        s = rasterio.open(f); T = Transformer.from_crs(s.crs, 'EPSG:4326', always_xy=True)
        b = s.bounds; cx, cy = T.transform((b.left + b.right) / 2, (b.top + b.bottom) / 2)
        cell = (math.floor(cx / 0.125) * 0.125, math.floor(cy / 0.125) * 0.125)
        name = f.split('/')[-1]; quad = name.split('_')[1]; yr = int(name.split('_')[3])
        if quad in PREF and yr != PREF[quad]: continue
        if cell in out and quad == 'New Richmond': continue
        out[cell] = f
    return out
def contour_seg(r0, c0, h, w, seg_offset=0):
    """Return (seg ids int32 [h,w] at 4 m, number of segments) for the crop rows r0.., cols c0.. of the 4 m grid."""
    seg = np.zeros((h, w), np.int32); n = seg_offset
    ex0, ey1 = X0 + c0 * RES, Y1 - r0 * RES; ex1, ey0 = ex0 + w * RES, ey1 - h * RES
    lo0, la0 = TOLL.transform(ex0, ey0); lo1, la1 = TOLL.transform(ex1, ey1)
    for cell, f in sheets().items():
        if cell[0] > max(lo0, lo1) or cell[0] + 0.125 < min(lo0, lo1) or cell[1] > max(la0, la1) or cell[1] + 0.125 < min(la0, la1): continue
        s = rasterio.open(f); V = Transformer.from_crs('EPSG:26916', s.crs, always_xy=True); U = Transformer.from_crs(s.crs, 'EPSG:26916', always_xy=True)
        xs, ys = V.transform([ex0, ex1, ex0, ex1], [ey1, ey1, ey0, ey0])
        ra, ca = s.index(min(xs), max(ys)); rb, cb = s.index(max(xs), min(ys))
        rr0, cc0 = max(0, min(ra, rb)), max(0, min(ca, cb)); rr1, cc1 = min(s.height, max(ra, rb)), min(s.width, max(ca, cb))
        if rr1 <= rr0 or cc1 <= cc0: continue
        win = rasterio.windows.Window(cc0, rr0, cc1 - cc0, rr1 - rr0)
        img = np.dstack([s.read(i, window=win) for i in (3, 2, 1)])
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32); Lc, ac, bc = lab[..., 0], lab[..., 1] - 128, lab[..., 2] - 128
        brownA = (ac > -3) & (ac < 26) & (bc > 24) & (bc > 1.6 * ac) & (Lc > 55) & (Lc < 172)       # on white
        brownB = (ac >= 25) & (ac < 45) & (bc >= 28) & (bc < 50) & (bc > 0.75 * ac) & (Lc < 200)    # over the pink urban tint
        red = cv2.dilate((ac > 50).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        brown = (brownA | brownB) & ~red
        brown = cv2.morphologyEx(brown.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8)).astype(bool)
        lb_, nb_ = ndi.label(brown, structure=np.ones((3, 3))); szb = np.bincount(lb_.ravel()); szb[0] = 0
        brown = np.isin(lb_, np.nonzero(szb >= 25)[0])
        sk = skeletonize(brown); cl, nc = ndi.label(sk, structure=np.ones((3, 3)))
        yy, xx = np.nonzero(sk); tr = s.window_transform(win)
        E, N = U.transform(tr.c + (xx + 0.5) * tr.a, tr.f + (yy + 0.5) * tr.e); E = np.asarray(E); N = np.asarray(N)
        lo, la = TOLL.transform(E, N); lo = np.asarray(lo); la = np.asarray(la)
        inq = (lo >= cell[0]) & (lo < cell[0] + 0.125) & (la >= cell[1]) & (la < cell[1] + 0.125)
        cc = ((E - ex0) / RES).astype(int); rr = ((ey1 - N) / RES).astype(int)
        ok = inq & (cc >= 0) & (cc < w) & (rr >= 0) & (rr < h)
        seg[rr[ok], cc[ok]] = cl[yy[ok], xx[ok]] + n; n += nc
    return seg, n
