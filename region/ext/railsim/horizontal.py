"""The horizontal alignment of a section for the run: railsim's fit of the section's drawn path. Pure.

Interim rule ``run.horizontal.fit_from_drawn_path`` (checklist 2.1.14, lean (b)): until the horizontal alignment is
geometry of its own, the curves are fitted to the polyline the line file draws, as railsim fits a KMZ line:
``horizontal.fit_horizontal`` with ``app.curve_design_from``, in railsim's local tangent plane around the path
(``geo.LocalProjection.around``), so radii and run chainage are in ground metres as railsim's are.

Section chainage ``c`` (Ben's, on ``grid:26916``) and run chainage ``s`` (along the fit) are two measures of the same
line: ``fit_section`` projects every section sample onto the fit (a vectorised windowed projection, monotone), so
any value on the section grid (the rail, a station centre, a structure run) is laid onto the run grid by
interpolation, and any run answer is drawn back in section chainage.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

WINDOW_M = 300.0
"""How far along the fit a section sample's projection is searched around its first guess."""
CHUNK = 256


def design_of(geometry: Mapping[str, Any]) -> Any:
    """railsim's ``CurveDesign`` for a geometry block (``app.curve_design_from``)."""
    from railsim import app

    return app.curve_design_from({"geometry": dict(geometry)}, None)


def _project(px: np.ndarray, py: np.ndarray, xy: np.ndarray, s: np.ndarray, guess: np.ndarray) -> np.ndarray:
    """The chainage on the polyline ``(xy, s)`` of each point, searched within ``WINDOW_M`` of ``guess``."""
    out = np.empty(len(px))
    a_all, b_all = xy[:-1], xy[1:]
    ab_all = b_all - a_all
    L2_all = np.einsum("ij,ij->i", ab_all, ab_all)
    L2_all[L2_all == 0] = 1e-12
    seg_len = np.sqrt(L2_all)
    for i0 in range(0, len(px), CHUNK):
        i1 = min(i0 + CHUNK, len(px))
        lo = int(np.searchsorted(s, guess[i0:i1].min() - WINDOW_M, side="right")) - 1
        hi = int(np.searchsorted(s, guess[i0:i1].max() + WINDOW_M, side="left")) + 1
        lo, hi = max(lo, 0), min(hi, len(s) - 1)
        a, ab, L2 = a_all[lo:hi], ab_all[lo:hi], L2_all[lo:hi]
        qx = px[i0:i1, None]
        qy = py[i0:i1, None]
        t = np.clip(((qx - a[None, :, 0]) * ab[None, :, 0] + (qy - a[None, :, 1]) * ab[None, :, 1]) / L2[None, :], 0, 1)
        cx = a[None, :, 0] + t * ab[None, :, 0]
        cy = a[None, :, 1] + t * ab[None, :, 1]
        d = np.hypot(cx - qx, cy - qy)
        j = np.argmin(d, axis=1)
        rows = np.arange(i1 - i0)
        out[i0:i1] = s[lo + j] + t[rows, j] * seg_len[lo + j]
    return out


def fit_section(
    path: Sequence[Sequence[float]], length_m: float, step_m: float, geometry: Mapping[str, Any]
) -> dict[str, Any]:
    """The fit of one section's drawn path ``[[c, lon, lat], ...]``: ``{meta, arrays}``.

    ``meta``: ``length_m`` (fitted), ``drawn_m``, ``proj`` (``lat0``, ``lon0``), ``curves`` (run and section
    chainage, R, spiral, cant, deflection, direction, tangent), ``grid`` (the section grid). ``arrays``: ``s_of_c`` (the
    run chainage of each section sample) and ``fit`` ([m, 3]: s, x, y of the fitted polyline)."""
    from railsim.geo import LocalProjection
    from railsim.horizontal import fit_horizontal

    p = np.asarray(path, dtype=float)
    if p.ndim != 2 or p.shape[0] < 2 or p.shape[1] < 3:
        raise ValueError("a section path is at least two [c, lon, lat] points")
    pc, lon, lat = p[:, 0], p[:, 1], p[:, 2]
    proj = LocalProjection.around(lat, lon)
    x, y = proj.to_xy(lat, lon)
    xy = np.column_stack([x, y])
    h = fit_horizontal(xy, design_of(geometry))
    n = int(np.floor(float(length_m) / float(step_m) + 1e-9)) + 1
    c = np.arange(n) * float(step_m)
    sx = np.interp(c, pc, x)
    sy = np.interp(c, pc, y)
    ratio = h.length / max(float(length_m), 1.0)
    s_of_c = _project(sx, sy, h.xy, h.s, c * ratio)
    s_of_c = np.clip(np.maximum.accumulate(s_of_c), 0.0, h.length)
    s_of_c[0] = 0.0 if s_of_c[0] < 1.0 else s_of_c[0]

    def c_at(sv: float) -> float:
        return float(np.interp(sv, s_of_c + np.arange(n) * 1e-9, c))

    curves = [
        {
            "s_ts": float(cv.s_ts),
            "s_sc": float(cv.s_sc),
            "s_cs": float(cv.s_cs),
            "s_st": float(cv.s_st),
            "c_ts": c_at(cv.s_ts),
            "c_st": c_at(cv.s_st),
            "radius_m": float(cv.radius),
            "spiral_m": float(cv.spiral),
            "cant_m": float(cv.cant),
            "deflection_rad": float(cv.deflection),
            "direction": int(cv.direction),
            "tangent_m": float(cv.tangent),
        }
        for cv in h.curves
    ]
    meta = {
        "length_m": float(h.length),
        "drawn_m": float(h.drawn_length),
        "section_m": float(length_m),
        "proj": {"lat0": float(proj.lat0), "lon0": float(proj.lon0)},
        "curves": curves,
        "grid": {"c0": 0.0, "step_m": float(step_m), "n": n},
        "rule": "run.horizontal.fit_from_drawn_path",
    }
    fit = np.column_stack([h.s, h.xy[:, 0], h.xy[:, 1]]).astype("<f8")
    return {"meta": meta, "arrays": {"s_of_c": s_of_c.astype("<f8"), "fit": fit}}


def run_grid(length_m: float, ds: float = 2.0) -> np.ndarray:
    """The run grid railsim samples a route on (``Route.track_data``): ``0, ds, ...`` with the last sample at the
    length."""
    s = np.arange(0.0, float(length_m) + ds, ds)
    s[-1] = float(length_m)
    return s


def c_of_s(s: np.ndarray, s_of_c: np.ndarray, step_m: float) -> np.ndarray:
    """Section chainage at each run chainage, the inverse of ``s_of_c`` (monotone)."""
    n = len(s_of_c)
    c = np.arange(n) * float(step_m)
    return np.interp(s, s_of_c + np.arange(n) * 1e-9, c)


def s_of(c: float | np.ndarray, s_of_c: np.ndarray, step_m: float) -> Any:
    """Run chainage of section chainage ``c``."""
    n = len(s_of_c)
    return np.interp(c, np.arange(n) * float(step_m), s_of_c)


__all__ = ["c_of_s", "design_of", "fit_section", "run_grid", "s_of"]
