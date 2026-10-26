"""Per-view detail for the 3D drawing: flights seen from behind or as slivers, and how much of the TRI islands and of the
lower half of each TRI escalator is visible. Same projection and draw order as fs_3d.py (merged floors, wells, Republic-style
elevators). Usage: fs_vis_detail.py THETA_FRAME PHI [K]"""
import sys
import numpy as np
from shapely.geometry import Polygon, MultiPoint
from shapely.ops import unary_union
from fs_model import *


def detail(theta, phi, K=1.4):
    ZD = {lv: -Z[lv] * K for lv in Z}
    th, ph = np.radians(theta), np.radians(phi)
    c, s, sp, cp = np.cos(th), np.sin(th), np.sin(ph), np.cos(ph)
    P = lambda x, y, z: (x * c - y * s, (x * s + y * c) * sp + z * cp)
    depth = lambda x, y: x * s + y * c
    far = np.array([s, c])
    cls_ = lambda p: 'court' if p['kind'] == 'court' else ('tri' if p['op'] == 'tri' else 'metro')

    def proj(g, z, t):
        out = []
        for q in (list(g.geoms) if hasattr(g, 'geoms') else [g]):
            if q.geom_type != 'Polygon' or q.is_empty:
                continue
            out += [Polygon([P(x, y, z) for x, y in q.exterior.coords]).buffer(0), Polygon([P(x, y, z - t) for x, y in q.exterior.coords]).buffer(0)]
        return unary_union(out) if out else Polygon()
    E = []
    for lv in (-4, -3, -2, -1.5, -1):
        z = ZD[lv]
        hl = unary_union([well(f).buffer(0.15, join_style=2) for f in FLIGHTS if f['top'] == lv] or [Polygon()])
        comps = []
        for cl in ('metro', 'tri', 'court'):
            gs = [p for p in PARTS if p['level'] == lv and cls_(p) == cl]
            if gs:
                u = unary_union([p['geom'].buffer(0.05, join_style=2) for p in gs]).buffer(-0.05, join_style=2)
                for q in (list(u.geoms) if hasattr(u, 'geoms') else [u]):
                    comps.append((depth(*q.centroid.coords[0]), q))
        for _, q in sorted(comps, key=lambda r: -r[0]):
            tag = 'island' if lv in (-3, -4) else None
            E.append(dict(g=proj(q.difference(hl), z, 1.1), tag=tag, name='floor %s' % lv))
        up = [(depth(*f['geom'].centroid.coords[0]), 'f', i, f) for i, f in enumerate(FLIGHTS) if f['bot'] == lv]
        for i, l in enumerate(LIFTS):
            for upper, lower in zip(l['levels'][:-1], l['levels'][1:]):
                if lower == lv:
                    up.append((depth(*l['xy']) + 0.02, 'l', i, (l, ZD[lv], 5.0 if upper == 0 else ZD[upper] - 1.1)))
            if l['levels'][0] == lv:
                up.append((depth(*l['xy']), 'l', i, (l, ZD[lv], ZD[lv] + 4.0)))
        for _, kind, i, it in sorted(up, key=lambda r: -r[0]):
            if kind == 'f':
                s0, e0 = np.array(it['start']), np.array(it['end']); d = np.array(it['d']); L = np.hypot(*(e0 - s0))
                zt, zb = ZD[it['top']], ZD[it['bot']]; n = np.array([-d[1], d[0]]); w = it['w']
                zf = lambda p_: zt + ((np.asarray(p_) - s0) @ d) / L * (zb - zt)
                co = np.asarray(it['geom'].exterior.coords)[:-1]
                g = unary_union([Polygon([P(x, y, zf((x, y)) - dz) for x, y in co]).buffer(0) for dz in (0.0, 0.8)])
                m0 = s0 + d * L * 0.6                     # lower 40% of the flight: its landing end
                low = Polygon([P(*q_, zf(q_)) for q_ in (m0 - n * w / 2, e0 - n * w / 2, e0 + n * w / 2, m0 + n * w / 2)]).buffer(0)
                tan_a = (zt - zb) / L
                back = not (np.tan(ph) > tan_a * (d @ far))
                A, B = np.array(P(*s0, zt)), np.array(P(*e0, zb)); Ls = np.hypot(*(B - A))
                width = Polygon([P(*q_, zf(q_)) for q_ in co]).area / max(Ls, 1e-6)
                E.append(dict(g=g, low=low, tag='tri_esc' if it['bot'] in (-3, -4) else 'flight', i=i, back=back, width=width))
            else:
                l, z0, z1 = it; x, y = l['xy']
                E.append(dict(g=MultiPoint([P(x + a, y + b, zz) for a in (-1.3, 1.3) for b in (-1.3, 1.3) for zz in (z0, z1)]).convex_hull, tag='lift'))
    U = Polygon()
    for e in reversed(E):
        if 'low' in e:
            e['low_vis'] = e['low'].difference(U).area / max(e['low'].area, 1e-6)
        e['vis'] = e['g'].difference(U).area / max(e['g'].area, 1e-6)
        U = U.union(e['g'])
    fl = [e for e in E if 'back' in e]
    isl = [e for e in E if e['tag'] == 'island']
    tri = [e for e in E if e['tag'] == 'tri_esc']
    return dict(back=sum(e['back'] for e in fl), thin=sum(e['width'] < 1.0 for e in fl), n=len(fl),
                islands=np.mean([e['vis'] for e in isl]), tri_landings=np.mean([e['low_vis'] for e in tri]),
                tri_landing_min=min(e['low_vis'] for e in tri), flights=fl, tri=tri)


if __name__ == '__main__':
    th, ph = float(sys.argv[1]), float(sys.argv[2]); K = float(sys.argv[3]) if len(sys.argv) > 3 else 1.4
    r = detail(th, ph, K)
    print('behind %d  thin %d  of %d  islands visible %.2f  TRI escalator landings visible %.2f (worst %.2f)' %
          (r['back'], r['thin'], r['n'], r['islands'], r['tri_landings'], r['tri_landing_min']))
