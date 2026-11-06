try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# plate 22-35N (Ben's georeferenced 1922 plate 35 north): pixel <-> EPSG:26916 through Ben's EPSG:3857 grid, plus our correction
import json, pickle, os, numpy as np
from pyproj import Transformer
SP = _ws.DATA
G = json.load(open(SP + 'cuf/ben_georef.json')); A = G['transform']        # a, b, c, d, e, f (rasterio order: x = a*col + b*row + c)
F = Transformer.from_crs(3857, 26916, always_xy=True); Bk = Transformer.from_crs(26916, 3857, always_xy=True)
def px2ben(x, y):
    x = np.asarray(x, float) + 0.5; y = np.asarray(y, float) + 0.5
    X = A[0] * x + A1(y) if False else A[0] * x + A[1] * y + A[2]; Y = A[3] * x + A[4] * y + A[5]
    return F.transform(X, Y)
def ben2px(E, N):
    X, Y = Bk.transform(np.asarray(E, float), np.asarray(N, float))
    det = A[0] * A[4] - A[1] * A[3]
    x = (A[4] * (X - A[2]) - A[1] * (Y - A[5])) / det; y = (-A[3] * (X - A[2]) + A[0] * (Y - A[5])) / det
    return x - 0.5, y - 0.5
CORR = SP + 'cuf/corr.pkl'
def load_corr():
    return pickle.load(open(CORR, 'rb')) if os.path.exists(CORR) else None
