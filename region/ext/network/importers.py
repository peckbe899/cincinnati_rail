"""``profile_lines@1``: the Metro line files into the ``import:profiles`` layer.

For each route ``data/profile/lines/index.json`` lists (16 today), the importer yields:

- a ``route`` and its one ``section`` (chainage basis ``grid:26916``, its ``scale``, the path, rivers, crossings,
  Deck pieces and ties), with a ``node`` at each end;
- a ``ground_profile`` (the file's ``ground_dm`` and ``ground_dm_lidar``);
- for each station entry a ``station``, a ``stop`` on the section (chainage, order) and a ``platform``;
- an empty ``profile`` (``attrs.no_doc``); the old hub's doc, where one was saved, is the ``legacy:old_hub``
  revision of the same record (``old_hub@1``);
- a ``param`` for each member of the file's ``settings`` overlay (the CVG Express's 204.216 m platforms), scoped to
  the route.

``records`` is pure: the same files give the same records. Ids come from ``ids.id_for`` (match before mint, 9.17): a
station renamed in a line file whose point stayed within 50 m keeps its stop, station and platform ids, so Ben's
levels stay on it; a route whose ends stayed put keeps its section, route, nodes and profile. Every record keeps the
line file's values, so the line file rebuilds from the records (``line_of``).

The runner reads the line files from git (``from_git``, decision 9.27) and records each file's sha256 in the run.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import Any

from region.core.errors import Invalid
from region.core.protocols import IdLookup, PathResolver

from . import lines as LN

ROUTE_ATTRS = ("variant", "opened", "src_flags", "route_chainage_m", "settings")
"""Line file members kept on the route's ``attrs`` (with ``system_name``), when the file has them."""
SECTION_PARTS = ("rivers", "crossings", "pieces", "segs")


class KeyGuard:
    """Refuses one key asked for under two legacy kinds in one run: ``ids.stable`` mints from the key alone, so the
    two records would get one id."""

    def __init__(self) -> None:
        self._kinds: dict[str, str] = {}

    def __call__(self, lkind: str, key: str) -> str:
        seen = self._kinds.setdefault(key, lkind)
        if seen != lkind:
            raise Invalid(f"legacy key {key!r} is asked for as both {seen} and {lkind}; keys must be distinct")
        return key


class Matcher:
    """The rename matches of one run (9.17). A primary record (a stop, by chainage on its section; a section, by
    its path's ends) is matched among the orphans whose own key is gone from this run; the records that hang off it
    (its station and platform; its route, nodes, ground profile and profile) then take the matched record's."""

    def __init__(self, keys: Mapping[str, set[str]]) -> None:
        self.keys = keys
        self.section: dict[str, Any] | None = None
        self.stop: dict[str, Any] | None = None

    def _gone(self, lkind: str, key: str) -> bool:
        return key not in self.keys.get(lkind, set())

    def section_match(self, route: str, ends: tuple[tuple[float, float], tuple[float, float]]) -> Callable:
        def match(orphans: list[dict[str, Any]]) -> str | None:
            best = None
            for o in orphans:
                d = o.get("data") or {}
                path = d.get("path") or []
                if len(path) < 2 or not self._gone("section", LN.section_key(str(d.get("key")))):
                    continue
                a, b = (path[0][1], path[0][2]), (path[-1][1], path[-1][2])
                gap = max(LN.near(a, ends[0]), LN.near(b, ends[1]))
                if gap <= LN.MATCH_M and (best is None or (gap, o["id"]) < best[0]):
                    best = ((gap, o["id"]), o)
            self.section = best[1] if best else None
            return self.section["id"] if self.section else None

        return match

    def stop_match(self, route: str, section_id: str, c: float) -> Callable:
        # An orphan's own old key names the route its section had then: the matched section's old key when the route
        # was renamed (its stops' keys all changed with it), else this route.
        was = str(_data(self.section).get("key") or route) if self.section is not None else route

        def match(orphans: list[dict[str, Any]]) -> str | None:
            best = None
            for o in orphans:
                d = o.get("data") or {}
                if d.get("section") != section_id or not self._gone("stop", LN.stop_key(was, str(d.get("key")))):
                    continue
                gap = abs(float(d.get("c", 0.0)) - c)
                if gap <= LN.MATCH_M and (best is None or (gap, o["id"]) < best[0]):
                    best = ((gap, o["id"]), o)
            self.stop = best[1] if best else None
            return self.stop["id"] if self.stop else None

        return match

    def follows(self, primary: str, test: Callable[[dict[str, Any], dict[str, Any]], bool]) -> Callable:
        """A match taking the orphan that ``test(orphan, matched primary)`` picks, when the primary was matched."""

        def match(orphans: list[dict[str, Any]]) -> str | None:
            found = getattr(self, primary)
            if found is None:
                return None
            hits = sorted(o["id"] for o in orphans if test(o, found))
            return hits[0] if hits else None

        return match


def _data(o: dict[str, Any]) -> dict[str, Any]:
    return o.get("data") or {}


class ProfileLines:
    """``profile_lines@1`` (see the module doc)."""

    name = "profile_lines"
    version = "1"
    namespace = "profiles"
    layer = "import:profiles"
    from_git = ("lines",)
    """Sources the runner reads from git when their folder is in the repo (9.27: Ben's copies can differ)."""

    def sources(self, paths: PathResolver) -> dict[str, str]:
        return {"lines": "tier://profile_lines/lines"}

    def records(self, src: Mapping[str, Path], ids: IdLookup) -> Iterator[dict[str, Any]]:
        folder = Path(src["lines"])
        files = LN.read_lines(folder)
        yield from records_of(files, ids)


def run_keys(files: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Every legacy key a run over ``files`` asks for, by legacy kind (what the rename matches leave alone)."""
    out: dict[str, set[str]] = {"section": set(), "stop": set()}
    for line in files:
        route = line["id"]
        out["section"].add(LN.section_key(route))
        out["stop"].update(LN.stop_key(route, k) for k in LN.station_keys(line))
    return out


def records_of(files: list[dict[str, Any]], ids: IdLookup) -> Iterator[dict[str, Any]]:
    """The records of the line files ``files`` (already read), in a stable order."""
    guard = KeyGuard()
    match = Matcher(run_keys(files))
    known_sections = {line["id"] for line in files}
    section_ids: dict[str, str] = {}
    staged: list[tuple[dict[str, Any], str, str, str, str, dict[str, Any] | None]] = []
    # sections first (crossings name the other lines' sections), then everything that hangs off each
    for line in files:
        route = line["id"]
        lonlat = LN.path_lonlat(line)
        ends = (lonlat[0], lonlat[-1])
        sid = ids.id_for(
            "section", guard("section", LN.section_key(route)), kind="section", match=match.section_match(route, ends)
        )
        rid = ids.id_for(
            "route",
            guard("route", LN.route_key(route)),
            kind="route",
            match=match.follows("section", lambda o, s: o["id"] == _data(s).get("route")),
        )
        a = ids.id_for(
            "node",
            guard("node", LN.node_key(route, "a")),
            kind="node",
            match=match.follows("section", lambda o, s: o["id"] == _data(s).get("a")),
        )
        b = ids.id_for(
            "node",
            guard("node", LN.node_key(route, "b")),
            kind="node",
            match=match.follows("section", lambda o, s: o["id"] == _data(s).get("b")),
        )
        section_ids[route] = sid
        staged.append((line, sid, rid, a, b, match.section))
        match.section = None
    for line, sid, rid, a, b, matched in staged:
        match.section = matched
        yield from _route(line, sid, rid, a, b, ids, guard, match, section_ids, known_sections)
        match.section = None


def _route(
    line: dict[str, Any],
    sid: str,
    rid: str,
    a: str,
    b: str,
    ids: IdLookup,
    guard: KeyGuard,
    match: Matcher,
    section_ids: Mapping[str, str],
    known: set[str],
) -> Iterator[dict[str, Any]]:
    from region.ext.profiles.doc import empty_profile

    route = line["id"]
    system = LN.system_of(line)
    source = f"tier://profile_lines/lines/{route}.json"
    lonlat = LN.path_lonlat(line)
    xy = LN.to_utm(lonlat)
    attrs: dict[str, Any] = {"system_name": line["system"]}
    for k in ROUTE_ATTRS:
        if k in line:
            attrs[k] = line[k]
    yield {
        "kind": "route",
        "id": rid,
        "data": {"key": route, "name": line["line"], "system": system, "color": line.get("color"), "attrs": attrs},
        "geom": None,
        "source": source,
    }
    for end, nid, (x, y) in (("a", a, xy[0]), ("b", b, xy[-1])):
        yield {
            "kind": "node",
            "id": nid,
            "data": {"key": LN.node_key(route, end), "name": f"{line['line']} {end}", "system": system},
            "geom": LN.wkt_point(x, y),
            "source": source,
        }
    section: dict[str, Any] = {
        "key": route,
        "name": line["line"],
        "system": system,
        "route": rid,
        "a": a,
        "b": b,
        "length_m": line["length_m"],
        "step_m": line["step_m"],
        "chainage_basis": "grid:26916",
        "scale": LN.scale_of(line),
        "path": line["path"],
    }
    for part in SECTION_PARTS:
        if part not in line:
            continue
        value = line[part]
        if part == "crossings":
            value = [{**x, "other": section_ids.get(x.get("wid")) if x.get("wid") in known else None} for x in value]
        section[part] = value
    yield {"kind": "section", "id": sid, "data": section, "geom": LN.wkt_line(xy), "source": source}
    of_section = match.follows("section", lambda o, s: _data(o).get("section") == s["id"])
    gid = ids.id_for(
        "ground_profile", guard("ground_profile", LN.ground_key(route)), kind="ground_profile", match=of_section
    )
    ground: dict[str, Any] = {
        "section": sid,
        "source": "line_file",
        "vdatum": "navd88_m",
        "step_m": line["step_m"],
        "z_dm": line.get("ground_dm") or [],
    }
    if "ground_dm_lidar" in line:
        ground["lidar_dm"] = line["ground_dm_lidar"]
    if "ground_note" in line:
        ground["note"] = line["ground_note"]
    yield {"kind": "ground_profile", "id": gid, "data": ground, "geom": None, "source": source}
    pid = ids.id_for("alignment", guard("alignment", LN.profile_key(route)), kind="profile", match=of_section)
    yield {"kind": "profile", "id": pid, "data": empty_profile(sid), "geom": None, "source": source}
    keys = LN.station_keys(line)
    points = LN.to_utm([(s["lon"], s["lat"]) for s in line["stations"]])
    for order, (st, key, (x, y)) in enumerate(zip(line["stations"], keys, points, strict=True)):
        stop_id = ids.id_for(
            "stop",
            guard("stop", LN.stop_key(route, key)),
            kind="stop",
            match=match.stop_match(route, sid, float(st["c"])),
        )
        station_id = ids.id_for(
            "station",
            guard("station", LN.station_key(route, key)),
            kind="station",
            match=match.follows("stop", lambda o, s: o["id"] == _data(s).get("station")),
        )
        platform_id = ids.id_for(
            "alignment_station",
            guard("alignment_station", LN.platform_key(route, key)),
            kind="platform",
            match=match.follows("stop", lambda o, s: _data(o).get("stop") == s["id"]),
        )
        match.stop = None
        station_attrs = {k: st[k] for k in st if k not in ("name", "c", "ground", "offset", "lon", "lat")}
        station: dict[str, Any] = {
            "key": LN.platform_key(route, key),
            "name": st["name"],
            "system": system,
            "lon": st.get("lon"),
            "lat": st.get("lat"),
        }
        if station_attrs:
            station["attrs"] = station_attrs
        point = LN.wkt_point(x, y)
        yield {"kind": "station", "id": station_id, "data": station, "geom": point, "source": source}
        yield {
            "kind": "stop",
            "id": stop_id,
            "data": {
                "key": key,
                "name": st["name"],
                "section": sid,
                "station": station_id,
                "c": st["c"],
                "order": order,
                "ground": st.get("ground"),
                "offset": st.get("offset"),
            },
            "geom": point,
            "source": source,
        }
        yield {
            "kind": "platform",
            "id": platform_id,
            "data": {"key": key, "name": st["name"], "section": sid, "stop": stop_id, "side": None, "length_m": None},
            "geom": None,
            "source": source,
        }
    for name, value in sorted((line.get("settings") or {}).items()):
        path = f"settings.{name}"
        param_id = ids.id_for("param", guard("param", LN.param_key(route, path)), kind="param")
        yield {
            "kind": "param",
            "id": param_id,
            "data": {
                "path": path,
                "value": value,
                "unit": "m" if name == "platform" else "value",
                "meaning": f"{line['line']}'s own {name} (the line file's settings overlay)",
                "source": f"data/profile/lines/{route}.json settings.{name}",
                "status": "recorded",
                "scope": {"kind": "route", "id": rid},
                "years": None,
                "ruling": None,
            },
            "geom": None,
            "source": source,
        }


def line_of(records: list[dict[str, Any]], route: str) -> dict[str, Any]:
    """The line file the records of one route stand for (the inputs round trip): every member as the file had it,
    in no particular order."""
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        by_kind.setdefault(r["kind"], []).append(r)
    sec = next(r for r in by_kind["section"] if r["data"]["key"] == route)
    rte = next(r for r in by_kind["route"] if r["id"] == sec["data"]["route"])
    grd = next(r for r in by_kind["ground_profile"] if r["data"]["section"] == sec["id"])
    stops = sorted((r for r in by_kind["stop"] if r["data"]["section"] == sec["id"]), key=lambda r: r["data"]["order"])
    stations = {r["id"]: r for r in by_kind["station"]}
    attrs = dict(rte["data"].get("attrs") or {})
    out: dict[str, Any] = {
        "id": route,
        "line": rte["data"]["name"],
        "system": attrs.pop("system_name"),
        "length_m": sec["data"]["length_m"],
        "step_m": sec["data"]["step_m"],
        "ground_dm": grd["data"]["z_dm"],
        "path": sec["data"]["path"],
        "color": rte["data"].get("color"),
    }
    out.update(attrs)
    for part in SECTION_PARTS:
        if part in sec["data"]:
            value = sec["data"][part]
            if part == "crossings":
                value = [{k: v for k, v in x.items() if k != "other"} for x in value]
            out[part] = value
    if "lidar_dm" in grd["data"]:
        out["ground_dm_lidar"] = grd["data"]["lidar_dm"]
    if "note" in grd["data"]:
        out["ground_note"] = grd["data"]["note"]
    out["stations"] = []
    for s in stops:
        stn = stations[s["data"]["station"]]["data"]
        entry = {
            "name": s["data"]["name"],
            "c": s["data"]["c"],
            "ground": s["data"]["ground"],
            "offset": s["data"]["offset"],
            "lon": stn["lon"],
            "lat": stn["lat"],
        }
        entry.update(stn.get("attrs") or {})
        out["stations"].append(entry)
    return out


PROFILE_LINES = ProfileLines()
IMPORTERS = [PROFILE_LINES]

__all__ = ["IMPORTERS", "KeyGuard", "Matcher", "PROFILE_LINES", "ProfileLines", "line_of", "records_of", "run_keys"]
