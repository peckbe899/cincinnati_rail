"""Small builders shared by the store's tests."""

from __future__ import annotations

from typing import Any

from region.core import ids
from region.core.protocols import ImportRun, etag
from region.core.view import View


def tag(rec: dict[str, Any]) -> str:
    """The ETag of a record in get() shape."""
    return etag(rec["layer"], rec["version"])


def tid(key: str) -> str:
    """A stable id of the ``test`` namespace."""
    return ids.stable("test", key)


def node(
    store,
    name: str,
    x: float = 715000.0,
    y: float = 4331000.0,
    *,
    view: View | None = None,
    by: str = "ben",
    id: str | None = None,
) -> dict[str, Any]:
    return store.put(
        {"kind": "t_node", "id": id, "data": {"name": name, "system": "metro"}, "geom": f"POINT ({x} {y})"},
        view or View(),
        if_match=None,
        by=by,
    )


def note(store, text: str = "a", *, view: View | None = None, by: str = "ben", **data: Any) -> dict[str, Any]:
    return store.put(
        {"kind": "note", "id": None, "data": {"text": text, **data}, "geom": None}, view or View(), if_match=None, by=by
    )


def feature(
    key: str,
    name: str = "Road",
    *,
    x: float = 715000.0,
    y: float = 4331000.0,
    level: float | None = 150.0,
    **extra: Any,
) -> dict[str, Any]:
    """An importer's record of kind ``feature`` in the ``test`` namespace."""
    data = {"name": name, "class": "road", "level_m": level, **extra}
    return {"kind": "feature", "id": tid(key), "data": data, "geom": f"POINT ({x} {y})"}


def run(layer: str = "import:test", namespace: str = "test", importer: str = "t") -> ImportRun:
    return ImportRun(importer=importer, version="1", layer=layer, namespace=namespace)


def raw(store):
    """A plain sqlite3 connection to the store's database (for raw-SQL checks)."""
    import sqlite3

    con = sqlite3.connect(str(store.path), isolation_level=None)
    con.execute("PRAGMA busy_timeout=5000")
    return con
