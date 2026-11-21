"""Records as the store holds them: bodies made into content (validated, upgraded, snapped, hashed) and rows made
into the get() shape (``region.core.protocols.Record``).

A *body* is the writable part of a record, ``{"data": {...}, "geom": WKT | None}``; ``kv`` (the data version, for
upgrades) and ``source`` (free provenance) may come with it. ``content()`` runs validation steps 1 to 4 of section 4
on a body: the kind is known and the data upgraded to the kind's current version, the JSON Schema passes, the
promoted columns and date intervals are derived, and the geometry is checked, snapped to 1 mm and given its bbox.
The content hash is ``fsio.content_hash({id, kind, kv, geom, data})``, so bookkeeping never enters it (9.29).
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any

from region.core import fsio
from region.core.errors import Invalid

from . import geom as G
from .kinds import Kind

BODY_KEYS = frozenset({"data", "geom", "kv", "source"})
COLS = (
    "name",
    "system",
    "parent",
    "c0",
    "c1",
    "ord",
    "phase",
    "open_lo",
    "open_hi",
    "close_lo",
    "close_hi",
    "x0",
    "y0",
    "x1",
    "y1",
)
RECORD_KEYS = (
    "id",
    "kind",
    "kv",
    "layer",
    "version",
    "hash",
    "deleted",
    "origin",
    "source",
    "by",
    "changeset",
    "created",
    "updated",
    "geom",
    "data",
)
# the columns every read selects, in RECORD_KEYS order (layer is the row id; base_hash, rid and the bbox follow)
SELECT = (
    "r.id, r.kind, r.kv, r.layer, r.version, r.hash, r.deleted, r.origin, r.source, r.by, r.changeset, "
    "r.created, r.updated, r.geom, r.data, r.base_hash, r.rid, r.x0, r.y0, r.x1, r.y1"
)


def dumps(value: Any) -> str:
    """Compact JSON with sorted keys, as stored in ``rec.data`` and ``rec_hist.row``."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def content_hash(id: str, kind: str, kv: int, geom: str | None, data: Any) -> str:
    """The content hash of a revision (bookkeeping left out)."""
    try:
        return fsio.content_hash({"id": id, "kind": kind, "kv": kv, "geom": geom, "data": data})
    except (TypeError, ValueError) as e:
        raise Invalid(f"data is not plain JSON: {e}", errors=[{"path": "/data", "message": str(e)}]) from None


@dataclass
class Content:
    """A validated body: what one revision holds and everything derived from it."""

    kind: str
    id: str
    kv: int
    geom: str | None
    data: dict[str, Any]
    hash: str
    cols: dict[str, Any] = field(default_factory=dict)
    refs: list[tuple[str, Any, Any, tuple[Any, ...]]] = field(default_factory=list)
    bbox: tuple[float, float, float, float] | None = None

    def body(self) -> dict[str, Any]:
        return {"data": self.data, "geom": self.geom}


def content(kind: Kind, id: str, body: Any) -> Content:
    """Validation steps 1 to 4 of section 4 for one body; ``Invalid`` lists every problem found."""
    if not isinstance(body, dict):
        raise Invalid("a record body is an object {data, geom}", errors=[{"path": "", "message": "object expected"}])
    extra = set(body) - BODY_KEYS
    if extra:
        raise Invalid(
            "a record body holds only data, geom, kv and source; also given: " + ", ".join(sorted(extra)),
            errors=[{"path": f"/{k}", "message": "not part of a record body"} for k in sorted(extra)],
        )
    data = body.get("data")
    if not isinstance(data, dict):
        raise Invalid("a record's data is a JSON object", errors=[{"path": "/data", "message": "object expected"}])
    kv = body.get("kv", kind.version)
    data = kind.upgrade(copy.deepcopy(data), kv)
    errors = kind.validate(data)
    try:
        geom, bbox = G.normalize(body.get("geom"), kind.geometry)
    except Invalid as e:
        errors.extend(e.errors or [{"path": "/geom", "message": str(e)}])
        geom, bbox = None, None
    try:
        opened, closed = kind.dates_of(data)
    except Invalid as e:
        errors.extend(e.errors)
        opened = closed = None
    if errors:
        raise Invalid(
            f"{kind.name} {id}: "
            + "; ".join(f"{e['path']}: {e['message']}" for e in errors[:5])
            + (f" (and {len(errors) - 5} more)" if len(errors) > 5 else ""),
            errors=errors,
        )
    cols = kind.columns_of(data)
    full = {c: cols.get(c) for c in COLS[:7]}
    full["open_lo"], full["open_hi"] = opened if opened else (None, None)
    full["close_lo"], full["close_hi"] = closed if closed else (None, None)
    full["x0"], full["y0"], full["x1"], full["y1"] = bbox if bbox else (None, None, None, None)
    h = content_hash(id, kind.name, kind.version, geom, data)
    return Content(kind.name, id, kind.version, geom, data, h, full, kind.refs_of(data), bbox)


@dataclass
class Rev:
    """One revision as read from ``rec`` (a row), with its layer as a row id."""

    id: str
    kind: str
    kv: int
    layer: int
    version: int
    hash: str
    deleted: bool
    origin: str
    source: str | None
    by: str
    changeset: str
    created: str | None
    updated: str | None
    geom: str | None
    data_text: str
    base_hash: str | None
    rid: int
    bbox: tuple[float, float, float, float] | None
    _data: Any = None

    @property
    def data(self) -> dict[str, Any]:
        if self._data is None:
            self._data = json.loads(self.data_text)
        return self._data

    def body(self) -> dict[str, Any]:
        return {"data": copy.deepcopy(self.data), "geom": self.geom}

    def record(self, slug: str) -> dict[str, Any]:
        """The get() shape (``slug`` is this revision's layer slug)."""
        return {
            "id": self.id,
            "kind": self.kind,
            "kv": self.kv,
            "layer": slug,
            "version": self.version,
            "hash": self.hash,
            "deleted": self.deleted,
            "origin": self.origin,
            "source": self.source,
            "by": self.by,
            "changeset": self.changeset,
            "created": self.created,
            "updated": self.updated,
            "geom": self.geom,
            "data": json.loads(self.data_text),
        }


def rev_of(row: Any) -> Rev:
    """A ``Rev`` from a row selected with ``SELECT``."""
    bbox = (row[17], row[18], row[19], row[20]) if row[17] is not None else None
    return Rev(
        row[0],
        row[1],
        row[2],
        row[3],
        row[4],
        row[5],
        bool(row[6]),
        row[7],
        row[8],
        row[9],
        row[10],
        row[11],
        row[12],
        row[13],
        row[14],
        row[15],
        row[16],
        bbox,
    )


def record_of(row: Any, slugs: dict[int, str]) -> dict[str, Any]:
    """The get() shape straight from a row selected with ``SELECT`` (the fast path of ``list``)."""
    return {
        "id": row[0],
        "kind": row[1],
        "kv": row[2],
        "layer": slugs[row[3]],
        "version": row[4],
        "hash": row[5],
        "deleted": bool(row[6]),
        "origin": row[7],
        "source": row[8],
        "by": row[9],
        "changeset": row[10],
        "created": row[11],
        "updated": row[12],
        "geom": row[13],
        "data": json.loads(row[14]),
    }


def body_of(record: dict[str, Any]) -> dict[str, Any]:
    """The body of a record in get() shape (a deep copy)."""
    return {"data": copy.deepcopy(record.get("data")), "geom": record.get("geom")}


def changed_fields(before: dict[str, Any] | None, after: dict[str, Any] | None) -> list[str]:
    """The changed paths between two bodies, with dots: ``data.pvi``, ``geom``."""
    b = before or {"data": {}, "geom": None}
    a = after or {"data": {}, "geom": None}
    out = []
    bd, ad = b.get("data") or {}, a.get("data") or {}
    for key in sorted(set(bd) | set(ad)):
        if key not in bd or key not in ad or fsio.canonical_json(bd[key]) != fsio.canonical_json(ad[key]):
            out.append(f"data.{key}")
    if b.get("geom") != a.get("geom"):
        out.append("geom")
    return out


__all__ = [
    "BODY_KEYS",
    "COLS",
    "Content",
    "RECORD_KEYS",
    "Rev",
    "SELECT",
    "body_of",
    "changed_fields",
    "content",
    "content_hash",
    "dumps",
    "record_of",
    "rev_of",
]
