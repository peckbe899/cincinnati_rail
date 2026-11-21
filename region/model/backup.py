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
"""

from __future__ import annotations

import contextlib
import datetime as dt
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


def restore(src: Path, db: Path, *, backup_dir: Path | None = None) -> None:
    """Replace the content of ``db`` with backup ``src``, after backing ``db`` up (reason ``pre-restore``).

    ``src`` must pass ``quick_check``. No other connection may be writing ``db`` (the CLI holds the lock). The
    restored database gets a new ``epoch`` in ``meta``, so clients resync.
    """
    src = Path(src)
    db = Path(db)
    problems = quick_check(src)
    if problems:
        raise Invalid(f"{src} is not a sound database: " + "; ".join(problems))
    fsio.check_write(db)
    if db.is_file():
        backup(db, Path(backup_dir) if backup_dir is not None else db.parent / "backups", "pre-restore")
    s = sqlite3.connect(src.resolve().as_uri() + "?mode=ro", uri=True)
    d = sqlite3.connect(str(db), isolation_level=None)
    try:
        d.execute("PRAGMA busy_timeout=5000")
        s.backup(d)
        d.execute("PRAGMA journal_mode=WAL")
        has_meta = d.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'meta'").fetchone()
        if has_meta:
            d.execute(
                "INSERT INTO meta (key, value) VALUES ('epoch', ?) "
                "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                (ids.new(),),
            )
        d.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        d.close()
        s.close()


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
            fsio.check_write(b.path)
            b.path.unlink()
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


__all__ = ["KEEP", "BackupFile", "auto", "backup", "backup_connection", "listing", "prune", "quick_check", "restore"]
