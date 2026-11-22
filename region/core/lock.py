"""The single-instance lock of a hub's ``var`` folder: ``var/hub.lock`` (9.22, 9.28).

    with lock.acquire(var, port) as held:      # crhub serve, before it opens anything
        ...
    holder = lock.reader(var)                  # who holds it now, or None

``acquire`` takes an operating-system lock on ``var/hub.lock`` (``flock`` on POSIX, ``LockFile`` on one byte far past
the end of the file on Windows) and writes the holder into the file: ``pid``, ``port``, ``started``, ``command``, the
``host`` a serve listens on and the checkout (``repo``) it runs from, so a command started in another checkout can tell
that the hub is not its own. The OS drops the lock when the process ends however it ends (``TerminateProcess``, ``kill
-9``, a crash), so a lock file left by a dead process is stale by construction: the next ``acquire`` simply takes it
over and rewrites the holder. A second process (or a second ``acquire`` in the same process) gets ``LockHeld``, which
names the holder.

The lock is held by a descriptor that child processes do not inherit (Node sidecars, job workers), so a child that
outlives its hub never keeps the lock. The file is never deleted: deleting a locked file lets a third process lock a
new file under the same name while a second still holds the old one. On release the holder is blanked, then the
lock is dropped.

The holder is written in place through the locked descriptor, not through ``fsio.write_atomic``: replacing the file
would leave the lock on the old file. The path still passes ``fsio.check_write``.

``reader`` tries the lock itself: when it gets it, nobody holds it (whatever the file says) and it lets go at once.
A probe can collide with a starting server or another probe, so ``acquire`` retries for ``wait_s`` and ``reader``
tries a few times before it reports a holder.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import fsio
from .errors import HubError

LOCK_NAME = "hub.lock"
RECORD_BYTES = 1024  # the holder record, padded with spaces, at the start of the file
LOCK_AT = 1 << 20  # Windows locks this one byte, past the record, so readers can still read the record
_PROBES = 5
_PROBE_GAP_S = 0.02

if os.name == "nt":  # pragma: no cover - exercised on Windows (CI's windows job)
    import msvcrt

    def _try_lock(fd: int) -> bool:
        os.lseek(fd, LOCK_AT, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        return True

    def _unlock(fd: int) -> None:
        os.lseek(fd, LOCK_AT, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _try_lock(fd: int) -> bool:
        # flock locks belong to the open file description, so a second open in the same process conflicts too
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, PermissionError):
            return False
        return True

    def _unlock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


@dataclass(frozen=True)
class Holder:
    """Who holds the lock: a process id, the port it serves on (0 for a command that serves nothing), when it
    started (local time with offset) and the command (``crhub serve``, ``crhub jobs run``)."""

    pid: int
    port: int
    started: str
    command: str = "crhub serve"
    host: str = ""
    repo: str = ""

    def describe(self) -> str:
        """``crhub serve (pid 4242, port 8766, started 2026-11-21T10:00:00+01:00, from C:\\cr)``."""
        port = f", port {self.port}" if self.port else ""
        repo = f", from {self.repo}" if self.repo else ""
        return f"{self.command} (pid {self.pid}{port}, started {self.started or 'at an unknown time'}{repo})"

    def url(self) -> str:
        """``http://<host>:<port>`` of a serving holder (127.0.0.1 when no host was recorded; IPv6 bracketed)."""
        host = self.host or "127.0.0.1"
        if host == "localhost":
            host = "127.0.0.1"
        if ":" in host:
            host = f"[{host}]"
        return f"http://{host}:{self.port}"


class LockHeld(HubError):
    """Another process holds ``var/hub.lock`` (409). ``holder`` names it; ``path`` is the lock file."""

    status = 409
    code = "hub_running"
    title = "Another hub is running"

    def __init__(self, holder: Holder, path: Path, detail: str = "") -> None:
        super().__init__(detail or f"{holder.describe()} holds {path}; stop it first")
        self.holder = holder
        self.path = path

    def _members(self) -> dict[str, Any]:
        return {"holder": asdict(self.holder)}


class Lock:
    """A held lock. ``release()`` (or leaving the ``with`` block) blanks the holder and drops the lock."""

    def __init__(self, path: Path, fd: int, holder: Holder) -> None:
        self.path = path
        self.holder = holder
        self._fd: int | None = fd

    @property
    def held(self) -> bool:
        return self._fd is not None

    def release(self) -> None:
        fd, self._fd = self._fd, None
        if fd is None:
            return
        try:
            _write_record(fd, b"")
        except OSError:
            pass
        try:
            _unlock(fd)
        except OSError:
            pass
        finally:
            os.close(fd)

    def __enter__(self) -> Lock:
        return self

    def __exit__(self, *exc: object) -> None:
        self.release()

    def __del__(self) -> None:  # a forgotten lock is still let go when the object goes
        try:
            self.release()
        except Exception:
            pass


def path_of(var: Path) -> Path:
    """``var/hub.lock``."""
    return Path(var) / LOCK_NAME


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _write_record(fd: int, body: bytes) -> None:
    if len(body) >= RECORD_BYTES:
        raise ValueError("the lock record is too long")
    os.lseek(fd, 0, os.SEEK_SET)
    os.write(fd, body + b" " * (RECORD_BYTES - 1 - len(body)) + b"\n")
    os.fsync(fd)


def _read_record(path: Path) -> Holder | None:
    """The holder written in the file, or ``None`` when it is blank or unreadable."""
    try:
        with open(path, "rb") as f:
            raw = f.read(RECORD_BYTES)
    except OSError:
        return None
    try:
        d = json.loads(raw.decode("utf-8").strip() or "null")
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(d, dict):
        return None
    try:
        return Holder(
            int(d["pid"]),
            int(d.get("port") or 0),
            str(d.get("started") or ""),
            str(d.get("command") or ""),
            str(d.get("host") or ""),
            str(d.get("repo") or ""),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _open(path: Path, *, write: bool) -> int:
    flags = (os.O_RDWR | os.O_CREAT) if write else os.O_RDONLY
    fd = os.open(path, flags | getattr(os, "O_BINARY", 0), 0o644)
    os.set_inheritable(fd, False)  # already the default (PEP 446); a child must never hold the hub's lock
    return fd


def this_repo() -> str:
    """The real path of the checkout this code runs from (what a holder records as ``repo``)."""
    from . import paths

    return os.path.realpath(paths.repo_root())


def acquire(
    var: Path, port: int, *, command: str = "crhub serve", wait_s: float = 1.0, host: str = "127.0.0.1"
) -> Lock:
    """Take ``var/hub.lock`` for this process and write the holder (``pid``, ``port``, ``started``, ``command``,
    ``host``, ``repo``).

    A lock left by a process that has ended is taken over. ``LockHeld`` (naming the holder) when another process, or
    another ``Lock`` of this one, still holds it after ``wait_s`` seconds of retries.
    """
    path = path_of(var)
    fsio.check_write(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = _open(path, write=True)
    deadline = time.monotonic() + max(0.0, float(wait_s))
    try:
        while not _try_lock(fd):
            if time.monotonic() >= deadline:
                holder = _read_record(path) or Holder(0, 0, "", "another process")
                raise LockHeld(holder, path)
            time.sleep(_PROBE_GAP_S)
        holder = Holder(os.getpid(), int(port), _now(), command, host if port else "", this_repo())
        _write_record(fd, json.dumps(asdict(holder), ensure_ascii=False, sort_keys=True).encode("utf-8"))
    except BaseException:
        os.close(fd)
        raise
    return Lock(path, fd, holder)


def reader(var: Path) -> Holder | None:
    """The process holding ``var/hub.lock``, or ``None`` when nobody does (a missing file, or one left by a process
    that has ended). Changes nothing: it only tries the lock and lets go."""
    path = path_of(var)
    if not path.is_file():
        return None
    try:
        fd = _open(path, write=False)
    except OSError:
        return None
    try:
        for attempt in range(_PROBES):
            if _try_lock(fd):
                _unlock(fd)
                return None
            if attempt + 1 < _PROBES:
                time.sleep(_PROBE_GAP_S)
    finally:
        os.close(fd)
    return _read_record(path) or Holder(0, 0, "", "another process")


def refuse_if_held(var: Path, doing: str) -> None:
    """Raise ``LockHeld`` when another process holds ``var/hub.lock``: for commands that must not run beside a
    server (``doing`` says what was refused, as ``"crhub setup"``)."""
    holder = reader(var)
    if holder is not None:
        path = path_of(var)
        raise LockHeld(holder, path, f"{doing} refused: {holder.describe()} holds {path}; stop it first")


__all__ = ["LOCK_NAME", "Holder", "Lock", "LockHeld", "acquire", "path_of", "reader", "refuse_if_held", "this_repo"]
