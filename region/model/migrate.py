"""Migrations: ``migrations/NNNN_<name>.sql`` and an optional ``NNNN_<name>.py``, applied in order.

Each migration is one transaction that includes its ``schema_version`` row (defect 11 of the old store: a crash can no
longer leave a migration applied but unrecorded). Within it the ``.py`` module's ``before(con)`` runs first, then
the ``.sql`` statements one by one, then ``after(con)``. Any failure rolls the whole migration back, so the schema is
exactly what it was.

When ``backup_dir`` is given and a migration is pending on a database that already holds tables, an online backup is
taken first (reason ``pre-migrate``, kept forever) and checked with ``quick_check``; a failed backup stops the
migration before anything changes (section 9, Database; 9.22).
"""

from __future__ import annotations

import importlib.util
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from region.core import fsio

from .db import now

MIGRATIONS = Path(__file__).resolve().parent / "migrations"
_NAME_RE = re.compile(r"^(\d{4})_([a-z0-9_]+)\.(sql|py)$")


@dataclass(frozen=True)
class Migration:
    """One numbered migration: its SQL file and its optional Python module."""

    version: int
    name: str
    sql: Path | None
    py: Path | None


def discover(folder: Path | None = None) -> list[Migration]:
    """The migrations in ``folder`` (default ``region/model/migrations``), by version."""
    folder = Path(folder) if folder is not None else MIGRATIONS
    found: dict[int, dict[str, Path | str]] = {}
    for f in sorted(folder.iterdir()):
        m = _NAME_RE.match(f.name)
        if not m:
            continue
        v = int(m.group(1))
        entry = found.setdefault(v, {"name": m.group(2)})
        entry[m.group(3)] = f
    out = []
    for v in sorted(found):
        e = found[v]
        sql = e.get("sql")
        py = e.get("py")
        out.append(
            Migration(v, str(e["name"]), sql if isinstance(sql, Path) else None, py if isinstance(py, Path) else None)
        )
    return out


def applied(con: sqlite3.Connection) -> list[int]:
    """The versions recorded in ``schema_version`` (empty for a new database)."""
    have = con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_version'").fetchone()
    if not have:
        return []
    return sorted({int(r[0]) for r in con.execute("SELECT version FROM schema_version")})


def current_version(con: sqlite3.Connection) -> int:
    """The highest applied version, 0 for a new database."""
    done = applied(con)
    return done[-1] if done else 0


def pending(con: sqlite3.Connection, folder: Path | None = None, target: int | None = None) -> list[Migration]:
    """The migrations not yet applied, up to ``target`` when given."""
    done = set(applied(con))
    return [m for m in discover(folder) if m.version not in done and (target is None or m.version <= target)]


def split_sql(text: str) -> list[str]:
    """The statements of a SQL script, split where SQLite's own tokenizer says a statement is complete (so trigger
    bodies, strings and comments holding ``;`` stay whole)."""
    out: list[str] = []
    buf = ""
    for piece in text.split(";"):
        buf += piece + ";"
        if sqlite3.complete_statement(buf):
            stmt = buf.strip()
            if _has_sql(stmt):
                out.append(stmt)
            buf = ""
    if _has_sql(buf.rstrip(";")):
        raise ValueError("the script ends inside a statement: " + buf.strip()[:80])
    return out


def _has_sql(stmt: str) -> bool:
    lines = [ln.split("--", 1)[0].strip() for ln in stmt.splitlines()]
    return any(ln and ln != ";" for ln in lines)


def _module(path: Path) -> ModuleType:
    name = "_crmigration_" + fsio.sha256_hex(str(path.resolve()))[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import migration {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def apply_one(con: sqlite3.Connection, m: Migration) -> bool:
    """Apply one migration in one transaction, its ``schema_version`` row included. Returns ``False`` (and changes
    nothing) when another connection applied it first: the check is made again under the write lock, so two
    processes opening a new database at once cannot both run it."""
    module = _module(m.py) if m.py is not None else None
    statements = split_sql(fsio.read_text(m.sql)) if m.sql is not None else []
    con.execute("BEGIN IMMEDIATE")
    try:
        if m.version in applied(con):
            con.execute("ROLLBACK")
            return False
        if module is not None and hasattr(module, "before"):
            module.before(con)
        for stmt in statements:
            con.execute(stmt)
        if module is not None and hasattr(module, "after"):
            module.after(con)
        con.execute("INSERT INTO schema_version (version, applied) VALUES (?, ?)", (m.version, now()))
        con.execute("COMMIT")
    except BaseException:
        if con.in_transaction:
            con.execute("ROLLBACK")
        raise
    return True


def migrate(
    con: sqlite3.Connection, *, backup_dir: Path | None = None, folder: Path | None = None, target: int | None = None
) -> list[int]:
    """Apply every pending migration in order (up to ``target``); return the versions applied now.

    ``con`` must not be inside a transaction. With ``backup_dir``, a database that already holds tables is backed up
    (reason ``pre-migrate``) and the copy checked before the first migration runs.
    """
    todo = pending(con, folder, target)
    if not todo:
        return []
    if backup_dir is not None:
        has_tables = con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' LIMIT 1").fetchone()
        if has_tables:
            from .backup import backup_connection

            backup_connection(con, Path(backup_dir), "pre-migrate")
    done = []
    for m in todo:
        if apply_one(con, m):
            done.append(m.version)
    return done


__all__ = [
    "MIGRATIONS",
    "Migration",
    "applied",
    "apply_one",
    "current_version",
    "discover",
    "migrate",
    "pending",
    "split_sql",
]
