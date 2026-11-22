"""Goals: the ``(type, scope, view)`` triples the hub keeps answers for (section 6, "Invalidation").

A goal row exists for every triple someone asked about. ``watch_goal`` makes it watched: the scheduler re-plans it
whenever one of its dependencies changes, until ``expires``. A plain ``submit`` makes an unwatched row, so
``result(type, scope, view)`` can answer later. ``want_key`` is the key last planned for the goal; ``latest_key`` the
key of its newest committed ok result. ``pinned`` goals keep their results through eviction. ``auto`` marks an
upstream goal that a downstream goal's ``need()`` registered; it is watched when its downstream goal is.

These helpers run inside the caller's cache transaction (``Cache.tx()``) and never commit by themselves.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from .cache import now_iso, now_s


def get(con: sqlite3.Connection, type: str, scope: str, view: str) -> dict[str, Any] | None:
    row = con.execute("SELECT * FROM goal WHERE type = ? AND scope = ? AND view = ?", (type, scope, view)).fetchone()
    return dict(row) if row is not None else None


def upsert(
    con: sqlite3.Connection,
    type: str,
    scope: str,
    view: str,
    *,
    priority: int,
    watch: bool | None = None,
    expires: float | None | bool = False,
    pinned: bool | None = None,
    auto: bool = False,
) -> dict[str, Any]:
    """Create the goal or update it. ``watch``, ``pinned`` and ``expires`` change only when given (``expires=False``
    means unchanged), and a goal watched for ever keeps no expiry when it is watched again for a while; a new
    priority replaces the old one only when the goal is not watched or is more urgent."""
    now = now_iso()
    old = get(con, type, scope, view)
    if old is None:
        con.execute(
            "INSERT INTO goal (type, scope, view, priority, watch, expires, pinned, auto, created, updated) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                type,
                scope,
                view,
                int(priority),
                int(bool(watch)),
                None if expires is False else expires,
                int(bool(pinned)),
                int(auto),
                now,
                now,
            ),
        )
    else:
        new_watch = old["watch"] if watch is None else int(bool(watch))
        if watch:
            new_priority = int(priority)
        elif old["watch"]:
            new_priority = min(int(old["priority"]), int(priority))
        else:
            new_priority = int(priority)
        if expires is False:
            new_expires = old["expires"]
        elif watch and old["watch"] and old["expires"] is None and not old["auto"]:
            # a goal watched for ever (the live hub's background goals) stays so when a pane watches it for a while
            new_expires = None
        else:
            new_expires = expires
        new_pinned = old["pinned"] if pinned is None else int(bool(pinned))
        new_auto = 0 if (watch and not auto) else old["auto"]
        con.execute(
            "UPDATE goal SET priority = ?, watch = ?, expires = ?, pinned = ?, auto = ?, updated = ? "
            "WHERE type = ? AND scope = ? AND view = ?",
            (new_priority, new_watch, new_expires, new_pinned, new_auto, now, type, scope, view),
        )
    found = get(con, type, scope, view)
    assert found is not None
    return found


def set_state(con: sqlite3.Connection, type: str, scope: str, view: str, **members: Any) -> None:
    """Update ``want_key``, ``latest_key``, ``state`` and ``error`` of one goal."""
    allowed = {"want_key", "latest_key", "state", "error"}
    bad = set(members) - allowed
    if bad:
        raise ValueError(f"cannot set goal members {sorted(bad)}")
    if not members:
        return
    cols = ", ".join(f"{k} = ?" for k in members)
    con.execute(
        f"UPDATE goal SET {cols}, updated = ? WHERE type = ? AND scope = ? AND view = ?",
        (*members.values(), now_iso(), type, scope, view),
    )


def watched(con: sqlite3.Connection, *, keys: set[str] | None = None, errors: bool = False) -> list[dict[str, Any]]:
    """Watched, unexpired goals: all of them, or those whose wanted or latest key is in ``keys`` (plus, with
    ``errors``, those whose last plan failed, which have no dependencies on record)."""
    now = now_s()
    base = "SELECT * FROM goal WHERE watch = 1 AND (expires IS NULL OR expires > ?)"
    if keys is None:
        return [dict(r) for r in con.execute(base + " ORDER BY priority, type, scope, view", (now,))]
    found: dict[tuple[str, str, str], dict[str, Any]] = {}
    key_list = sorted(keys)
    for i in range(0, len(key_list), 400):
        chunk = key_list[i : i + 400]
        marks = ",".join("?" * len(chunk))
        sql = base + f" AND (want_key IN ({marks}) OR latest_key IN ({marks}))"
        for r in con.execute(sql, (now, *chunk, *chunk)):
            found[(r["type"], r["scope"], r["view"])] = dict(r)
    if errors:
        for r in con.execute(base + " AND state = 'error'", (now,)):
            found[(r["type"], r["scope"], r["view"])] = dict(r)
    return sorted(found.values(), key=lambda g: (g["priority"], g["type"], g["scope"], g["view"]))


def pending(con: sqlite3.Connection) -> list[dict[str, Any]]:
    """Watched, unexpired goals whose answer is being worked on (queued, running, or waiting on an upstream)."""
    rows = con.execute(
        "SELECT type, scope, view, state, priority FROM goal WHERE watch = 1 AND (expires IS NULL OR expires > ?) "
        "AND state IN ('queued', 'running', 'waiting') ORDER BY priority, type, scope, view",
        (now_s(),),
    )
    return [dict(r) for r in rows]


def wanting(con: sqlite3.Connection, type: str, key: str) -> list[dict[str, Any]]:
    """Goals of ``type`` whose wanted key is ``key``."""
    return [dict(r) for r in con.execute("SELECT * FROM goal WHERE type = ? AND want_key = ?", (type, key))]


__all__ = ["get", "pending", "set_state", "upsert", "wanting", "watched"]
