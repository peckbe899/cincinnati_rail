"""Migration 0002, the Python part: refuse to drop 0001 tables that hold rows; seed the meta and layer rows.

``before(con)`` runs first, in the migration's transaction, then ``0002_store.sql``, then ``after(con)``.
"""

from __future__ import annotations

import sqlite3

from region.core import ids
from region.core.errors import Invalid

TABLES_0001 = (
    "node",
    "section",
    "track",
    "route",
    "route_section",
    "service",
    "station",
    "stop",
    "platform",
    "station_element",
    "structure",
    "bridge",
    "earthwork",
    "ground_layer",
    "context_feature",
    "yard",
    "era",
    "rule",
    "ruling",
    "snapshot",
    "result",
    "issue",
    "legacy_key",
    "history",
    "rtree_map",
)


def before(con: sqlite3.Connection) -> None:
    """Every 0001 table that exists must be empty: 0002 replaces the layout at no cost only then."""
    have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    full = []
    for name in TABLES_0001:
        if name in have and con.execute(f'SELECT 1 FROM "{name}" LIMIT 1').fetchone():
            full.append(name)
    if full:
        raise Invalid(
            "migration 0002 drops the 0001 tables, but these hold rows: "
            + ", ".join(full)
            + ". Export them first; nothing was changed."
        )


def after(con: sqlite3.Connection) -> None:
    """The meta rows (db_id, epoch, created) and the seeded layers: main, then one per declared namespace."""
    from region.model.db import now

    t = now()
    con.executemany(
        "INSERT INTO meta (key, value) VALUES (?, ?)", [("db_id", ids.new()), ("epoch", ids.new()), ("created", t)]
    )
    con.execute(
        "INSERT INTO layer (slug, tier, parent, namespace, state, title, created, by) "
        "VALUES ('main', 'main', NULL, NULL, 'open', 'Main design', ?, 'migration')",
        (t,),
    )
    for ns in ids.namespaces().values():
        if ns.test:
            continue
        tier = ns.layer.split(":", 1)[0]
        con.execute(
            "INSERT INTO layer (slug, tier, parent, namespace, state, title, created, by) "
            "VALUES (?, ?, NULL, ?, 'open', ?, ?, 'migration')",
            (ns.layer, tier, ns.name, ns.about, t),
        )
