"""``old_hub@1``: the old hub's records into the ``legacy:old_hub`` layer (decision 9.23).

The source is ``hub/seed`` (the old hub's export, the ``old_hub_seed`` tier), or, given ``--hub-db PATH``, a backup-API
snapshot of Ben's ``hub\\hub.db`` (``oldhub.snapshot``; the live file is never read). The importer yields:

- **a profile revision per Metro route** of the line files: the route's alignment doc as a ``profile`` record
  (``region.ext.profiles.doc.profile_of``), over the empty profile ``profile_lines`` made, with the same id (the
  doc's keys map to the same platform ids, through the profiles namespace's legacy index). A route no doc was saved
  for (Line_10, 11 and 13) yields that same empty profile, which the store finds unchanged and so writes nothing;
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
    from_git = ("lines",)
    borrows = {"profiles": ("section", "alignment", "alignment_station")}
    """Legacy kinds whose ids belong to another namespace (the profile revisions sit over ``import:profiles``)."""

    def sources(self, paths: PathResolver) -> dict[str, str]:
        return {"lines": "tier://profile_lines/lines", "seed": "tier://old_hub_seed/"}

    def records(self, src: Mapping[str, Path], ids: IdLookup) -> Iterator[dict[str, Any]]:
        if "hub_db" in src:
            docs, origin = read_db(Path(src["hub_db"])), "hub.db"
        else:
            docs, origin = read_seed(Path(src["seed"])), "seed"
        yield from records_of(LN.read_lines(Path(src["lines"])), docs, ids, origin=origin)


def _source(origin: str, path: str) -> str:
    return f"tier://old_hub_seed/{path}.json" if origin == "seed" else f"hub.db:{path}"


def records_of(
    files: list[dict[str, Any]], docs: Mapping[str, Any], ids: IdLookup, *, origin: str = "seed"
) -> Iterator[dict[str, Any]]:
    """The records of the old hub's documents ``docs`` (``{path: data}``) over the line files ``files``."""
    for line in files:
        route = line["id"]
        sid = ids.id_for("section", LN.section_key(route), kind="section")
        pid = ids.id_for("alignment", LN.profile_key(route), kind="profile")
        path = LN.profile_key(route)
        doc = docs.get(path)
        if isinstance(doc, Mapping):
            keys = LN.station_keys(line)
            platforms = {k: ids.id_for("alignment_station", LN.platform_key(route, k), kind="platform") for k in keys}
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
        yield {"kind": "profile", "id": pid, "data": data, "geom": None, "source": source}
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
