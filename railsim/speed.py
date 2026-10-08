"""Civil (posted) speed limits along an alignment.

Real speed limits are not a continuous function of curvature. They are posted in steps
(5 mph / 5 km/h), cover whole curves including spirals, and closely spaced restrictions
are combined into one zone. Restrictions are enforced until the REAR of the train has
cleared them; that part is handled in the dynamics (train-length window).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np

from .horizontal import G_ACC, HorizontalAlignment


@dataclass
class SpeedPolicy:
    line_speed: float  # m/s, maximum authorised speed on the line
    cant_deficiency: float  # m, Eu permitted for this train on this railroad
    rail_centres: float = 1.5
    max_deficiency_rate: float = 0.055  # m/s, dEu/dt allowed in spirals for running (not design)
    min_effective_spiral: float = 15.0  # m, bogie/vehicle smoothing when no spiral exists
    min_effective_arc: float = 20.0  # m; a car averages curvature over ~its length, so a short
    # kink of deflection D acts like a curve of radius >= min_effective_arc / D
    increment: float = 5 * 0.44704  # posting step (5 mph)
    min_zone_length: float = 200.0  # m; shorter faster zones are merged into slower neighbours
    zone_buffer: float = 0.0  # m added before/after each curve restriction


@dataclass
class Restriction:
    s0: float
    s1: float
    speed: float  # m/s
    reason: str = ""


@dataclass
class SpeedProfile:
    s: np.ndarray  # grid
    limit: np.ndarray  # posted limit at each grid point (m/s), for the front of the train
    zones: List[Restriction] = field(default_factory=list)

    def at(self, s_query):
        idx = np.clip(np.searchsorted(self.s, s_query, side="right") - 1, 0, len(self.s) - 1)
        return self.limit[idx]

    def reversed(self, length: float) -> "SpeedProfile":
        # limit[i] holds on [s[i], s[i+1]); flipping turns that into (L-s[i+1], L-s[i]]
        s_rev = length - self.s[::-1]
        lim_rev = np.concatenate([self.limit[::-1][1:], self.limit[:1]])
        zones = [Restriction(length - z.s1, length - z.s0, z.speed, z.reason) for z in self.zones][::-1]
        return SpeedProfile(s_rev, lim_rev, zones)


def curve_speed(R: float, cant: float, spiral: float, pol: SpeedPolicy,
                deflection: float = math.pi) -> float:
    """Max speed in a curve of radius R with installed cant, limited by cant deficiency and,
    in short or missing spirals, by the rate of change of cant deficiency."""
    if deflection > 0:
        R = max(R, pol.min_effective_arc / deflection)
    v = math.sqrt(G_ACC * R * (cant + pol.cant_deficiency) / pol.rail_centres)
    Ls = max(spiral, pol.min_effective_spiral)
    # dEu/dt = v * Eu(v) / Ls  with Eu(v) = G v^2/(gR) - cant  -> solve for v by bisection
    def rate(vv):
        eu = max(pol.rail_centres * vv * vv / (G_ACC * R) - cant, 0.0)
        return vv * eu / Ls

    if rate(v) > pol.max_deficiency_rate:
        lo, hi = 0.0, v
        for _ in range(50):
            mid = (lo + hi) / 2
            if rate(mid) > pol.max_deficiency_rate:
                hi = mid
            else:
                lo = mid
        v = lo
    return min(v, pol.line_speed)


def quantize(v: float, inc: float) -> float:
    if inc <= 0:
        return v
    return max(inc, math.floor(v / inc + 1e-9) * inc)


def build_from_zones(length: float, zones: Sequence[Restriction], grid: float = 5.0,
                     default: float = math.inf) -> SpeedProfile:
    s = np.arange(0.0, length + grid, grid)
    s[-1] = length
    lim = np.full(len(s), default)
    for z in zones:
        m = (s >= z.s0 - 1e-9) & (s <= z.s1 + 1e-9)
        lim[m] = np.minimum(lim[m], z.speed)
    return SpeedProfile(s, lim, list(zones))


def build_speed_profile(h: HorizontalAlignment, pol: SpeedPolicy,
                        extra: Sequence[Restriction] = (), grid: float = 5.0) -> SpeedProfile:
    L = h.length
    zones: List[Restriction] = []
    for c in h.curves:
        v = curve_speed(c.radius, c.cant, c.spiral, pol, c.deflection)
        v = quantize(v, pol.increment)
        if v < pol.line_speed - 1e-6:
            zones.append(Restriction(max(c.s_ts - pol.zone_buffer, 0.0),
                                     min(c.s_st + pol.zone_buffer, L), v,
                                     f"curve R={c.radius:.0f} m"))
    for z in extra:
        zones.append(Restriction(max(0.0, z.s0), min(L, z.s1), quantize(z.speed, pol.increment)
                                 if pol.increment else z.speed, z.reason))
    prof = build_from_zones(L, zones, grid, default=quantize(pol.line_speed, pol.increment))
    prof.limit = _merge_short_zones(prof.s, prof.limit, pol.min_zone_length)
    return prof


def _merge_short_zones(s, lim, min_len):
    """Lower any run of points that is faster than both neighbours and shorter than min_len
    to the faster of its neighbours, repeating until stable (posted-zone consolidation)."""
    lim = lim.copy()
    for _ in range(50):
        runs = []
        i = 0
        n = len(lim)
        while i < n:
            j = i
            while j + 1 < n and lim[j + 1] == lim[i]:
                j += 1
            runs.append((i, j))
            i = j + 1
        changed = False
        for k in range(1, len(runs) - 1):
            a, b = runs[k]
            v = lim[a]
            vl = lim[runs[k - 1][0]]
            vr = lim[runs[k + 1][0]]
            if v > vl and v > vr and (s[b] - s[a]) < min_len:
                lim[a:b + 1] = max(vl, vr)
                changed = True
        if not changed:
            break
    return lim


def zones_from_profile(sp: SpeedProfile) -> List[Restriction]:
    """Collapse the gridded limit back into posted zones (for reports / KML)."""
    out = []
    i = 0
    n = len(sp.limit)
    while i < n:
        j = i
        while j + 1 < n and sp.limit[j + 1] == sp.limit[i]:
            j += 1
        out.append(Restriction(float(sp.s[i]), float(sp.s[j]), float(sp.limit[i])))
        i = j + 1
    return out
