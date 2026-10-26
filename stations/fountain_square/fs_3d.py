"""Fountain Square, the 3D underground view (2026-10-05), from fs_model.py, in the manner of the Republic station view
(station_ref.py): floors as slabs, stairs and escalators as sloping slabs, elevators as shafts, tracks as broad arrows the way
their trains run (right-hand running), entrances numbered at the street. Depths times K (Ben chose 1.4 for Republic).
argv: OUT THETA PHI K"""
import sys, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.path import Path
from matplotlib.patches import PathPatch
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union
from fs_model import *
from fs_geom import put_badge, badge_box, COLS, HERE
from matplotlib.offsetbox import AnnotationBbox

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'fs_3d.png')
THETA = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
PHI = float(sys.argv[3]) if len(sys.argv) > 3 else 26.0
K = float(sys.argv[4]) if len(sys.argv) > 4 else 1.4
EXPL = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0   # extra drop for the TRI levels, m on the page (exploded view)
ZD = {lv: -Z[lv] * K for lv in Z}                      # drawing heights (street 0, down negative)
EXPL2 = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0  # extra drop for Line 2's level (-2)
GHOST = float(sys.argv[7]) if len(sys.argv) > 7 else 1.0  # (unused since 2026-10-05)
TRI_GLASS = float(sys.argv[8]) if len(sys.argv) > 8 else 0.5   # opacity of the TRI halls' floors, so their escalators show down to the islands
ZD[-2] -= EXPL2; ZD[-3] -= EXPL + EXPL2; ZD[-4] -= EXPL * 1.5 + EXPL2
ZD[-1.5] = ZD[-1] + (ZD[-2] - ZD[-1]) * (Z[-1.5] - Z[-1]) / (Z[-2] - Z[-1])
T_ = 1.1                                                # slab thickness, m
COL = dict(top='#dfe0e9', side='#ada397', edge='#2b2b2b', tri='#f3d9dc', tri_side='#c9a2a6', court='#d5ebc8', court_side='#9fbf92',
           stair='#f3dccb', stair_side='#cdb3a0', esc='#857a6d', esc_side='#5f564c', lift='#c6daf4', lift_side='#9fbde6',
           gate='#c0303a', gate_side='#7e1a20', arrow='#3fbf3f', xunder='#ece6d6')
TCOL = {'1': (COLS['1'], '#a68500'), '7': (COLS['7'], '#00634f'), '2': (COLS['2'], '#3f8fa5'), 'A': (COLS['A'], '#8a0010'),
        'D': (COLS['D'], '#005c22'), 'B': (COLS['B'], '#003a6b')}
TERM = {('1', 'EB'): 'to Southgate', ('1', 'WB'): 'to Finneytown', ('7', 'EB'): 'to Roselawn', ('7', 'WB'): 'to Visitation',
        ('2', 'NB'): 'to Anthony Wayne', ('2', 'SB'): 'to Winston Park', ('A', 'EB'): 'to Walnut Hills', ('A', 'WB'): 'to Union Terminal',
        ('D', 'EB'): 'to Newport', ('D', 'WB'): 'to Norwood', ('B', 'NB'): 'to Dayton', ('B', 'SB'): 'to Falmouth'}
BADGE = {'1': 'Metro_1', '7': 'Metro_7', '2': 'Metro_2', 'A': 'TRI_A', 'D': 'TRI_D', 'B': 'TRI_B'}


class V:
    c, s = np.cos(np.radians(THETA)), np.sin(np.radians(THETA))
    sp, cp = np.sin(np.radians(PHI)), np.cos(np.radians(PHI))

    @classmethod
    def P(cls, x, y, z):
        xr, yr = x * cls.c - y * cls.s, x * cls.s + y * cls.c
        return xr, yr * cls.sp + z * cls.cp

    @classmethod
    def depth(cls, x, y):                                  # larger = farther from the viewer
        return x * cls.s + y * cls.c


fig = plt.figure(figsize=(24, 15.5))
ax = fig.add_axes([0.0, 0.02, 1.0, 0.88]); ax.set_aspect(1); ax.axis('off')


def parts_of(g):
    if g.is_empty:
        return []
    return [q for q in (list(g.geoms) if hasattr(g, 'geoms') else [g]) if q.geom_type == 'Polygon']


def patch(pts, zo, fc, ec=COL['edge'], lw=0.6, alpha=1.0):
    ax.add_patch(plt.Polygon(np.asarray(pts), closed=True, facecolor=fc, edgecolor=ec, lw=lw, zorder=zo, joinstyle='round', alpha=alpha))


def slab(g, z, zo, top=COL['top'], side=COL['side'], t=T_, lw=0.6, alpha=1.0):
    for q in parts_of(g):
        q = q.buffer(0)
        for ring in [q.exterior] + list(q.interiors):
            co = np.asarray(ring.coords)
            for a, b in zip(co[:-1], co[1:]):
                mid = (a + b) / 2; n = np.array([b[1] - a[1], -(b[0] - a[0])]); nn = np.hypot(*n)
                if nn < 1e-6:
                    continue
                outward = n if not q.contains(Point(mid + n / nn * 0.05)) else -n
                if V.depth(*(mid + outward * 0.01)) < V.depth(*mid):
                    patch([V.P(*a, z), V.P(*b, z), V.P(*b, z - t), V.P(*a, z - t)], zo, side, lw=0.45, alpha=alpha)
        verts, codes = [], []
        for ring in [q.exterior] + list(q.interiors):
            xy = [V.P(x, y, z) for x, y in ring.coords]
            verts += xy; codes += [Path.MOVETO] + [Path.LINETO] * (len(xy) - 2) + [Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(verts, codes), facecolor=top, edgecolor=COL['edge'], lw=lw, zorder=zo + 0.001, alpha=alpha))


def ramp(f, zo):
    """A flight as a solid, the way station cutaways draw them (Ben, 2026-10-05: "the stairs look weird"): a stair has a
    stepped side (its stringer, 1 m deep), an escalator a truss side (1.6 m deep). Only the faces turned toward the viewer
    are drawn, so a flight whose top faces away shows its underside instead of a flipped top, and every flight shows the
    side turned toward the viewer, which carries its steps even when its top is seen edge-on."""
    d = np.array(f['d']); s0 = np.array(f['start']); e0 = np.array(f['end'])
    L = np.hypot(*(e0 - s0)); zt, zb = ZD[f['top']], ZD[f['bot']]
    n = np.array([-d[1], d[0]]); w = f['w']; esc = f['kind'] == 'esc'
    t = 1.6 if esc else 1.0
    far = np.array([V.s, V.c])
    top_c, side_c, under_c = (COL['esc'], COL['esc_side'], '#4e463e') if esc else (COL['stair'], COL['stair_side'], '#bfa18c')
    zf = lambda u: zt + (zb - zt) * u / L                  # nosing line along the flight, u = distance from the top edge
    tan_a = (zt - zb) / L
    top_up = np.tan(np.radians(PHI)) > tan_a * (d @ far)   # top surface turned toward the viewer
    P3 = lambda u, o, z: V.P(*(s0 + d * u + n * o), z)
    # underside
    if not top_up:
        patch([P3(0, -w / 2, zt - t), P3(L, -w / 2, zb - t), P3(L, w / 2, zb - t), P3(0, w / 2, zt - t)], zo, under_c, lw=0.45)
    # ends
    for u, z, out in ((0.0, zt, -d), (L, zb, d)):
        if out @ (-far) > 0:
            patch([P3(u, -w / 2, z), P3(u, w / 2, z), P3(u, w / 2, z - t), P3(u, -w / 2, z - t)], zo + 0.001, side_c, lw=0.45)
    # the side turned toward the viewer
    for o, out in ((-w / 2, -n), (w / 2, n)):
        if out @ (-far) <= 0:
            continue
        if esc:
            edge = [P3(0, o, zt), P3(L, o, zb)]
        else:
            N = max(4, int(round(L / 1.0)))                # stylised steps, about one per metre
            edge = [P3(0, o, zt)]
            for k in range(N):
                u0, u1 = L * k / N, L * (k + 1) / N
                edge += [P3(u1, o, zf(u0)), P3(u1, o, zf(u1))]
        patch(edge + [P3(L, o, zb - t), P3(0, o, zt - t)], zo + 0.002, side_c, lw=0.45)
        if esc:                                            # handrail line along the balustrade
            A, B = P3(0, o, zt + 0.9), P3(L, o, zb + 0.9)
            ax.plot([A[0], B[0]], [A[1], B[1]], color='#2b2b2b', lw=0.5, zorder=zo + 0.004)
    # top
    if top_up:
        patch([P3(0, -w / 2, zt), P3(L, -w / 2, zb), P3(L, w / 2, zb), P3(0, w / 2, zt)], zo + 0.003, top_c, lw=0.5)
        if esc:
            for k in range(1, f['units']):
                o = -w / 2 + k * w / f['units']
                A, B = P3(0, o, zt), P3(L, o, zb)
                ax.plot([A[0], B[0]], [A[1], B[1]], color='#c9c0b4', lw=0.4, zorder=zo + 0.0035)
        else:
            N = max(4, int(round(L / 1.0)))
            for k in range(1, N):
                u = L * k / N; A, B = P3(u, -w / 2, zf(u)), P3(u, w / 2, zf(u))
                ax.plot([A[0], B[0]], [A[1], B[1]], color='#d9bfae', lw=0.35, zorder=zo + 0.0035)


def prism(xy, z0, z1, zo, w=2.6):
    c = np.array(xy); h = w / 2
    sq = np.array([c + np.array(o) * h for o in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    for a, b in zip(sq, np.roll(sq, -1, axis=0)):
        mid = (a + b) / 2; out = mid - c
        if V.depth(*(mid + out * 0.01)) < V.depth(*mid):
            patch([V.P(*a, z0), V.P(*b, z0), V.P(*b, z1), V.P(*a, z1)], zo, COL['lift_side'], lw=0.45)
    patch([V.P(x, y, z1) for x, y in sq], zo + 0.001, COL['lift'], lw=0.45)


def gate_blocks(line, z, zo, step=1.3, w=0.8, h=1.3):
    n = max(int(line.length / step), 1)
    for k in range(n):
        c = line.interpolate((k + 0.5) * line.length / n)
        sq = np.array([(c.x - w / 2, c.y - w / 2), (c.x + w / 2, c.y - w / 2), (c.x + w / 2, c.y + w / 2), (c.x - w / 2, c.y + w / 2)])
        patch([V.P(x, y, z + h) for x, y in sq], zo + k * 1e-4, COL['gate'], ec=COL['gate_side'], lw=0.25)


ARROWS = []


def track_arrow(t, zo, hw=1.7, ext=14.0, tail=10.0, hh=3.4, hl=7.0):
    back, front = np.array(t['back'], float), np.array(t['front'], float)
    d = (front - back) / np.hypot(*(front - back)); n = np.array([-d[1], d[0]])
    t0, bb = back - d * tail, front + d * ext
    shape = LineString([t0, bb]).buffer(hw, cap_style='round', quad_segs=10).union(Polygon([bb + n * hh, bb + d * hl, bb - n * hh]))
    z = ZD[t['level']] - 0.3
    fc, ec = TCOL[t['line']]
    patch([V.P(x, y, z) for x, y in shape.exterior.coords], zo, fc, ec=ec, lw=0.6)
    ARROWS.append(dict(tip=bb + d * hl, d=d, z=z, line=t['line'], dir=t['dir']))


def holes(level):
    hs = [well(f).buffer(0.15, join_style=2) for f in FLIGHTS if f['top'] == level]   # the well only, not the whole flight
    return unary_union(hs) if hs else Polygon()


def klass(p):
    return 'court' if p['kind'] == 'court' else ('tri' if p['op'] == 'tri' else 'metro')


CLASS_COL = {'metro': (COL['top'], COL['side']), 'tri': (COL['tri'], COL['tri_side']), 'court': (COL['court'], COL['court_side'])}
# each level a shade of its own (Ben, 2026-10-05: "give the levels slightly different floor colors"): Metro grey and TRI pink
# keep their hue and step a little darker with each level down, so the levels read apart
LEVEL_COL = {('metro', -1): ('#e6e7ee', '#b3aa9f'), ('metro', -1.5): ('#dcdee8', '#a9a196'), ('metro', -2): ('#cdd3e3', '#9e988e'),
             ('tri', -2): ('#f6e0e2', '#cfaaae'), ('tri', -3): ('#eecad0', '#c39ba1'), ('tri', -4): ('#e3b3bd', '#b4878f')}


def colour(p):
    if p['kind'] == 'court':
        return COL['court'], COL['court_side']
    if p['kind'] == 'xunder':
        return COL['xunder'], COL['side']
    if p['op'] == 'tri':
        return COL['tri'], COL['tri_side']
    return COL['top'], COL['side']


# ---------------- street plane: faint curb lines and names, behind everything ----------------
from fs_geom import NS, EW
SX, SY = (-200, 185), (-150, 240)
for nm, (u0, u1) in NS.items():
    if SX[0] < u0 < SX[1]:
        for u in (u0, u1):
            A, B = V.P(u, SY[0], 0), V.P(u, SY[1], 0); ax.plot([A[0], B[0]], [A[1], B[1]], color='#b9b3a8', lw=0.6, zorder=0.2)
        X, Y = V.P((u0 + u1) / 2, SY[1] - 8, 0); ax.text(X, Y, nm, fontsize=9, style='italic', color='#8a847a', ha='center', va='center', zorder=0.3)
for nm, (v0, v1) in EW.items():
    if SY[0] < v0 < SY[1]:
        for v in (v0, v1):
            A, B = V.P(SX[0], v, 0), V.P(SX[1], v, 0); ax.plot([A[0], B[0]], [A[1], B[1]], color='#b9b3a8', lw=0.6, zorder=0.2)
        X, Y = V.P(SX[0] + 8, (v0 + v1) / 2, 0); ax.text(X, Y, nm, fontsize=9, style='italic', color='#8a847a', ha='center', va='center', zorder=0.3)
sq = [V.P(u, v, 0) for u, v in ((-44.5, -55), (33, -55), (33, 0), (-44.5, 0), (-44.5, -55))]
ax.plot([q[0] for q in sq], [q[1] for q in sq], color='#9fbf92', lw=0.9, zorder=0.2)

# ---------------- draw, deepest level first; within a level far to near ----------------
ORDER = [-4, -3, -2, -1.5, -1]
H_IN = 4.0
STREET_LIFTS = []
zo = 1.0
for lv in ORDER:
    z = ZD[lv]
    # floors of one kind that touch are drawn as one slab, so there is no seam where a passage meets a hall (Ben, 2026-10-05:
    # "a lot of edges don't line up"); Metro grey, TRI pink and the court green stay separate
    comps = []
    for cl in ('metro', 'tri', 'court'):
        gs = [p['geom'] for p in PARTS if p['level'] == lv and klass(p) == cl]
        if gs:
            u = unary_union([g.buffer(0.05, join_style=2) for g in gs]).buffer(-0.05, join_style=2)
            comps += [(V.depth(*q.centroid.coords[0]), cl, q) for q in parts_of(u)]
    hl = holes(lv)
    for _, cl, q in sorted(comps, key=lambda r: -r[0]):
        top, side = LEVEL_COL.get((cl, lv), CLASS_COL[cl])
        slab(q.difference(hl), z, zo, top=top, side=side, alpha=TRI_GLASS if (cl == 'tri' and lv == -2) else 1.0)
        zo += 0.01
    # tracks after the floors: they lie in the trackways, in front of the far platform's edge
    tr = [(V.depth(*((np.array(t['back']) + np.array(t['front'])) / 2)), t) for t in TRACKS if t['level'] == lv]
    for _, t in sorted(tr, key=lambda r: -r[0]):
        track_arrow(t, zo); zo += 0.01
    for g in GATES:
        if g['level'] == lv:
            gate_blocks(g['geom'], z, zo); zo += 0.01
    # the sunken court's retaining walls: the far walls, inner faces toward the viewer, up to the square (near walls cut away)
    for p in PARTS:
        if p['level'] == lv and p['kind'] == 'court':
            co = np.asarray(p['geom'].exterior.coords); q = p['geom']
            for a_, b_ in zip(co[:-1], co[1:]):
                mid = (a_ + b_) / 2; n = np.array([b_[1] - a_[1], -(b_[0] - a_[0])]); n = n / np.hypot(*n)
                out = n if not q.contains(Point(mid + n * 0.05)) else -n
                if V.depth(*(mid + out)) > V.depth(*mid):
                    patch([V.P(*a_, z), V.P(*b_, z), V.P(*b_, 0.0), V.P(*a_, 0.0)], zo, '#c3d6b5', ec='#5f7f50', lw=0.6, alpha=0.9); zo += 0.001
            rim = [V.P(x, y, 0.0) for x, y in co]
            ax.plot([r[0] for r in rim], [r[1] for r in rim], color='#5f7f50', lw=0.8, zorder=zo); zo += 0.01
    # everything rising from this level: flights whose foot is here, elevators whose bottom is here
    up = [(V.depth(*f['geom'].centroid.coords[0]), 'f', f) for f in FLIGHTS if f['bot'] == lv]
    # elevators as at Republic (station_ref.py): between two floors the shaft runs from the lower floor up to the underside
    # of the upper one; the car stands on the top floor it serves (H_IN high); a street elevator rises from its highest
    # underground floor to 5 m above the street and carries a green E
    for l in LIFTS:
        lvls = l['levels']
        for upper, lower in zip(lvls[:-1], lvls[1:]):
            if lower != lv:
                continue
            if upper == 0:
                up.append((V.depth(*l['xy']), 'street', (l, ZD[lv], 5.0)))
            else:
                up.append((V.depth(*l['xy']) + 0.02, 'shaft', (l, ZD[lv], ZD[upper] - T_)))
        if lvls[0] == lv:
            up.append((V.depth(*l['xy']), 'car', (l, ZD[lv], ZD[lv] + H_IN)))
    for _, kind, it in sorted(up, key=lambda r: -r[0]):
        if kind == 'f':
            ramp(it, zo)
        else:
            l, z0, z1 = it
            prism(l['xy'], z0, z1, zo)
            if kind == 'street':
                STREET_LIFTS.append(l['xy'])
        zo += 0.01

# ---------------- sheet size first, so labels can be placed clear of each other ----------------
ax.autoscale_view()
x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
x0, x1, y0, y1 = x0 - 48, x1 + 48, y0 - 10, y1 + 10
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
FW = 24.0; AH = FW * (y1 - y0) / (x1 - x0); FH = AH + 1.9
fig.set_size_inches(FW, FH); ax.set_position([0.0, 0.1 / FH, 1.0, AH / FH])
RND = fig.canvas.get_renderer()
BOXES = []
from matplotlib.transforms import Bbox


def badge_bb(X, Y, size):
    cx, cy = ax.transData.transform((X, Y)); h = size * fig.dpi / 72 / 2 + 2
    return Bbox([[cx - h, cy - h], [cx + h, cy + h]])


def free(bbs):
    return not any(b.overlaps(o) for b in bbs for o in BOXES)


for xy in STREET_LIFTS:
    X, Y = V.P(*xy, 5.0)
    t = ax.text(X, Y + 2.8, 'E', fontsize=7, color='white', weight='bold', ha='center', va='center', zorder=zo + 2,
                bbox=dict(boxstyle='circle,pad=0.22', facecolor='#2e7d4b', edgecolor='white', lw=0.8))
    BOXES.append(t.get_window_extent(RND).expanded(1.1, 1.1))
# keep labels off the sunken court
for p in PARTS:
    if p['kind'] == 'court':
        pts = np.array([ax.transData.transform(V.P(x, y, z)) for x, y in p['geom'].exterior.coords for z in (ZD[-1], 0.0)])
        BOXES.append(Bbox([pts.min(axis=0), pts.max(axis=0)]))
# ---------------- labels ----------------
halo = [pe.withStroke(linewidth=3, foreground='white')]
for e in ENT:
    f = next(f for f in FLIGHTS if f['ent'] == e['n'])
    X, Y = V.P(*f['start'], 0.0)
    rnd = e['kind'] in ('building', 'sidewalk')
    t = ax.text(X, Y + 3.2, str(e['n']), fontsize=8, color='#1e1e1e' if e['kind'] == 'sidewalk' else 'white', weight='bold', ha='center', va='center', zorder=zo + 2,
                bbox=dict(boxstyle='circle,pad=0.22' if rnd else 'round,pad=0.25,rounding_size=0.4',
                          facecolor={'pavilion': '#7a5d00', 'court': '#3b7d3b', 'tower': '#4f6d8f', 'building': '#1e1e1e', 'sidewalk': 'white'}[e['kind']],
                          edgecolor='#1e1e1e' if e['kind'] == 'sidewalk' else 'white', lw=0.8))
    BOXES.append(t.get_window_extent(RND).expanded(1.1, 1.1))
for a in ARROWS:
    ha = 'left' if V.P(*(a['tip'] + a['d'] * 10), a['z'])[0] >= V.P(*a['tip'], a['z'])[0] else 'right'
    placed = None
    for along in (6, 12, 20, 30, 42):
        for dy in (0, 6, -6, 12, -12, 18, -18):
            X, Y = V.P(*(a['tip'] + a['d'] * along), a['z']); Y += dy
            t = ax.text(X + (6 if ha == 'left' else -6), Y, TERM[(a['line'], a['dir'])], fontsize=8.5, ha=ha, va='center', zorder=zo + 2, path_effects=halo)
            bbs = [t.get_window_extent(RND).expanded(1.06, 1.25), badge_bb(X, Y, 15)]
            if free(bbs):
                placed = (X, Y, bbs); break
            t.remove()
        if placed:
            break
    if not placed:
        X, Y = V.P(*(a['tip'] + a['d'] * 6), a['z'])
        t = ax.text(X + (6 if ha == 'left' else -6), Y, TERM[(a['line'], a['dir'])], fontsize=8.5, ha=ha, va='center', zorder=zo + 2, path_effects=halo)
        placed = (X, Y, [t.get_window_extent(RND), badge_bb(X, Y, 15)])
    put_badge(ax, BADGE[a['line']], placed[:2], 15, zo=zo + 2)
    BOXES.extend(placed[2])
for name, xy, lv in (('Vine mezzanine', (-54.5, -34), -1), ('1927 passage', (-26, -45), -1), ('sunken court', (-8, -30), -1),
                     ('Sixth Street link', (-31, 42), -1), ('Line 1 ticket hall', (42, -76), -1), ('TRI hall', (5, -40), -2),
                     ('west hall', (-96, 20), -2), ('east hall', (40, 28), -2), ('Walnut hall', (88, -62), -2), ('B south end hall', (88, 23), -2), ('B north hall', (88, 84), -2)):
    X0, Y0 = V.P(*xy, ZD[lv])
    for dx, dy in ((0, 0), (0, 5), (0, -5), (12, 0), (-12, 0), (0, 10), (0, -10), (18, 6), (-18, -6)):
        t = ax.text(X0 + dx, Y0 + dy, name, fontsize=8, ha='center', va='center', zorder=zo + 1.5, path_effects=halo, color='#4a3d10', weight='bold')
        bb = t.get_window_extent(RND).expanded(1.05, 1.2)
        if free([bb]):
            BOXES.append(bb); break
        t.remove()
    else:
        t = ax.text(X0, Y0, name, fontsize=8, ha='center', va='center', zorder=zo + 1.5, path_effects=halo, color='#4a3d10', weight='bold')
# north arrow (frame north, up Vine, is true 349: true north is 11 degrees clockwise of frame north, as warp_rot.py)
tn = np.array([np.sin(np.radians(11)), np.cos(np.radians(11))])
nx, ny = np.array(V.P(*(tn * 10), 0)) - np.array(V.P(0, 0, 0)); nn = np.hypot(nx, ny); nx, ny = nx / nn, ny / nn
ax2 = fig.add_axes([0.92, 1 - 1.75 / FH, 0.05, 1.3 / FH]); ax2.axis('off'); ax2.set_xlim(-1, 1); ax2.set_ylim(-1, 1)
ax2.annotate('', xy=(nx * 0.8, ny * 0.8), xytext=(-nx * 0.5, -ny * 0.5), arrowprops=dict(arrowstyle='-|>', color='black', lw=2, mutation_scale=14))
ax2.text(-nx * 0.5 + (0.35 if nx <= 0 else -0.35), -ny * 0.5 - 0.3, 'N', fontsize=11, weight='bold', ha='center', va='center')
fig.text(0.02, 1 - 0.25 / FH, 'Fountain Square', fontsize=30, weight='bold', va='top')
for i, b in enumerate(('Metro_1', 'Metro_2', 'Metro_7', 'TRI_A', 'TRI_B', 'TRI_D')):
    fig.add_artist(AnnotationBbox(badge_box(b, 26), (0.215 + i * 0.022, 1 - 0.55 / FH), xycoords='figure fraction', frameon=False, pad=0))
FACE = (THETA - 11) % 360
_pts = ['north', 'north-north-east', 'north-east', 'east-north-east', 'east', 'east-south-east', 'south-east', 'south-south-east',
        'south', 'south-south-west', 'south-west', 'west-south-west', 'west', 'west-north-west', 'north-west', 'north-north-west']
_nm = lambda b: _pts[int(((b % 360) + 11.25) // 22.5) % 16]
fig.text(0.02, 1 - 1.05 / FH, 'Facing ' + _nm(FACE) + ' (%d°), seen from the ' % round(FACE) + _nm(FACE + 180) + ', %d° above the horizontal. Depths 1.4 times' % round(PHI) + ' (Lines 1 and 7 at 5 m, Line 2 at 12 m, TRI A and D at 28 m, TRI B at 42 m; drawing values),\n'
         'so every flight ends where it lands. Floors darken a shade with each level down (Metro grey, TRI pink). Stairs pink, escalators brown, elevators blue (E: from the street),\n'
         'TRI fare lines red, TRI hall floors see-through. '
         'Numbers: entrances.',
         fontsize=10, color='#555555', va='top')
fig.savefig(OUT, dpi=150)
print(OUT)
