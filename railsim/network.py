"""Track network built from hand-drawn KMZ LineStrings, and routing through it.

Replaces the old pairwise "stitcher": lines may be drawn in any order or direction, can
branch (RER trunks and branches), and may touch other lines in their interior (T-junctions).
Routing is turn-constrained so a route never doubles back through a junction the way
a train physically cannot (e.g. taking both legs of a wye).
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .geo import cumulative_length, dedupe_polyline, project_point_to_polyline, wrap_angle


@dataclass
class Edge:
    id: int
    xy: np.ndarray
    s: np.ndarray
    u: int  # node at start
    v: int  # node at end
    name: str = ""

    @property
    def length(self) -> float:
        return float(self.s[-1])

    def end_heading(self, at_start: bool, travelling_from_start: bool, look: float = 40.0) -> float:
        """Heading of travel at one end of the edge, measured over `look` metres."""
        L = self.length
        look = min(look, L)
        if at_start:
            p0 = self._at(0.0)
            p1 = self._at(look)
        else:
            p0 = self._at(L - look)
            p1 = self._at(L)
        h = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
        return h if travelling_from_start else h + math.pi

    def _at(self, ch: float):
        return np.array([np.interp(ch, self.s, self.xy[:, 0]), np.interp(ch, self.s, self.xy[:, 1])])


@dataclass
class Network:
    nodes: List[Tuple[float, float]] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    adj: Dict[int, List[int]] = field(default_factory=dict)

    # ------------------------------------------------------------------ construction
    @classmethod
    def build(cls, polylines: Sequence[np.ndarray], names: Sequence[str] | None = None,
              snap_tol: float = 30.0) -> "Network":
        names = list(names) if names is not None else [""] * len(polylines)
        lines = []
        for xy, nm in zip(polylines, names):
            xy = dedupe_polyline(np.asarray(xy, dtype=float)[:, :2], 0.5)
            if len(xy) >= 2:
                lines.append((xy, nm))

        # 1) cut lines where another line's endpoint touches their interior
        endpoints = [(li, end, xy[0 if end == 0 else -1]) for li, (xy, _) in enumerate(lines) for end in (0, 1)]
        cuts: Dict[int, List[float]] = {i: [] for i in range(len(lines))}
        for li, (xy, _) in enumerate(lines):
            s = cumulative_length(xy)
            for lj, _end, p in endpoints:
                if lj == li:
                    continue
                ch, d, _ = project_point_to_polyline(p[0], p[1], xy, s)
                if d <= snap_tol and snap_tol < ch < s[-1] - snap_tol:
                    cuts[li].append(ch)
        pieces = []
        for li, (xy, nm) in enumerate(lines):
            pieces.extend((p, nm) for p in _cut_polyline(xy, sorted(cuts[li]), min_gap=snap_tol))

        # 2) cluster piece endpoints into nodes (union-find within snap_tol)
        pts = []
        for xy, _ in pieces:
            pts.append(xy[0])
            pts.append(xy[-1])
        pts = np.array(pts)
        parent = list(range(len(pts)))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        for a in range(len(pts)):
            d = np.hypot(pts[:, 0] - pts[a, 0], pts[:, 1] - pts[a, 1])
            for b in np.nonzero(d <= snap_tol)[0]:
                ra, rb = find(a), find(int(b))
                if ra != rb:
                    parent[rb] = ra
        roots = sorted({find(a) for a in range(len(pts))})
        rid = {r: k for k, r in enumerate(roots)}
        net = cls()
        acc = np.zeros((len(roots), 3))
        for a in range(len(pts)):
            k = rid[find(a)]
            acc[k] += (pts[a, 0], pts[a, 1], 1)
        net.nodes = [(acc[k, 0] / acc[k, 2], acc[k, 1] / acc[k, 2]) for k in range(len(roots))]
        net.adj = {k: [] for k in range(len(roots))}

        for pi, (xy, nm) in enumerate(pieces):
            u = rid[find(2 * pi)]
            v = rid[find(2 * pi + 1)]
            xy = xy.copy()
            xy[0] = net.nodes[u]
            xy[-1] = net.nodes[v]
            xy = dedupe_polyline(xy, 0.5)
            if len(xy) < 2 or (u == v and cumulative_length(xy)[-1] < 2 * snap_tol):
                continue
            sx = cumulative_length(xy)
            if any(_same_track(f, u, v, xy, sx, snap_tol) for f in net.edges):
                continue  # the same track drawn twice (copied placemarks)
            e = Edge(len(net.edges), xy, sx, u, v, nm)
            net.edges.append(e)
            net.adj[u].append(e.id)
            net.adj[v].append(e.id)
        return net

    # ------------------------------------------------------------------ queries
    def locate(self, x: float, y: float, tol: float = 150.0) -> Optional[Tuple[int, float, float]]:
        """Nearest (edge_id, chainage_on_edge, offset) within tol, else None."""
        best = None
        for e in self.edges:
            ch, d, _ = project_point_to_polyline(x, y, e.xy, e.s)
            if best is None or d < best[2]:
                best = (e.id, ch, d)
        if best is None or best[2] > tol:
            return None
        return best

    def degree(self, n: int) -> int:
        return len(self.adj.get(n, []))

    def is_simple_path(self) -> bool:
        if not self.edges:
            return False
        degs = [self.degree(n) for n in self.adj]
        return max(degs) <= 2 and sum(1 for d in degs if d == 1) == 2 and self._connected()

    def _connected(self) -> bool:
        if not self.nodes:
            return False
        seen = {0}
        stack = [0]
        while stack:
            n = stack.pop()
            for eid in self.adj[n]:
                e = self.edges[eid]
                m = e.v if e.u == n else e.u
                if m not in seen:
                    seen.add(m)
                    stack.append(m)
        return len(seen) == len(self.nodes)

    # ------------------------------------------------------------------ routing
    def _leg(self, start: Tuple[int, float], forward: bool, goal: Tuple[int, float],
             max_turn: float, free_turn: bool = False) -> Dict[bool, Tuple[float, list]]:
        """Turn-constrained shortest path from a point on an edge, leaving in a given direction
        (forward = increasing chainage), to a point on another edge. `free_turn` lifts the
        turn limit at the first node (the train reverses there, at a stub terminal).
        Returns {arrival_forward: (cost, [(edge, ch_from, ch_to), ...])}."""
        se, sc = start
        ge, gc = goal
        results: Dict[bool, Tuple[float, list]] = {}
        if se == ge and ((forward and gc >= sc) or (not forward and gc <= sc)):
            results[forward] = (abs(gc - sc), [(se, sc, gc)])
        e0 = self.edges[se]
        first_cost = (e0.length - sc) if forward else sc
        first_piece = (se, sc, e0.length if forward else 0.0)
        # state: (edge, travelling_forward) at the END of the edge
        pq = [(first_cost, se, forward, (first_piece,))]
        best: Dict[Tuple[int, bool], float] = {}
        while pq:
            cost, eid, fwd, path = heapq.heappop(pq)
            key = (eid, fwd)
            if best.get(key, math.inf) <= cost:
                continue
            best[key] = cost
            if any(cost >= r[0] for r in results.values()) and len(results) == 2:
                break
            e = self.edges[eid]
            node = e.v if fwd else e.u
            h_in = e.end_heading(at_start=not fwd, travelling_from_start=fwd)
            free = free_turn and len(path) == 1
            for nid in self.adj[node]:
                f = self.edges[nid]
                for f_fwd in ((True,) if f.u == node else ()) + ((False,) if f.v == node else ()):
                    if nid == eid and f_fwd != fwd and not free:
                        continue  # no reversing back down the same edge
                    h_out = f.end_heading(at_start=f_fwd, travelling_from_start=f_fwd)
                    if not free and abs(float(wrap_angle(h_out - h_in))) > max_turn:
                        continue
                    if nid == ge:
                        piece = (nid, 0.0 if f_fwd else f.length, gc)
                        c = cost + (gc if f_fwd else f.length - gc)
                        if c < results.get(f_fwd, (math.inf,))[0]:
                            results[f_fwd] = (c, list(path) + [piece])
                    c2 = cost + f.length
                    piece = (nid, 0.0 if f_fwd else f.length, f.length if f_fwd else 0.0)
                    if c2 < best.get((nid, f_fwd), math.inf):
                        heapq.heappush(pq, (c2, nid, f_fwd, path + (piece,)))
        return results

    def stub_tip(self, x: float, y: float, radius: float = 500.0,
                 min_turn_deg: float = 150.0) -> Optional[Tuple[int, float, float]]:
        """The buffer-stop end of a stub terminal near (x, y): a dead-end node, or a node
        where two drawn lines meet head-on (track drawn into the station and back out).
        Returns (edge_id, chainage, distance) for a stop at that node, or None."""
        best = None
        for n, (nx, ny) in enumerate(self.nodes):
            d = math.hypot(nx - x, ny - y)
            if d > radius or (best is not None and d >= best[2]):
                continue
            eids = self.adj.get(n, [])
            if len(eids) == 2:
                (a, b) = (self.edges[eids[0]], self.edges[eids[1]])
                h_in = a.end_heading(at_start=a.u == n, travelling_from_start=a.v == n)
                h_out = b.end_heading(at_start=b.u == n, travelling_from_start=b.u == n)
                if abs(float(wrap_angle(h_out - h_in))) < math.radians(min_turn_deg):
                    continue
            elif len(eids) != 1:
                continue
            e = self.edges[eids[0]]
            best = (e.id, 0.0 if e.u == n else e.length, d)
        return best

    def route(self, stops: Sequence[Tuple[int, float]], max_turn_deg: float = 90.0,
              reverse_at: Sequence[int] = ()):
        """Route through stops (each (edge_id, chainage)) in order, keeping a consistent
        direction of travel: no reversals, except at the stop indices in `reverse_at`
        (stub terminals, where the driver changes ends). Returns (xy polyline, stop
        chainages along route); `self.last_reversals` holds the reversal chainages."""
        max_turn = math.radians(max_turn_deg)
        reverse_at = set(reverse_at)
        if len(stops) < 2:
            raise ValueError("need at least two stops to route")
        # DP over direction of travel at each stop
        INF = (math.inf, None)
        dp = {True: (0.0, []), False: (0.0, [])}
        for k in range(len(stops) - 1):
            new = {True: INF, False: INF}
            free = k in reverse_at and k > 0
            if free:  # the train may leave in either direction after reversing
                best_in = min(dp.values(), key=lambda t: t[0])
                dp = {True: best_in, False: best_in}
            for d_dep, (c0, legs) in dp.items():
                if c0 == math.inf:
                    continue
                res = self._leg(stops[k], d_dep, stops[k + 1], max_turn, free_turn=free)
                for d_arr, (c, pieces) in res.items():
                    if c0 + c < new[d_arr][0]:
                        new[d_arr] = (c0 + c, legs + [pieces])
            dp = new
            if all(v[0] == math.inf for v in dp.values()):
                raise ValueError(f"no turn-feasible route between stop {k} and stop {k + 1}")
        _, legs = min(dp.values(), key=lambda t: t[0])
        xy_parts = []
        stop_ch = [0.0]
        total = 0.0
        # record which drawn segment each piece of the route came from (operating zones)
        self.last_route_pieces = []
        ranges = []  # (segment name, chainage from, chainage to) along the route
        for pieces in legs:
            for eid, a, b in pieces:
                part = _slice(self.edges[eid], a, b)
                if len(part) >= 2 and abs(b - a) > 1.0:
                    self.last_route_pieces.append((self.edges[eid].name, part[0].copy(), part[-1].copy()))
                    ranges.append((self.edges[eid].name, total, total + abs(b - a)))
                if len(part) >= 2:
                    if xy_parts and np.hypot(*(xy_parts[-1][-1] - part[0])) < 1e-6:
                        part = part[1:]
                    xy_parts.append(part)
                total += abs(b - a)
            stop_ch.append(total)
        xy = np.vstack(xy_parts)
        xy = dedupe_polyline(xy, 0.05)
        # rescale stop chainages to the deduped polyline length (tiny differences)
        L = cumulative_length(xy)[-1]
        scale = L / total if total > 0 else 1.0
        self.last_reversals = [stop_ch[k] * scale for k in sorted(reverse_at) if 0 < k < len(stops) - 1]
        self.last_route_ranges = [(n, a * scale, b * scale) for n, a, b in ranges]
        return xy, [c * scale for c in stop_ch]

    def longest_route_between_leaves(self, max_turn_deg: float = 90.0):
        """For a line with no service definition: the longest turn-feasible route
        between any two dead-end nodes."""
        leaves = [n for n in self.adj if self.degree(n) == 1]
        best = None
        for i, a in enumerate(leaves):
            for b in leaves[i + 1:]:
                sa = self._node_stop(a)
                sb = self._node_stop(b)
                try:
                    xy, ch = self.route([sa, sb], max_turn_deg)
                except ValueError:
                    continue
                if best is None or ch[-1] > best[1][-1]:
                    best = (xy, ch, list(self.last_route_pieces), list(self.last_route_ranges))
        if best is None:
            raise ValueError("network has no routable pair of dead ends")
        self.last_route_pieces, self.last_route_ranges = best[2], best[3]
        return best[0]

    def _node_stop(self, n: int) -> Tuple[int, float]:
        eid = self.adj[n][0]
        e = self.edges[eid]
        return (eid, 0.0 if e.u == n else e.length)


def _same_track(f: Edge, u: int, v: int, xy: np.ndarray, s: np.ndarray, tol: float) -> bool:
    """True if a new piece between nodes u, v duplicates edge f (same ends, length within
    2 %, midpoint within tol)."""
    if {f.u, f.v} != {u, v} or abs(f.length - s[-1]) > 0.02 * max(s[-1], 1.0):
        return False
    mid = np.array([np.interp(s[-1] / 2, s, xy[:, 0]), np.interp(s[-1] / 2, s, xy[:, 1])])
    return project_point_to_polyline(mid[0], mid[1], f.xy, f.s)[1] <= tol


def _cut_polyline(xy: np.ndarray, cuts: List[float], min_gap: float) -> List[np.ndarray]:
    if not cuts:
        return [xy]
    s = cumulative_length(xy)
    merged = []
    for c in cuts:
        if not merged or c - merged[-1] > min_gap:
            merged.append(c)
    out = []
    prev = 0.0
    for c in merged + [s[-1]]:
        out.append(_slice_xy(xy, s, prev, c))
        prev = c
    return [p for p in out if len(p) >= 2]


def _slice_xy(xy, s, a, b):
    lo, hi = min(a, b), max(a, b)
    inner = (s > lo) & (s < hi)
    pa = [np.interp(lo, s, xy[:, 0]), np.interp(lo, s, xy[:, 1])]
    pb = [np.interp(hi, s, xy[:, 0]), np.interp(hi, s, xy[:, 1])]
    part = np.vstack([pa, xy[inner], pb])
    return part if a <= b else part[::-1]


def _slice(e: Edge, a: float, b: float) -> np.ndarray:
    return _slice_xy(e.xy, e.s, a, b)
