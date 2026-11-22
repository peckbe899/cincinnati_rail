"""cache.db and the blob folder (decision 9.18; section 6 "Blobs").

**cache.db** holds jobs, results, dependencies, goals, issues, blob rows, file hashes and the outbox cursor. Its
schema is ``migrations/0001_cache.sql``. It can be deleted at any time: the hub recomputes. It is never backed up.
It is opened on its own (``Cache``) by the scheduler, which is its only writer, through one connection used under one
lock; ``attach`` attaches the same file to a truth-DB connection as schema ``cache`` for read-only joins.

**Blobs** are the bytes of result arrays and other outputs (GLB), content-addressed by sha256 under the blob folder
(default: ``blobs`` beside ``cache.db``, so ``var/cache/cache.db`` and ``var/cache/blobs/``), as
``<sha256[:2]>/<sha256>``. A blob is written through ``fsio.write_atomic`` (a temp file, fsync, rename) before its row
is committed, so a row never names a missing file. Eviction deletes files while it holds the write lock, and a commit
checks its files again inside its own transaction (``ensure_blobs``), so the two cannot race. ``sweep`` (run at
start) removes temp files and files without a row, and drops rows whose file is gone together with the results that
need them.

An array blob holds the array's raw C-order little-endian bytes; its dtype (``"<f8"``) and shape live in the result
row, so the API can serve the bytes as they are with ``X-Dtype`` and ``X-Shape``.

**Eviction** is LRU by ``last_used`` down to a byte budget, sparing pinned results and the results of pinned goals.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import json
import logging
import os
import sqlite3
import sys
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from region.core import fsio, paths
from region.core.errors import Invalid, NotFound

if TYPE_CHECKING:
    import numpy as np

log = logging.getLogger("region.jobs")

SCHEMA_VERSION = 1
MIGRATIONS = Path(__file__).resolve().parent / "migrations"
SCHEMA_FILE = MIGRATIONS / "0001_cache.sql"


def now_s() -> float:
    """Unix seconds (leases, last_used)."""
    return time.time()


def now_iso() -> str:
    """UTC time as ISO 8601 with milliseconds and ``Z``."""
    return dt.datetime.now(dt.UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def default_cache_path() -> Path:
    """``var/cache/cache.db``; the blobs go beside it in ``var/cache/blobs``."""
    return paths.var_path("cache", "cache.db")


# ------------------------------------------------------------------------------------------------------- schema


def connect(path: Path) -> sqlite3.Connection:
    """A connection to ``cache.db`` with the hub's pragmas, in autocommit mode (transactions are explicit)."""
    con = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None, timeout=5.0)
    con.row_factory = sqlite3.Row
    # Switching a fresh file to WAL needs a lock that SQLite does not wait for, so two connections opening a new
    # cache.db at once (the server and a CLI command, say) can get "database is locked" here: retry for a while.
    deadline = time.monotonic() + 5.0
    while True:
        try:
            con.execute("PRAGMA journal_mode=WAL")
            break
        except sqlite3.OperationalError as e:
            if "locked" not in str(e) or time.monotonic() >= deadline:
                con.close()
                raise
            time.sleep(0.02)
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA busy_timeout=5000")
    return con


def schema_version(con: sqlite3.Connection, schema: str = "main") -> int:
    """The applied schema version of a cache database (0 when empty)."""
    found = con.execute(
        f"SELECT 1 FROM {schema}.sqlite_master WHERE type = 'table' AND name = 'schema_version'"
    ).fetchone()
    if not found:
        return 0
    row = con.execute(f"SELECT MAX(version) FROM {schema}.schema_version").fetchone()
    return int(row[0] or 0)


def migrate_connection(con: sqlite3.Connection) -> int:
    """Apply the cache schema to a connection's main database, in one transaction with its version row."""
    version = schema_version(con)
    if version > SCHEMA_VERSION:
        raise Invalid(f"cache.db has schema {version}, newer than this hub knows ({SCHEMA_VERSION}); delete it")
    if version == SCHEMA_VERSION:
        return version
    sql = fsio.read_text(SCHEMA_FILE)
    script = (
        "BEGIN IMMEDIATE;\n"
        + sql
        + f"\nINSERT INTO schema_version (version, applied) VALUES ({SCHEMA_VERSION}, '{now_iso()}');\nCOMMIT;\n"
    )
    try:
        con.executescript(script)
    except sqlite3.OperationalError:
        if con.in_transaction:
            con.execute("ROLLBACK")
        # another connection (a second process, or WP1's attach) created the schema between our check and our
        # BEGIN IMMEDIATE: that is a success
        if schema_version(con) == SCHEMA_VERSION:
            return SCHEMA_VERSION
        raise
    except BaseException:
        if con.in_transaction:
            con.execute("ROLLBACK")
        raise
    return SCHEMA_VERSION


def migrate(path: Path) -> int:
    """Create or upgrade ``cache.db`` at ``path`` (its folder is created); returns the schema version."""
    path = Path(path)
    fsio.check_write(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = connect(path)
    try:
        return migrate_connection(con)
    finally:
        con.close()


def attach(con: sqlite3.Connection, path: Path, schema: str = "cache") -> None:
    """Attach ``cache.db`` to another connection (the truth DB's) as ``schema``, migrating it first.

    The scheduler stays the only writer; an attached cache is for reads that join truth and cache.
    """
    if not schema.isidentifier():
        raise Invalid(f"{schema!r} is not a schema name")
    names = {r[1] for r in con.execute("PRAGMA database_list")}
    migrate(path)
    if schema not in names:
        con.execute(f"ATTACH DATABASE ? AS {schema}", (str(path),))


# ------------------------------------------------------------------------------------------------------- arrays


def encode_array(value: Any) -> tuple[bytes, str, list[int]]:
    """``(raw bytes, dtype string, shape)`` of an array: C order, little-endian, no object dtype."""
    import numpy as np

    arr = np.asarray(value)
    if arr.dtype.hasobject:
        raise Invalid("an output array cannot hold Python objects")
    order = arr.dtype.byteorder
    if order == ">" or (order == "=" and sys.byteorder == "big"):
        arr = arr.astype(arr.dtype.newbyteorder("<"))
    arr = np.ascontiguousarray(arr)
    return arr.tobytes(order="C"), arr.dtype.str, [int(n) for n in arr.shape]


def decode_array(data: bytes, dtype: str, shape: list[int]) -> np.ndarray:
    """The read-only array of raw bytes written by ``encode_array``."""
    import numpy as np

    arr = np.frombuffer(data, dtype=np.dtype(dtype))
    return arr.reshape(tuple(shape))


@dataclass
class EncodedOutput:
    """An ``Output`` ready to store: JSON meta and issues, array and blob manifests, the bytes by sha256, and the
    ``output_hash`` (what a downstream key holds for this result, so equal outputs give equal downstream keys)."""

    meta: Any
    arrays: dict[str, dict[str, Any]]
    blobs: dict[str, dict[str, Any]]
    data: dict[str, bytes]
    issues: list[dict[str, Any]]
    output_hash: str


def _json_value(value: Any, what: str) -> Any:
    try:
        return json.loads(fsio.canonical_json(value))
    except (TypeError, ValueError) as e:
        raise Invalid(f"the job's {what} is not plain JSON: {e}") from None


def encode_output(output: Any) -> EncodedOutput:
    """Encode a job's ``Output``. ``output_hash`` is ``content_hash`` of ``{meta, arrays: {name: [dtype, shape,
    sha256]}, blobs: {name: sha256}, issues}``. Meta and issues must be plain JSON (no NaN, no integer over 2**53)."""
    meta = _json_value(output.meta or {}, "meta")
    issues = _json_value(list(output.issues or []), "issues")
    arrays: dict[str, dict[str, Any]] = {}
    blobs: dict[str, dict[str, Any]] = {}
    data: dict[str, bytes] = {}
    for name in sorted(output.arrays or {}):
        raw, dtype, shape = encode_array(output.arrays[name])
        sha = fsio.sha256_hex(raw)
        arrays[name] = {"sha256": sha, "dtype": dtype, "shape": shape, "size": len(raw)}
        data[sha] = raw
    for name in sorted(output.blobs or {}):
        raw = bytes(output.blobs[name])
        sha = fsio.sha256_hex(raw)
        blobs[name] = {"sha256": sha, "size": len(raw)}
        data[sha] = raw
    output_hash = fsio.content_hash(
        {
            "meta": meta,
            "arrays": {n: [a["dtype"], a["shape"], a["sha256"]] for n, a in arrays.items()},
            "blobs": {n: b["sha256"] for n, b in blobs.items()},
            "issues": issues,
        }
    )
    return EncodedOutput(meta, arrays, blobs, data, issues, output_hash)


def output_hash(output: Any) -> str:
    """The ``output_hash`` of an ``Output`` (see ``encode_output``)."""
    return encode_output(output).output_hash


# -------------------------------------------------------------------------------------------------------- cache


def _loads(text: str | None, default: Any) -> Any:
    return json.loads(text) if text else default


class Cache:
    """One ``cache.db`` and its blob folder. Thread-safe: every use of the connection holds ``lock``."""

    def __init__(self, path: Path, *, blobs_dir: Path | None = None) -> None:
        self.path = Path(path)
        self.blobs_dir = Path(blobs_dir) if blobs_dir is not None else self.path.parent / "blobs"
        migrate(self.path)
        self.lock = threading.RLock()
        self.con = connect(self.path)
        self._depth = 0

    # ------------------------------------------------------------------------------------------- connection

    def close(self) -> None:
        with self.lock:
            with contextlib.suppress(sqlite3.Error):
                self.con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self.con.close()

    @contextlib.contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        """One write transaction (``BEGIN IMMEDIATE``); nested use joins the outer one."""
        with self.lock:
            if self._depth:
                self._depth += 1
                try:
                    yield self.con
                finally:
                    self._depth -= 1
                return
            self.con.execute("BEGIN IMMEDIATE")
            self._depth = 1
            try:
                yield self.con
            except BaseException:
                self._depth = 0
                self.con.execute("ROLLBACK")
                raise
            self._depth = 0
            try:
                self.con.execute("COMMIT")
            except BaseException:
                # a failed COMMIT (disk full, I/O error) leaves the transaction open; roll it back, or every later
                # BEGIN on this connection fails
                with contextlib.suppress(sqlite3.Error):
                    if self.con.in_transaction:
                        self.con.execute("ROLLBACK")
                raise

    def query(self, sql: str, args: tuple | list = ()) -> list[sqlite3.Row]:
        with self.lock:
            return self.con.execute(sql, args).fetchall()

    def one(self, sql: str, args: tuple | list = ()) -> sqlite3.Row | None:
        with self.lock:
            return self.con.execute(sql, args).fetchone()

    # ------------------------------------------------------------------------------------------------ blobs

    def blob_path(self, sha256: str) -> Path:
        if len(sha256) != 64 or any(c not in "0123456789abcdef" for c in sha256):
            raise Invalid(f"{sha256!r} is not a sha256")
        return self.blobs_dir / sha256[:2] / sha256

    def put_blob(self, data: bytes) -> tuple[str, int]:
        """Write ``data`` as a content-addressed file (if not already there); returns ``(sha256, size)``.
        The caller commits the blob row afterwards."""
        sha = fsio.sha256_hex(data)
        target = self.blob_path(sha)
        try:
            ok = target.stat().st_size == len(data)
        except FileNotFoundError:
            ok = False
        if not ok:
            fsio.write_atomic(target, data)
        return sha, len(data)

    def ensure_blobs(self, data: dict[str, bytes]) -> None:
        """Write again any blob of ``data`` (``{sha256: bytes}``) whose file is gone. Call it inside the commit's
        ``tx()``, which holds the database write lock and this cache's lock.

        A commit writes its blobs before it takes the lock, so eviction (in this process, or ``crhub jobs prune`` in
        another) may delete a file the commit found already there. Eviction deletes files inside its own transaction,
        so once a commit holds the write lock, a file that is present stays present until its rows are written.
        """
        for sha, raw in data.items():
            try:
                ok = self.blob_path(sha).stat().st_size == len(raw)
            except FileNotFoundError:
                ok = False
            if not ok:
                fsio.write_atomic(self.blob_path(sha), raw)

    def blob_bytes(self, sha256: str) -> bytes:
        try:
            return self.blob_path(sha256).read_bytes()
        except FileNotFoundError:
            raise NotFound(f"blob {sha256} is missing from the cache") from None

    # ---------------------------------------------------------------------------------------------- results

    def result_row(self, key: str) -> dict[str, Any] | None:
        """A result row with its JSON members parsed, or ``None``."""
        row = self.one("SELECT * FROM result WHERE key = ?", (key,))
        if row is None:
            return None
        out = dict(row)
        out["meta"] = _loads(out["meta"], {})
        out["arrays"] = _loads(out["arrays"], {})
        out["blobs"] = _loads(out["blobs"], {})
        out["pinned"] = bool(out["pinned"])
        return out

    def result_meta(self, key: str) -> dict[str, Any]:
        """What ``GET /results/{key}`` serves: the result, its issues and its dependencies (``NotFound`` if none)."""
        res = self.result_row(key)
        if res is None:
            raise NotFound(f"no result {key}")
        res["issues"] = [
            {**dict(r), "data": _loads(r["data"], None)}
            for r in self.query(
                "SELECT rule, sev, c0, c1, msg, data FROM issue WHERE key = ? ORDER BY c0, rule", (key,)
            )
        ]
        res["deps"] = [
            [r["ref"], r["ref_hash"]]
            for r in self.query("SELECT ref, ref_hash FROM result_dep WHERE key = ? ORDER BY ref", (key,))
        ]
        return res

    def touch(self, key: str) -> None:
        with self.tx() as con:
            t = now_s()
            con.execute("UPDATE result SET last_used = ? WHERE key = ?", (t, key))
            con.execute(
                "UPDATE blob SET last_used = ? WHERE sha256 IN (SELECT sha256 FROM result_blob WHERE key = ?)", (t, key)
            )

    def array_bytes(self, key: str, name: str) -> tuple[bytes, str, list[int]]:
        """``(raw bytes, dtype, shape)`` of a result array (for ``/results/{key}/a/{name}``)."""
        res = self.result_row(key)
        if res is None or res["status"] != "ok":
            raise NotFound(f"no result {key}")
        spec = res["arrays"].get(name)
        if spec is None:
            raise NotFound(f"result {key} has no array {name!r}")
        data = self.blob_bytes(spec["sha256"])
        self.touch(key)
        return data, spec["dtype"], list(spec["shape"])

    def read_array(self, key: str, name: str) -> np.ndarray:
        """A result array as a read-only numpy array (``NotFound`` for an unknown key or name)."""
        data, dtype, shape = self.array_bytes(key, name)
        return decode_array(data, dtype, shape)

    def read_blob(self, key: str, name: str) -> bytes:
        """The bytes of a result's named blob (``Output.blobs``)."""
        res = self.result_row(key)
        if res is None or res["status"] != "ok":
            raise NotFound(f"no result {key}")
        spec = res["blobs"].get(name)
        if spec is None:
            raise NotFound(f"result {key} has no blob {name!r}")
        data = self.blob_bytes(spec["sha256"])
        self.touch(key)
        return data

    def read_arrays(self, key: str) -> dict[str, np.ndarray]:
        """Every array of a result (``{}`` when the result or a blob is gone)."""
        res = self.result_row(key)
        if res is None:
            return {}
        out = {}
        for name, spec in res["arrays"].items():
            try:
                out[name] = decode_array(self.blob_bytes(spec["sha256"]), spec["dtype"], spec["shape"])
            except NotFound:
                return {}
        return out

    # ------------------------------------------------------------------------------------------- file hashes

    def file_sha256(self, path: Path) -> str | None:
        """The sha256 of a file, reused from ``file_hash`` while its size and mtime are unchanged; ``None`` when the
        file does not exist."""
        p = Path(path)
        try:
            st = p.stat()
        except (FileNotFoundError, NotADirectoryError):
            return None
        if not p.is_file():
            return None
        name = str(p)
        row = self.one("SELECT size, mtime_ns, sha256 FROM file_hash WHERE path = ?", (name,))
        if row is not None and row["size"] == st.st_size and row["mtime_ns"] == st.st_mtime_ns:
            return row["sha256"]
        sha = fsio.sha256_file(p)
        with self.tx() as con:
            con.execute(
                "INSERT OR REPLACE INTO file_hash (path, size, mtime_ns, sha256, checked) VALUES (?, ?, ?, ?, ?)",
                (name, st.st_size, st.st_mtime_ns, sha, now_iso()),
            )
        return sha

    # ------------------------------------------------------------------------------------------------ cursor

    def cursor(self, name: str) -> int | None:
        row = self.one("SELECT seq FROM cursor WHERE name = ?", (name,))
        return None if row is None else int(row["seq"])

    def set_cursor(self, name: str, seq: int) -> None:
        with self.tx() as con:
            con.execute(
                "INSERT INTO cursor (name, seq, updated) VALUES (?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET seq = excluded.seq, updated = excluded.updated",
                (name, int(seq), now_iso()),
            )

    # ---------------------------------------------------------------------------------------- maintenance

    def total_bytes(self) -> int:
        row = self.one("SELECT COALESCE(SUM(size), 0) FROM blob")
        return int(row[0]) if row else 0

    def stats(self) -> dict[str, Any]:
        """Counts for ``crhub jobs stats`` and doctor."""
        out: dict[str, Any] = {"path": str(self.path), "blobs_dir": str(self.blobs_dir)}
        for table in ("job", "result", "result_dep", "goal", "issue", "blob"):
            out[table] = int(self.one(f"SELECT COUNT(*) FROM {table}")[0])
        out["bytes"] = self.total_bytes()
        out["jobs_by_state"] = {
            r["state"]: r["n"] for r in self.query("SELECT state, COUNT(*) n FROM job GROUP BY state")
        }
        return out

    def _drop_result(self, con: sqlite3.Connection, key: str) -> list[str]:
        """Delete a result and its rows; return the blob shas no result needs any more (rows deleted too)."""
        shas = [r[0] for r in con.execute("SELECT sha256 FROM result_blob WHERE key = ?", (key,))]
        con.execute("DELETE FROM result WHERE key = ?", (key,))
        con.execute("DELETE FROM result_dep WHERE key = ?", (key,))
        con.execute("DELETE FROM result_blob WHERE key = ?", (key,))
        con.execute("DELETE FROM issue WHERE key = ?", (key,))
        con.execute("UPDATE goal SET latest_key = NULL, state = 'evicted' WHERE latest_key = ?", (key,))
        free = []
        for sha in shas:
            if con.execute("SELECT 1 FROM result_blob WHERE sha256 = ? LIMIT 1", (sha,)).fetchone() is None:
                con.execute("DELETE FROM blob WHERE sha256 = ?", (sha,))
                free.append(sha)
        return free

    def _unlink(self, shas: list[str]) -> None:
        """Delete blob files. A file that cannot go now (on Windows, one a reader holds open) is left as an orphan
        for the next start's sweep; it never fails the eviction around it."""
        for sha in shas:
            try:
                self.blob_path(sha).unlink()
            except FileNotFoundError:
                pass
            except OSError as e:
                log.warning("blob %s could not be deleted now (%s); the next start's sweep removes it", sha, e)

    def drop_result(self, key: str) -> bool:
        """Delete one result, its rows and the blobs no other result needs (for a result whose blob file was lost,
        so it is computed again instead of failing every reader). Returns whether there was a result."""
        with self.tx() as con:
            if con.execute("SELECT 1 FROM result WHERE key = ?", (key,)).fetchone() is None:
                return False
            self._unlink(self._drop_result(con, key))
        return True

    def protected_keys(self) -> set[str]:
        """Results eviction spares: pinned results, the latest and wanted results of pinned goals, and those of
        watched goals that have not expired (what an open sheet shows)."""
        keys = {r[0] for r in self.query("SELECT key FROM result WHERE pinned = 1")}
        for r in self.query("SELECT want_key, latest_key FROM goal WHERE pinned = 1"):
            keys.update(k for k in (r[0], r[1]) if k)
        for r in self.query(
            "SELECT want_key, latest_key FROM goal WHERE watch = 1 AND (expires IS NULL OR expires > ?)", (now_s(),)
        ):
            keys.update(k for k in (r[0], r[1]) if k)
        return keys

    def evict(self, max_bytes: int) -> dict[str, int]:
        """Drop least recently used results until the blobs total at most ``max_bytes``, sparing pinned goals.

        Returns ``{"results", "blobs", "bytes"}``: what was dropped and the bytes freed.
        """
        dropped_results = 0
        freed: list[str] = []
        freed_bytes = 0
        with self.tx() as con:
            total = int(con.execute("SELECT COALESCE(SUM(size), 0) FROM blob").fetchone()[0])
            if total <= max_bytes:
                return {"results": 0, "blobs": 0, "bytes": 0}
            spare = self.protected_keys()
            for row in con.execute("SELECT key FROM result ORDER BY last_used, key").fetchall():
                if total <= max_bytes:
                    break
                key = row[0]
                if key in spare:
                    continue
                sizes = {
                    r[0]: r[1]
                    for r in con.execute(
                        "SELECT b.sha256, b.size FROM result_blob rb JOIN blob b ON b.sha256 = rb.sha256 "
                        "WHERE rb.key = ?",
                        (key,),
                    )
                }
                for sha in self._drop_result(con, key):
                    freed.append(sha)
                    total -= sizes.get(sha, 0)
                    freed_bytes += sizes.get(sha, 0)
                dropped_results += 1
            # the files go while the write lock is held, so a commit never finds a file and then loses it (see
            # ensure_blobs); a failed COMMIT afterwards leaves rows without files, which sweep drops at the next start
            self._unlink(freed)
        return {"results": dropped_results, "blobs": len(freed), "bytes": freed_bytes}

    def sweep(self) -> dict[str, int]:
        """Start-up clean-up: remove temp files and blob files with no row; drop rows whose file is missing (and the
        results that need them). Run only while no job is committing."""
        removed_tmp = removed_orphans = dropped_rows = dropped_results = 0
        rows = {r[0]: r[1] for r in self.query("SELECT sha256, size FROM blob")}
        on_disk: dict[str, int] = {}
        if self.blobs_dir.is_dir():
            for folder in self.blobs_dir.iterdir():
                if not folder.is_dir():
                    continue
                for f in folder.iterdir():
                    name = f.name
                    if folder.name == "tmp" or name.startswith(".") or name.endswith(".tmp"):
                        with contextlib.suppress(OSError):
                            f.unlink()
                            removed_tmp += 1
                        continue
                    if name not in rows:
                        with contextlib.suppress(OSError):
                            f.unlink()
                            removed_orphans += 1
                        continue
                    with contextlib.suppress(OSError):
                        on_disk[name] = f.stat().st_size
        missing = [sha for sha, size in rows.items() if on_disk.get(sha) != size]
        if missing:
            freed: list[str] = []
            with self.tx() as con:
                for sha in missing:
                    keys = [r[0] for r in con.execute("SELECT key FROM result_blob WHERE sha256 = ?", (sha,))]
                    for key in keys:
                        freed += self._drop_result(con, key)
                        dropped_results += 1
                    if con.execute("DELETE FROM blob WHERE sha256 = ?", (sha,)).rowcount:
                        dropped_rows += 1
                self._unlink([s for s in freed if s not in missing])
        return {
            "tmp": removed_tmp,
            "orphans": removed_orphans,
            "missing_rows": dropped_rows,
            "results": dropped_results,
        }


# ------------------------------------------------------------------------------------------- the current cache

_current: Cache | None = None
_current_lock = threading.Lock()


def set_current(cache: Cache | None) -> None:
    """Make ``cache`` the one module-level ``read_array`` uses (the scheduler does this on start)."""
    global _current
    with _current_lock:
        _current = cache


def current(cache_path: Path | None = None) -> Cache:
    """The running scheduler's cache, else one opened at ``cache_path`` (default ``default_cache_path()``)."""
    global _current
    with _current_lock:
        if cache_path is None and _current is not None:
            return _current
        path = Path(cache_path) if cache_path is not None else default_cache_path()
        if _current is not None and _current.path == path:
            return _current
        opened = Cache(path)
        if _current is None:
            _current = opened
        return opened


def read_array(key: str, name: str, *, cache_path: Path | None = None) -> np.ndarray:
    """The array ``name`` of result ``key`` (``NotFound`` if the result or array is not in the cache)."""
    return current(cache_path).read_array(key, name)


def wipe(path: Path, *, blobs_dir: Path | None = None) -> int:
    """Delete ``cache.db`` (with its WAL files) and every blob beside it; returns the files removed. Only while no
    scheduler has the cache open."""
    path = Path(path)
    blobs = Path(blobs_dir) if blobs_dir is not None else path.parent / "blobs"
    count = 0
    if blobs.is_dir():
        for folder in list(blobs.iterdir()):
            if not folder.is_dir():
                continue
            for f in list(folder.iterdir()):
                fsio.check_write(f)
                with contextlib.suppress(OSError):
                    f.unlink()
                    count += 1
            with contextlib.suppress(OSError):
                folder.rmdir()
    return count + len(remove_cache_files(path))


def remove_cache_files(path: Path) -> list[Path]:
    """Delete ``cache.db`` and its WAL and shared-memory files (``crhub jobs wipe``); the blobs are kept for
    ``sweep`` to clear. Returns the files removed."""
    removed = []
    for suffix in ("", "-wal", "-shm", "-journal"):
        p = Path(str(path) + suffix)
        fsio.check_write(p)
        if p.exists():
            os.remove(p)
            removed.append(p)
    return removed


__all__ = [
    "Cache",
    "SCHEMA_VERSION",
    "attach",
    "connect",
    "current",
    "decode_array",
    "EncodedOutput",
    "default_cache_path",
    "encode_array",
    "encode_output",
    "output_hash",
    "migrate",
    "migrate_connection",
    "now_iso",
    "now_s",
    "read_array",
    "remove_cache_files",
    "schema_version",
    "set_current",
    "wipe",
]
