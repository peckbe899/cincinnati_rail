"""Record geometry: parse, check, snap to 1 mm and write one canonical WKT (section 4, validation step 4; 9.29).

A record's ``geom`` is WKT in EPSG:26916 metres, or ``None``. On every write the store parses it (WKT, or a GeoJSON
geometry object for convenience), checks its type against the kind's ``geometry``, refuses empty, 3D and invalid
shapes, snaps every coordinate to the nearest millimetre and writes it back in one canonical text form, so the same
shape always gives the same bytes and the same content hash on every machine:

    POINT (715000 4331000.125)
    LINESTRING (0 0, 10.5 0)
    POLYGON ((0 0, 10 0, 10 10, 0 0), (2 2, 3 2, 3 3, 2 2))
    MULTIPOINT ((0 0), (1 1))

The text is written from integer millimetres, never through float formatting or GEOS's writer, so it does not depend
on the GEOS version a machine has.
"""

from __future__ import annotations

import math
from typing import Any

from region.core.errors import Invalid

TYPES = ("Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon")
_WKT_NAME = {t: t.upper() for t in TYPES}


def _mm(v: float) -> int:
    f = float(v)
    if not math.isfinite(f):
        raise Invalid(
            "geometry has a NaN or infinite coordinate", errors=[{"path": "/geom", "message": "finite numbers"}]
        )
    return int(round(f * 1000.0))


def _num(mm: int) -> str:
    sign = "-" if mm < 0 else ""
    whole, frac = divmod(abs(mm), 1000)
    if frac == 0:
        return f"{sign}{whole}"
    return f"{sign}{whole}.{frac:03d}".rstrip("0")


def _coords(seq: Any) -> list[tuple[int, int]]:
    out = []
    for c in seq:
        if len(c) != 2:
            raise Invalid(
                "geometry has 3D coordinates; record geometry is 2D (EPSG:26916 metres)",
                errors=[{"path": "/geom", "message": "2D coordinates only"}],
            )
        out.append((_mm(c[0]), _mm(c[1])))
    return out


def _ring_text(pts: list[tuple[int, int]]) -> str:
    return "(" + ", ".join(f"{_num(x)} {_num(y)}" for x, y in pts) + ")"


def _parts(g: Any) -> tuple[str, Any]:
    """``(type, snapped integer coordinates)`` of a shapely geometry."""
    t = g.geom_type
    if t == "Point":
        return t, _coords(g.coords)
    if t == "LineString":
        return t, _coords(g.coords)
    if t == "Polygon":
        return t, [_coords(g.exterior.coords)] + [_coords(r.coords) for r in g.interiors]
    if t in ("MultiPoint", "MultiLineString", "MultiPolygon"):
        return t, [_parts(p)[1] for p in g.geoms]
    raise Invalid(f"geometry type {t} is not supported", errors=[{"path": "/geom", "message": f"{t} not supported"}])


def _text(t: str, parts: Any) -> str:
    name = _WKT_NAME[t]
    if t == "Point":
        return f"{name} {_ring_text(parts)}"
    if t == "LineString":
        return f"{name} {_ring_text(parts)}"
    if t == "Polygon":
        return f"{name} (" + ", ".join(_ring_text(r) for r in parts) + ")"
    if t == "MultiPoint":
        return f"{name} (" + ", ".join(_ring_text(p) for p in parts) + ")"
    if t == "MultiLineString":
        return f"{name} (" + ", ".join(_ring_text(p) for p in parts) + ")"
    return f"{name} (" + ", ".join("(" + ", ".join(_ring_text(r) for r in poly) + ")" for poly in parts) + ")"


def _flat(t: str, parts: Any) -> list[tuple[int, int]]:
    if t in ("Point", "LineString"):
        return list(parts)
    if t in ("Polygon", "MultiPoint", "MultiLineString"):
        return [c for p in parts for c in p]
    return [c for poly in parts for ring in poly for c in ring]


def parse(value: Any) -> Any:
    """A shapely geometry from WKT text or a GeoJSON geometry object. ``Invalid`` when it cannot be read."""
    import shapely
    from shapely.geometry import shape

    try:
        if isinstance(value, str):
            return shapely.from_wkt(value)
        if isinstance(value, dict):
            return shape(value)
    except Exception as e:  # GEOS and shapely raise several types for bad input
        raise Invalid(f"geometry cannot be read: {e}", errors=[{"path": "/geom", "message": str(e)}]) from None
    raise Invalid(
        "geometry must be WKT text, a GeoJSON geometry or null",
        errors=[{"path": "/geom", "message": "WKT, GeoJSON geometry or null"}],
    )


def normalize(value: Any, expected: str = "any") -> tuple[str | None, tuple[float, float, float, float] | None]:
    """``(canonical WKT, bbox)`` of a record geometry, checked against the kind's ``geometry`` declaration.

    ``expected`` is the kind's ``geometry``: ``none`` requires ``None``; ``any`` accepts every supported type.
    The bbox is ``(x0, y0, x1, y1)`` of the snapped coordinates. ``Invalid`` lists what is wrong.
    """
    if value is None:
        return None, None
    if expected == "none":
        raise Invalid("this kind has no geometry", errors=[{"path": "/geom", "message": "must be null"}])
    import shapely

    g = parse(value)
    if g is None or g.is_empty:
        raise Invalid("geometry is empty", errors=[{"path": "/geom", "message": "empty geometry"}])
    if g.has_z:
        raise Invalid(
            "geometry has 3D coordinates; record geometry is 2D (EPSG:26916 metres)",
            errors=[{"path": "/geom", "message": "2D coordinates only"}],
        )
    t, parts = _parts(g)
    if expected not in ("any", t):
        raise Invalid(
            f"geometry is a {t}; this kind takes a {expected}",
            errors=[{"path": "/geom", "message": f"{expected} expected, got {t}"}],
        )
    text = _text(t, parts)
    snapped = shapely.from_wkt(text)
    if not shapely.is_valid(snapped):
        reason = shapely.is_valid_reason(snapped)
        raise Invalid(
            f"geometry is not valid after snapping to 1 mm: {reason}", errors=[{"path": "/geom", "message": reason}]
        )
    pts = _flat(t, parts)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    bbox = (min(xs) / 1000.0, min(ys) / 1000.0, max(xs) / 1000.0, max(ys) / 1000.0)
    return text, bbox


def bbox_of(wkt: str | None) -> tuple[float, float, float, float] | None:
    """The bbox of a stored (canonical) WKT, or ``None``."""
    if wkt is None:
        return None
    return normalize(wkt, "any")[1]


def to_geojson(wkt: str | None) -> dict[str, Any] | None:
    """A GeoJSON geometry object of a stored WKT (coordinates still EPSG:26916)."""
    if wkt is None:
        return None
    import shapely
    from shapely.geometry import mapping

    return dict(mapping(shapely.from_wkt(wkt)))


__all__ = ["TYPES", "bbox_of", "normalize", "parse", "to_geojson"]
