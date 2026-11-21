"""The Metro line files (``data/profile/lines``): reading them, their station keys, and their geometry.

A line file is Deck-tie output (decision 9.27): one route with its path as ``[c, lon, lat]`` points, its stations,
rivers, crossings, Deck pieces and ties, and its ground on a 2 m grid in decimetres. ``index.json`` lists the
routes. Both importers that read the line files (``profile_lines`` and ``old_hub``) use these helpers, so they agree
on every station key and every legacy key.

**Station keys** are the old Profiles page's (``profiles.html`` 718): the name, or ``name#index`` (the index in the
line file, from 0) where the file repeats a name. Line_8's ``Cincinnati State#2`` and ``#3`` are the only cases.

**Legacy keys.** ``IdLookup`` mints ``ids.stable(namespace, key)`` from the key alone, so every key an importer asks
for must be distinct across its legacy kinds. A record keeps the old system's own key where the old system had one
(the section ``Line_6``, the doc's station key ``Line_8|Cincinnati State#2``, the old hub's record path
``alignments/Line_6``); a record the old system had no key for takes ``<what>:<old key>`` (``route:Line_6``,
``stop:Line_8|Cincinnati State#2``). ``LEGACY`` names them all.

**Geometry.** lon and lat are WGS84 as the files write them; geometry is EPSG:26916 through the same pyproj transform
the Deck tools use (``Transformer.from_crs(4326, 26916, always_xy=True)``), written to 1 mm.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Iterable, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from region.core.errors import Invalid

INDEX = "index.json"

SYSTEMS = {"Cincinnati Metro": "metro", "CVG Express": "metro"}
"""The line file's ``system`` text to the hub's system (``region/kinds/_vocab.yaml`` systems). The CVG Express is a
Metro route with its own platform length (its ``settings`` overlay)."""

SCALE_DECIMALS = 8
MATCH_M = 50.0
"""How far a renamed station's point may have moved and still keep its ids (match before mint, 9.17)."""


# ------------------------------------------------------------------------------------------------- legacy keys


def section_key(route: str) -> str:
    return route


def route_key(route: str) -> str:
    return f"route:{route}"


def node_key(route: str, end: str) -> str:
    return f"{route}|{end}"


def ground_key(route: str) -> str:
    return f"ground:{route}"


def profile_key(route: str) -> str:
    """The old hub's record path of the route's alignment doc."""
    return f"alignments/{route}"


def platform_key(route: str, station: str) -> str:
    """The doc's station key, which names a platform in the hub."""
    return f"{route}|{station}"


def stop_key(route: str, station: str) -> str:
    return f"stop:{route}|{station}"


def station_key(route: str, station: str) -> str:
    return f"station:{route}|{station}"


def param_key(route: str, path: str) -> str:
    return f"param:{route}|{path}"


LEGACY = {
    "section": ("section", "Line_6"),
    "route": ("route", "route:Line_6"),
    "node": ("node", "Line_6|a"),
    "ground_profile": ("ground_profile", "ground:Line_6"),
    "profile": ("alignment", "alignments/Line_6"),
    "platform": ("alignment_station", "Line_8|Cincinnati State#2"),
    "stop": ("stop", "stop:Line_8|Cincinnati State#2"),
    "station": ("station", "station:Line_8|Cincinnati State#2"),
    "param": ("param", "param:CVG_Express|settings.platform"),
}
"""Each record kind's legacy kind and an example key."""


# ---------------------------------------------------------------------------------------------------- reading


def read_json(path: Path) -> Any:
    """A JSON file (UTF-8, a BOM tolerated)."""
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def read_index(folder: Path) -> list[dict[str, Any]]:
    """``index.json``: the routes, in the file's order."""
    found = read_json(Path(folder) / INDEX)
    if not isinstance(found, list) or not all(isinstance(e, dict) and isinstance(e.get("id"), str) for e in found):
        raise Invalid(f"{Path(folder) / INDEX} is not a list of {{id, line, length_m, stations}}")
    return found


def read_line(folder: Path, route: str) -> dict[str, Any]:
    """One line file, checked for the members the importers read."""
    path = Path(folder) / f"{route}.json"
    line = read_json(path)
    missing = [k for k in ("id", "line", "system", "length_m", "step_m", "path", "stations") if k not in line]
    if missing:
        raise Invalid(f"{path}: missing {', '.join(missing)}")
    if line["id"] != route:
        raise Invalid(f"{path}: id {line['id']!r} is not {route!r}")
    return line


def read_lines(folder: Path) -> list[dict[str, Any]]:
    """Every line file the index lists, in its order."""
    return [read_line(folder, e["id"]) for e in read_index(folder)]


def station_keys(line: dict[str, Any]) -> list[str]:
    """The page's station keys: the name, or ``name#index`` where the file repeats the name."""
    names = [str(s["name"]) for s in line["stations"]]
    count = Counter(names)
    return [n if count[n] == 1 else f"{n}#{i}" for i, n in enumerate(names)]


def system_of(line: dict[str, Any]) -> str:
    """The hub system of a line file (``metro``)."""
    found = SYSTEMS.get(str(line.get("system")))
    if found is None:
        raise Invalid(f"line {line.get('id')}: unknown system {line.get('system')!r} (add it to SYSTEMS)")
    return found


# --------------------------------------------------------------------------------------------------- geometry


@lru_cache(maxsize=1)
def _to_utm() -> Any:
    from pyproj import Transformer

    return Transformer.from_crs(4326, 26916, always_xy=True)


def to_utm(lonlat: Iterable[Sequence[float]]) -> list[tuple[float, float]]:
    """EPSG:26916 ``(x, y)`` of ``(lon, lat)`` points."""
    pts = list(lonlat)
    if not pts:
        return []
    xs, ys = _to_utm().transform([float(p[0]) for p in pts], [float(p[1]) for p in pts])
    return [(float(x), float(y)) for x, y in zip(xs, ys, strict=True)]


def _num(v: float) -> str:
    mm = int(round(v * 1000.0))
    sign = "-" if mm < 0 else ""
    whole, frac = divmod(abs(mm), 1000)
    return f"{sign}{whole}" if frac == 0 else f"{sign}{whole}.{frac:03d}".rstrip("0")


def wkt_point(x: float, y: float) -> str:
    return f"POINT ({_num(x)} {_num(y)})"


def wkt_line(xy: Sequence[tuple[float, float]]) -> str:
    """A LINESTRING to 1 mm, dropping points that snap onto the one before (they would make no segment)."""
    out: list[str] = []
    last = None
    for x, y in xy:
        cell = (_num(x), _num(y))
        if cell != last:
            out.append(f"{cell[0]} {cell[1]}")
            last = cell
    if len(out) < 2:
        raise Invalid("a path needs two distinct points")
    return "LINESTRING (" + ", ".join(out) + ")"


def path_lonlat(line: dict[str, Any]) -> list[tuple[float, float]]:
    return [(float(p[1]), float(p[2])) for p in line["path"]]


def scale_of(line: dict[str, Any]) -> float:
    """Ground distance per unit of grid chainage (9.14): the path's geodesic length over its length in EPSG:26916.

    Chainage is grid length as drawn, so this is the UTM 16N scale along the path (0.99983 at Line 6: 29,534.8 m on
    the ground for 29,539.6 m of chainage). It is measured on the path itself rather than against ``length_m``,
    because one file (the CVG Express) numbers its chainage a little apart from its path's grid length.
    """
    from pyproj import Geod

    lonlat = path_lonlat(line)
    lons, lats = zip(*lonlat, strict=True)
    geodesic = Geod(ellps="WGS84").line_length(lons, lats)
    xy = to_utm(lonlat)
    grid = sum(math.dist(a, b) for a, b in zip(xy, xy[1:], strict=False))
    if not grid > 0 or not math.isfinite(geodesic):
        raise Invalid(f"line {line.get('id')}: a path of no length has no scale")
    return round(geodesic / grid, SCALE_DECIMALS)


def near(a: Sequence[float], b: Sequence[float]) -> float:
    """Metres between two (lon, lat) points, by the local flat approximation (enough to match within 50 m)."""
    lat = math.radians((a[1] + b[1]) / 2)
    dx = (a[0] - b[0]) * 111_320.0 * math.cos(lat)
    dy = (a[1] - b[1]) * 110_540.0
    return math.hypot(dx, dy)


__all__ = [
    "INDEX",
    "LEGACY",
    "MATCH_M",
    "SYSTEMS",
    "ground_key",
    "near",
    "node_key",
    "param_key",
    "path_lonlat",
    "platform_key",
    "profile_key",
    "read_index",
    "read_json",
    "read_line",
    "read_lines",
    "route_key",
    "scale_of",
    "section_key",
    "station_key",
    "station_keys",
    "stop_key",
    "system_of",
    "to_utm",
    "wkt_line",
    "wkt_point",
]
