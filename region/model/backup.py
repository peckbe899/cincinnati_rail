"""Backups: SQLite's online backup API, ``quick_check`` on every copy, retention tiers, restore (section 9, Backups).

    path = backup(db, var / "backups", "manual")      # region-20261121T153000Z-manual.db, checked
    restore(path, db)                                  # backs the current database up first (pre-restore)
    prune(var / "backups")                             # applies the retention tiers; returns what it removed

Retention: ``pre-migrate``, ``manual`` and ``pre-restore`` are kept forever; ``pre-import`` the newest 10; ``daily``
the newest 14; ``weekly`` the newest 8. ``auto`` takes the daily and weekly backups that are due.

A backup is written to a temporary name in the destination folder, checked, then renamed into place (with the same
retry on WinError 5 and 32 as ``fsio.write_atomic``), so a half-written backup never carries a backup's name. The
destination passes the write guard (``fsio.check_write``). ``rebuild`` never touches the live database; a restore
copies into it through the backup API, so an open WAL is handled by SQLite.

**Restore and the seed.** A backup carries ``seed_base`` as it was when the backup was taken, so the seed import's
rule "ours unchanged since the seed was last seen: take the seed" would silently undo the restore at the next start
(``region/seed`` usually holds newer exports). So a restore marks every seeded layer (``meta.seed_restore``), and the
next seed import of each such layer takes nothing silently: every record where ``region/seed`` and the restored
database differ becomes a listed ``both_changed`` seed conflict. Ben keeps the restored revision (take ``ours``) or
the seed's (take ``theirs``), one by one or with ``crhub conflicts resolve --all``.

**Restore refuses** a file that is not a hub database (no ``schema_version`` table, such as the old hub's
``hub.db``), and a hub database made by another ``crhub setup`` (another ``db_id``) unless ``force`` is given.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import json
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from region.core import fsio, ids
from region.core.errors import Invalid, NotFound

KEEP: dict[str, int | None] = {
    "pre-migrate": None,
    "manual": None,
    "pre-restore": None,
    "pre-import": 10,
    "daily": 14,
    "weekly": 8,
}
REASON_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
NAME_RE = re.compile(r"^region-(\d{8}T\d{6}Z)(?:-(\d+))?-([a-z][a-z0-9-]{0,31})\.db$")


@dataclass(frozen=True)
class BackupFile:
    """One backup in a backup folder, read from its name."""

    path: Path
    at: dt.datetime
    reason: str


def quick_check(target: Path | sqlite3.Connection) -> list[str]:
    """``PRAGMA quick_check`` of a database file or connection: ``[]`` when it passes, else SQLite's messages."""
    if isinstance(target, sqlite3.Connection):
        rows = target.execute("PRAGMA quick_check").fetchall()
    else:
        if not Path(target).is_file():
            return [f"{target} does not exist"]
        con = sqlite3.connect(Path(target).resolve().as_uri() + "?mode=ro", uri=True)
        try:
            rows = con.execute("PRAGMA quick_check").fetchall()
        except sqlite3.DatabaseError as e:
            return [str(e)]
        finally:
            con.close()
    msgs = [str(r[0]) for r in rows]
    return [] if msgs == ["ok"] else msgs


def _stamp(now: dt.datetime | None = None) -> str:
    t = (now or dt.datetime.now(dt.UTC)).astimezone(dt.UTC)
    return t.strftime("%Y%m%dT%H%M%SZ")


def _target(dest: Path, reason: str, now: dt.datetime | None = None) -> Path:
    stamp = _stamp(now)
    path = dest / f"region-{stamp}-{reason}.db"
    n = 2
    while path.exists():
        path = dest / f"region-{stamp}-{n}-{reason}.db"
        n += 1
    return path


def _replace(src: str, dst: str) -> None:
    deadline = time.monotonic() + fsio.RETRY_TOTAL_S
    delay = 0.01
    while True:
        try:
            os.replace(src, dst)
            return
        except OSError as e:
            if getattr(e, "winerror", None) not in fsio.RETRY_WINERRORS or time.monotonic() >= deadline:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 0.2)


def backup_connection(con: sqlite3.Connection, dest: Path, reason: str, *, now: dt.datetime | None = None) -> Path:
    """Back up the database of an open connection into folder ``dest``; return the checked copy's path."""
    if not REASON_RE.match(reason):
        raise Invalid(f"backup reason {reason!r} is not a slug")
    dest = Path(dest)
    target = fsio.check_write(_target(dest, reason, now))
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.{ids.new()}.tmp")
    try:
        out = sqlite3.connect(str(tmp))
        try:
            con.backup(out)
            out.execute("PRAGMA journal_mode=DELETE")
        finally:
            out.close()
        problems = quick_check(tmp)
        if problems:
            raise Invalid(f"the backup of {reason} failed its quick_check: " + "; ".join(problems))
        _replace(str(tmp), str(target))
    finally:
        with contextlib.suppress(OSError):
            tmp.unlink()
    return target


def backup(db: Path, dest: Path, reason: str) -> Path:
    """Back up database file ``db`` into folder ``dest`` with ``reason``; return the checked copy's path."""
    db = Path(db)
    if not db.is_file():
        raise NotFound(f"no database at {db}")
    con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        return backup_connection(con, dest, reason)
    finally:
        con.close()


SEED_RESTORE_KEY = "seed_restore"
SEEDED_TIERS = ("main", "proposal")


def _table(con: sqlite3.Connection, name: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)).fetchone() is not None


def _meta_of(con: sqlite3.Connection) -> dict[str, str]:
    if not _table(con, "meta"):
        return {}
    return {str(k): str(v) for k, v in con.execute("SELECT key, value FROM meta").fetchall()}


def describe(path: Path) -> dict[str, object]:
    """What a database file holds, for a restore's report: ``{"db_id", "schema", "records", "last_export"}`` (the
    values a file does not have are ``None``). Read-only."""
    con = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        out: dict[str, object] = {"db_id": None, "schema": None, "records": None, "last_export": None}
        if _table(con, "schema_version"):
            row = con.execute("SELECT max(version) FROM schema_version").fetchone()
            out["schema"] = row[0] if row else None
        meta = _meta_of(con)
        out["db_id"] = meta.get("db_id")
        out["last_export"] = meta.get("last_export")
        if _table(con, "rec"):
            out["records"] = con.execute("SELECT count(*) FROM rec WHERE deleted = 0").fetchone()[0]
        return out
    finally:
        con.close()


def restore(src: Path, db: Path, *, backup_dir: Path | None = None, force: bool = False) -> dict[str, object]:
    """Replace the content of ``db`` with backup ``src``, after backing ``db`` up (reason ``pre-restore``).

    ``src`` must pass ``quick_check`` and be a hub database (``schema_version``); one made by another ``crhub
    setup`` (another ``db_id`` than ``db``'s) is refused unless ``force``. No other connection may be writing ``db``
    (the CLI holds the lock). The restored database gets a new ``epoch`` in ``meta``, so clients resync, and its
    seeded layers are marked for the next seed import (see the module doc). Returns ``{"pre_restore": path or
    None, "replaced": describe(db) or None, "restored": describe(src), "seed_layers": [slug, ...]}``.
    """
    src = Path(src)
    db = Path(db)
    problems = quick_check(src)
    if problems:
        raise Invalid(f"{src} is not a sound database: " + "; ".join(problems))
    restored = describe(src)
    if restored["schema"] is None:
        raise Invalid(
            f"{src} is not a hub database (it has no schema_version table; the old hub's hub.db is not one). "
            "Pick a file from the backups folder (crhub info shows where it is)."
        )
    replaced = describe(db) if db.is_file() else None
    if (
        not force
        and replaced is not None
        and replaced["db_id"] is not None
        and restored["db_id"] is not None
        and replaced["db_id"] != restored["db_id"]
    ):
        raise Invalid(
            f"{src} is a backup of another database (db_id {restored['db_id']}), not of {db} "
            f"(db_id {replaced['db_id']}). Pass --force to restore it anyway."
        )
    fsio.check_write(db)
    pre = None
    if db.is_file():
        pre = backup(db, Path(backup_dir) if backup_dir is not None else db.parent / "backups", "pre-restore")
    s = sqlite3.connect(src.resolve().as_uri() + "?mode=ro", uri=True)
    d = sqlite3.connect(str(db), isolation_level=None)
    slugs: list[str] = []
    try:
        d.execute("PRAGMA busy_timeout=5000")
        s.backup(d)
        d.execute("PRAGMA journal_mode=WAL")
        if _table(d, "meta"):
            epoch = ids.new()
            d.execute(
                "INSERT INTO meta (key, value) VALUES ('epoch', ?) "
                "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                (epoch,),
            )
            if _table(d, "layer") and _table(d, "seed_base"):
                marks = ",".join("?" * len(SEEDED_TIERS))
                rows = d.execute(
                    f"SELECT id, slug FROM layer WHERE tier IN ({marks}) ORDER BY id", SEEDED_TIERS
                ).fetchall()
                slugs = [r[1] for r in rows]
                mark = {"epoch": epoch, "from": src.name, "at": _stamp(), "layers": [r[0] for r in rows]}
                d.execute(
                    "INSERT INTO meta (key, value) VALUES (?, ?) "
                    "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                    (SEED_RESTORE_KEY, json.dumps(mark, sort_keys=True)),
                )
        d.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        d.close()
        s.close()
    return {"pre_restore": pre, "replaced": replaced, "restored": restored, "seed_layers": slugs}


def listing(dest: Path) -> list[BackupFile]:
    """The backups in folder ``dest``, oldest first (files not named by ``backup`` are ignored)."""
    dest = Path(dest)
    if not dest.is_dir():
        return []
    out = []
    for f in dest.iterdir():
        m = NAME_RE.match(f.name)
        if not m or not f.is_file():
            continue
        at = dt.datetime.strptime(m.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.UTC)
        out.append(BackupFile(f, at, m.group(3)))
    out.sort(key=lambda b: (b.at, b.path.name))
    return out


def prune(dest: Path) -> list[Path]:
    """Apply the retention tiers in ``dest``; return the files removed. Unknown reasons are kept."""
    removed = []
    by_reason: dict[str, list[BackupFile]] = {}
    for b in listing(dest):
        by_reason.setdefault(b.reason, []).append(b)
    for reason, files in by_reason.items():
        keep = KEEP.get(reason)
        if keep is None:
            continue
        for b in files[: max(0, len(files) - keep)]:
            fsio.remove(b.path)  # retried while a scanner or sync client holds it (Windows)
            removed.append(b.path)
    return removed


def auto(db: Path, dest: Path, *, now: dt.datetime | None = None) -> list[Path]:
    """Take the ``daily`` backup if none exists for today (UTC) and the ``weekly`` one if none for this ISO week;
    then prune. Returns the backups made."""
    t = (now or dt.datetime.now(dt.UTC)).astimezone(dt.UTC)
    have = listing(dest)
    made = []
    if not any(b.reason == "daily" and b.at.date() == t.date() for b in have):
        made.append(_backup_at(db, dest, "daily", t))
    if not any(b.reason == "weekly" and b.at.isocalendar()[:2] == t.isocalendar()[:2] for b in have):
        made.append(_backup_at(db, dest, "weekly", t))
    prune(dest)
    return made


def _backup_at(db: Path, dest: Path, reason: str, t: dt.datetime) -> Path:
    con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        return backup_connection(con, dest, reason, now=t)
    finally:
        con.close()


__all__ = [
    "KEEP",
    "SEED_RESTORE_KEY",
    "BackupFile",
    "auto",
    "backup",
    "backup_connection",
    "describe",
    "listing",
    "prune",
    "quick_check",
    "restore",
]
