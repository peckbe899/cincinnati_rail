"""Which viewing angle for the Fountain Square 3D view? (2026-10-05, Ben: "I think it needs analysis to see what the best
viewing angle (up-down and 360)."). Scores every facing direction (15-degree steps, true compass) at a range of elevations,
reproducing fs_3d.py's projection and draw order (deepest level first, far to near within a level, flights and elevators
after the floor they rise from), so 'visible' means visible in the drawing as made. Depths 1.4 times, no exploding.
Writes views.csv; fs_views_plot.py draws the charts."""
import csv
import numpy as np
from shapely.geometry import Polygon, Point, box, MultiPoint
from shapely.ops import unary_union
from fs_model import *

K = 1.4
ZD = {lv: -Z[lv] * K for lv in Z}
NORTH_OFF = 11.0                                     # true north is 11 degrees clockwise of frame north (Vine runs 349 true)
FRAMES = list(range(0, 360, 15))                     # frame bearing the viewer looks toward (0 = up Vine); includes the grid diagonals
FACINGS = [(b - 11) % 360 for b in FRAMES]           # the same, as true compass bearings
ELEVS = [12, 16, 20, 24, 28, 32, 36, 40, 45]
LEVEL_STEP = Z[-1] * K                               # one Metro level on the page before projection, m


def holes(level):
    hs = [well(f).buffer(0.15, join_style=2) for f in FLIGHTS if f['top'] == level]   # the well only, not the whole flight
    return unary_union(hs) if hs else Polygon()


HOLES = {lv: holes(lv) for lv in (-1, -1.5, -2, -3, -4)}
COURT = next(p for p in PARTS if p['kind'] == 'court')
COURT_FLIGHTS = [i for i, f in enumerate(FLIGHTS) if f['geom'].intersection(COURT['geom']).area > 0.5 * f['geom'].area]
COURT_LIFTS = [i for i, l in enumerate(LIFTS) if COURT['geom'].contains(Point(l['xy']))]


def score(facing, elev):
    th = np.radians(facing + NORTH_OFF); ph = np.radians(elev)
    c, s, sp, cp = np.cos(th), np.sin(th), np.sin(ph), np.cos(ph)
    P = lambda x, y, z: (x * c - y * s, (x * s + y * c) * sp + z * cp)
    depth = lambda x, y: x * s + y * c
    far = np.array([s, c])

    def proj(g, z, t):
        out = []
        for q in (list(g.geoms) if hasattr(g, 'geoms') else [g]):
            if q.geom_type != 'Polygon' or q.is_empty:
                continue
            top = Polygon([P(x, y, z) for x, y in q.exterior.coords], [[P(x, y, z) for x, y in r.coords] for r in q.interiors])
            bot = Polygon([P(x, y, z - t) for x, y in q.exterior.coords])
            out += [top.buffer(0), bot.buffer(0)]
        return unary_union(out) if out else Polygon()

    E = []                                            # painter's order: (screen polygon, category, weight, tag)
    for lv in (-4, -3, -2, -1.5, -1):
        z = ZD[lv]
        cls_ = lambda p: 'court' if p['kind'] == 'court' else ('tri' if p['op'] == 'tri' else 'metro')
        comps = []
        for cl in ('metro', 'tri', 'court'):
            gs = [p for p in PARTS if p['level'] == lv and cls_(p) == cl]
            if gs:
                u = unary_union([p['geom'].buffer(0.05, join_style=2) for p in gs]).buffer(-0.05, join_style=2)
                for q in (list(u.geoms) if hasattr(u, 'geoms') else [u]):
                    # share of this slab that is platform, for the platform test
                    plat = sum(p['geom'].intersection(q).area for p in gs if p['kind'] in ('plat', 'island')) / q.area
                    comps.append((depth(*q.centroid.coords[0]), cl, q, plat))
        for _, cl, q, plat in sorted(comps, key=lambda r: -r[0]):
            g = proj(q.difference(HOLES[lv]), z, 1.1)
            # a merged slab counts toward 'platforms' by its platform share, toward 'hall' by the rest
            E.append(dict(g=g, cat='court' if cl == 'court' else 'mixed', plat=plat, deep=lv in (-3, -4), w=g.area,
                          glass=(cl == 'tri' and lv == -2)))   # TRI hall floors drawn see-through: they hide nothing
        tr = [(depth(*((np.array(t['back']) + np.array(t['front'])) / 2)), t) for t in TRACKS if t['level'] == lv]
        for _, it in sorted(tr, key=lambda r: -r[0]):
            b, f = np.array(it['back']), np.array(it['front']); d = (f - b) / np.hypot(*(f - b))
            nrm = np.array([-d[1], d[0]])
            shape = Polygon([b - d * 10 + nrm * 1.7, f + d * 21 + nrm * 1.7, f + d * 21 - nrm * 1.7, b - d * 10 - nrm * 1.7])
            g = proj(shape, z - 0.3, 0.0)
            E.append(dict(g=g, cat='track', deep=lv in (-3, -4), w=g.area))
        if lv == -1:                                  # the court's far walls
            co = np.asarray(COURT['geom'].exterior.coords)
            for a_, b_ in zip(co[:-1], co[1:]):
                mid = (a_ + b_) / 2; n = np.array([b_[1] - a_[1], -(b_[0] - a_[0])]); n = n / np.hypot(*n)
                out = n if not COURT['geom'].contains(Point(mid + n * 0.05)) else -n
                if depth(*(mid + out)) > depth(*mid):
                    g = Polygon([P(*a_, z), P(*b_, z), P(*b_, 0.0), P(*a_, 0.0)]).buffer(0)
                    E.append(dict(g=g, cat='wall', deep=False, w=g.area))
        up = [(depth(*f['geom'].centroid.coords[0]), 'f', i, f) for i, f in enumerate(FLIGHTS) if f['bot'] == lv]
        for i, l in enumerate(LIFTS):                 # elevators as fs_3d.py now draws them (Republic manner)
            lv_ = l['levels']
            for upper, lower in zip(lv_[:-1], lv_[1:]):
                if lower == lv:
                    up.append((depth(*l['xy']) + 0.02, 'l', i, (l, ZD[lv], 5.0 if upper == 0 else ZD[upper] - 1.1)))
            if lv_[0] == lv:
                up.append((depth(*l['xy']), 'l', i, (l, ZD[lv], ZD[lv] + 4.0)))
        for _, kind, i, it in sorted(up, key=lambda r: -r[0]):
            if kind == 'f':
                s0, e0 = np.array(it['start']), np.array(it['end']); d = np.array(it['d']); L = np.hypot(*(e0 - s0))
                zt, zb = ZD[it['top']], ZD[it['bot']]
                # the flight as fs_3d.py draws it: a solid (stair 1 m deep, escalator 1.6 m), faces toward the viewer only
                n_ = np.array([-d[1], d[0]]); w_ = it['w']; t_ = 1.6 if it['kind'] == 'esc' else 1.0
                P3 = lambda u, o, zz: P(*(s0 + d * u + n_ * o), zz)
                tan_a = (zt - zb) / L
                top_up = np.tan(ph) > tan_a * (d @ far)
                faces = []
                if top_up:
                    faces.append([P3(0, -w_ / 2, zt), P3(L, -w_ / 2, zb), P3(L, w_ / 2, zb), P3(0, w_ / 2, zt)])
                else:
                    faces.append([P3(0, -w_ / 2, zt - t_), P3(L, -w_ / 2, zb - t_), P3(L, w_ / 2, zb - t_), P3(0, w_ / 2, zt - t_)])
                for o, out in ((-w_ / 2, -n_), (w_ / 2, n_)):
                    if out @ (-far) > 0:
                        faces.append([P3(0, o, zt), P3(L, o, zb), P3(L, o, zb - t_), P3(0, o, zt - t_)])
                for u, zz, out in ((0.0, zt, -d), (L, zb, d)):
                    if out @ (-far) > 0:
                        faces.append([P3(u, -w_ / 2, zz), P3(u, w_ / 2, zz), P3(u, w_ / 2, zz - t_), P3(u, -w_ / 2, zz - t_)])
                g = unary_union([Polygon(fc).buffer(0) for fc in faces])
                A, B = np.array(P(*s0, zt)), np.array(P(*e0, zb))
                width = g.area / max(np.hypot(*(B - A)), 1e-6)                  # how wide the flight reads on the page, m
                # heights legible: a flight's drop on the page is its real rise (rise cos ph) plus or minus its plan run seen in
                # depth (run (d.far) sin ph). The share that is real rise is what lets equal rises look equal.
                dist = abs(d @ far) * np.tan(ph) / tan_a
                E.append(dict(g=g, cat='flight', deep=it['bot'] in (-3, -4), w=np.hypot(L, zt - zb), face=1.0 if top_up else 0.0,
                              readable=1.0 if width >= 1.5 else 0.0, width=width, court=i in COURT_FLIGHTS, true_h=1 / (1 + dist)))
            else:
                l_, z0, z1 = it
                x, y = l_['xy']
                pts = [P(x + a, y + b, zz) for a in (-1.3, 1.3) for b in (-1.3, 1.3) for zz in (z0, z1)]
                g = MultiPoint(pts).convex_hull
                E.append(dict(g=g, cat='lift', deep=False, w=g.area, court=i in COURT_LIFTS))
    # visible part of each element: what nothing drawn after it covers
    U = Polygon()
    for e in reversed(E):
        a = e['g'].area
        e['vis'] = (e['g'].difference(U).area / a) if a > 1e-6 else 1.0
        if not e.get('glass'):
            U = U.union(e['g'])
    union_area = U.area
    sum_area = sum(e['g'].area for e in E)

    def wmean(sel, key='vis'):
        es = [e for e in E if sel(e)]
        tw = sum(e['w'] for e in es)
        return sum(e[key] * e['w'] for e in es) / tw if tw else np.nan
    fl = [e for e in E if e['cat'] == 'flight']
    stairs_read = sum(e['readable'] * e['w'] for e in fl) / sum(e['w'] for e in fl)      # share (by length) at least 1.5 m wide on the page
    court_es = [e for e in E if e['cat'] == 'court' or e.get('court')]
    court = np.mean([e['vis'] * (e.get('readable', 1.0)) for e in court_es])
    allpts = np.array([v for p in PARTS for v in p['geom'].exterior.coords])
    dep = allpts @ far
    height = LEVEL_STEP * np.cos(ph) / ((dep.max() - dep.min()) * np.sin(ph))
    minx, miny, maxx, maxy = U.bounds
    return dict(facing=facing, elev=elev,
                platforms=(sum(e['vis'] * e['w'] * e.get('plat', 0) for e in E) / sum(e['w'] * e.get('plat', 0) for e in E)),
                connections=wmean(lambda e: e['cat'] in ('flight', 'lift')),
                stairs_read=stairs_read,
                stairs_face=sum(e['face'] * e['w'] for e in fl) / sum(e['w'] for e in fl),
                deep=wmean(lambda e: e['deep']),
                court=court,
                overlap=sum_area / union_area,
                height=sum(e['true_h'] * e['w'] for e in fl) / sum(e['w'] for e in fl),
                spread=height,
                aspect=(maxx - minx) / (maxy - miny))


if __name__ == '__main__':
    import time
    t0 = time.time(); rows = []
    for el in ELEVS:
        for fc in FACINGS:
            rows.append(score(fc, el))
    print('views:', len(rows), 'in %.0f s' % (time.time() - t0))
    with open('views.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
