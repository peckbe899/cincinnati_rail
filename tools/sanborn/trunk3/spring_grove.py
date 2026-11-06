try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Spring Grove Avenue moved west through Ivorydale to clear ORR X2 round the RER B island by 3 m (Ben, 26 October: shift it west, keep APEx straight)
import sys, json, numpy as np
from shapely.geometry import LineString, Point, shape
from scipy.ndimage import minimum_filter1d, gaussian_filter1d
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'trunk3'); import north as N
def new_geom(coords, half_w):
    c = np.asarray(coords, float)[:, :2]; g = LineString(c); n = int(g.length / 4) + 1
    P = np.array([g.interpolate(x).coords[0] for x in np.linspace(0, g.length, n)])
    s = np.array([N.FD.proj(q) for q in P]); base = np.array([N.FD.at(x)[0] for x in s]); e = np.array([N.FD.at(x, 1.0)[0] for x in s]) - base
    o = np.einsum('ij,ij->i', P - base, e)
    near = (s > N.S0) & (s < N.S_IV1 + N.TP + 300) & (np.abs(o) < 80)
    req = np.array([N.o_x2(0)(x) - 4.2 - 3.4 - half_w for x in s])            # street centre must be at or west of this
    push = np.where(near, np.minimum(0.0, req - o), 0.0)                        # negative = west
    push = minimum_filter1d(push, 31); push = gaussian_filter1d(push, 12)       # taper in and out (about 120 m each side)
    Q = P + e * push[:, None]
    return LineString(Q).simplify(0.2), float(push.min())
if __name__ == '__main__':
    BJ = json.load(open(SP + 'deckpage/basin.json'))
    f = [f for f in BJ['features'] if f['properties'].get('id') == 'SZ0326'][0]
    g, m = new_geom(f['geometry']['coordinates'], f['properties']['width_m'] / 2)
    old = LineString(np.asarray(f['geometry']['coordinates'])[:, :2])
    print('max move %.1f m; Hausdorff %.1f; length %.0f -> %.0f' % (-m, old.hausdorff_distance(g), old.length, g.length))
    json.dump(dict(name='Spring Grove Avenue', id_at_build='SZ0326', start=list(old.coords[0]), end=list(old.coords[-1]),
                   coords=[[round(x, 1), round(y, 1)] for x, y in g.coords]), open(SP + 'wh/street_shifts.json', 'w'))
