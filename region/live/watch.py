"""The source watcher: polls what the hub reads from outside its database and says when a change has settled.

Nothing here depends on inotify, ReadDirectoryChangesW or watchdog: a poll of ``os.scandir`` and ``stat`` works the
same on Windows, on Linux, on a OneDrive folder and on a network share, and costs little when nothing changes (a
stat per watched file; ``os.scandir`` on Windows returns the sizes and times with the listing itself).

**Watches.** A ``Watch`` names a path and how to look at it:

- ``file``: one file, by size and modification time (absent is a state too);
- ``dir``: a folder's own entries, one level (a tile folder of thousands of files is listed, never walked);
- ``tree``: a folder and everything under it (the line files, the old hub's seed), hidden files and ``__pycache__``
  left out, at most ``TREE_CAP`` files;
- ``db``: a SQLite database written by another program (the old hub's ``hub.db``): its size and time, its ``-wal``
  file's, and ``PRAGMA data_version`` on a read-only connection held open by the probe. ``data_version`` changes
  whenever another connection commits, which catches a write that leaves the times as they were (NTFS updates a
  file's time lazily while a program holds it open).

**Settling.** A source is a group of watches (a Deck tie writes all sixteen line files). When any of its signatures
moves, the source is ``changing``; once nothing in it has moved for ``settle_s`` (1.5 s by default) it is settled and
``on_settled(source, changed)`` is called once, with the changed paths by watch. The quiet period counts from the
write: the newest modification time of the changed files, held between the round before the change was seen and the
round that saw it (a clock that disagrees, a network share's, a test's, falls back to the round that saw it); and the
watcher wakes when the period ends rather than at its next round. A burst of fifty writes over a
second is one call; a half-written file that is still growing is not read until it stops. A source that never stops
moving is acted on after ``max_wait_s`` all the same.

**Pause.** While paused the watcher keeps looking (cheap) but calls nothing; ``pending()`` lists the sources that
moved, and ``resume()`` lets them settle and be acted on.
"""

from __future__ import annotations

import contextlib
import logging
import os
import sqlite3
import stat as stat_mod
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

log = logging.getLogger("region.live")

Mode = Literal["file", "dir", "tree", "db"]
Sig = dict[str, tuple[Any, ...]]

TREE_CAP = 20000
"""At most this many files of one ``tree`` watch are looked at; past it the rest are not watched (logged once)."""
SKIP_DIRS = frozenset({"__pycache__", "node_modules", ".git"})


@dataclass(frozen=True)
class Watch:
    """One path to look at (see the module doc). ``label`` is how a message names it (``"lines"``)."""

    path: Path
    mode: Mode = "file"
    label: str = ""


@dataclass
class Source:
    """A group of watches acted on together. ``id`` is stable (``import:profile_lines``, ``tier:deck``)."""

    id: str
    label: str
    watches: list[Watch]
    kind: str = "import"
    info: dict[str, Any] = field(default_factory=dict)


# ------------------------------------------------------------------------------------------------- signatures


def _stat_sig(st: os.stat_result) -> tuple[int, int]:
    return (int(st.st_size), int(st.st_mtime_ns))


def file_sig(path: Path) -> Sig:
    try:
        st = os.stat(path)
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        return {}
    except OSError:
        return {}
    if stat_mod.S_ISDIR(st.st_mode):
        return {"": ("dir",)}
    return {"": _stat_sig(st)}


def dir_sig(path: Path) -> Sig:
    out: Sig = {}
    try:
        with os.scandir(path) as it:
            for e in it:
                if e.name.startswith("."):
                    continue
                try:
                    if e.is_dir(follow_symlinks=False):
                        out[e.name] = ("dir",)
                    else:
                        out[e.name] = _stat_sig(e.stat(follow_symlinks=False))
                except OSError:
                    continue
    except OSError:
        return {}
    return out


_capped: set[str] = set()


def tree_sig(path: Path, cap: int = TREE_CAP) -> Sig:
    out: Sig = {}
    root = str(path)
    if os.path.isfile(root):
        return file_sig(path)
    stack = [(root, "")]
    while stack:
        folder, rel = stack.pop()
        try:
            with os.scandir(folder) as it:
                entries = sorted(it, key=lambda e: e.name)
        except OSError:
            continue
        for e in entries:
            if e.name.startswith(".") or e.name in SKIP_DIRS:
                continue
            name = f"{rel}/{e.name}" if rel else e.name
            try:
                if e.is_dir(follow_symlinks=False):
                    stack.append((e.path, name))
                    continue
                out[name] = _stat_sig(e.stat(follow_symlinks=False))
            except OSError:
                continue
            if len(out) >= cap:
                if root not in _capped:
                    _capped.add(root)
                    log.warning("live: %s holds more than %d files; the rest are not watched", root, cap)
                return out
    return out


class DbProbe:
    """Looks at a SQLite database another program writes, without ever reading its tables (see the module doc).

    The read-only connection is opened lazily and held, since ``data_version`` only means something across the calls
    of one connection. When it cannot be opened (a WAL database whose ``-shm`` cannot be made read-only, say) the
    probe falls back to the file times, trying the connection again every ``retry_s``."""

    def __init__(self, path: Path, retry_s: float = 5.0) -> None:
        self.path = Path(path)
        self.retry_s = retry_s
        self._con: sqlite3.Connection | None = None
        self._tried = -1e9
        self._lock = threading.Lock()
        # data_version is only comparable within one connection, and a new connection starts it afresh: the
        # signature carries a count of the moves seen, so a reconnect (after a pause, an error) is no change
        self._dv: int | None = None
        self._moves = 0
        self._ever = False
        self.hold = False
        """While held (live paused) the probe opens no connection: only the file times are looked at."""

    def _connect(self) -> sqlite3.Connection | None:
        now = time.monotonic()
        if now - self._tried < self.retry_s:
            return None
        self._tried = now
        try:
            con = sqlite3.connect(
                f"{self.path.resolve().as_uri()}?mode=ro", uri=True, timeout=0.05, check_same_thread=False
            )
            con.execute("PRAGMA data_version").fetchone()
            return con
        except sqlite3.Error:
            return None

    def data_version(self) -> int | None:
        """How many times another connection's commit was seen (``None`` before the first connection)."""
        with self._lock:
            if self._con is None and not self.hold:
                self._con = self._connect()
            if self._con is None:
                return self._moves if self._ever else None
            try:
                row = self._con.execute("PRAGMA data_version").fetchone()
            except sqlite3.Error:
                with contextlib.suppress(sqlite3.Error):
                    self._con.close()
                self._con = None
                self._dv = None
                return self._moves
            value = int(row[0]) if row else 0
            if self._dv is not None and value != self._dv:
                self._moves += 1
            self._dv = value
            self._ever = True
            return self._moves

    def signature(self) -> Sig:
        out: Sig = {}
        main = file_sig(self.path)
        if not main:
            self.close()
            return out
        out[""] = main[""]
        wal = file_sig(Path(str(self.path) + "-wal"))
        if wal:
            out["-wal"] = wal[""]
        dv = self.data_version()
        if dv is not None:
            out["data_version"] = (dv,)
        return out

    def close(self) -> None:
        with self._lock:
            if self._con is not None:
                with contextlib.suppress(sqlite3.Error):
                    self._con.close()
                self._con = None
                self._tried = -1e9
            self._dv = None  # the next connection's first value is its baseline, not a change


def changed_keys(old: Sig, new: Sig) -> list[str]:
    """The keys (relative paths) whose signature differs, appeared or went."""
    return sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))


# ---------------------------------------------------------------------------------------------------- watcher


@dataclass
class _State:
    seen: list[Sig]
    acted: list[Sig]
    changed_at: float | None = None
    first_at: float | None = None


Settled = Callable[[Source, dict[str, list[str]]], None]


class Watcher:
    """Polls every source's watches and calls ``on_settled`` once per settled change (see the module doc).

    ``poll_once(now)`` does one round and returns what settled (tests drive it with their own clock);
    ``start()`` runs rounds every ``poll_s`` on a daemon thread until ``stop()``."""

    def __init__(
        self,
        sources: Iterable[Source],
        *,
        on_settled: Settled,
        on_changing: Callable[[Source], None] | None = None,
        settle_s: float = 1.5,
        poll_s: float = 0.25,
        max_wait_s: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.sources = list(sources)
        self.on_settled = on_settled
        self.on_changing = on_changing
        self.settle_s = float(settle_s)
        self.poll_s = float(poll_s)
        self.max_wait_s = float(max_wait_s)
        self.clock = clock
        self.paused = False
        self.rounds = 0
        self._last_t: float | None = None
        """When the round before this one looked (a change seen now was written after it)."""
        self._probes: dict[Path, DbProbe] = {}
        self._round: dict[tuple[str, Path], Sig] | None = None
        """One round's signatures by (mode, path): a folder two sources watch (the line files, read by the line
        files' and the old hub's importers) is looked at once per round."""
        self._state: dict[str, _State] = {}
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        for s in self.sources:
            sig = self._sigs(s)
            self._state[s.id] = _State(seen=sig, acted=[dict(x) for x in sig])

    # ------------------------------------------------------------------------------------------------ looking

    def _sig(self, w: Watch) -> Sig:
        memo = self._round
        if memo is None or w.mode == "db":
            return self._look(w)
        key = (w.mode, w.path)
        if key not in memo:
            memo[key] = self._look(w)
        return dict(memo[key])

    def _look(self, w: Watch) -> Sig:
        if w.mode == "file":
            return file_sig(w.path)
        if w.mode == "dir":
            return dir_sig(w.path)
        if w.mode == "tree":
            return tree_sig(w.path)
        if w.mode == "db":
            probe = self._probes.get(w.path)
            if probe is None:
                probe = self._probes[w.path] = DbProbe(w.path)
                probe.hold = self.paused
            return probe.signature()
        raise ValueError(f"unknown watch mode {w.mode!r}")

    def _sigs(self, s: Source) -> list[Sig]:
        return [self._sig(w) for w in s.watches]

    def changes(self, s: Source, old: list[Sig], new: list[Sig]) -> dict[str, list[str]]:
        """``{watch label or path: [changed relative paths]}`` between two signature lists of a source."""
        out: dict[str, list[str]] = {}
        for w, a, b in zip(s.watches, old, new, strict=True):
            keys = changed_keys(a, b)
            if keys:
                out[w.label or str(w.path)] = keys
        return out

    def changed_paths(self, s: Source, changed: dict[str, list[str]]) -> list[Path]:
        """The absolute paths a ``changes`` result names (a db watch names the database file)."""
        out: list[Path] = []
        for w in s.watches:
            keys = changed.get(w.label or str(w.path))
            if not keys:
                continue
            if w.mode in ("file", "db"):
                out.append(w.path)
            else:
                out.extend(w.path / k for k in keys if k)
        return out

    def _written_at(self, s: Source, old: list[Sig], new: list[Sig], t: float) -> float:
        """When the change seen at ``t`` was written, on the watcher's clock: the newest modification time of the
        files that changed, held between the last round (it was not written then) and ``t``. Only on the monotonic
        clock (a file time is wall time); a deletion, a database or another clock counts from ``t``."""
        lo = self._last_t
        if lo is None or self.clock is not time.monotonic:
            return t
        newest = None
        for w, a, b in zip(s.watches, old, new, strict=True):
            if w.mode == "db":
                return t
            for k in changed_keys(a, b):
                sig = b.get(k)
                if not (isinstance(sig, tuple) and len(sig) == 2 and isinstance(sig[1], int)):
                    return t  # gone, or a folder: no time of its own
                newest = sig[1] if newest is None else max(newest, sig[1])
        if newest is None:
            return t
        at = newest / 1e9 - (time.time() - time.monotonic())
        return min(t, max(lo, at))

    def next_due(self, now: float | None = None) -> float | None:
        """Seconds until the next changing source's quiet period ends (``None``: none is changing, or paused)."""
        if self.paused:
            return None
        t = self.clock() if now is None else now
        with self._lock:
            due = [st.changed_at + self.settle_s - t for st in self._state.values() if st.changed_at is not None]
        return max(0.0, min(due)) if due else None

    # ------------------------------------------------------------------------------------------------- rounds

    def poll_once(self, now: float | None = None) -> list[tuple[Source, dict[str, list[str]]]]:
        """One round: look at every source, and act on (return) those whose change settled."""
        t = self.clock() if now is None else now
        settled: list[tuple[Source, dict[str, list[str]]]] = []
        began: list[Source] = []
        self.rounds += 1
        self._round = {}
        try:
            for s in self.sources:
                try:
                    sig = self._sigs(s)
                except Exception:
                    log.exception("live: looking at %s failed", s.id)
                    continue
                with self._lock:
                    st = self._state[s.id]
                    if sig != st.seen:
                        written = self._written_at(s, st.seen, sig, t)
                        st.seen = sig
                        if st.first_at is None:
                            st.first_at = t
                            began.append(s)
                        st.changed_at = written
                        # a source that never stops moving (a log another program appends to) is acted on after
                        # max_wait_s all the same
                        if self.paused or t - st.first_at < self.max_wait_s:
                            continue
                    else:
                        if st.changed_at is None or self.paused:
                            continue
                        quiet = t - st.changed_at >= self.settle_s
                        overdue = st.first_at is not None and t - st.first_at >= self.max_wait_s
                        if not (quiet or overdue):
                            continue
                    changed = self.changes(s, st.acted, st.seen)
                    st.acted = [dict(x) for x in st.seen]
                    st.changed_at = st.first_at = None
                if changed:
                    settled.append((s, changed))
        finally:
            self._round = None
            self._last_t = t
        for s in began:  # outside the lock: the callback may ask for pending()
            if self.on_changing is not None:
                try:
                    self.on_changing(s)
                except Exception:
                    log.exception("live: the changing callback of %s failed", s.id)
        for s, changed in settled:
            try:
                self.on_settled(s, changed)
            except Exception:
                log.exception("live: acting on %s failed", s.id)
        return settled

    def pending(self) -> list[str]:
        """The sources that moved and are not yet acted on (changing, or held by a pause)."""
        with self._lock:
            return [sid for sid, st in self._state.items() if st.seen != st.acted]

    def changing(self, source_id: str) -> bool:
        with self._lock:
            st = self._state.get(source_id)
            return bool(st and st.changed_at is not None)

    def mark_acted(self, source_id: str) -> None:
        """Take the source's current state as acted on (a start-up catch-up that already ran its importer)."""
        with self._lock:
            st = self._state.get(source_id)
            if st is not None:
                st.acted = [dict(x) for x in st.seen]
                st.changed_at = st.first_at = None

    def pause(self) -> None:
        self.paused = True
        # a paused hub holds no handle on another program's database (the old hub can replace or delete it): the
        # probes close and stay closed, looking at the file times only, until resume
        for p in self._probes.values():
            p.hold = True
            p.close()

    def resume(self) -> None:
        self.paused = False
        for p in self._probes.values():
            p.hold = False
        now = self.clock()
        with self._lock:
            for st in self._state.values():
                if st.seen != st.acted and st.changed_at is None:
                    st.changed_at = now - self.settle_s  # held by the pause: act at the next round
        self._wake.set()

    # ------------------------------------------------------------------------------------------------- thread

    def start(self) -> Watcher:
        if self._thread is not None:
            return self
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="live-watch", daemon=True)
        self._thread.start()
        return self

    def _run(self) -> None:
        while not self._stop.is_set():
            due = self.next_due()
            # a little past the end of the quiet period, so the round that wakes finds it over
            self._wake.wait(self.poll_s if due is None else min(self.poll_s, due + 0.005))
            self._wake.clear()
            if self._stop.is_set():
                break
            try:
                self.poll_once()
            except Exception:
                log.exception("live: a watch round failed; it carries on")

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None
        for p in self._probes.values():
            p.close()


__all__ = [
    "DbProbe",
    "Settled",
    "Source",
    "TREE_CAP",
    "Watch",
    "Watcher",
    "changed_keys",
    "dir_sig",
    "file_sig",
    "tree_sig",
]
