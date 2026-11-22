"""The network feature's validators: a section's path runs forward to its length, its ``scale`` is the one its
geometry gives, and a ground profile covers its section's grid."""

from __future__ import annotations

import math
from typing import Any

from region.core.protocols import ValidateCtx

TOLERANCE_M = 1.0
# scale is derived from the geometry (9.14: geodesic over grid length). Snapping to 1 mm moves it by a few parts in a
# billion; a re-path moves it by parts per million, so a stale value is caught.
SCALE_TOLERANCE = 1e-7


def scale_of_geom(geom: str) -> float | None:
    """The UTM 16N scale along a section's geometry (EPSG:26916 WKT): its geodesic length over its grid length, as
    ``region.ext.network.lines.scale_of`` measures a line file's path. ``None`` for no geometry or no length."""
    from pyproj import Geod, Transformer
    from shapely import wkt

    try:
        xy = list(wkt.loads(geom).coords)
    except Exception:
        return None
    if len(xy) < 2:
        return None
    lons, lats = Transformer.from_crs(26916, 4326, always_xy=True).transform([p[0] for p in xy], [p[1] for p in xy])
    grid = sum(math.dist(a[:2], b[:2]) for a, b in zip(xy, xy[1:], strict=False))
    geodesic = Geod(ellps="WGS84").line_length(lons, lats)
    if not grid > 0 or not math.isfinite(geodesic):
        return None
    return geodesic / grid


def section_path(rec: dict[str, Any], ctx: ValidateCtx) -> list[dict[str, Any]]:
    data = rec.get("data") or {}
    path = data.get("path") or []
    errors: list[dict[str, Any]] = []
    last = None
    for i, p in enumerate(path):
        c = p[0]
        if last is not None and c < last:
            errors.append(
                {"path": f"/data/path/{i}/0", "message": f"chainage {c} m runs back from {last} m", "rule": None}
            )
            break
        last = c
    length = data.get("length_m")
    if path and isinstance(length, (int, float)) and abs(path[-1][0] - length) > TOLERANCE_M:
        errors.append(
            {"path": "/data/length_m", "message": f"the path ends at {path[-1][0]} m, not {length} m", "rule": None}
        )
    scale, geom = data.get("scale"), rec.get("geom")
    if isinstance(scale, (int, float)) and isinstance(geom, str):
        want = scale_of_geom(geom)
        if want is not None and abs(want - scale) > SCALE_TOLERANCE:
            errors.append(
                {
                    "path": "/data/scale",
                    "message": f"scale {scale} is not the one the geometry gives ({want:.9f}); a re-path must carry "
                    "its new scale",
                    "rule": None,
                }
            )
    return errors


def ground_covers(rec: dict[str, Any], ctx: ValidateCtx) -> list[dict[str, Any]]:
    data = rec.get("data") or {}
    section = ctx.get("section", data.get("section")) if isinstance(data.get("section"), str) else None
    if section is None:
        return []
    length, step = (section.get("data") or {}).get("length_m"), data.get("step_m")
    if not isinstance(length, (int, float)) or not isinstance(step, (int, float)) or step <= 0:
        return []
    need = math.floor(length / step) + 1
    have = len(data.get("z_dm") or [])
    if have < need:
        return [
            {
                "path": "/data/z_dm",
                "message": f"{have} levels do not cover {length} m at {step} m ({need})",
                "rule": None,
            }
        ]
    return []


VALIDATORS = {"section": section_path, "ground_profile": ground_covers}

__all__ = ["SCALE_TOLERANCE", "TOLERANCE_M", "VALIDATORS", "ground_covers", "scale_of_geom", "section_path"]
