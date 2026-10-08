"""Horizontal alignment reconstruction from a hand-drawn polyline.

A Google Earth polyline has straight segments meeting at vertices. Real track has
tangents, transition spirals (clothoids) and circular arcs. Each vertex (or each group
of closely-spaced same-direction vertices, which is how people draw a long curve) is
treated as a point of intersection (PI). The largest radius whose spiral-arc-spiral
fits within the available tangent lengths is fitted, subject to:

* sharing each straight segment with the neighbouring curve(s),
* a minimum tangent between reverse curves,
* spiral lengths from the program's cant / cant-deficiency rate limits,
* the fitted curve staying within `group_dev_tol` of the drawn line when vertices are grouped.

The output is a new, smooth alignment whose length is the true track length (shorter than
the drawn polygon around every bend), with an exact curvature diagram k(s).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from .geo import cumulative_length, dedupe_polyline

G_ACC = 9.80665


@dataclass
class CurveDesign:
    """Infrastructure design parameters used to size spirals (program defaults; see configs)."""

    line_speed: float  # m/s, design speed of the line (upper bound for spiral sizing)
    max_cant: float  # Ea max, m
    max_cant_deficiency: float  # Eu max used for design, m
    rail_centres: float = 1.5  # m; G in E = G v^2/(g R) is rail-centre spacing, not gauge
    # Spiral length rules (AREMA Ch.5): L = 1.63 Eu V  (dEu/dt ~ 23 mm/s) and L = 62 Ea
    # (twist 1:744); EN 13803 cant rate check 50 mm/s.
    max_cant_rate: float = 0.050  # dEa/dt, m/s
    max_deficiency_rate: float = 0.023  # dEu/dt, m/s
    max_cant_gradient: float = 1 / 744.0  # dEa/ds
    min_spiral: float = 20.0  # m
    min_reverse_tangent: float = 30.0  # m; also >= 2 s of running (0.57 V_kmh), see below
    min_radius: float = 25.0  # m, absolute floor for fitting
    straight_radius: float = 50000.0  # m, fitted radii above this are treated as tangent
    group_dev_tol: float = 10.0  # m, max offset of a fitted curve from vertices drawn along it
    corner_offset_tol: float = 40.0  # m, max offset of a fitted curve from a single drawn corner
    max_group_deflection_deg: float = 150.0
    simplify_tol: float = 3.0  # m, Douglas-Peucker tolerance: hand-drawing jitter (~2-5 m) is removed

    def reverse_tangent(self) -> float:
        """Tangent between reverse curves: max(30 m, 2 s at line speed) (Amtrak 3V ft rule)."""
        return max(self.min_reverse_tangent, 2.05 * self.line_speed)

    def curve_speed(self, R: float) -> float:
        v = math.sqrt(G_ACC * R * (self.max_cant + self.max_cant_deficiency) / self.rail_centres)
        return min(v, self.line_speed)

    def cant_for(self, R: float) -> tuple:
        """(Ea, Eu) at the curve's design speed. Cant balances all but ~2/3 of the allowed
        deficiency, which is typical practice for passenger-only lines."""
        v = self.curve_speed(R)
        Ee = self.rail_centres * v * v / (G_ACC * R)
        Ea = min(self.max_cant, max(0.0, Ee - 0.67 * self.max_cant_deficiency))
        Eu = max(0.0, Ee - Ea)
        return Ea, Eu

    def spiral_length(self, R: float) -> float:
        if R >= self.straight_radius:
            return 0.0
        v = self.curve_speed(R)
        Ea, Eu = self.cant_for(R)
        return max(self.min_spiral,
                   Ea / self.max_cant_gradient,
                   v * Ea / self.max_cant_rate,
                   v * Eu / self.max_deficiency_rate)


@dataclass
class Curve:
    direction: int  # +1 left (CCW), -1 right
    deflection: float  # rad, absolute
    radius: float  # m
    spiral: float  # m, each end
    s_ts: float = 0.0  # chainages on the reconstructed alignment
    s_sc: float = 0.0
    s_cs: float = 0.0
    s_st: float = 0.0
    tangent: float = 0.0
    cant: float = 0.0
    vertices: tuple = ()

    @property
    def length(self) -> float:
        return self.s_st - self.s_ts


@dataclass
class HorizontalAlignment:
    xy: np.ndarray  # dense reconstructed polyline (~2 m spacing in curves)
    s: np.ndarray
    curves: List[Curve] = field(default_factory=list)
    drawn_length: float = 0.0

    @property
    def length(self) -> float:
        return float(self.s[-1])

    def curvature(self, s_query) -> np.ndarray:
        """Signed curvature (1/m, + = left) at chainages."""
        s_query = np.atleast_1d(np.asarray(s_query, dtype=float))
        k = np.zeros_like(s_query)
        for c in self.curves:
            kc = c.direction / c.radius
            m = (s_query >= c.s_ts) & (s_query <= c.s_st)
            if not m.any():
                continue
            sq = s_query[m]
            val = np.full_like(sq, kc)
            if c.spiral > 0:
                up = sq < c.s_sc
                dn = sq > c.s_cs
                val[up] = kc * (sq[up] - c.s_ts) / c.spiral
                val[dn] = kc * (c.s_st - sq[dn]) / c.spiral
            k[m] = val
        return k

    def radius(self, s_query) -> np.ndarray:
        k = np.abs(self.curvature(s_query))
        with np.errstate(divide="ignore"):
            return np.where(k > 0, 1.0 / np.maximum(k, 1e-12), np.inf)


# ----------------------------------------------------------------------------- fitting

def simplify(P: np.ndarray, tol: float) -> np.ndarray:
    """Douglas-Peucker simplification (iterative)."""
    n = len(P)
    if n < 3 or tol <= 0:
        return P
    keep = np.zeros(n, dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = P[i], P[j]
        ab = b - a
        L = math.hypot(ab[0], ab[1])
        seg = P[i + 1:j]
        if L < 1e-9:
            d = np.hypot(seg[:, 0] - a[0], seg[:, 1] - a[1])
        else:
            d = np.abs(ab[0] * (seg[:, 1] - a[1]) - ab[1] * (seg[:, 0] - a[0])) / L
        k = int(np.argmax(d))
        if d[k] > tol:
            m = i + 1 + k
            keep[m] = True
            stack.append((i, m))
            stack.append((m, j))
    return P[keep]


def _unit(v):
    n = math.hypot(v[0], v[1])
    return v / n if n > 0 else v


def _intersect(p, u, q, w):
    """Intersection of lines p + t u and q + r w. Returns (point, t, r) or None."""
    den = u[0] * w[1] - u[1] * w[0]
    if abs(den) < 1e-9:
        return None
    d = q - p
    t = (d[0] * w[1] - d[1] * w[0]) / den
    r = (d[0] * u[1] - d[1] * u[0]) / den
    return p + t * u, t, r


class _Group:
    __slots__ = ("a", "b", "pi", "delta", "dirn", "back_base", "fwd_base", "u_in", "u_out")


def _group_geometry(P: np.ndarray, a: int, b: int, max_defl: float) -> Optional[_Group]:
    u_in = _unit(P[a] - P[a - 1])
    u_out = _unit(P[b + 1] - P[b])
    cross = u_in[0] * u_out[1] - u_in[1] * u_out[0]
    dot = float(np.clip(u_in @ u_out, -1, 1))
    delta = math.atan2(cross, dot)
    if abs(delta) < 1e-6 or abs(delta) > max_defl:
        return None
    if a == b:
        pi, t, r = P[a], 0.0, 0.0
    else:
        res = _intersect(P[a], u_in, P[b], u_out)
        if res is None:
            return None
        pi, t, r = res
        if t < 0 or r > 0:  # PI must lie ahead of a and behind b
            return None
    g = _Group()
    g.a, g.b, g.pi, g.delta = a, b, pi, abs(delta)
    g.dirn = 1 if delta > 0 else -1
    g.back_base = float(t)  # distance from P[a] forward to PI along entry line
    g.fwd_base = float(-r)  # distance from PI forward to P[b] along exit line
    g.u_in, g.u_out = u_in, u_out
    return g


def _tangent_len(R: float, delta: float, design: CurveDesign):
    """(tangent length T, spiral length Ls, shift p) of a spiral-arc-spiral curve."""
    Ls = min(design.spiral_length(R), 0.999 * R * delta)
    p = Ls * Ls / (24 * R)
    k = Ls / 2 - Ls ** 3 / (240 * R * R)
    return (R + p) * math.tan(delta / 2) + k, Ls, p


def _radius_for_tangent(T: float, delta: float, design: CurveDesign) -> float:
    """Largest R (with spirals) whose tangent length does not exceed T."""
    lo, hi = design.min_radius, design.straight_radius * 2
    if _tangent_len(lo, delta, design)[0] > T:
        # not even the tightest curve with spirals fits: plain circular curve
        return max(T / math.tan(delta / 2), design.min_radius)
    if _tangent_len(hi, delta, design)[0] <= T:
        return hi
    for _ in range(60):
        mid = math.sqrt(lo * hi)
        if _tangent_len(mid, delta, design)[0] <= T:
            lo = mid
        else:
            hi = mid
    return lo


def _deviation(P, g: _Group, R: float, design: CurveDesign) -> float:
    """Max distance of the drawn vertices a..b from the fitted curve (circle shifted by the
    spiral offset p, tangent to the entry and exit lines). For a single vertex this is the
    distance from the drawn corner to the curve's midpoint."""
    _, _, p = _tangent_len(R, g.delta, design)
    bis = _unit(g.u_out - g.u_in)  # towards the inside of the bend
    c = g.pi + bis * (R + p) / math.cos(g.delta / 2)
    d = np.abs(np.hypot(P[g.a:g.b + 1, 0] - c[0], P[g.a:g.b + 1, 1] - c[1]) - R)
    return float(d.max())


def _radius_cap(P, g: _Group, design: CurveDesign) -> Optional[float]:
    """Upper bound on the radius from what was drawn.

    * single drawn corner: the largest radius whose midpoint stays within corner_offset_tol
      of the corner (the drawing says nothing more precise);
    * several vertices drawn along a curve: the best-fit radius to those vertices, provided
      the fit is within group_dev_tol (otherwise None: they are not one curve).
    """
    radii = np.geomspace(design.min_radius, design.straight_radius * 2, 160)
    dev = np.array([_deviation(P, g, R, design) for R in radii])
    if g.a != g.b:
        i = int(np.argmin(dev))
        if dev[i] > design.group_dev_tol:
            return None
        lo, hi = radii[max(i - 1, 0)], radii[min(i + 1, len(radii) - 1)]
        for _ in range(40):  # golden-section refinement of the best fit
            m1 = lo * (hi / lo) ** 0.382
            m2 = lo * (hi / lo) ** 0.618
            if _deviation(P, g, m1, design) <= _deviation(P, g, m2, design):
                hi = m2
            else:
                lo = m1
        return float(math.sqrt(lo * hi))
    ok = dev <= design.corner_offset_tol
    if not ok.any():
        return float(design.min_radius)
    i = int(np.nonzero(ok)[0].max())
    if i == len(radii) - 1:
        return float(radii[-1])
    lo, hi = radii[i], radii[i + 1]
    for _ in range(30):
        mid = math.sqrt(lo * hi)
        if _deviation(P, g, mid, design) <= design.corner_offset_tol:
            lo = mid
        else:
            hi = mid
    return float(lo)


def fit_horizontal(xy: np.ndarray, design: CurveDesign, step: float = 2.0) -> HorizontalAlignment:
    P0 = dedupe_polyline(np.asarray(xy, dtype=float)[:, :2], 1.0)
    drawn_len = float(cumulative_length(P0)[-1])
    P = simplify(P0, design.simplify_tol)
    n = len(P)
    if n < 3:
        s = cumulative_length(P)
        return HorizontalAlignment(P, s, [], drawn_len)
    seg = np.hypot(np.diff(P[:, 0]), np.diff(P[:, 1]))
    max_defl = math.radians(design.max_group_deflection_deg)

    # --- initial groups: every interior vertex with a real deflection
    groups: List[_Group] = []
    for i in range(1, n - 1):
        g = _group_geometry(P, i, i, max_defl)
        if g is not None and g.delta > math.radians(0.05):
            groups.append(g)
        elif g is None:
            u0 = _unit(P[i] - P[i - 1])
            u1 = _unit(P[i + 1] - P[i])
            if float(u0 @ u1) < math.cos(max_defl):
                # hairpin drawn as one vertex: keep as a tight curve
                h = _Group()
                h.a = h.b = i
                h.pi = P[i]
                h.delta = min(math.acos(float(np.clip(u0 @ u1, -1, 1))), math.radians(175))
                h.dirn = 1 if (u0[0] * u1[1] - u0[1] * u1[0]) >= 0 else -1
                h.back_base = h.fwd_base = 0.0
                h.u_in, h.u_out = u0, u1
                groups.append(h)
    caps = {}

    def cap(g: _Group) -> float:
        key = (g.a, g.b)
        if key not in caps:
            c = _radius_cap(P, g, design)
            caps[key] = c if c is not None else -1.0
        return caps[key]

    def est_radius(g: _Group, prev: Optional[_Group], nxt: Optional[_Group]) -> float:
        lb = seg[g.a - 1] * (0.5 if prev is not None and prev.b == g.a - 1 else 1.0)
        lf = seg[g.b] * (0.5 if nxt is not None and nxt.a == g.b + 1 else 1.0)
        T = min(g.back_base + lb, g.fwd_base + lf)
        c = cap(g)
        r = _radius_for_tangent(max(T, 0.01), g.delta, design)
        return min(r, c) if c > 0 else min(r, design.min_radius)

    # --- merge runs of same-direction vertices that one circle fits within tolerance:
    # a curve drawn as a chain of short chords is ONE curve. Best-fitting merges first.
    def fit_dev(g: _Group) -> float:
        c = cap(g)
        return _deviation(P, g, c, design) if c > 0 else math.inf

    merged = True
    while merged and len(groups) > 1:
        merged = False
        best = None
        for j in range(len(groups) - 1):
            g1, g2 = groups[j], groups[j + 1]
            if g1.dirn != g2.dirn:
                continue
            m = _group_geometry(P, g1.a, g2.b, max_defl)
            if m is None or cap(m) <= 0:
                continue
            dev = fit_dev(m)
            if dev > design.group_dev_tol:
                continue
            if best is None or dev < best[0]:
                best = (dev, j, m)
        if best is not None:
            _, j, m = best
            groups[j:j + 2] = [m]
            merged = True

    # --- share each straight segment between the curves at its ends
    k = len(groups)
    if k == 0:
        s = cumulative_length(P)
        return HorizontalAlignment(P, s, [], drawn_len)
    back_seg = [g.a - 1 for g in groups]
    fwd_seg = [g.b for g in groups]
    alloc_b = np.zeros(k)
    alloc_f = np.zeros(k)
    for j, g in enumerate(groups):
        w = math.tan(g.delta / 2)
        # back segment
        if j > 0 and fwd_seg[j - 1] == back_seg[j]:
            o = groups[j - 1]
            wo = math.tan(o.delta / 2)
            gap = design.reverse_tangent() if o.dirn != g.dirn else 0.0
            avail = max(seg[back_seg[j]] - gap, 0.5 * seg[back_seg[j]])
            alloc_b[j] = avail * w / (w + wo)
            alloc_f[j - 1] = avail * wo / (w + wo)
        else:
            alloc_b[j] = seg[back_seg[j]]
        if j == k - 1 or fwd_seg[j] != back_seg[j + 1]:
            alloc_f[j] = seg[fwd_seg[j]]

    radii = np.zeros(k)
    spirals = np.zeros(k)
    tangents = np.zeros(k)
    for _ in range(8):
        for j, g in enumerate(groups):
            T = max(min(g.back_base + alloc_b[j], g.fwd_base + alloc_f[j]), 0.01)
            R = _radius_for_tangent(T, g.delta, design)
            c = cap(g)
            if c > 0:
                R = min(R, c)
            radii[j] = R
            tangents[j], spirals[j], _ = _tangent_len(R, g.delta, design)
            if tangents[j] > T + 1e-6:  # tight fallback curve without spirals
                spirals[j] = 0.0
                tangents[j] = R * math.tan(g.delta / 2)
        # redistribute slack on shared segments to the binding neighbour
        changed = False
        for j in range(k - 1):
            if fwd_seg[j] != back_seg[j + 1]:
                continue
            g, o = groups[j], groups[j + 1]
            gap = design.reverse_tangent() if o.dirn != g.dirn else 0.0
            used_j = max(tangents[j] - g.fwd_base, 0.0)
            used_o = max(tangents[j + 1] - o.back_base, 0.0)
            slack = seg[fwd_seg[j]] - gap - used_j - used_o
            if slack <= 0.01:
                continue
            bind_j = (g.fwd_base + alloc_f[j]) <= (g.back_base + alloc_b[j]) + 1e-6
            bind_o = (o.back_base + alloc_b[j + 1]) <= (o.fwd_base + alloc_f[j + 1]) + 1e-6
            if bind_j and bind_o:
                alloc_f[j] = used_j + slack / 2
                alloc_b[j + 1] = used_o + slack / 2
            elif bind_j:
                alloc_f[j] = used_j + slack
                alloc_b[j + 1] = used_o
            elif bind_o:
                alloc_b[j + 1] = used_o + slack
                alloc_f[j] = used_j
            else:
                continue
            changed = True
        if not changed:
            break

    # --- build the reconstructed alignment, tracking chainage as points are appended
    pts = [P[0]]
    run = 0.0
    curves: List[Curve] = []
    for j, g in enumerate(groups):
        R, Ls, T = radii[j], spirals[j], tangents[j]
        if R >= design.straight_radius:
            continue
        ts = g.pi - g.u_in * T
        run += float(math.hypot(*(ts - pts[-1])))
        pts.append(ts)
        arc_pts, total = _trace_curve(ts, g.u_in, g.dirn, R, Ls, g.delta, step)
        pts.extend(arc_pts[1:])
        Ea, _ = design.cant_for(R)
        c = Curve(g.dirn, g.delta, R, Ls, tangent=T, cant=Ea, vertices=(g.a, g.b))
        c.s_ts, c.s_st = run, run + total
        c.s_sc, c.s_cs = run + Ls, run + total - Ls
        curves.append(c)
        run += total
    pts.append(P[-1])
    out = np.array(pts)
    s = cumulative_length(out)  # polyline chords in curves are ~1e-6 shorter than arc length
    return HorizontalAlignment(out, s, curves, drawn_len)


def _trace_curve(ts, u_in, dirn, R, Ls, delta, step):
    """Points of spiral-arc-spiral starting at TS with heading u_in, total deflection delta."""
    arc_len = max(R * delta - Ls, 0.0)
    total = 2 * Ls + arc_len
    m = max(int(math.ceil(total / step)), 2)
    ss = np.linspace(0, total, m + 1)

    def kappa(x):
        if Ls > 0 and x < Ls:
            return x / (Ls * R)
        if Ls > 0 and x > Ls + arc_len:
            return (total - x) / (Ls * R)
        return 1.0 / R

    h0 = math.atan2(u_in[1], u_in[0])
    pts = [np.array(ts, dtype=float)]
    h = h0
    for i in range(m):
        a, b = ss[i], ss[i + 1]
        ds = b - a
        # Simpson integration of heading over the step
        k0, k1, k2 = kappa(a), kappa((a + b) / 2), kappa(b)
        h_mid = h + dirn * (k0 + k1) / 2 * (ds / 2)
        h_end = h + dirn * (k0 + 4 * k1 + k2) / 6 * ds
        pts.append(pts[-1] + ds * np.array([math.cos(h_mid), math.sin(h_mid)]))
        h = h_end
    return pts, total
