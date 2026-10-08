"""Designed vertical track profile from a ground profile.

Ground is not track. Railways run on designed grades: bounded slopes, level-ish platforms,
smooth vertical curves, and structures (fill, viaduct, cut) where the ground does not
cooperate. This module fits such a profile to the ground with a bounded least-squares
problem on the grades:

    minimise  sum_i w_i (z_i - ground_i)^2  +  lam * sum_i (g_{i+1} - g_i)^2
    subject to |g_i| <= max_grade   (|g_i| <= platform_grade inside platforms)

with z = z0 + cumsum(g * ds). Weights are asymmetric (going below ground costs more than
going above, since these lines are surface / at-grade / elevated) and are zero inside
user-declared structures, where the ground is irrelevant. A final moving-average pass of
the vertical-curve length enforces smooth grade changes (it cannot violate the bounds).

The result also classifies each point as at-grade, fill, viaduct, cut or tunnel by its
height relative to the ground.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import lsq_linear
from scipy.sparse.linalg import LinearOperator


@dataclass
class ProfileDesign:
    max_grade: float = 0.03  # sustained ruling grade (fraction)
    platform_grade: float = 0.005  # within platforms
    platform_length: float = 150.0  # m, used to flatten around each station
    vertical_curve_length: float = 120.0  # m, smoothing length of grade changes
    smoothness: float = 5.0e4  # lam, penalty on grade changes (m^2 per unit grade^2)
    below_ground_weight: float = 4.0  # relative cost of cut vs fill
    allow_tunnels: bool = False
    grid: float = 20.0  # m, design grid spacing
    viaduct_height: float = 6.0  # m above ground -> viaduct / elevated structure
    fill_height: float = 1.0  # m above ground -> embankment
    cut_depth: float = 1.0  # m below ground -> cut
    tunnel_depth: float = 12.0  # m below ground -> tunnel (if allowed) else deep cut


@dataclass
class Profile:
    s: np.ndarray
    ground: np.ndarray
    track: np.ndarray
    grade: np.ndarray  # fraction, per point (centred)
    structure: List[str] = field(default_factory=list)
    has_ground_data: bool = True

    def grade_at(self, s_query):
        return np.interp(s_query, self.s, self.grade)

    def elevation_at(self, s_query):
        return np.interp(s_query, self.s, self.track)

    def reversed(self) -> "Profile":
        L = self.s[-1]
        return Profile(L - self.s[::-1], self.ground[::-1].copy(), self.track[::-1].copy(),
                       -self.grade[::-1], self.structure[::-1], self.has_ground_data)

    def segments(self) -> List[Tuple[float, float, str]]:
        out = []
        start = 0
        for i in range(1, len(self.s) + 1):
            if i == len(self.s) or self.structure[i] != self.structure[start]:
                out.append((float(self.s[start]), float(self.s[i - 1]), self.structure[start]))
                start = i
        return out


def flat_profile(length: float, grid: float = 20.0) -> Profile:
    s = np.linspace(0.0, length, max(int(length // grid) + 2, 2))
    z = np.zeros_like(s)
    return Profile(s, z, z.copy(), z.copy(), ["at-grade"] * len(s), has_ground_data=False)


def design_profile(length: float, ground_fn, design: ProfileDesign,
                   stations: Sequence[float] = (),
                   structures: Sequence[Tuple[float, float, str]] = (),
                   fixed_points: Sequence[Tuple[float, float]] = ()) -> Profile:
    """ground_fn(s_array) -> ground elevation (m). structures: (s0, s1, kind) user overrides
    where the ground is ignored (kind e.g. 'viaduct', 'bridge', 'tunnel', 'cut').
    fixed_points: (s, z) elevations the track must pass through (e.g. surveyed grade crossings)."""
    n = max(int(np.ceil(length / design.grid)) + 1, 3)
    s = np.linspace(0.0, length, n)
    ds = s[1] - s[0]
    g = np.asarray(ground_fn(s), dtype=float)
    m = n - 1  # number of grade intervals
    mid = (s[:-1] + s[1:]) / 2

    # bounds on grades
    ub = np.full(m, design.max_grade)
    for st in stations:
        inside = np.abs(mid - st) <= design.platform_length / 2 + ds
        ub[inside] = np.minimum(ub[inside], design.platform_grade)
    lb = -ub

    w_base = np.ones(n)
    for s0, s1, _kind in structures:
        w_base[(s >= min(s0, s1)) & (s <= max(s0, s1))] = 0.0
    fixed_w = 50.0

    lam = np.sqrt(design.smoothness) / ds  # scale so penalty ~ grade change per metre

    def solve(w):
        sw = np.sqrt(w)
        rows_fit = n
        rows_smooth = m - 1
        rows_fix = len(fixed_points)
        fix_idx = [int(round(fs / ds)) for fs, _ in fixed_points]

        # unknowns: x = [z0, g_0..g_{m-1}]
        def mv(x):
            x = np.ravel(x)
            z = x[0] + np.concatenate([[0.0], np.cumsum(x[1:]) * ds])
            r1 = sw * z
            r2 = lam * np.diff(x[1:])
            r3 = np.array([np.sqrt(fixed_w) * z[i] for i in fix_idx])
            return np.concatenate([r1, r2, r3])

        def rmv(r):
            r = np.ravel(r)
            r1 = r[:rows_fit] * sw
            r2 = r[rows_fit:rows_fit + rows_smooth] * lam
            r3 = r[rows_fit + rows_smooth:]
            zt = r1.copy()
            for k, i in enumerate(fix_idx):
                zt[i] += np.sqrt(fixed_w) * r3[k]
            out = np.empty(m + 1)
            out[0] = zt.sum()
            # d z_i / d g_j = ds for i > j
            tail = np.cumsum(zt[::-1])[::-1]  # tail[i] = sum_{k>=i} zt[k]
            out[1:] = tail[1:] * ds
            # smoothness: r2_k = lam (g_{k+1} - g_k)
            gsm = np.zeros(m)
            gsm[:-1] -= r2
            gsm[1:] += r2
            out[1:] += gsm
            return out

        A = LinearOperator((rows_fit + rows_smooth + rows_fix, m + 1), matvec=mv, rmatvec=rmv,
                           dtype=float)
        b = np.concatenate([sw * g, np.zeros(rows_smooth),
                            [np.sqrt(fixed_w) * fz for _, fz in fixed_points]])
        lo = np.concatenate([[-np.inf], lb])
        hi = np.concatenate([[np.inf], ub])
        x0 = np.concatenate([[g[0]], np.clip(np.diff(g) / ds, lb, ub)])
        res = lsq_linear(A, b, bounds=(lo, hi), lsq_solver="lsmr", method="trf",
                         lsmr_tol="auto", max_iter=200, verbose=0)
        x = res.x if res.success or res.status >= 0 else x0
        return x

    w = w_base.copy()
    x = solve(w)
    for _ in range(3):  # iteratively reweight: cuts cost more than fill
        z = x[0] + np.concatenate([[0.0], np.cumsum(x[1:]) * ds])
        below = z < g - 0.25
        w = w_base * np.where(below, design.below_ground_weight, 1.0)
        x = solve(w)

    grades = x[1:]
    # vertical curves: moving average over the vertical-curve length (keeps bounds)
    k = max(int(round(design.vertical_curve_length / ds)), 1)
    if k > 1:
        pad = np.pad(grades, (k // 2, k - 1 - k // 2), mode="edge")
        sm = np.convolve(pad, np.ones(k) / k, mode="valid")
        # never relax platform limits
        grades = np.clip(sm, lb, ub)
    z = x[0] + np.concatenate([[0.0], np.cumsum(grades) * ds])
    grade_pts = np.concatenate([[grades[0]], (grades[:-1] + grades[1:]) / 2, [grades[-1]]])

    struct = []
    user = [(min(a, b), max(a, b), kind) for a, b, kind in structures]
    for si, zi, gi in zip(s, z, g):
        kind = next((kd for a, b, kd in user if a <= si <= b), None)
        if kind is None:
            h = zi - gi
            if h >= design.viaduct_height:
                kind = "viaduct"
            elif h >= design.fill_height:
                kind = "fill"
            elif h <= -design.tunnel_depth:
                kind = "tunnel" if design.allow_tunnels else "deep-cut"
            elif h <= -design.cut_depth:
                kind = "cut"
            else:
                kind = "at-grade"
        struct.append(kind)
    return Profile(s, g, z, grade_pts, struct, True)
