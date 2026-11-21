"""The list query: one query over a layer chain, with the R-tree and the time columns as filters.

A record's revisions on the chain's layers are ranked by the chain; the first (the ``min`` rank of the record's
group) wins, and a tombstone hides the record. The grouping runs over the covering index ``rec_kind_id`` and only
then are the winning rows read whole, so a list of 10,000 records costs one index walk and 10,000 row reads.

Filters are applied twice: once loosely to pick candidate ids cheaply (any revision on the chain matches), then
exactly to the winning revision, so a scenario that moves a record out of a bbox, or gives it another parent, is
listed correctly.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from typing import Any

from region.core.errors import Invalid

from .kinds import Kind
from .layers import Layer
from .records import SELECT, record_of


def _like(q: str) -> str:
    return "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def list_rows(
    con: sqlite3.Connection,
    slugs: dict[int, str],
    chain: list[Layer],
    kind: Kind,
    instant: int | None,
    *,
    bbox: tuple[float, float, float, float] | None = None,
    parent: str | None = None,
    ref: str | None = None,
    ids: Iterable[str] | None = None,
    q: str | None = None,
    limit: int = 500,
    after: str | None = None,
    time_filter: bool = True,
) -> tuple[list[dict[str, Any]], str | None]:
    """Records of ``kind`` resolved in ``chain`` (see the module doc); returns ``(page, cursor)``."""
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise Invalid(f"limit {limit!r} is not a positive integer")
    if not chain:
        return [], None
    marks = ",".join("?" * len(chain))
    rank = "CASE r.layer " + " ".join("WHEN ? THEN ?" for _ in chain) + " END"
    args: list[Any] = []
    for i, c in enumerate(chain):
        args.extend((c.id, i))
    inner = ["r.kind = ?", f"r.layer IN ({marks})"]
    args.append(kind.name)
    args.extend(c.id for c in chain)
    if after is not None:
        inner.append("r.id > ?")
        args.append(after)
    outer = ["x.deleted = 0"]
    oargs: list[Any] = []
    if ids is not None:
        id_list = [i for i in ids]
        inner.append("r.id IN (SELECT value FROM json_each(?))")
        args.append(json.dumps(id_list))
    if bbox is not None:
        try:
            x0, y0, x1, y1 = (float(v) for v in bbox)
        except (TypeError, ValueError):
            raise Invalid(f"bbox {bbox!r} is not four numbers x0, y0, x1, y1") from None
        inner.append(
            "r.id IN (SELECT r2.id FROM rec_rtree t JOIN rec r2 ON r2.rid = t.rid "
            "WHERE t.x1 >= ? AND t.x0 <= ? AND t.y1 >= ? AND t.y0 <= ? AND t.kind = ?)"
        )
        args.extend((x0, x1, y0, y1, kind.name))
        outer.append("x.x0 IS NOT NULL AND x.x1 >= ? AND x.x0 <= ? AND x.y1 >= ? AND x.y0 <= ?")
        oargs.extend((x0, x1, y0, y1))
    if parent is not None:
        inner.append("r.id IN (SELECT r3.id FROM rec r3 WHERE r3.parent = ? AND r3.kind = ?)")
        args.extend((parent, kind.name))
        outer.append("x.parent = ?")
        oargs.append(parent)
    if ref is not None:
        inner.append("r.id IN (SELECT src FROM ref WHERE dst = ?)")
        args.append(ref)
        outer.append("EXISTS (SELECT 1 FROM ref f WHERE f.layer = x.layer AND f.src = x.id AND f.dst = ?)")
        oargs.append(ref)
    if q:
        outer.append("x.name LIKE ? ESCAPE '\\'")
        oargs.append(_like(q))
    if time_filter and kind.dated:
        if instant is None:
            outer.append("x.close_lo IS NULL")
        else:
            outer.append("x.open_lo IS NOT NULL AND x.open_lo <= ? AND (x.close_lo IS NULL OR x.close_lo > ?)")
            oargs.extend((instant, instant))
    cols = SELECT.replace("r.", "x.")
    # SQLite takes a bare column (r.rid) from the row that holds the min() of its group: the winning revision.
    sql = (
        f"WITH win AS (SELECT r.rid AS rid, min({rank}) AS rk FROM rec r WHERE {' AND '.join(inner)} "
        f"GROUP BY r.id) "
        f"SELECT {cols} FROM win JOIN rec x ON x.rid = win.rid WHERE {' AND '.join(outer)} ORDER BY x.id LIMIT ?"
    )
    rows = con.execute(sql, (*args, *oargs, limit + 1)).fetchall()
    more = len(rows) > limit
    page = [record_of(r, slugs) for r in rows[:limit]]
    return page, (page[-1]["id"] if more and page else None)


__all__ = ["list_rows"]
