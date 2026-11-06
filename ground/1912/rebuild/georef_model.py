"""1912 sheet georeference: scan pixel <-> survey grid (feet) <-> EPSG:26916.

Start model (the I4 joint transform, georef_1912.json, reused unchanged):
  grid g0 = CoonsInverse(p)                       homography from the four border corners + traced neatline bow
  q = p + 2*(J.F(g0) + S(p/2 - (u0, v0)))         F: regional field on a 4000 ft lattice; S: per-sheet cubic shape
  grid = CoonsInverse(q); ground = AEQD(Hughes HS station, feet) -> EPSG:26916
This module adds the correction fitted by the joint solve (joint_georef.py): a smoothing thin-plate spline D in
ground metres, so ground = start(p) + D(start(p)). Every parameter lives in georef/<sheet_id>.json.
"""
import json
import numpy as np
import cv2
from pyproj import Transformer

FT = 1200 / 3937


def _aeqd(lat, lon):
    return f"+proj=aeqd +lat_0={lat} +lon_0={lon} +units=m +datum=WGS84"


def basis(a, b, deg):
    return np.stack([a ** i * b ** j for i in range(deg + 1) for j in range(deg + 1 - i)], 1)


_LO = np.array([i + j <= 1 for i in range(4) for j in range(4 - i)])


class StartSheet:
    """One sheet of the start model, built from a georef_1912.json entry plus the global meta block."""

    def __init__(self, m, meta):
        self.m = m
        self.H = np.array(m['H_grid_to_px'], float); self.Hi = np.linalg.inv(self.H)
        self.T = np.linspace(0, 1, 401)
        self.C = {k: np.array(v, float) for k, v in m['neatline_offsets_px'].items()}
        self.N = {k: np.array(v, float) for k, v in m['neatline_normals'].items()}
        f = meta['F']
        self.F = np.array([f['Fx'], f['Fy']], float)
        self.X0, self.Y0, self.SP, self.nx, self.ny = f['X0'], f['Y0'], f['SP'], f['nx'], f['ny']
        self.J = np.array(m['J'], float)
        self.sx = np.array(m['shape_x'], float); self.sy = np.array(m['shape_y'], float)
        aeqd = _aeqd(meta['origin_lat'], meta['origin_lon'])
        self.loc2utm = Transformer.from_crs(aeqd, "EPSG:26916", always_xy=True)
        self.utm2loc = Transformer.from_crs("EPSG:26916", aeqd, always_xy=True)

    # --- Coons neatline correction ---
    def _st(self, gx, gy):
        m = self.m
        return (gx - m['x_w']) / (m['x_e'] - m['x_w']), (m['y_n'] - gy) / (m['y_n'] - m['y_s'])

    def _disp(self, gx, gy):
        a, b = self._st(gx, gy); a = np.clip(a, 0, 1); b = np.clip(b, 0, 1)
        f = lambda k, x: np.interp(x, self.T, self.C[k])[:, None] * self.N[k][None]
        return (1 - b)[:, None] * f('top', a) + b[:, None] * f('bottom', a) + (1 - a)[:, None] * f('left', b) + a[:, None] * f('right', b)

    def _coons_g2p(self, gx, gy):
        p = cv2.perspectiveTransform(np.c_[gx, gy][None].astype(np.float64), self.H)[0]
        return p + self._disp(gx, gy)

    def _coons_p2g(self, u, v):
        g = cv2.perspectiveTransform(np.c_[u, v][None].astype(np.float64), self.Hi)[0]
        for _ in range(4):
            D = self._disp(g[:, 0], g[:, 1])
            g = cv2.perspectiveTransform(np.c_[u - D[:, 0], v - D[:, 1]][None].astype(np.float64), self.Hi)[0]
        return g[:, 0], g[:, 1]

    # --- regional field and sheet shape ---
    def _Fat(self, gx, gy):
        fx = (gx - self.X0) / self.SP; fy = (gy - self.Y0) / self.SP
        i = np.clip(np.floor(fx).astype(int), 0, self.nx - 2); j = np.clip(np.floor(fy).astype(int), 0, self.ny - 2)
        tx = fx - i; ty = fy - j
        c = np.stack([j * self.nx + i, j * self.nx + i + 1, (j + 1) * self.nx + i, (j + 1) * self.nx + i + 1], 1)
        w = np.stack([(1 - tx) * (1 - ty), tx * (1 - ty), (1 - tx) * ty, tx * ty], 1)
        return (self.F[0][c] * w).sum(1), (self.F[1][c] * w).sum(1)

    def p2g(self, u, v):
        u = np.asarray(u, float).ravel(); v = np.asarray(v, float).ravel(); m = self.m
        if len(u) == 0:
            return u.copy(), v.copy()
        g0x, g0y = self._coons_p2g(u, v); fx, fy = self._Fat(g0x, g0y)
        du = self.J[0, 0] * fx + self.J[0, 1] * fy; dv = self.J[1, 0] * fx + self.J[1, 1] * fy
        P = basis((u / 2 - m['u0']) / m['W'], (v / 2 - m['v0']) / m['H'], 3)[:, ~_LO]
        du = du + P @ self.sx; dv = dv + P @ self.sy
        return self._coons_p2g(u + 2 * du, v + 2 * dv)

    def g2p(self, gx, gy, it=6):
        gx = np.asarray(gx, float).ravel(); gy = np.asarray(gy, float).ravel()
        T = self._coons_g2p(gx, gy); p = T.copy()
        for _ in range(it):
            g = np.c_[self.p2g(p[:, 0], p[:, 1])]
            p = p + (T - self._coons_g2p(g[:, 0], g[:, 1]))
        return p[:, 0], p[:, 1]

    def p2utm(self, u, v):
        gx, gy = self.p2g(u, v)
        E, N = self.loc2utm.transform(gx * FT, gy * FT)
        return np.asarray(E, float), np.asarray(N, float)

    def utm2p(self, E, N):
        e, n = self.utm2loc.transform(np.asarray(E, float).ravel(), np.asarray(N, float).ravel())
        return self.g2p(np.asarray(e) / FT, np.asarray(n) / FT)

    def utm2g(self, E, N):
        e, n = self.utm2loc.transform(np.asarray(E, float).ravel(), np.asarray(N, float).ravel())
        return np.asarray(e) / FT, np.asarray(n) / FT

    def g2utm(self, gx, gy):
        E, N = self.loc2utm.transform(np.asarray(gx, float) * FT, np.asarray(gy, float) * FT)
        return np.asarray(E, float), np.asarray(N, float)


class TPS:
    """Smoothing thin-plate spline R^2 -> R^2 (ground metres), kernel r^2 log r, centres in ground metres."""

    def __init__(self, centres=None, w=None, a=None, scale=1000.0):
        self.c = np.zeros((0, 2)) if centres is None else np.asarray(centres, float)
        self.w = np.zeros((0, 2)) if w is None else np.asarray(w, float)
        self.a = np.zeros((3, 2)) if a is None else np.asarray(a, float)
        self.s = scale

    @staticmethod
    def _k(r):
        with np.errstate(divide='ignore', invalid='ignore'):
            return np.where(r > 0, r * r * np.log(r), 0.0)

    def __call__(self, xy):
        xy = np.asarray(xy, float)
        out = np.c_[np.ones(len(xy)), (xy - self.c0()) / self.s] @ self.a
        if len(self.c):
            for i in range(0, len(xy), 20000):
                r = np.hypot(*((xy[i:i + 20000, None, :] - self.c[None]) / self.s).transpose(2, 0, 1))
                out[i:i + 20000] += self._k(r) @ self.w
        return out

    def c0(self):
        return self.c.mean(0) if len(self.c) else np.zeros(2)

    @classmethod
    def fit(cls, xy, d, wt, lam, scale=1000.0):
        """Weighted smoothing TPS through displacements d at xy (weights wt, smoothing lam)."""
        xy = np.asarray(xy, float); d = np.asarray(d, float); n = len(xy)
        t = cls(xy, scale=scale); c0 = t.c0()
        K = cls._k(np.hypot(*((xy[:, None, :] - xy[None]) / scale).transpose(2, 0, 1)))
        P = np.c_[np.ones(n), (xy - c0) / scale]
        A = np.zeros((n + 3, n + 3)); A[:n, :n] = K + np.diag(lam / np.maximum(wt, 1e-9)); A[:n, n:] = P; A[n:, :n] = P.T
        b = np.zeros((n + 3, 2)); b[:n] = d
        sol = np.linalg.solve(A, b)
        t.w, t.a = sol[:n], sol[n:]
        return t

    def to_json(self):
        return {'kernel': 'r^2 log r, r = |x - c| / scale', 'scale_m': self.s, 'centre_origin': self.c0().round(3).tolist(),
                'centres': self.c.round(3).tolist(), 'weights': self.w.round(9).tolist(), 'affine': self.a.round(9).tolist(),
                'affine_basis': '[1, (x - centre_origin)/scale, (y - centre_origin)/scale]'}


class Sheet:
    """Full model for one sheet: start model plus the joint-solve correction."""

    def __init__(self, start, tps=None):
        self.start = start; self.tps = tps or TPS()

    def p2utm(self, u, v):
        E, N = self.start.p2utm(u, v); d = self.tps(np.c_[E, N])
        return E + d[:, 0], N + d[:, 1]

    def g2utm(self, gx, gy):
        """Ground position of a survey-grid point as printed on this sheet (via its own pixel model)."""
        u, v = self.start.g2p(gx, gy); return self.p2utm(u, v)

    def utm2p(self, E, N, it=4):
        E = np.asarray(E, float).ravel(); N = np.asarray(N, float).ravel()
        e, n = E.copy(), N.copy()
        for _ in range(it):
            d = self.tps(np.c_[e, n]); e, n = E - d[:, 0], N - d[:, 1]
        return self.start.utm2p(e, n)


def load_start(path):
    M = json.load(open(path))
    meta = M['_meta']
    return {k: StartSheet(v, meta) for k, v in M.items() if not k.startswith('_')}, meta
