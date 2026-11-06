"""Parametric earthworks: a design surface with a footprint that daylights into the existing ground.

Per cell, with Z the design level at the nearest point of the work's edge and d the distance to that edge:
    proposed = clip(existing, Z - fill_slope * d, Z + cut_slope * d)
Inside the footprint d = 0, so the cell takes Z; outside, the slopes run until they meet the ground (the daylight line
is found, not drawn). A wall is an infinite slope. Slopes are rise over run (0.5 = 1 in 2). mode 'replace' cuts and
fills, 'fill' only raises, 'cut' only lowers.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from rasterio.features import rasterize
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Polygon

from .raster import Target

WALL = float("inf")


def _volumes(before, after, step):
    d = np.nan_to_num(after - before)
    return float(d[d > 0].sum() * step * step), float(-d[d < 0].sum() * step * step)


@dataclass
class Pad:
    """An areal work: a polygon at a level, or on a plane, with side slopes to daylight."""
    id: str
    polygon: Polygon                      # EPSG:26916
    level: float                          # metres NAVD88 at `origin` (or everywhere, if no plane)
    plane: tuple | None = None            # (origin_x, origin_y, grade_x, grade_y): level + gx (x - ox) + gy (y - oy)
    cut_slope: float = 0.5                # 1 in 2
    fill_slope: float = 0.5
    mode: str = "replace"
    code: int = 200
    stats: dict = field(default_factory=dict)

    def design_level(self, X, Y):
        if self.plane is None:
            return np.full(X.shape, self.level, np.float32)
        ox, oy, gx, gy = self.plane
        return (self.level + gx * (X - ox) + gy * (Y - oy)).astype(np.float32)

    def apply(self, existing: np.ndarray, tgt: Target):
        inside = rasterize([(self.polygon, 1)], out_shape=tgt.shape, transform=tgt.transform, fill=0, dtype="uint8").astype(bool)
        if not inside.any():
            return existing, inside
        d, idx = distance_transform_edt(~inside, return_indices=True)
        d = d * tgt.step
        xs = tgt.x0 + (np.arange(tgt.width) + 0.5) * tgt.step; ys = tgt.y1 - (np.arange(tgt.height) + 0.5) * tgt.step
        X, Y = np.meshgrid(xs, ys)
        Zin = self.design_level(X, Y)
        Z = Zin[idx[0], idx[1]]                            # design level at the nearest footprint cell
        lower = Z - self.fill_slope * d if np.isfinite(self.fill_slope) else np.where(inside, Z, -np.inf)
        upper = Z + self.cut_slope * d if np.isfinite(self.cut_slope) else np.where(inside, Z, np.inf)
        new = existing.copy()
        if self.mode in ("replace", "fill"):
            new = np.fmax(new, lower)
        if self.mode in ("replace", "cut"):
            new = np.fmin(new, upper)
        new[inside] = Zin[inside]
        changed = ~np.isclose(np.nan_to_num(new, nan=-1e9), np.nan_to_num(existing, nan=-1e9))
        fill, cut = _volumes(existing, new, tgt.step)
        self.stats = dict(fill_m3=fill, cut_m3=cut, footprint_m2=float(inside.sum() * tgt.step ** 2), changed_m2=float(changed.sum() * tgt.step ** 2))
        return new, changed


@dataclass
class Corridor:
    """A linear work: a centre line with a level at each vertex, a formation width, and side slopes to daylight."""
    id: str
    line: list                            # [(x, y, z)] EPSG:26916, metres
    half_width: float                     # formation half width
    cut_slope: float = 0.667              # 1 in 1.5
    fill_slope: float = 0.5               # 1 in 2
    mode: str = "replace"
    code: int = 201
    stats: dict = field(default_factory=dict)

    def _dense(self, step):
        pts = np.asarray(self.line, float)
        out = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            n = max(1, int(np.ceil(np.hypot(*(b[:2] - a[:2])) / step)))
            for k in range(1, n + 1):
                out.append(a + (b - a) * k / n)
        return np.asarray(out)

    def apply(self, existing: np.ndarray, tgt: Target):
        pts = self._dense(tgt.step)
        tree = cKDTree(pts[:, :2])
        xs = tgt.x0 + (np.arange(tgt.width) + 0.5) * tgt.step; ys = tgt.y1 - (np.arange(tgt.height) + 0.5) * tgt.step
        X, Y = np.meshgrid(xs, ys)
        dist, near = tree.query(np.column_stack([X.ravel(), Y.ravel()]))
        dist = dist.reshape(X.shape); Z = pts[near, 2].reshape(X.shape).astype(np.float32)
        d = np.clip(dist - self.half_width, 0, None)
        inside = dist <= self.half_width
        lower = Z - self.fill_slope * d if np.isfinite(self.fill_slope) else np.where(inside, Z, -np.inf)
        upper = Z + self.cut_slope * d if np.isfinite(self.cut_slope) else np.where(inside, Z, np.inf)
        new = existing.copy()
        if self.mode in ("replace", "fill"):
            new = np.fmax(new, lower)
        if self.mode in ("replace", "cut"):
            new = np.fmin(new, upper)
        new[inside] = Z[inside]
        changed = ~np.isclose(np.nan_to_num(new, nan=-1e9), np.nan_to_num(existing, nan=-1e9))
        fill, cut = _volumes(existing, new, tgt.step)
        self.stats = dict(fill_m3=fill, cut_m3=cut, footprint_m2=float(inside.sum() * tgt.step ** 2), changed_m2=float(changed.sum() * tgt.step ** 2),
                          length_m=float(LineString([p[:2] for p in self.line]).length))
        return new, changed
