"""Centrelines that follow OSM for named streets (Ben, 2026-10-11: Central Parkway, Eggleston Ave, Reading Rd).
Dual carriageways are centred: each sample on one carriageway is paired with the nearest parallel point on another
way of the same street on the opposite side (6-45 m away) and replaced by the midpoint; the centre points are then
chained along the longest path of their spanning tree and simplified."""
import json, numpy as np, collections
from shapely.geometry import LineString, Point, MultiPoint
from shapely.ops import unary_union, linemerge
from shapely.strtree import STRtree
from scipy.sparse.csgraph import minimum_spanning_tree, shortest_path, connected_components
from scipy.spatial import cKDTree
SKIP = {'motorway', 'motorway_link', 'footway', 'steps', 'path', 'cycleway', 'corridor', 'service', 'trunk_link', 'primary_link', 'secondary_link', 'tertiary_link'}

def ways(osm_path, names):
    out = []
    for f in json.load(open(osm_path))['features']:
        p = f['properties']
        if p.get('name') in names and p.get('highway') not in SKIP:
            g = LineString(f['geometry']['coordinates'])
            if g.length >= 15: out.append((p['name'], g))
    return out

def centreline(W, step=3.0, pair=(6.0, 45.0), simplify=1.5):
    """W: list of (name, LineString). Returns list of (LineString, name)."""
    pts, dirs, own, nm = [], [], [], []
    for k, (n, g) in enumerate(W):
        for d in np.arange(0, g.length + 0.01, step):
            p = g.interpolate(d); a = g.interpolate(max(0, d - 4)); b = g.interpolate(min(g.length, d + 4))
            v = np.array([b.x - a.x, b.y - a.y]); v /= np.hypot(*v) + 1e-9
            pts.append((p.x, p.y)); dirs.append(v); own.append(k); nm.append(n)
    pts = np.array(pts); dirs = np.array(dirs); own = np.array(own)
    T = cKDTree(pts); mids = []
    for i, p in enumerate(pts):
        nrm = np.array([-dirs[i][1], dirs[i][0]]); best = None
        for j in T.query_ball_point(p, pair[1]):
            if own[j] == own[i]: continue
            v = pts[j] - p; dn = v @ nrm; da = abs(v @ dirs[i])
            if abs(dn) < pair[0] or da > 6 or abs(dirs[i] @ dirs[j]) < 0.94: continue
            if best is None or abs(dn) < best[0]: best = (abs(dn), j)
        mids.append((p + pts[best[1]]) / 2 if best else p)
    mids = np.array(mids)
    # thin duplicates (both carriageways give the same midpoints)
    keep = []; Tm = cKDTree(mids); used = np.zeros(len(mids), bool)
    for i in range(len(mids)):
        if used[i]: continue
        grp = Tm.query_ball_point(mids[i], 1.5)
        for j in grp: used[j] = True
        keep.append(i)
    C = mids[keep]; CN = [nm[i] for i in keep]
    D = cKDTree(C).sparse_distance_matrix(cKDTree(C), 12.0).toarray()
    M = minimum_spanning_tree(D).toarray(); M = M + M.T
    nc, lab = connected_components(M > 0, directed=False)
    out = []
    for c in range(nc):
        idx = np.where(lab == c)[0]
        if len(idx) < 8: continue
        sub = M[np.ix_(idx, idx)]
        dist, pred = shortest_path(sub, directed=False, return_predecessors=True)
        dd = np.where(np.isinf(dist), -1, dist); a, b = np.unravel_index(np.argmax(dd), dd.shape)
        path = [b]
        while path[-1] != a: path.append(pred[a, path[-1]])
        P = C[idx[path[::-1]]]
        if len(P) < 3: continue
        # light smoothing then simplify
        Ps = P.copy()
        for _ in range(2): Ps[1:-1] = (Ps[:-2] + 2 * Ps[1:-1] + Ps[2:]) / 4
        g = LineString(Ps).simplify(simplify)
        names = collections.Counter(CN[i] for i in idx[path])
        out.append((g, names.most_common(1)[0][0], [CN[i] for i in idx[path[::-1]]], P))
    return out

def _trim_hook(P, at_end, look=(30.0, 70.0), tol=20.0, maxcut=30.0):
    """Drop a short hook at one end: trailing points whose heading leaves the street's run-in heading by more than tol."""
    P = np.asarray(P, float)
    if not at_end: return _trim_hook(P[::-1], True, look, tol, maxcut)[::-1]
    g = LineString(P); L = g.length
    if L < look[1] + 10: return P
    a = np.array(g.interpolate(L - look[1]).coords[0]); b = np.array(g.interpolate(L - look[0]).coords[0])
    ref = (b - a) / np.hypot(*(b - a))
    keep = len(P)
    for i in range(len(P) - 1, 0, -1):
        v = P[i] - P[i - 1]; n = np.hypot(*v)
        if n < 1e-6: keep = i; continue
        if np.degrees(np.arccos(np.clip(v @ ref / n, -1, 1))) > tol and L - g.project(Point(P[i - 1])) < maxcut: keep = i
        else: break
    return P[:keep]

def bridge(lines, maxgap=70.0, n=24):
    """Join centreline pieces whose ends face each other across a turn (the carriageways part there, so pairing fails)
    with a curve tangent to both: a circular-arc fillet written as a cubic Bezier. lines: list of LineStrings."""
    P = [np.asarray(l.coords, float) for l in lines]
    joined = True
    while joined:
        joined = False
        best = None
        for i in range(len(P)):
            for j in range(len(P)):
                if i == j: continue
                for ei in (0, 1):
                    for ej in (0, 1):
                        a = P[i][-1] if ei else P[i][0]; b = P[j][-1] if ej else P[j][0]
                        d = np.hypot(*(a - b))
                        if 1.0 < d < maxgap and (best is None or d < best[0]): best = (d, i, ei, j, ej)
        if best is None: break
        _, i, ei, j, ej = best
        A = P[i] if ei else P[i][::-1]; B = P[j][::-1] if ej else P[j]          # A ends at the gap, B starts there
        A = _trim_hook(A, True); B = _trim_hook(B, False)
        p0, p3 = A[-1], B[0]
        t0 = A[-1] - A[max(0, len(A) - 4)]; t0 /= np.hypot(*t0) + 1e-9
        t3 = B[min(len(B) - 1, 3)] - B[0]; t3 /= np.hypot(*t3) + 1e-9
        th = np.arccos(np.clip(t0 @ t3, -1, 1))
        M = np.array([t0, -t3]).T
        if abs(np.linalg.det(M)) > 1e-6 and th > np.radians(5):
            s_ = np.linalg.solve(M, p3 - p0); T0, T3 = abs(s_[0]), abs(s_[1])
            k = 4 / 3 * np.tan(th / 4) / np.tan(th / 2)          # handle length per tangent length for a circular arc
            h0, h3 = k * T0, k * T3
        else: h0 = h3 = np.hypot(*(p3 - p0)) / 3
        c1, c2 = p0 + t0 * h0, p3 - t3 * h3
        u = np.linspace(0, 1, n)[1:-1, None]
        curve = (1 - u) ** 3 * p0 + 3 * (1 - u) ** 2 * u * c1 + 3 * (1 - u) * u ** 2 * c2 + u ** 3 * p3
        new = np.vstack([A, curve, B])
        P = [q for k_, q in enumerate(P) if k_ not in (i, j)] + [new]; joined = True
    return [LineString(q) for q in P]
