"""Map points between plates through the cufp world models (data/sanborn/cufp/<N>/model.npz).

model.npz holds an inverse grid: world (E, N) on a 2 m lattice -> plate pixel (px, py).
world_to_px reads it by bilinear interpolation; px_to_world inverts it by a local search
plus Gauss-Newton on the bilinear grid. Read-only use of repo data.
"""
import numpy as np
ROOT = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/cufp/'
_M = {}


def model(plate):
    if plate not in _M:
        m = np.load(f'{ROOT}{plate}/model.npz')
        _M[plate] = dict(E0=float(m['E0']), N1=float(m['N1']), step=float(m['step']), px=m['px'], py=m['py'])
    return _M[plate]


def world_to_px(plate, E, N):
    m = model(plate)
    j = (E - m['E0']) / m['step']; i = (m['N1'] - N) / m['step']
    i0, j0 = int(np.floor(i)), int(np.floor(j))
    if i0 < 0 or j0 < 0 or i0 + 1 >= m['px'].shape[0] or j0 + 1 >= m['px'].shape[1]:
        return None
    di, dj = i - i0, j - j0
    out = []
    for g in (m['px'], m['py']):
        q = g[i0:i0 + 2, j0:j0 + 2].astype(float)
        if (q < -1e5).any():
            return None
        out.append((1 - di) * ((1 - dj) * q[0, 0] + dj * q[0, 1]) + di * ((1 - dj) * q[1, 0] + dj * q[1, 1]))
    return out


def px_to_world(plate, x, y):
    m = model(plate)
    d = np.abs(m['px'] - x) + np.abs(m['py'] - y)
    i, j = np.unravel_index(np.argmin(d), d.shape)
    E = m['E0'] + j * m['step']; N = m['N1'] - i * m['step']
    for _ in range(8):                      # Gauss-Newton on the interpolated grid
        p = world_to_px(plate, E, N)
        if p is None:
            break
        h = 0.5
        pe = world_to_px(plate, E + h, N); pn = world_to_px(plate, E, N + h)
        if pe is None or pn is None:
            break
        J = np.array([[(pe[0] - p[0]) / h, (pn[0] - p[0]) / h], [(pe[1] - p[1]) / h, (pn[1] - p[1]) / h]])
        dE, dN = np.linalg.solve(J, np.array([x - p[0], y - p[1]]))
        E += dE; N += dN
        if abs(dE) + abs(dN) < 1e-3:
            break
    return E, N


def px_to_px(src, dst, x, y):
    E, N = px_to_world(src, x, y)
    return world_to_px(dst, E, N)


if __name__ == '__main__':
    import sys
    s, d = sys.argv[1], sys.argv[2]
    pts = [tuple(map(float, p.split(','))) for p in sys.argv[3:]]
    for x, y in pts:
        E, N = px_to_world(s, x, y)
        print(f'{s} ({x:.0f},{y:.0f}) -> world ({E:.1f},{N:.1f}) -> {d}', world_to_px(d, E, N))
