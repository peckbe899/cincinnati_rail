"""Geodesy helpers: local planar projection, distances, polyline utilities."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np

EARTH_RADIUS_M = 6371008.8

MPH = 0.44704  # m/s per mph
KMH = 1 / 3.6  # m/s per km/h
FT = 0.3048  # m per ft
INCH = 0.0254  # m per inch


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


@dataclass
class LocalProjection:
    """Azimuthal equidistant-like local tangent plane, accurate to ~1e-4 relative over 100 km.

    Uses an ellipsoidal (WGS84) radius of curvature at the reference latitude so that
    both east and north scales are right; good enough for alignment geometry at city scale.
    """

    lat0: float
    lon0: float

    def __post_init__(self):
        a = 6378137.0
        e2 = 6.69437999014e-3
        phi = math.radians(self.lat0)
        s = math.sin(phi)
        self._m_per_rad_lat = a * (1 - e2) / (1 - e2 * s * s) ** 1.5
        self._m_per_rad_lon = a * math.cos(phi) / math.sqrt(1 - e2 * s * s)

    def to_xy(self, lat, lon):
        lat = np.asarray(lat, dtype=float)
        lon = np.asarray(lon, dtype=float)
        x = np.radians(lon - self.lon0) * self._m_per_rad_lon
        y = np.radians(lat - self.lat0) * self._m_per_rad_lat
        return x, y

    def to_latlon(self, x, y):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        lat = self.lat0 + np.degrees(y / self._m_per_rad_lat)
        lon = self.lon0 + np.degrees(x / self._m_per_rad_lon)
        return lat, lon

    @classmethod
    def around(cls, lats: Sequence[float], lons: Sequence[float]) -> "LocalProjection":
        return cls(float(np.mean(lats)), float(np.mean(lons)))


def cumulative_length(xy: np.ndarray) -> np.ndarray:
    d = np.hypot(np.diff(xy[:, 0]), np.diff(xy[:, 1]))
    return np.concatenate([[0.0], np.cumsum(d)])


def dedupe_polyline(xy: np.ndarray, min_seg: float = 0.5) -> np.ndarray:
    """Drop consecutive vertices closer than min_seg metres (keeps the last vertex)."""
    if len(xy) < 2:
        return xy
    keep = [0]
    for i in range(1, len(xy)):
        if math.hypot(*(xy[i] - xy[keep[-1]])) >= min_seg:
            keep.append(i)
    if keep[-1] != len(xy) - 1:
        keep[-1] = len(xy) - 1
    return xy[keep]


def project_point_to_polyline(px: float, py: float, xy: np.ndarray, s: np.ndarray | None = None):
    """Return (chainage, offset_distance, segment_index) of the closest point on a polyline."""
    if s is None:
        s = cumulative_length(xy)
    a = xy[:-1]
    b = xy[1:]
    ab = b - a
    L2 = np.einsum("ij,ij->i", ab, ab)
    L2[L2 == 0] = 1e-12
    t = np.clip(((px - a[:, 0]) * ab[:, 0] + (py - a[:, 1]) * ab[:, 1]) / L2, 0, 1)
    cx = a[:, 0] + t * ab[:, 0]
    cy = a[:, 1] + t * ab[:, 1]
    d = np.hypot(cx - px, cy - py)
    i = int(np.argmin(d))
    return float(s[i] + t[i] * math.sqrt(L2[i])), float(d[i]), i


def interp_polyline(xy: np.ndarray, s: np.ndarray, s_query) -> np.ndarray:
    s_query = np.asarray(s_query, dtype=float)
    return np.column_stack([np.interp(s_query, s, xy[:, 0]), np.interp(s_query, s, xy[:, 1])])


def heading(dx: float, dy: float) -> float:
    """Planar heading in radians (atan2 of dy, dx)."""
    return math.atan2(dy, dx)


def wrap_angle(a):
    return (np.asarray(a) + np.pi) % (2 * np.pi) - np.pi
