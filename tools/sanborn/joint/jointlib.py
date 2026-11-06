"""1922 plate positions after the joint refit (tools/sanborn/joint/solve.py): plate pixel -> world (EPSG:26916) and back.

new(px) = P + d(P), P = F(px), where F is the plate's own model as it was (cufp/<N>/fwd.pkl, cuf_cw/<half>/fwd.pkl,
cuf38/fwd38.pkl, or Ben's georeference for 22-35N) and d is the plate's world-space correction from the joint solve
(affine, or affine plus quadratic), stored beside the old model as fwd_joint.pkl (cuf38/fwd38_joint.pkl,
cuf/joint35N.pkl). The old files are never changed.

A model may also carry a page curl (tools/sanborn/joint/curl.py; local3.py): then new(px) = Q + d(Q), Q = F(px + c(px)),
c the curl's pixel displacement across the plate's gutter.

A model of kind 'tps_px' (tools/sanborn/joint/complete.py, rule 12) keeps nothing of the old model: world is a
thin-plate spline of the plate pixel, fitted on the plate's complete control set (tps_px_many below).
"""
import os, pickle, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _ws  # noqa: E402

SP = _ws.DATA
for _d in ('cuf', 'cufp', 'cuf38', 'sbg', 'lph'):
    sys.path.insert(0, _ws.CODE + _d)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def base_path(pid):
    n = pid[3:]
    if pid == '22-35N':
        return 'cuf/ben_georef.json'
    if pid == '22-38':
        return 'cuf38/fwd38.pkl'
    return f'cufp/{n}/fwd.pkl' if os.path.exists(SP + f'cufp/{n}/fwd.pkl') else f'cuf_cw/{n}/fwd.pkl'


def joint_path(pid, tag='joint'):
    """the new model's file, beside the old one: fwd_<tag>.pkl (cuf38/fwd38_<tag>.pkl, cuf/<tag>35N.pkl)"""
    if pid == '22-35N':
        return f'cuf/{tag}35N.pkl'
    if pid == '22-38':
        return f'cuf38/fwd38_{tag}.pkl'
    return os.path.dirname(base_path(pid)) + f'/fwd_{tag}.pkl'


def has(pid, tag):
    return os.path.exists(SP + joint_path(pid, tag))


def base_many(pid, q):
    """the plate's own (old) model, pixel -> world"""
    q = np.asarray(q, float)
    if pid == '22-35N':
        import common as C
        E, N = C.px2ben(q[:, 0], q[:, 1]); return np.c_[E, N]
    if pid == '22-38':
        import fwd38lib
        return fwd38lib.world_many(q)
    import fwdlib
    return fwdlib.world_many(pid[3:], q)


def base_inv(pid, E, N):
    """world -> plate pixel through the old model's inverse (the inverse grid the page tiles were drawn with)"""
    import plates
    p = next(p for p in plates.PLATES if p['id'] == pid)
    return p['inv'](E, N)


def basis(P, center, scale, kind):
    u = (P[:, 0] - center[0]) / scale; v = (P[:, 1] - center[1]) / scale
    cols = [np.ones_like(u), u, v]
    if kind == 'quadratic':
        cols += [u * u, u * v, v * v]
    return np.stack(cols, 1)


_J = {}


def load(pid, tag='joint'):
    if (pid, tag) not in _J:
        _J[(pid, tag)] = pickle.load(open(SP + joint_path(pid, tag), 'rb'))
    return _J[(pid, tag)]


def tps_kernel(P, centers, U):
    """thin-plate kernel r2 log r between points and centres, distances in units of U metres"""
    d = np.hypot(P[:, None, 0] - centers[None, :, 0], P[:, None, 1] - centers[None, :, 1]) / U
    with np.errstate(divide='ignore', invalid='ignore'):
        k = np.where(d > 0, d * d * np.log(d), 0.0)
    return k


def corr(pid, P, tag='joint'):
    j = load(pid, tag); P = np.asarray(P, float)
    if j.get('kind', '').startswith('tps') or j.get('kind') in ('affine', 'curl'):     # the local fits (local.py, local2.py, local3.py)
        B = basis(P, j['center'], j['scale'], 'affine')
        d = np.c_[B @ np.asarray(j['coefE']), B @ np.asarray(j['coefN'])]
        if j.get('centers'):
            K = tps_kernel(P, np.asarray(j['centers'], float), j['U'])
            d = d + np.c_[K @ np.asarray(j['wE']), K @ np.asarray(j['wN'])]
        return d
    B = basis(P, j['center'], j['scale'], j['basis'])
    return np.c_[B @ np.asarray(j['coefE']), B @ np.asarray(j['coefN'])]


_BO = {}


def base_for(pid, tag):
    """the plate's own model under this model set: rebuilt from corrected controls if the model file carries one
    (base_override, tools/sanborn/joint/local2.py), else the stored one"""
    j = load(pid, tag)
    bo = j.get('base_override')
    if not bo:
        return lambda q: base_many(pid, q)
    if (pid, tag) not in _BO:
        import fwdlib
        _BO[(pid, tag)] = fwdlib.make(bo['model'], np.asarray(bo['X'], float), np.asarray(bo['O'], float))
    return lambda q: _BO[(pid, tag)](np.asarray(q, float))


def curl_disp(pid, q, tag):
    """the model's page-curl pixel displacement at pixels q (zero if it has none)"""
    c = load(pid, tag).get('curl')
    q = np.asarray(q, float)
    if not c:
        return np.zeros_like(q)
    import curl
    return curl.disp(c['side'], c['a'], c['k'], q)


def tps_px_many(j, q):
    """a 'tps_px' model: world = affine . [1, (x - center) / scale] + sum_j w_j phi(|x - c_j| / scale), phi = r2 log r"""
    x = np.asarray(q, float); sc = j['scale_px']; c = np.asarray(j['center_px'], float)
    q = x
    if j.get('curl'):                       # complete2.py: page curl under the spline (37L, 37R)
        import curl
        cu = j['curl']; q = x + curl.disp(cu['side'], cu['a'], cu['k'], x)
    B = np.c_[np.ones(len(q)), (q - c) / sc]
    Cc = np.asarray(j['centers_px'], float)
    out = B @ np.asarray(j['affine'], float)
    for i in range(0, len(q), 20000):
        qq = q[i:i + 20000]
        d = np.hypot(qq[:, None, 0] - Cc[None, :, 0], qq[:, None, 1] - Cc[None, :, 1]) / sc
        with np.errstate(divide='ignore', invalid='ignore'):
            K = np.where(d > 0, d * d * np.log(d), 0.0)
        t = K @ np.asarray(j['w'], float)
        if j.get('damp'):                   # complete2.py: thin-plate part damped outside the controls' hull
            t = t * damp_w(np.asarray(j['damp']['hull_px'], float), x[i:i + 20000], j['damp']['width_px'])[:, None]
        out[i:i + 20000] += t
    return out


def damp_w(H, Q, width):
    """1 inside the convex polygon H, a cosine taper to 0 over width px outside it"""
    a = H; b = np.roll(H, -1, 0); e = b - a
    cross = e[None, :, 0] * (Q[:, None, 1] - a[None, :, 1]) - e[None, :, 1] * (Q[:, None, 0] - a[None, :, 0])
    inside = np.all(cross >= 0, 1)
    t = np.clip(((Q[:, None, 0] - a[None, :, 0]) * e[None, :, 0] + (Q[:, None, 1] - a[None, :, 1]) * e[None, :, 1]) / (e[:, 0] ** 2 + e[:, 1] ** 2)[None, :], 0, 1)
    d = np.hypot(Q[:, None, 0] - (a[None, :, 0] + t * e[None, :, 0]), Q[:, None, 1] - (a[None, :, 1] + t * e[None, :, 1])).min(1)
    d = np.where(inside, 0.0, d)
    return np.where(d >= width, 0.0, 0.5 * (1 + np.cos(np.pi * np.clip(d / width, 0, 1))))


def world_many(pid, q, tag='joint'):
    q = np.asarray(q, float)
    if load(pid, tag).get('kind') == 'tps_px':
        return tps_px_many(load(pid, tag), q)
    P = base_for(pid, tag)(q + curl_disp(pid, q, tag)); return P + corr(pid, P, tag)


def world(pid, x, y, tag='joint'):
    r = world_many(pid, [[x, y]], tag)[0]; return float(r[0]), float(r[1])


def inv(pid, E, N, it=8, tag='joint'):
    """world -> plate pixel for the new position: undo the correction (fixed point, it is small and smooth), then the
    old inverse"""
    W = np.c_[np.ravel(E), np.ravel(N)].astype(float); P = W.copy()
    if load(pid, tag).get('kind') == 'tps_px':      # Newton from the old inverse
        px, py = base_inv(pid, W[:, 0], W[:, 1])
        q = np.c_[np.ravel(px), np.ravel(py)].astype(float)
        ok = np.all(np.abs(q) < 1e5, 1) & np.all(np.isfinite(q), 1)
        j = load(pid, tag)
        for _ in range(it):
            if not ok.any():
                break
            Q = q[ok]; h = 2.0
            ex = (tps_px_many(j, Q + [h, 0]) - tps_px_many(j, Q - [h, 0])) / (2 * h)
            ey = (tps_px_many(j, Q + [0, h]) - tps_px_many(j, Q - [0, h])) / (2 * h)
            Jm = np.stack([ex, ey], 2)
            q[ok] = Q + np.linalg.solve(Jm, (W[ok] - tps_px_many(j, Q))[:, :, None])[:, :, 0]
        q[~ok] = -1e6
        return q[:, 0].reshape(np.shape(E)), q[:, 1].reshape(np.shape(N))
    for _ in range(it):
        P = W - corr(pid, P, tag)
    px, py = base_inv(pid, P[:, 0].reshape(np.shape(E)), P[:, 1].reshape(np.shape(N)))
    if load(pid, tag).get('curl'):           # px + c(px) = the old inverse's pixel: undo the curl (fixed point)
        Q = np.c_[np.ravel(px), np.ravel(py)].astype(float); X = Q.copy()
        for _ in range(it):
            X = Q - curl_disp(pid, X, tag)
        px, py = X[:, 0].reshape(np.shape(E)), X[:, 1].reshape(np.shape(N))
    return px, py
