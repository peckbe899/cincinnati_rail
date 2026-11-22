"""The live hub: watch every source, import what changed, recompute what it touched, and say so in plain words.

    live = Live(store, scheduler, cfg=cfg, publish=hub.events.publish).start()
    ...
    live.stop()

**Flow.** The ``Watcher`` (``watch.py``) polls every declared source (``sources.py``). A change that settles goes to
one worker thread, which handles one source at a time, coalescing repeats:

- **an importer's source** (the line files, the old hub's seed or its live ``hub.db``, the registry): the importer
  reads the files as they are in the working tree, never git (9.27 as updated: git stays the source for
  ``crhub rebuild`` and CI), and the old hub's database through a backup-API snapshot. The sha256 of every file read
  is recorded in the run. A source whose files hash as the last applied run's is left alone (a re-save of the same
  bytes runs nothing). Otherwise a dry run is made; one with errors (a half-written file) is reported and nothing is
  applied; one with changes is applied as one import changeset, which Undo this import reverts. Applying never
  overrides Ben (design rule 3): his revisions sit in the layers above the import's, the rebase merges what touches
  nothing he changed, and every change that touches his edit (a field he changed, geometry under his profile) is a
  review-queue conflict with the import's proposal, while his revision stays what he sees;
- **a data tier** (the 1912 ground's handshake, the Sanborn tiles' index, the Deck files): the tier is scanned
  again (a ``tier`` event when its status moves), the ``file:`` dependencies under it are checked so exactly the
  results that read a changed file are planned again, and the importers that follow it run (the ground layer
  records follow the ground tiers' handshakes).

**Recompute.** Records an import changed invalidate, through the scheduler's outbox tail, exactly the results
whose plans read them; an unchanged output stops the chain (early cutoff). Every section in ``main`` has a
background goal (``profiles.solve_section``, priority 5); a pane asks for its own at priority 0 when it has the
focus and 1 when it is open (``set_priority``), so the section in front of Ben is solved first.

**What Ben sees.** Each step sends a ``source`` event (``{source, label, state, text, at, run, changeset, review,
sections, toast, undo}``), a ``live`` event (``{paused, pending, updated}``) when the summary moves, and a
``pending`` event (``{items: [{scope, type, view, state}]}``) with the sections being imported or re-solved.

**Pause and undo.** ``pause()`` stops acting (the watcher keeps looking, so the chip counts what waits);
``resume()`` acts on it. ``undo(source)`` reverts the source's last import changeset, marks its run reverted, and
holds those exact source files: they are not imported again until they change (``apply_held`` takes them anyway).
The pause and the holds are kept in ``var/live/state.json``.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import json
import logging
import queue
import sqlite3
import threading
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from region.core import fsio, paths
from region.core.errors import Conflict, HubError, NotFound
from region.core.view import View

from . import sources as S
from . import words as W
from .watch import Source, Watcher

log = logging.getLogger("region.live")

SOLVE_JOB = "profiles.solve_section"
STATE_FILE = "live/state.json"
RETRY_S = (1.0, 2.0, 5.0, 10.0, 30.0)
"""How long to wait before looking again at a source another program holds open (Windows: WinError 32, a file
being written, Excel or a virus scanner holding it); past the last, the source waits for its next change."""
Publish = Callable[[str, dict[str, Any]], None]


def now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _fingerprint(entries: Mapping[str, Any]) -> str:
    return fsio.content_hash({k: (v or {}).get("sha256") for k, v in sorted(entries.items()) if "/" not in k})


def transient(e: BaseException) -> bool:
    """Whether a read failed only because another program holds the file or database for now (Windows sharing
    violations, a locked SQLite file), so looking again shortly will do."""
    if isinstance(e, PermissionError | fsio.FileInUse) or getattr(e, "winerror", None) in fsio.RETRY_WINERRORS:
        return True
    if isinstance(e, sqlite3.OperationalError):
        text = str(e).lower()
        return "locked" in text or "busy" in text
    cause = e.__cause__ or e.__context__
    return cause is not None and cause is not e and transient(cause)


def _locked(paths_: list[Path]) -> Path | None:
    """The first of these files that cannot be opened for reading because another program holds it (Windows), or
    ``None``. Missing files and folders are not locked."""
    for p in paths_:
        try:
            if not p.is_file():
                continue
            with open(p, "rb") as f:
                f.read(1)
        except OSError as e:
            if transient(e):
                return p
    return None


class Live:
    """The live service of one server (see the module doc)."""

    def __init__(
        self,
        store: Any,
        jobs: Any = None,
        *,
        cfg: Mapping[str, Any] | None = None,
        publish: Publish | None = None,
        settle_s: float | None = None,
        poll_s: float | None = None,
        max_wait_s: float | None = None,
        importers: Mapping[str, Any] | None = None,
        sources: list[Source] | None = None,
        ledger_dir: Path | None = None,
        work: Path | None = None,
        state_path: Path | None = None,
        watch_sections: bool = True,
        backup_every_s: float = 3600.0,
        view: View | None = None,
    ) -> None:
        self.cfg = dict(cfg) if cfg is not None else paths.config()
        live_cfg = self.cfg.get("live") or {}
        self.store = store
        self.jobs = jobs
        self.publish_fn = publish
        self.settle_s = float(settle_s if settle_s is not None else live_cfg.get("settle_s", 1.5))
        self.poll_s = float(poll_s if poll_s is not None else live_cfg.get("poll_s", 0.25))
        self.max_wait_s = float(max_wait_s if max_wait_s is not None else live_cfg.get("max_wait_s", 60.0))
        if importers is None:
            from region.cli import imports as I

            importers = I.importers()
        self.importers = dict(importers)
        self.sources = sources if sources is not None else S.declared(self.cfg, self.importers)
        self.by_id = {s.id: s for s in self.sources}
        self._quiet = {s.id for s in self.sources if self._is_quiet(s)}
        """Tiers no pane, map layer or importer reads (the 3D artifacts, whose root is the project folder above the
        repo; the folders that only hold an importer's files): a change to them is said only once it turns out to
        move the tier's status or a result input, never as "changing" or a pending count while it settles."""
        self.ledger_dir = ledger_dir
        self.work = Path(work) if work is not None else paths.var_path("imports", "live", cfg=self.cfg)
        self.state_path = (
            Path(state_path) if state_path is not None else paths.var_path(*STATE_FILE.split("/"), cfg=self.cfg)
        )
        self.watch_sections = watch_sections
        self.backup_every_s = float(backup_every_s)
        self.view = view or View()
        self.paused = False
        self.held: dict[str, str] = {}
        self.state: dict[str, dict[str, Any]] = {
            s.id: {
                "source": s.id,
                "label": s.label,
                "kind": s.kind,
                "state": "idle",
                "text": "",
                "at": None,
                "changed": None,
                "run": None,
                "changeset": None,
                "review": 0,
                "sections": [],
                "undo": False,
                "failed": False,
                "watching": [str(w.path) for w in s.watches],
            }
            for s in self.sources
        }
        self.history: list[dict[str, Any]] = []
        self.updated: str | None = None
        self.counts = {"imports": 0, "applied": 0, "unchanged": 0, "skipped": 0, "errors": 0}
        self._last_backup = -1e9
        self._timing: dict[str, float] = {}
        self._marks: dict[str, dict[str, Any]] = {}
        self._jobs_active: dict[tuple[str, str, str], str] = {}
        self._marks_sent: list[dict[str, Any]] | None = None
        self._marks_timer: threading.Timer | None = None
        self._lock = threading.RLock()
        self._busy = threading.Lock()
        self._queue: queue.Queue[tuple[str, dict[str, list[str]], str] | None] = queue.Queue()
        self._queued: dict[str, dict[str, list[str]]] = {}
        self._thread: threading.Thread | None = None
        self._unsub: Callable[[], None] | None = None
        self._tiers: dict[str, Any] = {}
        self._docs_seen: dict[str, Any] = {}
        self._started = False
        self._working = False
        self._deferred: set[str] = set()
        self._retries: dict[str, int] = {}
        self._timers: set[threading.Timer] = set()
        self._stopping = threading.Event()
        self._load_state()
        self.watcher = Watcher(
            self.sources,
            on_settled=self._on_settled,
            on_changing=self._on_changing,
            settle_s=self.settle_s,
            poll_s=self.poll_s,
            max_wait_s=self.max_wait_s,
        )
        if self.paused:
            self.watcher.pause()

    # ------------------------------------------------------------------------------------------------ lifecycle

    def start(self, *, catch_up: bool = True) -> Live:
        """Start the worker and the watcher; with ``catch_up``, first bring every importer up to its sources as
        they are now (a change made while the hub was stopped) and watch every section's solve."""
        if self._started:
            return self
        self._started = True
        self._stopping.clear()
        subscribe = getattr(self.jobs, "subscribe", None)
        if callable(subscribe):
            self._unsub = subscribe(self._on_job_event)
        self._thread = threading.Thread(target=self._work, name="live-import", daemon=True)
        self._thread.start()
        if catch_up:
            self._queue.put(("@start", {}, "start"))
        self.watcher.start()
        return self

    def stop(self) -> None:
        self._stopping.set()  # a start-up catch-up stops between importers
        self.watcher.stop()
        with self._lock:
            timers, self._timers = self._timers, set()
        for t in timers:
            t.cancel()
        self._queue.put(None)
        if self._thread is not None:
            self._thread.join(timeout=30)
            self._thread = None
        if self._unsub is not None:
            with contextlib.suppress(Exception):
                self._unsub()
            self._unsub = None
        if self._marks_timer is not None:
            self._marks_timer.cancel()
        self._started = False

    def wait_idle(self, timeout: float = 30.0) -> bool:
        """Wait until nothing is changing, queued or importing (tests)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                busy = bool(self._queued) or self._queue.unfinished_tasks > 0 or self._working
            if not busy and not self._busy.locked() and not any(self.watcher.changing(s.id) for s in self.sources):
                return True
            time.sleep(0.02)
        return False

    # ---------------------------------------------------------------------------------------------- persisted

    def _load_state(self) -> None:
        try:
            doc = fsio.read_json(self.state_path) if self.state_path.is_file() else {}
        except Exception:
            log.exception("live: %s cannot be read; starting with no holds", self.state_path)
            doc = {}
        self.paused = bool(doc.get("paused"))
        self.held = {str(k): str(v) for k, v in (doc.get("held") or {}).items()}

    def _save_state(self) -> None:
        try:
            fsio.write_json(self.state_path, {"paused": self.paused, "held": dict(sorted(self.held.items()))})
        except Exception:
            log.exception("live: %s cannot be written", self.state_path)

    # ------------------------------------------------------------------------------------------------- events

    def _publish(self, type: str, data: dict[str, Any]) -> None:
        if self.publish_fn is None:
            return
        try:
            self.publish_fn(type, data)
        except Exception:
            log.exception("live: publishing a %s event failed", type)

    def _is_quiet(self, source: Source) -> bool:
        if source.kind != "tier":
            return False
        spec = (self.cfg.get("tiers") or {}).get(source.info.get("tier"), {})
        return not (isinstance(spec, Mapping) and spec.get("mount")) and not source.info.get("importers")

    def summary(self) -> dict[str, Any]:
        """``{paused, pending, updated}``: what the status bar's Sources chip shows."""
        pending = set(self.watcher.pending()) - self._quiet
        with self._lock:
            pending |= (set(self._queued) | self._deferred) - self._quiet
            pending |= {sid for sid, st in self.state.items() if st["state"] in ("importing", "changing", "waiting")}
        return {"paused": self.paused, "pending": len(pending), "updated": self.updated}

    def _source_event(self, sid: str, *, toast: bool = False, level: str = "info") -> None:
        with self._lock:
            st = dict(self.state[sid])
        st["toast"] = toast
        st["level"] = level
        st["live"] = self.summary()
        self._publish("source", st)
        self._publish("live", st["live"])

    def _set(self, sid: str, **members: Any) -> None:
        with self._lock:
            st = self.state[sid]
            st.update(members)
            # Undo this import stays offered while the source's last applied changeset is the newest it made: a
            # re-save of the same files, a half-written file or a change that alters nothing does not take it away
            st["undo"] = st["kind"] == "import" and bool(st.get("changeset"))

    def _remember(self, sid: str, text: str) -> None:
        with self._lock:
            self.history.insert(0, {"at": now_iso(), "source": sid, "label": self.state[sid]["label"], "text": text})
            del self.history[50:]

    def status(self) -> dict[str, Any]:
        """``GET /live``: the summary, every source's state and the last actions."""
        with self._lock:
            sources = [dict(v) for v in self.state.values()]
            history = list(self.history)
            counts = dict(self.counts)
        return {
            **self.summary(),
            "settle_s": self.settle_s,
            "poll_s": self.poll_s,
            "sources": sources,
            "history": history,
            "counts": counts,
            "marks": self.marks(),
        }

    # ------------------------------------------------------------------------------------------- pending marks

    def marks(self) -> list[dict[str, Any]]:
        """The sections being imported or re-solved: ``[{scope, type, view, state}]``."""
        with self._lock:
            out = [dict(m) for m in self._marks.values()]
            seen = {(m["type"], m["scope"], m["view"]) for m in out}
            for (t, s, v), state in sorted(self._jobs_active.items()):
                if (t, s, v) not in seen:
                    out.append({"type": t, "scope": s, "view": v, "state": state})
        return out

    def _marks_changed(self) -> None:
        with self._lock:
            if self._marks_timer is not None:
                return
            self._marks_timer = threading.Timer(0.05, self._send_marks)
            self._marks_timer.daemon = True
            self._marks_timer.start()

    def _send_marks(self) -> None:
        with self._lock:
            self._marks_timer = None
        items = self.marks()
        if items == self._marks_sent:
            return
        self._marks_sent = items
        self._publish("pending", {"items": items})

    def _on_job_event(self, kind: str, payload: dict[str, Any]) -> None:
        if kind != "job":
            return
        k = (str(payload.get("type")), str(payload.get("scope")), str(payload.get("view")))
        state = payload.get("state")
        with self._lock:
            if state in ("queued", "running"):
                self._jobs_active[k] = "re-solving" if state == "running" else "queued"
            else:
                self._jobs_active.pop(k, None)
        self._marks_changed()

    # --------------------------------------------------------------------------------------------- the watcher

    def _on_changing(self, source: Source) -> None:
        with self._lock:
            st = self.state[source.id]
            if st["state"] == "changing" or source.id in self._quiet:
                return
            st["state"] = "changing"
            st["changed"] = now_iso()
            st["text"] = "changing, waiting for it to settle"
        self._source_event(source.id)

    def _on_settled(self, source: Source, changed: dict[str, list[str]]) -> None:
        self.enqueue(source.id, changed, "change")

    def enqueue(self, sid: str, changed: dict[str, list[str]] | None = None, reason: str = "change") -> None:
        """Queue a source to be acted on (coalesced with a change already queued for it)."""
        with self._lock:
            if sid in self._queued:
                for k, v in (changed or {}).items():
                    self._queued[sid].setdefault(k, [])
                    self._queued[sid][k] = sorted(set(self._queued[sid][k]) | set(v))
                return
            self._queued[sid] = {k: list(v) for k, v in (changed or {}).items()}
        self._queue.put((sid, {}, reason))

    # --------------------------------------------------------------------------------------------- the worker

    def _work(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                self._queue.task_done()
                return
            sid, _unused, reason = item
            self._working = True
            try:
                if sid == "@start":
                    self._catch_up()
                    continue
                with self._lock:
                    changed = self._queued.pop(sid, {})
                source = self.by_id.get(sid)
                if source is None:
                    continue
                with self._busy:
                    self.act(source, changed, reason)
            except Exception as e:
                log.exception("live: acting on %s failed", sid)
                if sid in self.state:
                    self._set(sid, state="error", text=f"failed: {type(e).__name__}: {e}", at=now_iso())
                    self._source_event(sid, toast=True, level="error")
            finally:
                self._working = False
                self._queue.task_done()

    def act(self, source: Source, changed: dict[str, list[str]], reason: str = "change") -> dict[str, Any]:
        """Act on one source now (the worker calls this; tests may too). Returns the source's new state."""
        if self.paused and reason not in ("held", "check"):
            with self._lock:
                self._deferred.add(source.id)  # queued before the pause: acted on at resume
            return dict(self.state[source.id])
        held_open = _locked(self._paths_of(source, changed))
        if held_open is not None:
            return self._wait_for(source, changed, reason, held_open.name)
        if source.kind == "tier":
            self._tier(source, changed)
        else:
            self.run_import(source, reason=reason, changed=changed)
        if self.state[source.id]["state"] != "waiting":
            self._retries.pop(source.id, None)
        return dict(self.state[source.id])

    def _paths_of(self, source: Source, changed: dict[str, list[str]]) -> list[Path]:
        """The files a change names, or (a check, a retry, the start) the source's own file watches."""
        if changed:
            return [p for p in self.watcher.changed_paths(source, changed) if p.suffix not in (".db",)]
        return [w.path for w in source.watches if w.mode == "file"]

    def _wait_for(self, source: Source, changed: dict[str, list[str]], reason: str, what: str) -> dict[str, Any]:
        """Another program holds a file of the source open (Windows): look again in a moment, quietly, and say so
        only if it is still held after the last try."""
        sid = source.id
        n = self._retries.get(sid, 0)
        if n >= len(RETRY_S) or self._stopping.is_set():
            self._retries.pop(sid, None)
            return self._fail(
                sid, f"{source.label}: {what} is still open in another program; it is taken in when it changes again"
            )
        delay = RETRY_S[n]
        self._retries[sid] = n + 1
        self._set(
            sid, state="waiting", text=f"{what} is open in another program; looking again in {delay:g} s", at=now_iso()
        )
        self._source_event(sid)
        again = dict(changed)

        def fire() -> None:
            with self._lock:
                self._timers.discard(timer)
            if not self._stopping.is_set():
                self.enqueue(sid, again, "retry" if reason != "held" else "held")

        timer = threading.Timer(delay, fire)
        timer.daemon = True
        with self._lock:
            self._timers.add(timer)
        timer.start()
        return dict(self.state[sid])

    def _catch_up(self) -> None:
        """At start: every importer against its sources as they are now, the tiers' first scan, and a background
        goal for every section."""
        from region import tiers as T

        try:
            self._tiers = dict(T.scan(self.cfg))
        except Exception:
            log.exception("live: the first tier scan failed")
        if not self.paused:
            for s in self.sources:
                if s.kind != "import":
                    continue
                if self._stopping.is_set():
                    return
                with self._busy:
                    try:
                        self.run_import(s, reason="start")
                    except Exception as e:
                        log.exception("live: catching up %s failed", s.id)
                        self._set(s.id, state="error", text=f"failed: {type(e).__name__}: {e}", at=now_iso())
                        self._source_event(s.id, toast=True, level="error")
        self.watch_all_sections()

    def watch_all_sections(self) -> int:
        """A background goal (priority 5, for ever) for every section in the view; returns how many were added."""
        if not self.watch_sections or self.jobs is None or not hasattr(self.jobs, "ensure_watched"):
            return 0
        try:
            self.jobs.registry.get(SOLVE_JOB)
        except Exception:
            return 0
        added = 0
        try:
            from region.jobs.plan import all_records

            for rec in all_records(self.store, "section", self.view):
                try:
                    if self.jobs.ensure_watched(SOLVE_JOB, rec["id"], self.view, priority=5):
                        added += 1
                except HubError as e:
                    log.info("live: no background solve of %s: %s", rec["id"], e.detail)
                    break  # the engine is off: every section would say the same
        except Exception:
            log.exception("live: watching the sections failed")
        return added

    # ------------------------------------------------------------------------------------------------- tiers

    def _tier(self, source: Source, changed: dict[str, list[str]]) -> None:
        from region import tiers as T

        name = source.info["tier"]
        before = self._tiers.get(name)
        T.clear_cache()
        reports = T.scan(self.cfg)
        after = reports.get(name)
        self._tiers = dict(reports)
        moved = before is None or after is None or (before.status, before.detail) != (after.status, after.detail)
        if after is not None and moved:
            self._publish("tier", dict(after.event()))
        # the importers that follow the tier first (the ground layer records), so the results that read both the
        # record and the file are planned once, with both changed
        for imp_name in source.info.get("importers") or ():
            sid = f"import:{imp_name}"
            if sid in self.by_id:
                self.run_import(self.by_id[sid], reason="tier")
        refs: set[str] = set()
        if self.jobs is not None and hasattr(self.jobs, "files_changed"):
            try:
                refs = self.jobs.files_changed(self.watcher.changed_paths(source, changed))
            except Exception:
                log.exception("live: checking the file dependencies of %s failed", name)
        mount = bool((self.cfg.get("tiers") or {}).get(name, {}).get("mount"))
        if source.id in self._quiet and not (moved or refs):
            # nothing Ben sees moved: a file saved beside the 3D artifacts in the project folder (that tier's root
            # is the folder above the repo), or a seed file whose importer tells the change itself. Not a change
            # in the pane, its history or the chip's "updated" time.
            log.debug("live: %s moved (%s); its status and every result input stayed as they were", name, changed)
            if self.state[source.id]["state"] in ("waiting", "error"):
                self._set(source.id, state="idle", text="", at=now_iso())
                self._source_event(source.id)
            return
        files = [k for keys in changed.values() for k in keys]
        text = W.tier_text(source.label, before.as_dict() if before else None, after.as_dict() if after else {}, files)
        if refs:
            text += f"; {len(refs)} result input(s) changed, re-solving"
        self._set(source.id, state="applied", text=text, at=now_iso())
        self.updated = now_iso()
        self._remember(source.id, text)
        # a tier the line sheet or the map reads, or whose status moved, is worth a toast; a folder that only holds an
        # importer's files (the old hub's seed) is told by that importer
        self._source_event(source.id, toast=bool(moved or refs or mount))

    # ------------------------------------------------------------------------------------------------ imports

    def _resolve(self, source: Source) -> Any:
        from region.cli import imports as I

        imp = self.importers[source.info["importer"]]
        hub_db = source.info.get("hub_db")
        hub_db = Path(hub_db) if hub_db and Path(hub_db).is_file() else None
        overrides = dict(source.info.get("overrides") or {})
        if hub_db is not None:
            overrides.pop("seed", None)
        # each file is read once into a copy, which is both hashed and imported: a save that lands between the
        # hashing and the reading cannot make the recorded sha256 name other bytes than the records came from
        staged = {name: self._stage(name, Path(local)) for name, local in overrides.items()}
        src = I.resolve_sources(imp, overrides=staged, hub_db=hub_db, work=self.work, use_git=False)
        return imp, src

    def _stage(self, name: str, local: Path) -> Path:
        """A copy of one source (a file, or a folder's files) as it is now, under ``work/read/<name>``; only the
        files whose bytes changed are written, and a file gone from the source goes from the copy. A source that is
        not there is returned as it is, so the importer says what is missing."""
        root = self.work / "read" / name
        if local.is_file():
            files = {local.name: local}
        elif local.is_dir():
            files = {p.relative_to(local).as_posix(): p for p in sorted(local.rglob("*")) if p.is_file()}
        else:
            return local
        for rel, path in files.items():
            data = path.read_bytes()
            target = root / rel
            if not target.is_file() or target.read_bytes() != data:
                fsio.write_atomic(target, data)
        if root.is_dir():
            for old in sorted(root.rglob("*")):
                if old.is_file() and old.relative_to(root).as_posix() not in files:
                    fsio.remove(old)
        return root / local.name if local.is_file() else root

    def run_import(
        self, source: Source, *, reason: str = "change", changed: dict[str, list[str]] | None = None
    ) -> dict[str, Any]:
        """One live import of ``source`` (see the module doc). Returns the source's new state."""
        from region.cli import imports as I
        from region.core.protocols import ImportRun

        sid = source.id
        name = source.info["importer"]
        origin = S.ORIGIN_WORDS.get(name, source.label)
        # the old hub commits its own bookkeeping too (a pipeline run's log line by line): when only hub.db moved
        # and its documents did not, nothing is snapshotted or read
        docs = _docs_print(source.info.get("hub_db"))
        if (
            docs is not None
            and changed
            and set(changed) <= {"hub.db"}
            and self._docs_seen.get(sid) == docs
            and self.state[sid]["state"] not in ("error", "waiting", "held")
        ):
            self.counts["skipped"] += 1
            return dict(self.state[sid])
        self._set(sid, state="importing", text="reading", at=now_iso())
        if reason != "start":
            self._source_event(sid)
        t0 = time.perf_counter()
        self._timing = {}
        try:
            imp, src = self._resolve(source)
        except Exception as e:
            if transient(e):
                return self._wait_for(source, changed or {}, reason, _what(e, source))
            return self._fail(sid, f"{source.label}: cannot be read ({plain(e)}); it is tried again when it changes")
        print_ = _fingerprint(src.entries)
        self._timing["read_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        last = I.last_applied(self.store, name)
        if last is not None and _fingerprint(last["sources"]) == print_:
            self.counts["skipped"] += 1
            # after a file that could not be read (half-written, missing, held open) the all-clear is said too
            recovered = self.state[sid].get("failed", False)
            if reason == "start":
                text = "up to date"
            elif recovered:
                text = f"{source.label} can be read again; nothing changed since the last import"
            else:
                text = "saved again with the same contents; nothing to do"
            self._set(sid, state="idle", text=text, at=now_iso(), failed=False)
            if recovered:
                self._remember(sid, text)
            if reason != "start":
                self._source_event(sid, toast=recovered)
            return dict(self.state[sid])
        if self.held.get(name) == print_ and reason != "held":
            self._set(
                sid,
                state="held",
                text=f"you undid the last import from {origin}; it stays undone until its files change again "
                "(Apply takes it anyway)",
                at=now_iso(),
            )
            self._source_event(sid)
            return dict(self.state[sid])
        lock = _import_lock()
        with lock:
            out = self._import_locked(source, imp, src, reason, print_, origin, ImportRun, I, changed or {})
        if docs is not None and out["state"] not in ("error", "waiting"):
            self._docs_seen[sid] = docs
        return out

    def _import_locked(
        self,
        source: Source,
        imp: Any,
        src: Any,
        reason: str,
        print_: str,
        origin: str,
        ImportRun: Any,
        runner: Any,
        changed: dict[str, list[str]],
    ) -> dict[str, Any]:
        sid = source.id
        name = imp.name
        self.counts["imports"] += 1
        t0 = time.perf_counter()
        ids = runner.id_lookup(self.store, imp, ledger_dir=self.ledger_dir)
        try:
            records = list(imp.records(src.local, ids))
        except Exception as e:
            if transient(e):
                return self._wait_for(source, changed, reason, _what(e, source))
            if not isinstance(e, HubError | ValueError | OSError | KeyError | TypeError):
                raise
            return self._fail(
                sid, f"{source.label}: cannot be read yet ({plain(e)}); it is tried again when it changes"
            )

        def make_run() -> Any:
            return ImportRun(
                importer=imp.name, version=imp.version, layer=imp.layer, namespace=imp.namespace, sources=src.entries
            )

        self._timing["records_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        t0 = time.perf_counter()
        dry = self.store.apply_import(make_run(), records, dry_run=True, ids=ids)
        self._timing["dry_run_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        if dry.errors:
            first = dry.errors[0]
            where = f"{first.get('path') or first.get('id') or ''} {first.get('message', '')}".strip()
            return self._fail(sid, f"{source.label}: not imported, {len(dry.errors)} record(s) refused ({where})")
        changes = [c for c in dry.changes if c.get("op") in ("create", "put", "delete")]
        touched = self._sections_of(changes)
        if changes:
            with self._lock:
                for s in touched:
                    self._marks[s] = {"type": "import", "scope": s, "view": self.view.token(), "state": "importing"}
            self._marks_changed()
        try:
            backup = time.monotonic() - self._last_backup >= self.backup_every_s and bool(changes)
            t0 = time.perf_counter()
            rep = self.store.apply_import(make_run(), records, dry_run=False, ids=ids, backup=backup)
            self._timing["apply_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            if backup:
                self._last_backup = time.monotonic()
        except HubError as e:
            return self._fail(sid, f"{source.label}: not imported ({e.detail})")
        finally:
            with self._lock:
                for s in touched:
                    self._marks.pop(s, None)
            self._marks_changed()
        if self.held.pop(name, None) is not None:
            self._save_state()
        if not rep.changeset:
            self.counts["unchanged"] += 1
            text = "up to date" if reason == "start" else f"files changed, but nothing {origin} holds for the hub did"
            self._set(sid, state="idle", text=text, run=rep.run, at=now_iso(), failed=False)
            if reason != "start":
                self._source_event(sid)
            return dict(self.state[sid])
        self.counts["applied"] += 1
        applied = [c for c in rep.changes if c.get("op") in ("create", "put", "delete")]
        records_of = self._records_of([c["id"] for c in applied])
        sections = sorted(
            {r["parent"] for r in records_of.values() if r.get("parent")}
            | {c["id"] for c in applied if c.get("kind") == "section"}
        )
        names = self._names(sections)
        bodies = self._profile_bodies(imp.layer, rep.changeset, [c["id"] for c in applied if c["kind"] == "profile"])
        bens = {lay["slug"] for lay in self.store.layers() if lay.get("tier") in ("main", "scenario", "proposal")}
        review = sum(1 for c in rep.conflicts if c.get("layer") in bens)
        review_other = len(rep.conflicts) - review
        said = W.describe(
            label=source.label,
            origin=origin,
            changes=applied,
            records=records_of,
            names=names,
            bodies=bodies,
            review=review,
            review_other=review_other,
            resolving=self.jobs is not None,
        )
        if reason == "start":
            said.text = "While the hub was stopped: " + said.text
        self.updated = now_iso()
        self._set(
            sid,
            state="review" if rep.conflicts else "applied",
            text=said.text,
            run=rep.run,
            applied_run=rep.run,
            changeset=rep.changeset,
            review=len(rep.conflicts),
            timing_ms=dict(self._timing),
            sections=said.sections,
            counts=dict(rep.counts),
            at=self.updated,
            failed=False,
        )
        self._remember(sid, said.text)
        self._source_event(sid, toast=True, level="warn" if review else "info")
        log.info("live: %s %s (%s)", sid, said.text, self._timing)
        if any(c.get("kind") == "section" and c.get("op") == "create" for c in applied):
            self.watch_all_sections()
        return dict(self.state[sid])

    def _fail(self, sid: str, text: str) -> dict[str, Any]:
        self.counts["errors"] += 1
        self._set(sid, state="error", text=text, at=now_iso(), failed=True)
        self._remember(sid, text)
        self._source_event(sid, toast=True, level="warn")
        return dict(self.state[sid])

    # -------------------------------------------------------------------------------------------- store reads

    def _rows(self, sql: str, ids: list[str]) -> list[Any]:
        out: list[Any] = []
        con = self.store._reader()
        for i in range(0, len(ids), 400):
            chunk = ids[i : i + 400]
            out.extend(con.execute(sql.format(marks=",".join("?" * len(chunk))), chunk).fetchall())
        return out

    def _records_of(self, ids: list[str]) -> dict[str, dict[str, Any]]:
        """``{id: {kind, parent}}`` of changed records (any layer: a tombstone keeps its parent column)."""
        out: dict[str, dict[str, Any]] = {}
        for rid, kind, parent in self._rows("SELECT id, kind, parent FROM rec WHERE id IN ({marks})", sorted(set(ids))):
            cur = out.setdefault(rid, {"kind": kind, "parent": None})
            if parent and not cur["parent"]:
                cur["parent"] = parent
        return out

    def _sections_of(self, changes: list[dict[str, Any]]) -> list[str]:
        rows = self._records_of([c["id"] for c in changes])
        found = {c["id"] for c in changes if c.get("kind") == "section"}
        for c in changes:
            r = rows.get(c["id"])
            if r and r["kind"] in W.SECTION_CHILDREN and r.get("parent"):
                found.add(r["parent"])
        return sorted(found)

    def _names(self, section_ids: list[str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for rid, name in self._rows(
            "SELECT id, name FROM rec WHERE kind = 'section' AND id IN ({marks})", sorted(set(section_ids))
        ):
            if name and rid not in out:
                out[rid] = str(name).replace("_", " ")
        return out

    def _profile_bodies(self, layer: str, changeset: str | None, ids: list[str]) -> dict[str, tuple[Any, Any]]:
        if not changeset or not ids:
            return {}
        out: dict[str, tuple[Any, Any]] = {}
        con = self.store._reader()
        lay = con.execute("SELECT id FROM layer WHERE slug = ?", (layer,)).fetchone()
        if lay is None:
            return {}
        for rid in ids:
            row = con.execute(
                "SELECT version, row FROM rec_hist WHERE layer = ? AND id = ? AND changeset = ?",
                (lay[0], rid, changeset),
            ).fetchone()
            if row is None:
                continue
            after = json.loads(row[1]).get("data")
            prev = con.execute(
                "SELECT row FROM rec_hist WHERE layer = ? AND id = ? AND version = ?", (lay[0], rid, int(row[0]) - 1)
            ).fetchone()
            before = json.loads(prev[0]).get("data") if prev else None
            out[rid] = (before, after)
        return out

    # ---------------------------------------------------------------------------------------- Ben's controls

    def pause(self, by: str = "ben") -> dict[str, Any]:
        """Pause live: keep looking, act on nothing until ``resume``."""
        self.paused = True
        self.watcher.pause()
        self._save_state()
        self._publish("live", self.summary())
        return self.summary()

    def resume(self, by: str = "ben") -> dict[str, Any]:
        """Resume live: act on what changed while paused."""
        self.paused = False
        self.watcher.resume()
        with self._lock:
            deferred, self._deferred = self._deferred, set()
        for sid in sorted(deferred):
            self.enqueue(sid, {}, "change")
        self._save_state()
        self._publish("live", self.summary())
        return self.summary()

    def check(self, sid: str) -> dict[str, Any]:
        """Look at a source now, whatever the watcher saw (the sources pane's Check now)."""
        if sid not in self.by_id:
            raise NotFound(f"no live source {sid!r}")
        self.enqueue(sid, {}, "check")
        return dict(self.state[sid])

    def apply_held(self, sid: str) -> dict[str, Any]:
        """Import a source whose last import Ben undid, as its files are now."""
        source = self.by_id.get(sid)
        if source is None or source.kind != "import":
            raise NotFound(f"no live import source {sid!r}")
        self.held.pop(source.info["importer"], None)
        self._save_state()
        self.enqueue(sid, {}, "held")
        return dict(self.state[sid])

    def undo(self, sid: str, *, by: str = "ben", client: str | None = None) -> dict[str, Any]:
        """Undo this import: revert the source's last live import changeset (see the module doc)."""
        from region.cli import imports as I
        from region.model.imports import mark_reverted

        source = self.by_id.get(sid)
        if source is None or source.kind != "import":
            raise NotFound(f"no live import source {sid!r}")
        with self._busy:
            # read under the worker's lock: an import of the same source that is running now lands first, and its
            # changeset is the one undone (never an older one under it)
            with self._lock:
                st = dict(self.state[sid])
            cs, run = st.get("changeset"), st.get("applied_run") or st.get("run")
            if not cs:
                raise Conflict(f"{source.label} has no import to undo", reason="revert")
            self.store.revert(cs, by=by, client=client)
            if run is not None:
                mark_reverted(self.store, int(run), by)
                rep = self.store.import_run(int(run))
                self.held[source.info["importer"]] = _fingerprint(rep.get("sources") or {})
                self._save_state()
        last = I.last_applied(self.store, source.info["importer"])
        text = f"Undone: {st['text']}" if st.get("text") else "Undone"
        self.updated = now_iso()
        self._set(
            sid,
            state="held",
            text=text + " (held until its files change again)",
            changeset=None,
            applied_run=None,
            review=0,
            at=self.updated,
            run=last["run"] if last else None,
        )
        self._remember(sid, text)
        self._source_event(sid, toast=True)
        return dict(self.state[sid])


def plain(e: BaseException) -> str:
    """A read failure in Ben's words: "Line_3.json is missing", "Line_3.json is not complete JSON (line 1, column
    83798)"; anything else as its type and message."""
    name = getattr(e, "filename", None)
    if isinstance(e, FileNotFoundError) and name:
        return f"{Path(str(name)).name} is missing"
    if isinstance(e, json.JSONDecodeError):
        return f"a file is not complete JSON (line {e.lineno}, column {e.colno})"
    if isinstance(e, HubError):
        return str(e.detail)
    return f"{type(e).__name__}: {e}"


def _docs_print(db: Any) -> tuple[Any, ...] | None:
    """A cheap print of the old hub's documents (count, versions, last save) read from its live database on a
    read-only connection, or ``None`` when it cannot be read now. The old hub (``hub/store.py``, its only writer of
    documents) bumps a document's version and time on every save that changes it, so an equal print means its
    documents are as they were. Check now in the Sources pane always takes a snapshot."""
    if not db or not Path(db).is_file():
        return None
    try:
        con = sqlite3.connect(f"{Path(db).resolve().as_uri()}?mode=ro", uri=True, timeout=0.2)
        try:
            row = con.execute("SELECT count(*), total(version), max(updated), total(length(data)) FROM docs").fetchone()
        finally:
            con.close()
    except sqlite3.Error:
        return None
    return tuple(row) if row else None


def _what(e: BaseException, source: Source) -> str:
    """The file a read failure names ("Line_3.json"), for the waiting text."""
    name = getattr(e, "filename", None)
    return Path(str(name)).name if name else f"a file of {source.label}"


_lock_fallback = threading.Lock()


def _import_lock() -> Any:
    """The server's one-import-at-a-time lock (``POST /imports`` takes it too)."""
    try:
        from region.api.imports import _one_at_a_time

        return _one_at_a_time
    except Exception:
        return _lock_fallback


__all__ = ["Live", "SOLVE_JOB", "STATE_FILE"]
