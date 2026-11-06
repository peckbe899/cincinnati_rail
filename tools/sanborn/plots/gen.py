"""Plots for every block (Ben, 2026-10-15): "measured and snapped".
Each block's street faces get lots facing the street: the lot width on each face is the repeating width measured on the
1904 sheet along that face (default 7.5 m in the basin, 8.5 m north of Hopple, 7.5 m on the deck and the west side), and
each cut is snapped to the strongest sheet line (lot line or party wall) within 2.5 m. A lot runs back to the alley or to
the line where it meets the lots of the opposite face, at most 40 m; deeper land is interior plots."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import sys, json, math, numpy as np, shapely
from shapely.geometry import LineString, Point, Polygon, MultiPolygon, MultiPoint, GeometryCollection, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union, split
sys.path.insert(0, (_ws.CODE + 'plots'))
from frontage import Faces, scan2, face_width, cuts_for
from common import Tiles, SP
D_MAX = 40.0
def default_w(b, pg):
    if b['src'] == 'deck': return 7.5
    return 8.5 if pg.centroid.y > 4333300 else 7.5
def polys(g):
    if g.is_empty: return []
    if g.geom_type == 'Polygon': return [g]
    if g.geom_type in ('MultiPolygon', 'GeometryCollection'): return [q for x in g.geoms for q in polys(x)]
    return []
def run_frame(run, step=0.5):
    L = LineString(run['pts']); n = max(2, int(L.length / step)); S = np.linspace(0, L.length, n + 1)
    P = np.array([L.interpolate(d).coords[0] for d in S]); T = np.gradient(P, axis=0); T /= np.hypot(T[:, 0], T[:, 1])[:, None] + 1e-9
    for _ in range(10): T[1:-1] = (T[:-2] + 2 * T[1:-1] + T[2:]) / 4
    T /= np.hypot(T[:, 0], T[:, 1])[:, None] + 1e-9; return L, S, P, np.c_[-T[:, 1], T[:, 0]]
def _dir(r):
    a, b = np.array(r['pts'][0]), np.array(r['pts'][-1]); v = b - a; n = np.hypot(*v); return v / n if n > 0 else v
def primary_runs(runs):
    """lots front on the long faces: with three or more faces, the longest face, the faces opposite it and any other long face
    not square to it carry lots; the short end faces only side the corner lots (no herringbone or pinwheel corners)"""
    if len(runs) <= 2: return runs
    Ls = [LineString(r['pts']).length for r in runs]; m = int(np.argmax(Ls)); dm = _dir(runs[m]); keep = []
    for i, r in enumerate(runs):
        if i == m: keep.append(r); continue
        c = abs(float(_dir(r) @ dm))
        if Ls[i] >= 0.4 * Ls[m] and c > 0.82: keep.append(r)            # roughly parallel or opposite to the longest face
        elif Ls[i] >= 0.8 * Ls[m] and c > 0.5: keep.append(r)            # another long face at an angle
    return keep
def merge_small(pieces, min_area):
    """fold slivers into the neighbour they share the longest edge with"""
    pieces = [p for p in pieces if p['g'].area > 0.05]
    changed = True
    while changed:
        changed = False
        pieces.sort(key=lambda p: p['g'].area)
        for i, p in enumerate(pieces):
            if p['g'].area >= min_area: break
            best, bl = None, 0.0
            for j, q in enumerate(pieces):
                if j == i: continue
                l = p['g'].boundary.intersection(q['g'].boundary).length
                if l > bl: best, bl = j, l
            if best is not None and bl > 0.3:
                q = pieces[best]; u = unary_union([q['g'], p['g']]).buffer(0.01).buffer(-0.01)
                if u.geom_type == 'Polygon': q['g'] = u; pieces.pop(i); changed = True; break
    return pieces
def block_plots(F, T, b):
    out = []
    for pi, pg in enumerate(polys(b['g'])):
        pg = orient(pg.buffer(0), 1.0)
        if pg.area < 20: continue
        if b['type'] in ('park', 'square', 'planting'): out.append(dict(g=pg, kind='open')); continue
        ring = list(pg.exterior.coords); smp = F.classify(ring); runs = F.runs(smp)
        if not runs: out.append(dict(g=pg, kind='interior')); continue
        runs = primary_runs(runs)
        # zones: the part of the block nearest each (primary) street face
        pts, owner = [], []
        for ri, r in enumerate(runs):
            L = LineString(r['pts'])
            for d in np.arange(0, L.length + 1e-6, 1.5): q = L.interpolate(d); pts.append((q.x, q.y)); owner.append(ri)
        vor = shapely.voronoi_polygons(MultiPoint(pts), extend_to=pg.buffer(50), ordered=True)
        cells = [[] for _ in runs]
        for k, c in enumerate(vor.geoms): cells[owner[k]].append(c)
        used = []
        for ri, r in enumerate(runs):
            zone = unary_union(cells[ri]).intersection(pg)
            Lr, S, P, N = run_frame(r)
            depth = max((Lr.distance(Point(c)) for z in polys(zone) for c in z.exterior.coords), default=0.0)
            if depth > 60.0:          # only very deep blocks keep an interior; otherwise lots run back to the alley or the middle
                cap = Polygon(list(P) + list((P + N * D_MAX)[::-1])).buffer(0)
                zone = zone.intersection(cap) if cap.is_valid and cap.area > 0 else zone
            zps = polys(zone)
            if not zps: continue
            # the cut positions: measured width on the 1904 sheet where there is one, snapped to its lines
            frac, w = None, default_w(b, pg)
            if b['src'] == 'basin':
                _, _, frac = scan2(T, r)
                wm = face_width(frac)
                if wm and 5.0 <= wm <= 15.0: w = wm
            cuts = cuts_for(Lr.length, frac, w)
            lines = []
            for s in cuts:
                i = int(round(s / (S[1] - S[0]))); i = min(max(i, 0), len(S) - 1)
                lines.append(LineString([P[i] - N[i] * 2.0, P[i] + N[i] * 70.0]))
            for zp in zps:
                pieces = [zp]
                if lines:
                    try: pieces = polys(split(zp, shapely.MultiLineString(lines)))
                    except Exception: pieces = [zp]
                for q in pieces: out.append(dict(g=q, kind='lot', street=r['street'], s=float(Lr.project(q.centroid)), run=ri, w=round(w, 2)))
            used.append(zone)
        rest = pg.difference(unary_union(used)) if used else pg
        for q in polys(rest):
            if q.area < 1: continue
            if q.area > 3000:          # deep interior: about 40 m parcels on the block's own axis
                mrr = q.minimum_rotated_rectangle; c = list(mrr.exterior.coords)
                e1 = np.subtract(c[1], c[0]); e2 = np.subtract(c[2], c[1]); ax = e1 if np.hypot(*e1) >= np.hypot(*e2) else e2
                ang = math.degrees(math.atan2(ax[1], ax[0])); from shapely import affinity
                qq = affinity.rotate(q, -ang, origin='centroid'); x0, y0, x1, y1 = qq.bounds
                nx, ny = max(1, round((x1 - x0) / 40)), max(1, round((y1 - y0) / 40))
                for i in range(nx):
                    for j in range(ny):
                        cell = box(x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny, x0 + (x1 - x0) * (i + 1) / nx, y0 + (y1 - y0) * (j + 1) / ny)
                        for z in polys(qq.intersection(cell)): out.append(dict(g=affinity.rotate(z, ang, origin=q.centroid), kind='interior'))
            else: out.append(dict(g=q, kind='interior'))
    out = merge_small(out, 30.0)
    # interior scraps under 400 m2 join their neighbour
    out = merge_small_interior(out)
    return out
def merge_small_interior(pieces):
    keep = [p for p in pieces if not (p['kind'] == 'interior' and p['g'].area < 400)]
    for p in [p for p in pieces if p['kind'] == 'interior' and p['g'].area < 400]:
        best, bl = None, 0.0
        for q in keep:
            l = p['g'].boundary.intersection(q['g'].boundary).length
            if l > bl: best, bl = q, l
        if best is not None and bl > 0.5:
            u = unary_union([best['g'], p['g']]).buffer(0.01).buffer(-0.01)
            if u.geom_type == 'Polygon': best['g'] = u; continue
        keep.append(p)
    return keep
if __name__ == '__main__':
    import time
    F = Faces(); T = Tiles(); t0 = time.time()
    ids = sys.argv[1:] if len(sys.argv) > 1 else None
    res = []
    for b in F.blocks:
        if ids and b['id'] not in ids: continue
        pl = block_plots(F, T, b); res.append((b, pl))
    print('blocks', len(res), 'plots', sum(len(p) for _, p in res), 'time', round(time.time() - t0, 1))
