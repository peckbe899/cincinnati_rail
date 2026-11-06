try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# 1922 plate N png px -> world (EPSG:26916), rebuilt from cufp/N/fwd.pkl (written by cufp/fit.py)
import pickle, numpy as np
from scipy.interpolate import RBFInterpolator
SP = _ws.DATA
def poly(x, y, deg):
    x = np.asarray(x, float) / 10000; y = np.asarray(y, float) / 10000
    return np.stack([x ** i * y ** j for i in range(deg + 1) for j in range(deg + 1 - i)], -1)
def fit_poly(Xs, Os, deg):
    A = poly(Xs[:, 0], Xs[:, 1], deg); ce, *_ = np.linalg.lstsq(A, Os[:, 0], rcond=None); cn, *_ = np.linalg.lstsq(A, Os[:, 1], rcond=None)
    return lambda q: np.stack([poly(q[:, 0], q[:, 1], deg) @ ce, poly(q[:, 0], q[:, 1], deg) @ cn], 1)
def fit_tps(Xs, Os, sm):
    base_ = fit_poly(Xs, Os, 1); R = Os - base_(Xs)
    rb = RBFInterpolator(Xs / 1000, R, kernel='thin_plate_spline', smoothing=sm, degree=1)
    return lambda q: base_(q) + rb(q / 1000)
def make(model, X, O):
    if model == 'affine': return fit_poly(X, O, 1)
    if model == 'quadratic': return fit_poly(X, O, 2)
    return fit_tps(X, O, float(model[3:]))
_F = {}
def world_many(n, q):
    n = str(n)
    if n not in _F:
        import os; fp = SP + f'cufp/{n}/fwd.pkl'
        if not os.path.exists(fp): fp = SP + f'cuf_cw/{n}/fwd.pkl'          # 2026-10-22: the vol. 1 halves refitted (34L, 37R ...)
        d = pickle.load(open(fp, 'rb')); _F[n] = make(d['model'], d['X'], d['O'])
    return _F[n](np.asarray(q, float))
def world(n, x, y):
    r = world_many(n, [[x, y]])[0]; return float(r[0]), float(r[1])
