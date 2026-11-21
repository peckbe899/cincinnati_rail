"""region.db connections: pragmas, one writer thread per database file, per-thread readers, the attached cache.

- **Pragmas** (section 9, Database): WAL, ``synchronous=NORMAL``, ``busy_timeout=5000``, ``foreign_keys=ON``.
  Readers also set ``query_only``, so a read path can never write.
- **One writer thread per database file** (9.18). ``Writer.run(fn)`` runs ``fn(con)`` on the file's writer thread
  inside ``BEGIN IMMEDIATE`` ... ``COMMIT`` (``ROLLBACK`` when ``fn`` raises, and the error is raised in the caller).
  Every store opened on the same file in one process shares that thread, so writes are serialised in process and
  SQLite's lock serialises them across processes (the CLI, scripts, seed imports).
- **Readers** are one connection per thread (sqlite3 connections are not shared between threads), opened lazily.
- **Read-only stores** (``open_store(readonly=True)``) open their readers ``mode=ro`` and have a ``ReadOnlyWriter``
  in place of the writer thread, so they never take a write lock and never change the file.
- **cache.db** (WP3's, rebuildable) is attached to every reader as schema ``cache`` when the store is given one, and
  never to the writer: ``BEGIN IMMEDIATE`` takes the write lock of every attached database, so a writer with the cache
  attached would block the scheduler's cache writes for as long as each truth write lasts. The outbox stays in
  region.db because SQLite does not make one transaction atomic across attached WAL databases.

Transactions are explicit: connections are opened with ``isolation_level=None``, which works the same on Python 3.12
and 3.13.
"""

from __future__ import annotations

import datetime as dt
import os
import queue
import sqlite3
import threading
from collections.abc import Callable
from concurrent.futures import Future
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")

BUSY_TIMEOUT_MS = 5000
PRAGMAS = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA synchronous=NORMAL",
    f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}",
    "PRAGMA foreign_keys=ON",
)


def now() -> str:
    """The current UTC time as ISO 8601 with milliseconds: ``2026-11-21T15:30:00.123Z``."""
    t = dt.datetime.now(dt.UTC)
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"


def connect(path: str | os.PathLike[str], *, readonly: bool = False, cache: Path | None = None) -> sqlite3.Connection:
    """A connection to ``path`` with the hub's pragmas; ``readonly`` opens it ``mode=ro`` and ``query_only``."""
    if readonly:
        uri = Path(path).resolve().as_uri() + "?mode=ro"
        con = sqlite3.connect(uri, uri=True, isolation_level=None, check_same_thread=False)
        con.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        con.execute("PRAGMA query_only=ON")
    else:
        con = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False)
        for p in PRAGMAS:
            con.execute(p)
    if cache is not None:
        attach_cache(con, cache, readonly=readonly)
    return con


def attach_cache(con: sqlite3.Connection, cache: Path, *, readonly: bool = False) -> None:
    """Attach ``cache.db`` as schema ``cache`` (created when absent; its tables are WP3's). ``readonly`` attaches it
    ``mode=ro`` (the connection must have been opened with ``uri=True``, as ``connect(readonly=True)`` does), and
    then the file must exist."""
    names = {r[1] for r in con.execute("PRAGMA database_list")}
    if "cache" in names:
        return
    if readonly:
        con.execute("ATTACH DATABASE ? AS cache", (Path(cache).resolve().as_uri() + "?mode=ro",))
        return
    con.execute("ATTACH DATABASE ? AS cache", (str(cache),))
    con.execute("PRAGMA cache.journal_mode=WAL")


def file_of(con: sqlite3.Connection) -> Path | None:
    """The main database file of a connection (``None`` for an in-memory database)."""
    for row in con.execute("PRAGMA database_list"):
        if row[1] == "main":
            return Path(row[2]) if row[2] else None
    return None


def run_in_transaction[R](
    con: sqlite3.Connection, fn: Callable[[sqlite3.Connection], R], *, begin: str = "BEGIN IMMEDIATE"
) -> R:
    """``fn(con)`` inside one transaction: committed when it returns, rolled back when it raises."""
    con.execute(begin)
    try:
        out = fn(con)
        con.execute("COMMIT")
    except BaseException:
        # a failed COMMIT (a full disk, an I/O error) must not leave the connection inside the transaction, or
        # every later BEGIN on it fails
        if con.in_transaction:
            con.execute("ROLLBACK")
        raise
    return out


# ------------------------------------------------------------------------------------------------- writer thread


class Writer:
    """The one writer thread of one database file. ``run(fn)`` executes ``fn(con)`` there in a write transaction.

    Its connection has no attached databases (see the module doc on cache.db)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._q: queue.Queue[tuple[Callable[[sqlite3.Connection], Any], Future[Any], bool] | None] = queue.Queue()
        self._ready: Future[None] = Future()
        self._thread = threading.Thread(target=self._loop, name=f"region-writer:{path.name}", daemon=True)
        self._con: sqlite3.Connection | None = None
        self._thread.start()
        self._ready.result()

    def _loop(self) -> None:
        try:
            self._con = connect(self.path)
        except BaseException as e:
            self._ready.set_exception(e)
            return
        self._ready.set_result(None)
        while True:
            item = self._q.get()
            if item is None:
                break
            fn, fut, tx = item
            if not fut.set_running_or_notify_cancel():
                continue
            try:
                out = run_in_transaction(self._con, fn) if tx else fn(self._con)
            except BaseException as e:
                fut.set_exception(e)
            else:
                fut.set_result(out)
        # work queued behind the stop is refused, not left waiting for ever
        while True:
            try:
                left = self._q.get_nowait()
            except queue.Empty:
                break
            if left is not None and left[1].set_running_or_notify_cancel():
                left[1].set_exception(RuntimeError(f"the writer of {self.path} has stopped"))
        try:
            self._con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error:
            pass
        self._con.close()

    @property
    def on_thread(self) -> bool:
        return threading.current_thread() is self._thread

    def run(self, fn: Callable[[sqlite3.Connection], T], *, transaction: bool = True) -> T:
        """Run ``fn(con)`` on the writer thread (in a write transaction unless ``transaction=False``)."""
        if self.on_thread:
            assert self._con is not None
            if transaction and not self._con.in_transaction:
                return run_in_transaction(self._con, fn)
            return fn(self._con)
        if not self._thread.is_alive():
            raise RuntimeError(f"the writer of {self.path} has stopped")
        fut: Future[T] = Future()
        self._q.put((fn, fut, transaction))
        return fut.result()

    def stop(self) -> None:
        """Stop the thread after the queued work (checkpointing the WAL with TRUNCATE on the way out)."""
        if self._thread.is_alive():
            self._q.put(None)
            self._thread.join(timeout=30)


class ReadOnlyWrite(PermissionError):
    """A write asked of a store opened read-only (a bug in the caller, so it surfaces as a 500)."""


class ReadOnlyWriter:
    """The writer of a read-only store: ``run`` refuses every call with ``ReadOnlyWrite``. No thread, no connection."""

    def __init__(self, path: Path) -> None:
        self.path = path

    on_thread = False

    def run(self, fn: Callable[[sqlite3.Connection], T], *, transaction: bool = True) -> T:
        raise ReadOnlyWrite(f"the store on {self.path} is open read-only; it cannot write")

    def stop(self) -> None:
        return None


_writers: dict[str, tuple[Writer, int]] = {}
_writers_lock = threading.Lock()


def _key(path: Path) -> str:
    return os.path.normcase(str(Path(path).resolve()))


def writer_for(path: Path) -> Writer:
    """The shared writer of ``path`` (started on first use); pair every call with ``release_writer``."""
    k = _key(path)
    with _writers_lock:
        found = _writers.get(k)
        if found is not None and found[0]._thread.is_alive():
            _writers[k] = (found[0], found[1] + 1)
            return found[0]
        w = Writer(Path(path))
        _writers[k] = (w, 1)
        return w


def release_writer(path: Path) -> None:
    """Drop one use of the writer of ``path``; the last release stops its thread."""
    k = _key(path)
    with _writers_lock:
        found = _writers.get(k)
        if found is None:
            return
        w, n = found
        if n > 1:
            _writers[k] = (w, n - 1)
            return
        del _writers[k]
    w.stop()


# ------------------------------------------------------------------------------------------------------ readers


class Readers:
    """One read connection per thread for one database file (``query_only``; ``mode=ro`` when ``readonly``)."""

    def __init__(self, path: Path, *, cache: Path | None = None, readonly: bool = False) -> None:
        self.path = path
        self.cache = cache
        self.readonly = readonly
        self._local = threading.local()
        self._all: list[sqlite3.Connection] = []
        self._lock = threading.Lock()
        self._closed = False

    def get(self) -> sqlite3.Connection:
        con = getattr(self._local, "con", None)
        if con is None:
            if self._closed:
                raise RuntimeError(f"the store on {self.path} is closed")
            con = connect(self.path, cache=self.cache, readonly=self.readonly)
            con.execute("PRAGMA query_only=ON")
            self._local.con = con
            with self._lock:
                self._all.append(con)
        return con

    def close(self) -> None:
        self._closed = True
        with self._lock:
            cons, self._all = self._all, []
        for con in cons:
            try:
                con.close()
            except sqlite3.Error:
                pass


# ------------------------------------------------------------------------------------------------- schema dumps

SHADOW_SUFFIXES = ("_node", "_parent", "_rowid")


def dump_schema(con: sqlite3.Connection) -> str:
    """The schema as committed in ``region/model/schema.sql``: every object's SQL, sorted by type and name.

    Left out: SQLite's own objects, the R-tree's shadow tables (their SQL differs between SQLite versions) and the
    per-kind views ``v_<kind>`` (made from the kind files at open, not by migrations).
    """
    rows = con.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' "
        "ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1 WHEN 'trigger' THEN 2 ELSE 3 END, name"
    ).fetchall()
    virtual = {r[1] for r in rows if r[3].upper().startswith("CREATE VIRTUAL TABLE")}
    out = ["-- region.db schema after every migration (generated: python -m region.model schema --write)", ""]
    for typ, name, _tbl, sql in rows:
        if typ == "view" and name.startswith("v_"):
            continue
        if typ == "table" and any(name == v + s for v in virtual for s in SHADOW_SUFFIXES):
            continue
        out.append(sql.strip() + ";")
        out.append("")
    return "\n".join(out)


__all__ = [
    "BUSY_TIMEOUT_MS",
    "PRAGMAS",
    "ReadOnlyWrite",
    "ReadOnlyWriter",
    "Readers",
    "Writer",
    "attach_cache",
    "connect",
    "dump_schema",
    "file_of",
    "now",
    "release_writer",
    "run_in_transaction",
    "writer_for",
]
