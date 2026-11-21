"""Refs: the references a record's data makes to other records (kind files declare them), their integrity on write,
and reverse lookups.

Each current revision's refs are rows of table ``ref`` ``(layer, src, role, dst)``. A write checks that every ref
resolves in the writer's chain to a live record of a declared kind (``Conflict(reason="reference")`` when one does
not; ``Invalid`` for a required ref that is null or absent). A delete applies each referrer's ``on_delete``:
``restrict`` refuses it, ``cascade`` tombstones the referrer too, ``nullify`` sets the ref to null (section 4,
validation step 5).
"""

from __future__ import annotations

import copy
import sqlite3
from typing import Any

from .layers import Layer


def set_at(data: Any, location: tuple[Any, ...], value: Any) -> Any:
    """A copy of ``data`` with ``value`` at ``location`` (a tuple of keys and indices)."""
    out = copy.deepcopy(data)
    node = out
    for step in location[:-1]:
        node = node[step]
    node[location[-1]] = value
    return out


def rows_for(content_refs: list[tuple[str, Any, Any, tuple[Any, ...]]]) -> list[tuple[str, str]]:
    """The distinct ``(role, dst)`` pairs to store for a revision's refs (nulls left out)."""
    out = sorted({(role, value) for role, value, _spec, _at in content_refs if isinstance(value, str) and value})
    return out


def write_rows(con: sqlite3.Connection, layer_id: int, src: str, pairs: list[tuple[str, str]]) -> None:
    """Replace the ref rows of ``(layer, src)``."""
    con.execute("DELETE FROM ref WHERE layer = ? AND src = ?", (layer_id, src))
    if pairs:
        con.executemany(
            "INSERT OR IGNORE INTO ref (layer, src, role, dst) VALUES (?, ?, ?, ?)",
            [(layer_id, src, role, dst) for role, dst in pairs],
        )


def referrers(con: sqlite3.Connection, chain: list[Layer], dst: str) -> list[tuple[int, str, str]]:
    """``(layer, src, role)`` of every stored ref to ``dst`` on a layer of ``chain``."""
    if not chain:
        return []
    marks = ",".join("?" * len(chain))
    return [
        tuple(r)
        for r in con.execute(
            f"SELECT layer, src, role FROM ref WHERE dst = ? AND layer IN ({marks}) ORDER BY src, role",
            (dst, *[c.id for c in chain]),
        )
    ]  # type: ignore[misc]


def has_row(con: sqlite3.Connection, layer_id: int, src: str, role: str, dst: str) -> bool:
    return (
        con.execute(
            "SELECT 1 FROM ref WHERE layer = ? AND src = ? AND role = ? AND dst = ?", (layer_id, src, role, dst)
        ).fetchone()
        is not None
    )


__all__ = ["has_row", "referrers", "rows_for", "set_at", "write_rows"]
