"""``old_hub@1``: the old hub's records into the ``legacy:old_hub`` layer (decision 9.23).

The source is ``hub/seed`` (the old hub's export, the ``old_hub_seed`` tier), or, given ``--hub-db PATH``, a backup-API
snapshot of Ben's ``hub\\hub.db`` (``oldhub.snapshot``; the live file is never read). The importer yields:

- **a profile revision per Metro route** of the line files: the route's alignment doc as a ``profile`` record
  (``region.ext.profiles.doc.profile_of``), over the empty profile ``profile_lines`` made, with the same id (the
  doc's keys map to the same platform ids, through the profiles namespace's legacy index). A route no doc was saved
  for (Line_10, 11 and 13) yields that same empty profile, which the store finds unchanged and so writes nothing;
- **Ben's access choices** (``params/station_access``) into each route's profile revision as ``access`` (profile
  version 2), keyed by platform id, so an access choice goes through drafts and undo like every station edit; a key
  that names no station of the line stays in ``attrs.unmatched.access``;
- **a platform revision per station** with its ``side`` (side or island) from ``params/station_platforms``, over the
  platform ``profile_lines`` made (equal to it where the params name no side, so nothing is written);
- **a station complex per group** of ``params/station_complexes`` (``auto`` and ``marked``);
- **the Chronology** (``chronology/segments`` with the routes of ``data/profile/chronology_lines.json``), one record;
- **the roadmap items**, **the cameras** (``data/users/<user>/camera_<name>``) and **saved views**;
- **an authority record per legacy-owned kind** (``authority.LEGACY_KINDS``).

**Why every route yields a profile.** A legacy import tombstones any record on its layer that a run no longer
yields, and that tombstone would hide the import layer's profile underneath, in main as well. So the importer reads
the line files too, and for every route they list it yields either the doc's profile or the empty one: a rerun
never drops a profile by accident. A profile goes only when its route goes from the line files, which tombstones it
in ``import:profiles`` as well. The doc's keys that name no station of the line file stay in ``attrs.unmatched``.

The 30 RER docs are not read: the RER sections are slice 2's.
"""

from __future__ import annotations

import copy
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from region.core.protocols import IdLookup, PathResolver
from region.ext.network import lines as LN
from region.ext.profiles.doc import empty_profile, profile_of

from . import authority
from .oldhub import read_db, read_seed

ROADMAP_FIELDS = ("phase", "status", "title", "detail", "order")
CAMERA_FIELDS = ("pos", "target", "exag", "station")


class OldHub:
    """``old_hub@1`` (see the module doc)."""

    name = "old_hub"
    version = "1"
    namespace = "old_hub"
    layer = "legacy:old_hub"
    from_git = ("lines", "chronology_lines")
    borrows = {"profiles": ("section", "alignment", "alignment_station", "stop")}
    """Legacy kinds whose ids belong to another namespace (the profile revisions sit over ``import:profiles``)."""

    def sources(self, paths: PathResolver) -> dict[str, str]:
        return {
            "lines": "tier://profile_lines/lines",
            "seed": "tier://old_hub_seed/",
            "chronology_lines": "tier://profile_lines/chronology_lines.json",
        }

    def records(self, src: Mapping[str, Path], ids: IdLookup) -> Iterator[dict[str, Any]]:
        if "hub_db" in src:
            docs, origin = read_db(Path(src["hub_db"])), "hub.db"
        else:
            docs, origin = read_seed(Path(src["seed"])), "seed"
        lines = Path(src["lines"])
        routes = read_chronology_lines(Path(src.get("chronology_lines") or lines.parent / "chronology_lines.json"))
        yield from records_of(LN.read_lines(lines), docs, ids, origin=origin, chronology_routes=routes)


def _source(origin: str, path: str) -> str:
    return f"tier://old_hub_seed/{path}.json" if origin == "seed" else f"hub.db:{path}"


ACCESS = "params/station_access"
PLATFORMS = "params/station_platforms"
COMPLEXES = "params/station_complexes"
CHRONOLOGY = "chronology/segments"
CHRONOLOGY_ROUTE_FIELDS = ("id", "sys", "name", "kind", "parent", "stations", "segments")
"""The members of a chronology_lines route the Chronology record keeps (its plan path and colour are drawing)."""


def read_chronology_lines(path: Path) -> list[dict[str, Any]] | None:
    """The routes of ``chronology_lines.json`` (``None`` where the file is not there)."""
    import json

    if not path.is_file():
        return None
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    routes = doc.get("routes") if isinstance(doc, dict) else None
    return routes if isinstance(routes, list) else None


def _by_station(table: Any, route: str, keys: list[str], names: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    """A params table's entries for one route (``{route: {key: value}}``), matched to the line's stations by key,
    else by name, as the old page reads them (``ST_ACCESS[id][keyOf(s)] || ST_ACCESS[id][s.name]``, profiles.html
    505 and 1287): ``({station key: value}, {unmatched key: value})``."""
    entry = table.get(route) if isinstance(table, Mapping) else None
    if not isinstance(entry, Mapping):
        return {}, {}
    out: dict[str, Any] = {}
    used: set[str] = set()
    for k, n in zip(keys, names, strict=True):
        if k in entry:
            out[k] = entry[k]
            used.add(k)
        elif n in entry:
            out[k] = entry[n]
            used.add(n)
    return out, {k: v for k, v in entry.items() if k not in used}


def _access_of(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or not isinstance(value.get("type"), str):
        return None
    out: dict[str, Any] = {"type": value["type"]}
    for k in ("stages", "source"):
        if k in value:
            out[k] = copy.deepcopy(value[k])
    return out


def records_of(
    files: list[dict[str, Any]],
    docs: Mapping[str, Any],
    ids: IdLookup,
    *,
    origin: str = "seed",
    chronology_routes: list[dict[str, Any]] | None = None,
) -> Iterator[dict[str, Any]]:
    """The records of the old hub's documents ``docs`` (``{path: data}``) over the line files ``files``;
    ``chronology_routes`` are the routes of ``chronology_lines.json``."""
    access_table = docs.get(ACCESS)
    side_table = docs.get(PLATFORMS)
    for line in files:
        route = line["id"]
        sid = ids.id_for("section", LN.section_key(route), kind="section")
        pid = ids.id_for("alignment", LN.profile_key(route), kind="profile")
        path = LN.profile_key(route)
        doc = docs.get(path)
        keys = LN.station_keys(line)
        names = [str(s["name"]) for s in line["stations"]]
        platforms = {k: ids.id_for("alignment_station", LN.platform_key(route, k), kind="platform") for k in keys}
        if isinstance(doc, Mapping):
            data = profile_of(
                doc,
                section_id=sid,
                keys=keys,
                names=[str(s["name"]) for s in line["stations"]],
                platforms=platforms,
                route_name=str(line["line"]),
                system_name=str(line["system"]),
            )
            source = _source(origin, path)
        else:
            data = empty_profile(sid)
            source = f"tier://profile_lines/lines/{route}.json"
        chosen, lost = _by_station(access_table, route, keys, names)
        access = {platforms[k]: a for k, v in chosen.items() if (a := _access_of(v)) is not None}
        bad = {k: copy.deepcopy(v) for k, v in chosen.items() if _access_of(v) is None}
        lost.update(bad)
        if access:
            data["access"] = access
        if lost:
            attrs = data.setdefault("attrs", {})
            attrs.setdefault("unmatched", {})["access"] = copy.deepcopy(lost)
        yield {"kind": "profile", "id": pid, "data": data, "geom": None, "source": source}
        yield from _platforms(line, sid, keys, names, platforms, side_table, ids, origin)
    yield from _complexes(docs.get(COMPLEXES), ids, origin)
    chron = _chronology(docs.get(CHRONOLOGY), chronology_routes, ids, origin)
    if chron is not None:
        yield chron
    for path in sorted(docs):
        doc = docs[path]
        if not isinstance(doc, Mapping):
            continue
        if path.startswith("roadmap/"):
            yield _roadmap(path, doc, ids, origin)
        elif path.startswith("data/users/") and path.rsplit("/", 1)[-1].startswith("camera_"):
            yield _camera(path, doc, ids, origin)
        elif path.startswith("views/"):
            yield _view(path, doc, ids, origin)
    yield from authority.authority_records(ids)


def _platforms(
    line: dict[str, Any],
    sid: str,
    keys: list[str],
    names: list[str],
    platforms: Mapping[str, str],
    side_table: Any,
    ids: IdLookup,
    origin: str,
) -> Iterator[dict[str, Any]]:
    """A platform revision per station of the line, as ``profile_lines`` makes it, with ``side`` from
    ``params/station_platforms`` (by key, else by name; ``None`` where the params have none or another value)."""
    route = line["id"]
    sides, _ = _by_station(side_table, route, keys, names)
    for k, n in zip(keys, names, strict=True):
        side = sides.get(k)
        stop_id = ids.id_for("stop", LN.stop_key(route, k), kind="stop")
        yield {
            "kind": "platform",
            "id": platforms[k],
            "data": {
                "key": k,
                "name": n,
                "section": sid,
                "stop": stop_id,
                "side": side if side in ("side", "island") else None,
                "length_m": None,
            },
            "geom": None,
            "source": _source(origin, PLATFORMS)
            if side in ("side", "island")
            else f"tier://profile_lines/lines/{route}.json",
        }


def complex_key(group: str) -> str:
    """The legacy key of a station complex: its id in params/station_complexes."""
    return f"complex:{group}"


def _complexes(table: Any, ids: IdLookup, origin: str) -> Iterator[dict[str, Any]]:
    if not isinstance(table, Mapping):
        return
    seen: set[str] = set()
    for group in ("auto", "marked"):
        for g in table.get(group) or []:
            if not isinstance(g, Mapping) or not isinstance(g.get("id"), str) or g["id"] in seen:
                continue
            seen.add(g["id"])
            data: dict[str, Any] = {
                "key": g["id"],
                "name": str(g.get("name") or g["id"]),
                "group": group,
                "members": [copy.deepcopy(m) for m in g.get("members") or [] if isinstance(m, Mapping)],
            }
            for k in ("x", "y"):
                if k in g:
                    data[k] = g[k]
            rest = _rest(g, ("id", "name", "members", "x", "y"))
            if rest:
                data["attrs"] = copy.deepcopy(rest)
            yield {
                "kind": "station_complex",
                "id": ids.id_for("station_complex", complex_key(g["id"]), kind="station_complex"),
                "data": data,
                "geom": None,
                "source": _source(origin, COMPLEXES),
            }


def _chronology(doc: Any, routes: list[dict[str, Any]] | None, ids: IdLookup, origin: str) -> dict[str, Any] | None:
    if not isinstance(doc, Mapping):
        return None
    data: dict[str, Any] = {
        "key": "chronology",
        "segments": copy.deepcopy(doc.get("segments") or {}),
        "stations": copy.deepcopy(doc.get("stations") or {}),
        "phase_years": copy.deepcopy(doc.get("phase_years") or []),
        "routes": [
            {k: copy.deepcopy(r[k]) for k in CHRONOLOGY_ROUTE_FIELDS if k in r}
            for r in routes or []
            if isinstance(r, Mapping)
        ],
    }
    rest = _rest(doc, ("segments", "stations", "phase_years"))
    attrs: dict[str, Any] = copy.deepcopy(rest) if rest else {}
    attrs["routes_file"] = "data/profile/chronology_lines.json" if routes is not None else None
    data["attrs"] = attrs
    return {
        "kind": "chronology",
        "id": ids.id_for("chronology", CHRONOLOGY, kind="chronology"),
        "data": data,
        "geom": None,
        "source": _source(origin, CHRONOLOGY),
    }


def _rest(doc: Mapping[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {k: v for k, v in doc.items() if k not in fields}


def _roadmap(path: str, doc: Mapping[str, Any], ids: IdLookup, origin: str) -> dict[str, Any]:
    data: dict[str, Any] = {"key": path.split("/", 1)[1]}
    data.update({f: doc[f] for f in ROADMAP_FIELDS if f in doc})
    rest = _rest(doc, ROADMAP_FIELDS)
    if rest:
        data["attrs"] = rest
    return {
        "kind": "roadmap_item",
        "id": ids.id_for("roadmap_item", path, kind="roadmap_item"),
        "data": data,
        "geom": None,
        "source": _source(origin, path),
    }


def _camera(path: str, doc: Mapping[str, Any], ids: IdLookup, origin: str) -> dict[str, Any]:
    _, _, user, leaf = path.split("/", 3)
    data: dict[str, Any] = {"user": user, "name": leaf[len("camera_") :]}
    data.update({f: doc[f] for f in CAMERA_FIELDS if f in doc})
    rest = _rest(doc, CAMERA_FIELDS)
    if rest:
        data["attrs"] = rest
    return {
        "kind": "camera",
        "id": ids.id_for("camera", path, kind="camera"),
        "data": data,
        "geom": None,
        "source": _source(origin, path),
    }


def _view(path: str, doc: Mapping[str, Any], ids: IdLookup, origin: str) -> dict[str, Any]:
    camera = {f: doc[f] for f in CAMERA_FIELDS if f in doc}
    data: dict[str, Any] = {"name": str(doc.get("name") or path.split("/", 1)[1]), "camera": camera}
    if "user" in doc:
        data["user"] = doc["user"]
    if "note" in doc:
        data["note"] = doc["note"]
    rest = _rest(doc, (*CAMERA_FIELDS, "name", "user", "note"))
    if rest:
        data["attrs"] = rest
    return {
        "kind": "view",
        "id": ids.id_for("saved_view", path, kind="view"),
        "data": data,
        "geom": None,
        "source": _source(origin, path),
    }


OLD_HUB = OldHub()
IMPORTERS = [OLD_HUB]

__all__ = ["IMPORTERS", "OLD_HUB", "OldHub", "records_of"]
