try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# plate 38 png px -> world (EPSG:26916), rebuilt from cuf38/fwd38.pkl (written by fit38.py)
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
_f = None
def world(x, y):
    global _f
    if _f is None: d = pickle.load(open(SP + 'cuf38/fwd38.pkl', 'rb')); _f = make(d['model'], d['X'], d['O'])
    r = _f(np.array([[x, y]], float))[0]; return float(r[0]), float(r[1])
def world_many(q):
    world(0, 0); return _f(np.asarray(q, float))
