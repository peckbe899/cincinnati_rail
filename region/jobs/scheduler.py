"""The job scheduler over ``cache.db`` (decision 9.19; section 6).

    sched = Scheduler(store, cache_path, engine, threads=4, processes=2).start()
    sched.watch_goal("profiles.solve_section", section_id, View("try"), priority=1)
    ...
    sched.stop()

**Flow.** ``submit`` and ``watch_goal`` plan the job at once (``plan.Planner``: reads only, every read a ref with its
content hash) and compute the key; a plan kept for the same job is used again while nothing it read has moved, so two
tabs asking for one job plan it once (a watch answers as a submit does and needs none of its own). A key with an ok
result is a hit: the goal's ``latest_key`` moves to it and a ``result`` event goes out. Otherwise the goal wants the
key and one job is queued for it, unless one is already queued or running for the same ``(type, key)`` (equal
content in two views shares the work). A plan that ``need``s an upstream result that does not exist yet queues a
waiting job (``key`` NULL) and the upstream job; when the upstream commits, the waiting job is planned again.

**Coalescing and supersession.** A goal has at most one pending job: when a goal comes to want a new key, its
queued job for an older key is cancelled, and a running one is cancelled by its token (a process job is killed
1 s later; a thread job that ignores the token is abandoned and its answer dropped). A job still wanted by another
view's goal is left alone.

**Hosts and priorities.** Queued jobs run in priority order (0 focused pane, 1 open panes, 5 goals, 9 maintenance),
oldest first within a priority, on the host their type names (``hosts``). Each type has a timeout.

**The foreground.** A live import holds the foreground (``foreground()``) while it runs, and so do a record write
over the API and the reads a pane makes to follow one (``region.api.context.foreground``). While one does, and until
the invalidator has taken in what it wrote, the background (priority 2 and up: a sheet's run chain, the goals of
every line) waits: no such job starts, and its planning stops at the next step of a plan (``Planner.pause``). No
background job starts either while a job at the panes' priority (0 or 1) is queued or running. The invalidator, the
job commits and the dispatcher never plan background work themselves: they hand it to the background planner thread,
which takes the most urgent first. So the import and the focused section's solve always come first. A background
plan waits ``BACKGROUND_WAIT_S`` at most in all (once its wait has run out it goes on), a job the dispatcher handed
to the background planner is not picked again until the planner has dealt with it, and a restore that takes the
outbox back forgets the seq the invalidator was to reach.

**Commit.** ``run`` gets only what ``plan`` returned. After it, the scheduler plans again and compares keys: an
unchanged key commits the result, its dependencies, blobs and issues in one cache.db transaction (blobs written
first); a changed key stores the result as ``stale`` and re-queues the job with the new key. Every other goal that
wants the key (another view sharing the work) is planned again too: the result commits while any of them still plans
to it, and each goal whose content moved gets the work for its new key queued. Job types with
``effect = "truth"`` (the seed jobs) have their ``apply`` called after the key check and before the commit; no
other code path of the scheduler writes to the store.

**Invalidation.** A thread tails the store's outbox (``Store.events_since``) past ``cursor('invalidator')``, looks
the changed refs up in ``result_dep`` (rows are written when a key is first wanted, so pending keys are covered
too), and re-plans the watched goals that want or hold an affected key. An upstream result whose ``output_hash``
changed re-plans its dependants (``job:`` refs); an unchanged one does not (early cutoff). Through the store's
``epoch``, ``last_seq`` and ``min_seq`` (``Store`` protocol members; a store without them only loses these checks), a
new epoch (a restore, even one followed by new writes before the next poll), an outbox that went backwards or one
pruned past the cursor re-plans every watched goal, because what changed is unknown. The epoch is remembered in
memory, so a restore made while no scheduler runs is caught by the other two checks only.

**Leases.** A running job holds a lease (30 s) renewed by a heartbeat (every 5 s) while its scheduler is running or
committing it. A lease that expires (its scheduler died, or could not record the job's end) re-queues the job, at
most ``max_requeue`` (2) times, then the job fails.

**Events.** ``job`` and ``result`` payloads of ``region.core.events`` go to every subscriber (``subscribe`` or
``on_event``); the server forwards them over SSE. They are ephemeral and never stored.
"""

from __future__ import annotations

import collections
import contextlib
import heapq
import itertools
import json
import logging
import threading
import time
import traceback
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

from region.core import fsio, ids, paths
from region.core.errors import EngineUnavailable, HubError, NotFound
from region.core.log import log_context
from region.core.protocols import EngineClient, Output, Store, parse_ref, ref_job
from region.core.view import View

from . import goals
from .cache import Cache, decode_array, encode_output, now_iso, now_s, set_current
from .hosts import EngineHost, Failure, InlineHost, ProcessHost, Task, ThreadHost, as_output
from .plan import PARAM_KIND, ParamResolver, Plan, Planner, iter_deps, query_prefix
from .registry import Registry, default_registry, module_of

if TYPE_CHECKING:
    import numpy as np

log = logging.getLogger("region.jobs")

ACTIVE = ("queued", "running")
BACKGROUND_WAIT_S = 10.0
"""The longest the background waits for the foreground at a time (a foreground that never frees cannot starve it)."""
FINAL = ("done", "failed", "cancelled")
EventSink = Callable[[str, dict[str, Any]], None]


def changed_ranges(old: dict[str, np.ndarray], new: dict[str, np.ndarray], c0: float, step: float) -> list[list[float]]:
    """Chainage ranges ``[c0, c1]`` where the 1-D arrays of two results differ, on a grid ``c0 + i * step``.

    An array present in only one result, or with another length, makes the whole grid changed. NaN equals NaN.
    """
    import numpy as np

    n = None
    for a in new.values():
        if getattr(a, "ndim", 0) == 1:
            n = max(n or 0, len(a))
    if n is None or n == 0:
        return []
    whole = [[float(c0), float(c0 + (n - 1) * step)]]
    if not old:
        return whole
    mask = np.zeros(n, dtype=bool)
    for name in set(old) | set(new):
        a, b = old.get(name), new.get(name)
        if a is None or b is None or a.shape != b.shape:
            if (a is not None and a.ndim != 1) or (b is not None and b.ndim != 1):
                continue
            return whole
        if a.ndim != 1:
            continue
        if a.dtype.kind in "fc" and b.dtype.kind in "fc":
            diff = ~((a == b) | (np.isnan(a) & np.isnan(b)))
        else:
            diff = a != b
        mask[: len(diff)] |= diff
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    out: list[list[float]] = []
    start = prev = int(idx[0])
    for i in idx[1:]:
        i = int(i)
        if i != prev + 1:
            out.append([float(c0 + start * step), float(c0 + prev * step)])
            start = i
        prev = i
    out.append([float(c0 + start * step), float(c0 + prev * step)])
    return out


@dataclass
class _Run:
    job_id: str
    type: str
    scope: str
    view: str
    key: str
    host: str
    plan: Plan
    task: Task
    t0: float
    deadline: float
    expired: bool = False
    last_progress: float = 0.0


class Scheduler:
    """``region.core.protocols.Scheduler`` over one ``cache.db``. See the module doc."""

    def __init__(
        self,
        store: Store,
        cache_path: Path,
        engine: EngineClient | None,
        *,
        threads: int = 4,
        processes: int = 2,
        registry: Registry | None = None,
        params: ParamResolver | None = None,
        on_event: EventSink | None = None,
        blobs_dir: Path | None = None,
        engine_slots: int | None = None,
        lease_s: float | None = None,
        heartbeat_s: float | None = None,
        max_requeue: int | None = None,
        poll_s: float = 0.5,
        kill_grace_s: float = 1.0,
        max_tasks_per_child: int = 50,
    ) -> None:
        cfg = paths.config()
        jobs_cfg = cfg.get("jobs") or {}
        pools = cfg.get("pools") or {}
        self.store = store
        self.engine = engine
        self.cache = Cache(Path(cache_path), blobs_dir=blobs_dir)
        self.registry = registry if registry is not None else default_registry()
        self.owner = ids.new()
        self.lease_s = float(lease_s if lease_s is not None else jobs_cfg.get("lease_s", 30))
        self.heartbeat_s = float(heartbeat_s if heartbeat_s is not None else jobs_cfg.get("heartbeat_s", 5))
        self.max_requeue = int(max_requeue if max_requeue is not None else jobs_cfg.get("max_requeue", 2))
        self.poll_s = float(poll_s)
        self.kill_grace_s = float(kill_grace_s)
        self.hosts: dict[str, Any] = {
            "inline": InlineHost(),
            "thread": ThreadHost(threads),
            "process": ProcessHost(processes, max_tasks_per_child=max_tasks_per_child, kill_grace_s=kill_grace_s),
            "engine": EngineHost(engine_slots if engine_slots is not None else int(pools.get("engine", 2)), engine),
        }
        self.planner = Planner(
            store,
            registry=self.registry,
            file_hash=self.cache.file_sha256,
            upstream_output=self._ok_output_hash,
            engine_info=self._engine_info,
            params=params,
        )
        self._lock = threading.RLock()
        self._plans: dict[str, Plan] = {}
        self._running: dict[str, _Run] = {}
        # jobs whose run ended and whose result is being committed here (re-plan, apply, the cache transaction)
        self._finishing: set[str] = set()
        self._events: list[tuple[str, dict[str, Any]]] = []
        self._listeners: list[EventSink] = [on_event] if on_event is not None else []
        self._hello: tuple[str, dict[str, Any]] | None = None
        self._epoch: str | None = None  # the truth DB's epoch as last seen by the invalidator
        self._wake = threading.Event()
        self._inval_wake = threading.Event()
        self._stopping = threading.Event()
        self._threads: list[threading.Thread] = []
        self._started = False
        self._closed = False
        # the foreground (see the module doc): live imports holding it, the threads that do, the store's seq when the
        # last one ended (the invalidator must pass it), and since when the dispatcher has held the background back
        self._fg_lock = threading.Lock()
        self._fg_holds = 0
        self._fg_threads: collections.Counter[int] = collections.Counter()
        self._fg_seq = 0
        self._fg_busy_since: float | None = None
        # background work handed to the background planner: a heap of (priority, n, item)
        self._later: list[tuple[int, int, tuple]] = []
        self._later_n = itertools.count()
        self._later_cond = threading.Condition()
        self._later_busy = False
        self._later_thread: threading.Thread | None = None
        # queued jobs the dispatcher handed to the background planner: not picked again until it has dealt with them
        self._handed: set[str] = set()
        self._bg = threading.local()
        self.planner.pause = self._pause

    # ============================================================================================== lifecycle

    def start(self) -> Scheduler:
        """Sweep the blob folder, then start the dispatcher, invalidator and monitor threads."""
        if self._started:
            return self
        self._started = True
        swept = self.cache.sweep()
        if any(swept.values()):
            log.info("cache sweep: %s", swept)
        self._prune_deps()
        set_current(self.cache)
        for name, target in (
            ("jobs-dispatch", self._dispatch_loop),
            ("jobs-invalidate", self._invalidate_loop),
            ("jobs-monitor", self._monitor_loop),
            ("jobs-background", self._later_loop),
        ):
            t = threading.Thread(target=target, name=name, daemon=True)
            if name == "jobs-background":
                self._later_thread = t
            t.start()
            self._threads.append(t)
        rows = self.cache.query("SELECT * FROM job WHERE state = 'queued' AND key IS NULL")
        self._drain([("replan_job", dict(r)) for r in rows])
        # a watched goal is planned again at start: a pull that changed the code (its hash), the engine source
        # (engine_build) or a file it reads moves its key though no record changed (planning only, so cheap)
        try:
            self.replan_all()
        except Exception:
            log.exception("re-planning the watched goals at start failed; they are re-planned on their next change")
        self._wake.set()
        self._inval_wake.set()
        return self

    def stop(self, timeout: float = 10.0) -> None:
        """Stop the threads, cancel running jobs and put them back in the queue for the next start."""
        if self._closed:
            return
        self._stopping.set()
        self._wake.set()
        self._inval_wake.set()
        with self._later_cond:
            self._later_cond.notify_all()
        for t in self._threads:
            t.join(timeout)
        with self._lock:
            runs = list(self._running.values())
        for run in runs:
            run.task.cancel.set()
        self.hosts["process"].close()
        deadline = time.monotonic() + min(timeout, 2.0)
        while time.monotonic() < deadline:
            with self._lock:
                if not any(r.host != "process" for r in self._running.values()):
                    break
            time.sleep(0.02)
        for name in ("thread", "engine"):
            self.hosts[name].close()
        with self._lock:
            self._closed = True
            with self.cache.tx() as con:
                con.execute(
                    "UPDATE job SET state = 'queued', reason = 'restart', lease_owner = NULL, lease_until = NULL, "
                    "heartbeat = NULL, pid = NULL, progress = 0, msg = 'requeued at stop' "
                    "WHERE state = 'running' AND lease_owner = ?",
                    (self.owner,),
                )
            self._running.clear()
            self._plans.clear()
        with contextlib.suppress(Exception):
            from . import cache as cache_mod

            if cache_mod._current is self.cache:
                set_current(None)
        self.cache.close()

    def __enter__(self) -> Scheduler:
        return self.start()

    def __exit__(self, *exc: Any) -> None:
        self.stop()

    # ================================================================================================= events

    def subscribe(self, fn: EventSink) -> Callable[[], None]:
        """Call ``fn(event_type, payload)`` for every ``job`` and ``result`` event; returns the unsubscribe."""
        with self._lock:
            self._listeners.append(fn)

        def unsubscribe() -> None:
            with self._lock, contextlib.suppress(ValueError):
                self._listeners.remove(fn)

        return unsubscribe

    def _emit(self, kind: str, payload: dict[str, Any]) -> None:
        self._events.append((kind, payload))

    def _flush(self) -> None:
        with self._lock:
            events, self._events = self._events, []
            listeners = list(self._listeners)
        for kind, payload in events:
            for fn in listeners:
                try:
                    fn(kind, payload)
                except Exception:
                    log.exception("a job event subscriber failed")

    def _job_event(self, row: dict[str, Any], **over: Any) -> None:
        data = {**row, **over}
        payload: dict[str, Any] = {
            "id": data["id"],
            "type": data["type"],
            "scope": data["scope"],
            "state": data["state"],
            "progress": float(data.get("progress") or 0.0),
            "msg": data.get("msg") or "",
            "view": data["view"],
        }
        if data.get("key"):
            payload["key"] = data["key"]
        if data.get("error"):
            payload["error"] = str(data["error"]).strip().splitlines()[-1][:500]
        self._emit("job", payload)

    def _result_event(self, type: str, scope: str, view: str, key: str, status: str, prev: str | None) -> None:
        changed: list[list[float]] = []
        if status == "ok":
            try:
                changed = self._changed(prev, key)
            except Exception:
                log.exception("changed ranges for %s failed", key)
        self._emit(
            "result", {"key": key, "type": type, "scope": scope, "view": view, "status": status, "changed": changed}
        )

    def _changed(self, prev: str | None, key: str) -> list[list[float]]:
        res = self.cache.result_row(key)
        grid = (res or {}).get("meta", {}).get("grid") if res else None
        if not isinstance(grid, dict):
            return []
        step = grid.get("step_m", grid.get("step"))
        if not isinstance(step, (int, float)) or step <= 0:
            return []
        old = self.cache.read_arrays(prev) if prev else {}
        return changed_ranges(old, self.cache.read_arrays(key), float(grid.get("c0", 0.0)), float(step))

    # ============================================================================================ public API

    def submit(self, type: str, scope: str, view: View, priority: int = 1) -> dict[str, Any]:
        """Plan now; return ``{"key", "state", "job"}`` with ``state`` ``hit``, ``queued`` or ``running``."""
        self.registry.get(type)
        with self._background(int(priority) > self.PANE_PRIORITY):
            plan = self.planner.plan(type, scope, view, reuse=True)
        with self._lock, self.cache.tx() as con:
            goals.upsert(con, type, scope, view.token(), priority=priority)
        out = self._drain([("want", plan, int(priority), "submit", None)])
        return out or {"key": plan.key, "state": "queued", "job": None}

    def result(self, type: str, scope: str, view: View) -> str | None:
        """The key of the ok result of ``(type, scope, view)`` for its inputs as they are now, or ``None`` while that
        result is not computed. The goal is planned again on every read, so an edit, an import, new code or an
        eviction is never answered with an older result as if it were current; when the inputs cannot be planned
        (the engine down, the scope gone) the answer is ``None`` too."""
        try:
            with self._background(int(getattr(self.registry.get(type), "priority", 0)) > self.PANE_PRIORITY):
                plan = self.planner.plan(type, scope, view, reuse=True)
        except HubError:
            return None
        key = getattr(plan, "key", None)
        if not key:
            return None
        row = self.cache.one("SELECT 1 FROM result WHERE key = ? AND status = 'ok'", (key,))
        return key if row is not None else None

    def watch_goal(
        self,
        type: str,
        scope: str,
        view: View,
        priority: int = 5,
        ttl_s: float | None = None,
        *,
        pinned: bool | None = None,
    ) -> dict[str, Any]:
        """Keep ``(type, scope, view)`` fresh until ``ttl_s`` from now (for ever when ``None``). Plans it now and
        returns what ``submit`` would (``{"key", "state", "job"}``), so a watch needs no submit of its own."""
        self.registry.get(type)
        expires = None if ttl_s is None else now_s() + float(ttl_s)
        token = view.token()
        with self._lock, self.cache.tx() as con:
            goals.upsert(con, type, scope, token, priority=priority, watch=True, expires=expires, pinned=pinned)
        try:
            with self._background(int(priority) > self.PANE_PRIORITY):
                plan = self.planner.plan(type, scope, view, reuse=True)
        except Exception as e:
            with self._lock, self.cache.tx() as con:
                goals.set_state(con, type, scope, token, state="error", error=str(e)[:2000])
            raise
        out = self._drain([("want", plan, int(priority), "goal", None)])
        return out or {"key": plan.key, "state": "queued", "job": None}

    def ensure_watched(self, type: str, scope: str, view: View, priority: int = 5) -> bool:
        """Watch ``(type, scope, view)`` for ever unless it is watched already (a pane's priority and the goal's
        answer are left as they are). The live hub's background goals. Returns whether a watch was added."""
        self.registry.get(type)
        with self._lock, self.cache.tx() as con:
            g = goals.get(con, type, scope, view.token())
            if g is not None and g["watch"] and (g["expires"] is None or g["expires"] > now_s()):
                return False
        self.watch_goal(type, scope, view, priority=priority, ttl_s=None)
        return True

    def set_priority(self, type: str, scope: str, view: View, priority: int) -> None:
        """Make a goal (and its queued or running job) this urgent: 0 for the pane in focus, 1 for open panes, 5 for
        the background. Unlike ``watch_goal`` this lowers a priority too, so a pane that loses the focus hands it
        back; a goal nobody asked for is left alone."""
        token = view.token()
        with self._lock, self.cache.tx() as con:
            g = goals.get(con, type, scope, token)
            if g is None:
                return
            con.execute(
                "UPDATE goal SET priority = ?, updated = ? WHERE type = ? AND scope = ? AND view = ?",
                (int(priority), now_iso(), type, scope, token),
            )
            if g.get("want_key"):
                con.execute(
                    "UPDATE job SET priority = ? WHERE type = ? AND key = ? AND state = 'queued'",
                    (int(priority), type, g["want_key"]),
                )
            con.execute(
                "UPDATE job SET priority = ? WHERE type = ? AND scope = ? AND view = ? AND state = 'queued' "
                "AND key IS NULL",
                (int(priority), type, scope, token),
            )
        self._wake.set()

    def pending(self) -> list[dict[str, Any]]:
        """Watched goals whose answer is being worked on: ``[{"type", "scope", "view", "state", "priority"}]``
        (the per-section pending marks of the live hub)."""
        with self._lock, self.cache.tx() as con:
            return goals.pending(con)

    def unwatch(self, type: str, scope: str, view: View) -> None:
        """Stop keeping a goal fresh (its latest result stays)."""
        with self._lock, self.cache.tx() as con:
            con.execute(
                "UPDATE goal SET watch = 0, updated = ? WHERE type = ? AND scope = ? AND view = ?",
                (now_iso(), type, scope, view.token()),
            )

    def pin(self, type: str, scope: str, view: View, on: bool = True) -> None:
        """Pin a goal: eviction spares its results."""
        with self._lock, self.cache.tx() as con:
            goals.upsert(con, type, scope, view.token(), priority=9, pinned=on)

    def cancel(self, job_id: str) -> None:
        """Cancel a queued or running job (a running process job is killed after 1 s)."""
        with self._lock:
            row = self._row(job_id)
            if row is None:
                raise NotFound(f"no job {job_id}")
            if row["state"] in ACTIVE:
                with self.cache.tx() as con:
                    self._cancel_row(con, row, "cancelled")
                    if row["key"]:
                        con.execute(
                            "UPDATE goal SET state = 'cancelled', updated = ? WHERE type = ? AND want_key = ?",
                            (now_iso(), row["type"], row["key"]),
                        )
        self._flush()

    def jobs(self, active: bool = True, limit: int = 500) -> list[dict[str, Any]]:
        """Jobs, newest first: ``{"id", "type", "scope", "view", "state", "progress", "msg", "key", ...}``."""
        where = "WHERE state IN ('queued', 'running')" if active else ""
        rows = self.cache.query(f"SELECT * FROM job {where} ORDER BY id DESC LIMIT ?", (int(limit),))
        return [self._job_dict(r) for r in rows]

    def job(self, job_id: str) -> dict[str, Any]:
        row = self._row(job_id)
        if row is None:
            raise NotFound(f"no job {job_id}")
        return self._job_dict(row)

    def job_log(self, job_id: str) -> list[dict[str, Any]]:
        """The log lines of a job, oldest first."""
        if self._row(job_id) is None:
            raise NotFound(f"no job {job_id}")
        rows = self.cache.query("SELECT at, level, msg FROM job_log WHERE job = ? ORDER BY seq", (job_id,))
        return [dict(r) for r in rows]

    def result_meta(self, key: str) -> dict[str, Any]:
        """The result row of ``key`` with its issues and dependencies (``/results/{key}``)."""
        return self.cache.result_meta(key)

    def read_array(self, key: str, name: str) -> np.ndarray:
        return self.cache.read_array(key, name)

    def array_bytes(self, key: str, name: str) -> tuple[bytes, str, list[int]]:
        """``(bytes, dtype, shape)`` for ``/results/{key}/a/{name}``."""
        return self.cache.array_bytes(key, name)

    def read_blob(self, key: str, name: str) -> bytes:
        return self.cache.read_blob(key, name)

    def notify(self) -> None:
        """Wake the invalidator now (the server calls this after a write; it also polls every ``poll_s``)."""
        self._inval_wake.set()

    def invalidate(self, refs: Iterable[str]) -> None:
        """Re-plan the watched goals that depend on ``refs`` (``file:`` refs after a file changed, for example)."""
        refs = set(refs)
        params = any(parse_ref(r)[0] == "param" for r in refs)
        self._drain(self._affected(refs, set(), set(), params), defer=True)

    def replan_all(self, *, defer: bool = False) -> None:
        """Re-plan every watched goal (after the outbox was reset, a restore or a new server epoch). With ``defer``
        (the invalidator) the background goals go to the background planner."""
        with self._lock, self.cache.tx() as con:
            found = goals.watched(con)
        self._drain([("replan", g, "resync") for g in found], defer=defer)

    def evict(self, max_bytes: int) -> dict[str, int]:
        """LRU eviction down to ``max_bytes`` of blobs, sparing pinned goals; then drop dependency rows of keys
        nothing holds."""
        with self._lock:
            out = self.cache.evict(max_bytes)
            self._prune_deps()
        return out

    def wait_idle(self, timeout: float = 30.0) -> bool:
        """Wait until the outbox is followed to its end and no job is queued or running (tests, CLI)."""
        deadline = time.monotonic() + timeout
        calm = 0
        while time.monotonic() < deadline:
            if self._idle():
                calm += 1
                if calm >= 3:
                    return True
            else:
                calm = 0
                self._inval_wake.set()
                self._wake.set()
            time.sleep(0.02)
        return False

    def wait_job(self, job_id: str, timeout: float = 30.0) -> dict[str, Any]:
        """Wait until a job is done, failed or cancelled; return it."""
        deadline = time.monotonic() + timeout
        while True:
            job = self.job(job_id)
            if job["state"] in FINAL or time.monotonic() >= deadline:
                return job
            time.sleep(0.02)

    # ============================================================================================ internals

    def _engine_info(self) -> tuple[str, dict[str, Any]]:
        if self.engine is None:
            raise EngineUnavailable("no engine is configured for this hub", reason="closed")
        if self._hello is None:
            hello = self.engine.hello()
            self._hello = (str(hello["engine_build"]), dict(hello.get("contracts") or {}))
        return self._hello

    def _ok_output_hash(self, key: str) -> str | None:
        row = self.cache.one("SELECT output_hash FROM result WHERE key = ? AND status = 'ok'", (key,))
        return row[0] if row is not None else None

    def _row(self, job_id: str) -> dict[str, Any] | None:
        row = self.cache.one("SELECT * FROM job WHERE id = ?", (job_id,))
        return dict(row) if row is not None else None

    @staticmethod
    def _job_dict(row: Any) -> dict[str, Any]:
        d = dict(row)
        d["waiting"] = json.loads(d["waiting"]) if d.get("waiting") else []
        return d

    def _log(self, con: Any, job_id: str, level: str, msg: str) -> None:
        con.execute(
            "INSERT INTO job_log (job, at, level, msg) VALUES (?, ?, ?, ?)", (job_id, now_iso(), level, msg[:20000])
        )

    def _idle(self) -> bool:
        with self._later_cond:
            if self._later or self._later_busy:
                return False
        cursor = self.cache.cursor("invalidator") or 0
        try:
            if self.store.events_since(cursor, 1):
                return False
        except Exception:
            return False
        n = self.cache.one("SELECT COUNT(*) FROM job WHERE state IN ('queued', 'running')")[0]
        return n == 0

    def _prune_deps(self) -> None:
        with self.cache.tx() as con:
            con.execute(
                "DELETE FROM result_dep WHERE key NOT IN (SELECT key FROM result) "
                "AND key NOT IN (SELECT key FROM job WHERE key IS NOT NULL AND state IN ('queued', 'running')) "
                "AND key NOT IN (SELECT want_key FROM goal WHERE want_key IS NOT NULL) "
                "AND key NOT IN (SELECT latest_key FROM goal WHERE latest_key IS NOT NULL)"
            )

    # ---------------------------------------------------------------------------------------------- the work

    def _drain(self, items: list[tuple], *, defer: bool = False, own: int = 0) -> dict[str, Any] | None:
        """Process a work list of plans to want, upstreams to plan, results that became ready and goals to
        re-plan. Plans run outside the lock; cache changes inside it. Returns the first ``want``'s answer.

        Background items (priority 2 and up) are planned in the background mode, which stops while the foreground
        is busy; with ``defer`` they are handed to the background planner instead (all but the first ``own``
        items): the invalidator, the job commits and the dispatcher never plan background work themselves."""
        work = collections.deque(items)
        first: dict[str, Any] | None = None
        first_set = False
        n = 0
        while work:
            item = work.popleft()
            kind = item[0]
            n += 1
            pr = self._item_priority(item)
            if pr > self.PANE_PRIORITY and defer and n > own and self._later_on():
                self._defer(pr, item)
                continue
            try:
                with self._background(pr > self.PANE_PRIORITY):
                    if kind == "want":
                        _, plan, priority, reason, reuse = item
                        with self._lock:
                            if self._closed:
                                break
                            out, more = self._want(plan, priority, reason, reuse)
                        if not first_set:
                            first, first_set = out, True
                        work.extend(more)
                    else:
                        work.extend(self._work_item(item))
            except Exception:
                log.exception("job work item %s failed", kind)
        self._flush()
        self._wake.set()
        return first

    def _work_item(self, item: tuple) -> list[tuple]:
        """One ``upstream``, ``ready``, ``upfailed``, ``replan`` or ``replan_job`` item of ``_drain``; returns the
        items it leads to."""
        kind = item[0]
        if kind == "upstream":
            _, utype, uscope, view, priority, down = item
            try:
                up = self.planner.plan(utype, uscope, view)
            except Exception as e:
                return [("upfailed", utype, uscope, view, f"planning {utype}/{uscope} failed: {e}")]
            with self._lock, self.cache.tx() as con:
                dgoal = goals.get(con, down[0], down[1], down[2]) or {}
                watch = bool(dgoal.get("watch"))
                goals.upsert(
                    con,
                    utype,
                    uscope,
                    view.token(),
                    priority=priority,
                    watch=True if watch else None,
                    expires=dgoal.get("expires") if watch else False,
                    auto=True,
                )
            return [("want", up, priority, "upstream", None)]
        if kind == "ready":
            _, rtype, rscope, changed, *rest = item
            return self._ready(rtype, rscope, changed, rest[0] if rest else None)
        if kind == "upfailed":
            _, utype, uscope, view, text = item
            self._fail_waiting(ref_job(utype, uscope), view.token() if view else None, text)
            return []
        if kind == "replan":
            _, g, reason = item
            view = View.parse(g["view"])
            try:
                plan = self.planner.plan(g["type"], g["scope"], view)
            except Exception as e:
                log.warning("re-planning %s/%s in %s failed: %s", g["type"], g["scope"], g["view"], e)
                with self._lock, self.cache.tx() as con:
                    goals.set_state(con, g["type"], g["scope"], g["view"], state="error", error=str(e)[:2000])
                return []
            return [("want", plan, int(g["priority"]), reason, None)]
        if kind == "replan_job":
            _, row = item
            try:
                plan = self.planner.plan(row["type"], row["scope"], View.parse(row["view"]))
            except Exception as e:
                self._fail_row(row["id"], f"planning failed: {e}", traceback.format_exc())
                return []
            return [("want", plan, int(row["priority"]), "upstream", row["id"])]
        return []

    @staticmethod
    def _item_priority(item: tuple) -> int:
        """The priority a work item is done at (a result that became ready, or a failure, at once)."""
        kind = item[0]
        if kind == "want":
            return int(item[2])
        if kind == "upstream":
            return int(item[4])
        if kind == "replan":
            return int(item[1]["priority"])
        if kind == "replan_job":
            return int(item[1]["priority"])
        return 0

    # ------------------------------------------------------------------------------------------ the foreground

    @contextlib.contextmanager
    def foreground(self) -> Iterator[None]:
        """Hold the foreground while a live import runs (see the module doc): the background waits till it ends,
        the invalidator has taken in what it wrote, and the panes' jobs it led to have run."""
        me = threading.get_ident()
        with self._fg_lock:
            self._fg_holds += 1
            self._fg_threads[me] += 1
        try:
            yield
        finally:
            seq = 0
            last_seq = getattr(self.store, "last_seq", None)
            if callable(last_seq):
                with contextlib.suppress(Exception):
                    seq = int(last_seq())
            with self._fg_lock:
                self._fg_holds -= 1
                self._fg_threads[me] -= 1
                if self._fg_threads[me] <= 0:
                    del self._fg_threads[me]
                self._fg_seq = max(self._fg_seq, seq)
            self._inval_wake.set()
            self._wake.set()

    def _fg_rewound(self, last: int) -> None:
        """The outbox went back to ``last`` (a restore): the seq the last import ended at may never come again, so
        the background no longer waits for the invalidator to reach it."""
        with self._fg_lock:
            if self._fg_seq > last:
                self._fg_seq = 0

    def _foreground_busy(self, *, jobs: bool = True) -> bool:
        """Whether the background waits now: a live import holds the foreground, the invalidator has not yet taken
        in what the last one wrote, or (``jobs``: for starting a job) a job at the panes' priority (0 or 1) is queued
        or running."""
        with self._fg_lock:
            if self._fg_holds:
                return True
            seq = self._fg_seq
        if seq and self._started and not self._stopping.is_set() and int(self.cache.cursor("invalidator") or 0) < seq:
            return True
        if not jobs:
            return False
        row = self.cache.one(
            "SELECT 1 FROM job WHERE state IN ('queued', 'running') AND key IS NOT NULL AND priority <= ? LIMIT 1",
            (self.PANE_PRIORITY,),
        )
        return row is not None

    def _background_may_start(self) -> bool:
        """Whether the dispatcher may start a background job now: the foreground is free, or it has been busy for
        ``BACKGROUND_WAIT_S`` on end (then one starts, and the wait begins again)."""
        if not self._foreground_busy():
            self._fg_busy_since = None
            return True
        now = time.monotonic()
        if self._fg_busy_since is None:
            self._fg_busy_since = now
            return False
        if now - self._fg_busy_since >= BACKGROUND_WAIT_S:
            self._fg_busy_since = now
            return True
        return False

    def _wait_foreground(self) -> bool:
        """Wait until no import holds the foreground and the invalidator has taken in what it wrote (at most
        ``BACKGROUND_WAIT_S``). Planning does not wait for the panes' jobs: they run on hosts it does not take.
        Returns whether the foreground is free (False: the wait ran out)."""
        deadline = time.monotonic() + BACKGROUND_WAIT_S
        while not self._stopping.is_set() and self._foreground_busy(jobs=False):
            if time.monotonic() >= deadline:
                return False
            self._stopping.wait(0.02)
        return True

    @contextlib.contextmanager
    def _background(self, on: bool) -> Iterator[None]:
        """Plans made in this block are background work (they stop while the foreground is busy). A block whose wait
        ran out once goes on without waiting again: it waits ``BACKGROUND_WAIT_S`` at most, not that at each step
        (a plan that holds a lock the foreground's own work needs would otherwise keep the foreground busy too)."""
        was, gave_up = getattr(self._bg, "on", False), getattr(self._bg, "gave_up", False)
        self._bg.on, self._bg.gave_up = on, False
        try:
            yield
        finally:
            self._bg.on, self._bg.gave_up = was, gave_up

    def _pause(self, held: tuple[str, ...]) -> None:
        """``Planner.pause``: background planning waits here for the foreground, unless this thread holds it, or holds
        the plan lock of a type the panes plan (a pane's plan would wait for that lock)."""
        if not getattr(self._bg, "on", False) or getattr(self._bg, "gave_up", False):
            return
        with self._fg_lock:
            if threading.get_ident() in self._fg_threads:
                return
        for t in held:
            try:
                if int(getattr(self.registry.get(t), "priority", 0)) <= self.PANE_PRIORITY:
                    return
            except Exception:  # noqa: BLE001 - an unknown type: do not wait
                return
        # a plan reads the store many times: the foreground found free is not asked again for 20 ms
        if time.monotonic() - getattr(self._bg, "free_at", -1.0) < 0.02:
            return
        if not self._wait_foreground():
            self._bg.gave_up = True
        self._bg.free_at = time.monotonic()

    def _later_on(self) -> bool:
        t = self._later_thread
        return t is not None and t.is_alive() and not self._stopping.is_set()

    def _defer(self, priority: int, item: tuple) -> None:
        with self._later_cond:
            heapq.heappush(self._later, (int(priority), next(self._later_n), item))
            self._later_cond.notify()

    def _hand_on(self, item: tuple, jid: str) -> None:
        """The dispatcher's own ``want`` (the job's key moved) or ``replan_job`` (an upstream output is gone) for the
        queued job ``jid``. At the background's priority it goes to the background planner, and the dispatcher does
        not pick the job again until that is done (else it would plan it and hand it on again, over and over)."""
        pr = self._item_priority(item)
        if pr > self.PANE_PRIORITY and self._later_on():
            with self._later_cond:
                self._handed.add(jid)
            self._defer(pr, item)
            self._wake.set()
            return
        self._drain([item])

    @staticmethod
    def _item_job(item: tuple) -> str | None:
        """The queued job a work item is about, when the dispatcher handed it on (``_hand_on``)."""
        if item[0] == "want":
            return item[4]
        if item[0] == "replan_job":
            return item[1].get("id")
        return None

    def _later_loop(self) -> None:
        """The background planner: the background work the invalidator, the commits and the dispatcher handed on,
        most urgent first, each item once the foreground is free; what an item leads to goes back on the heap."""
        while not self._stopping.is_set():
            with self._later_cond:
                while not self._later and not self._stopping.is_set():
                    self._later_cond.wait(0.25)
                if self._stopping.is_set():
                    return
                self._later_busy = True
            try:
                self._wait_foreground()
                with self._later_cond:
                    item = heapq.heappop(self._later)[2] if self._later else None
                if item is not None:
                    try:
                        self._drain([item], defer=True, own=1)
                    finally:
                        jid = self._item_job(item)
                        if jid is not None:
                            with self._later_cond:
                                self._handed.discard(jid)
                        self._wake.set()
            except Exception:
                log.exception("the background planner failed; it carries on")
            finally:
                with self._later_cond:
                    self._later_busy = False

    def _want(self, plan: Plan, priority: int, reason: str, reuse: str | None) -> tuple[dict[str, Any], list[tuple]]:
        """Make the plan's goal want its key: a hit, a link to an active job, a new or reused queued job, or a
        waiting job. Called with the lock held. Returns the answer and follow-up work items."""
        t, s, v = plan.type, plan.scope, plan.view.token()
        more: list[tuple] = []
        with self.cache.tx() as con:
            goal = goals.get(con, t, s, v) or goals.upsert(con, t, s, v, priority=priority)
            if plan.key is None:
                waiting = json.dumps(plan.missing)
                existing = con.execute(
                    "SELECT id FROM job WHERE type = ? AND scope = ? AND view = ? AND state = 'queued' AND key IS NULL "
                    "ORDER BY id",
                    (t, s, v),
                ).fetchone()
                jid = reuse or (existing[0] if existing else None)
                self._supersede(con, t, s, v, keep_key=None, keep_job=jid)
                if jid is None:
                    jid = self._insert_job(con, plan, priority, reason, key=None, waiting=waiting)
                else:
                    self._requeue_row(con, jid, None, priority, reason, waiting=waiting)
                goals.set_state(con, t, s, v, want_key=None, state="waiting", error=None)
                down = (t, s, v)
                for ref in plan.missing:
                    utype, uscope = plan.needs[ref]
                    more.append(("upstream", utype, uscope, plan.view, priority, down))
                more += self._watch_upstreams(con, plan, goal, priority, skip=set(plan.missing))
                return {"key": None, "state": "queued", "job": jid}, more

            more += self._watch_upstreams(con, plan, goal, priority)

            key = plan.key
            res = con.execute("SELECT status, output_hash FROM result WHERE key = ?", (key,)).fetchone()
            if res is not None and res["status"] == "ok":
                self._supersede(con, t, s, v, keep_key=key, keep_job=reuse)
                if reuse:
                    self._close_row(con, reuse, "done", "inputs moved back to a cached result")
                prev = goal.get("latest_key")
                goals.set_state(con, t, s, v, want_key=key, latest_key=key, state="ok", error=None)
                now = now_s()
                con.execute("UPDATE result SET last_used = ? WHERE key = ?", (now, key))
                if prev != key:
                    prev_hash = None
                    if prev:
                        r = con.execute("SELECT output_hash FROM result WHERE key = ?", (prev,)).fetchone()
                        prev_hash = r[0] if r else None
                    self._result_event(t, s, v, key, "ok", prev)
                    more.append(("ready", t, s, prev_hash != res["output_hash"], {v}))
                return {"key": key, "state": "hit", "job": None}, more

            active = con.execute(
                "SELECT * FROM job WHERE type = ? AND key = ? AND state IN ('queued', 'running')", (t, key)
            ).fetchone()
            if (
                res is not None
                and res["status"] == "error"
                and active is None
                and reason in ("invalidated", "upstream", "resync")
                and goal.get("want_key") == key
            ):
                # the same inputs failed before; only an explicit submit or watch runs them again
                if reuse:
                    self._close_row(con, reuse, "failed", "the same inputs failed before")
                return {"key": key, "state": "queued", "job": None}, more
            self._supersede(con, t, s, v, keep_key=key, keep_job=reuse)
            for ref, h, kind in iter_deps(plan):
                con.execute(
                    "INSERT OR IGNORE INTO result_dep (key, ref, ref_hash, kind) VALUES (?, ?, ?, ?)",
                    (key, ref, h, kind),
                )
            if active is not None:
                active = dict(active)
                if active["priority"] > priority:
                    con.execute("UPDATE job SET priority = ? WHERE id = ?", (priority, active["id"]))
                if reuse and reuse != active["id"]:
                    self._close_row(con, reuse, "cancelled", f"the same work is job {active['id']}")
                goals.set_state(con, t, s, v, want_key=key, state=active["state"], error=None)
                return {"key": key, "state": active["state"], "job": active["id"]}, more
            if reuse:
                jid = reuse
                self._requeue_row(con, jid, key, priority, reason)
            else:
                jid = self._insert_job(con, plan, priority, reason, key=key)
            self._plans[jid] = plan
            goals.set_state(con, t, s, v, want_key=key, state="queued", error=None)
        self._wake.set()
        return {"key": key, "state": "queued", "job": jid}, more

    def _watch_upstreams(
        self,
        con: Any,
        plan: Plan,
        goal: dict[str, Any],
        priority: int,
        *,
        skip: set[str] | frozenset[str] = frozenset(),
    ) -> list[tuple]:
        """``upstream`` items for the needs of a watched goal whose own goal is not watched as long. A watched goal is
        re-planned when a ref its own result read changes, or when a watched upstream's output changes (``_ready``);
        a chain that was computed before (for another view, by a submit) has no upstream goals, so without this an
        edit of an upstream's records would never reach the watched goal. An upstream already watched keeps its own
        priority (the pane in focus watches the rail at 0, the run at 2)."""
        if not goal.get("watch"):
            return []
        token = plan.view.token()
        expires = goal.get("expires")
        down = (plan.type, plan.scope, token)
        out: list[tuple] = []
        for ref, (utype, uscope) in plan.needs.items():
            if ref in skip:
                continue
            ug = goals.get(con, utype, uscope, token)
            if ug is not None and ug["watch"]:
                if ug["expires"] is not None and (expires is None or ug["expires"] < expires):
                    # watched for less long: kept as long as the goal that needs it, its priority as it is
                    con.execute(
                        "UPDATE goal SET expires = ?, updated = ? WHERE type = ? AND scope = ? AND view = ?",
                        (expires, now_iso(), utype, uscope, token),
                    )
                continue
            out.append(("upstream", utype, uscope, plan.view, priority, down))
        return out

    def _insert_job(
        self, con: Any, plan: Plan, priority: int, reason: str, *, key: str | None, waiting: str | None = None
    ) -> str:
        jid = ids.new()
        row = {
            "id": jid,
            "type": plan.type,
            "scope": plan.scope,
            "view": plan.view.token(),
            "key": key,
            "state": "queued",
            "priority": int(priority),
            "host": plan.host,
            "reason": reason,
            "waiting": waiting,
            "created": now_iso(),
        }
        con.execute(
            "INSERT INTO job (id, type, scope, view, key, state, priority, host, reason, waiting, created) "
            "VALUES (:id, :type, :scope, :view, :key, :state, :priority, :host, :reason, :waiting, :created)",
            row,
        )
        self._log(con, jid, "info", f"queued ({reason})" + (f" key {key}" if key else f" waiting for {waiting}"))
        self._job_event(row)
        return jid

    def _requeue_row(
        self, con: Any, jid: str, key: str | None, priority: int, reason: str, *, waiting: str | None = None
    ) -> None:
        con.execute(
            "UPDATE job SET key = ?, state = 'queued', waiting = ?, reason = ?, priority = MIN(priority, ?), "
            "progress = 0, msg = '', error = NULL, lease_owner = NULL, lease_until = NULL, heartbeat = NULL, "
            "pid = NULL, started = NULL, finished = NULL WHERE id = ?",
            (key, waiting, reason, int(priority), jid),
        )
        self._log(con, jid, "info", f"re-queued ({reason})" + (f" key {key}" if key else f" waiting for {waiting}"))
        row = con.execute("SELECT * FROM job WHERE id = ?", (jid,)).fetchone()
        if row is not None:
            self._job_event(dict(row))

    def _close_row(self, con: Any, jid: str, state: str, msg: str) -> None:
        con.execute(
            "UPDATE job SET state = ?, msg = ?, finished = ?, lease_owner = NULL WHERE id = ?",
            (state, msg, now_iso(), jid),
        )
        self._plans.pop(jid, None)
        self._log(con, jid, "info", f"{state}: {msg}")
        row = con.execute("SELECT * FROM job WHERE id = ?", (jid,)).fetchone()
        if row is not None:
            self._job_event(dict(row))

    def _cancel_row(self, con: Any, row: dict[str, Any], why: str) -> None:
        self._close_row(con, row["id"], "cancelled", why)
        run = self._running.get(row["id"])
        if run is not None:
            run.task.cancel.set()

    def _supersede(self, con: Any, t: str, s: str, v: str, *, keep_key: str | None, keep_job: str | None) -> None:
        """Cancel the goal's other pending jobs (one pending job per goal; the newest wins), sparing a job another
        view's goal still wants."""
        rows = con.execute(
            "SELECT * FROM job WHERE type = ? AND scope = ? AND view = ? AND state IN ('queued', 'running')", (t, s, v)
        ).fetchall()
        for r in rows:
            r = dict(r)
            if r["id"] == keep_job or (keep_key is not None and r["key"] == keep_key):
                continue
            if r["key"] is not None:
                other = con.execute(
                    "SELECT 1 FROM goal WHERE type = ? AND want_key = ? AND NOT (scope = ? AND view = ?) LIMIT 1",
                    (t, r["key"], s, v),
                ).fetchone()
                if other is not None:
                    continue
            self._cancel_row(con, r, "superseded by newer inputs")

    def _ready(self, t: str, s: str, changed: bool, views: set[str] | None = None) -> list[tuple]:
        """Work after a result of ``(t, s)`` became current: plan waiting jobs again, and when its output changed,
        re-plan the watched goals that depend on it. ``views``: the views whose goal of ``(t, s)`` changed its
        output (None: unknown, every view). Keys are by content, so a downstream goal in another view, whose own
        ``(t, s)`` did not move, keeps its plan: a save in one scenario never re-plans the chains of the others."""
        ref = ref_job(t, s)
        items: list[tuple] = []
        pattern = "%" + json.dumps(ref)[1:-1] + "%"
        rows = self.cache.query(
            "SELECT * FROM job WHERE state = 'queued' AND key IS NULL AND waiting LIKE ?", (pattern,)
        )
        for r in rows:
            others = [x for x in (json.loads(r["waiting"]) if r["waiting"] else []) if x != ref]
            if others and self._still_coming(others, r["view"]):
                continue  # the last of its upstreams to land plans it (once, not once per upstream)
            items.append(("replan_job", dict(r)))
        if changed:
            keys = {r[0] for r in self.cache.query("SELECT DISTINCT key FROM result_dep WHERE ref = ?", (ref,))}
            with self._lock, self.cache.tx() as con:
                found = goals.watched(con, keys=keys) if keys else []
            if views is not None:
                found = [g for g in found if g["view"] in views]
            items += [("replan", g, "upstream") for g in found]
        return items

    def _still_coming(self, refs: list[str], view: str) -> bool:
        """Whether any of these ``job:`` refs is still being worked on in ``view`` (its goal queued, running or
        waiting). A ref with no goal, or a goal done or failed, is not (its failure fails the waiting job)."""
        with self._lock, self.cache.tx() as con:
            for ref in refs:
                kind, rest = parse_ref(ref)
                if kind != "job" or "/" not in rest:
                    continue
                utype, uscope = rest.split("/", 1)
                g = goals.get(con, utype, uscope, view)
                if g is not None and g["state"] in ("queued", "running", "waiting"):
                    return True
        return False

    def _fail_waiting(self, ref: str, view: str | None, text: str) -> None:
        pattern = "%" + json.dumps(ref)[1:-1] + "%"
        rows = self.cache.query(
            "SELECT * FROM job WHERE state = 'queued' AND key IS NULL AND waiting LIKE ?", (pattern,)
        )
        for r in rows:
            if view is None or r["view"] == view:
                self._fail_row(r["id"], f"upstream failed: {text}", text)

    def _fail_row(self, jid: str, msg: str, detail: str) -> None:
        with self._lock, self.cache.tx() as con:
            row = con.execute("SELECT * FROM job WHERE id = ?", (jid,)).fetchone()
            if row is None or row["state"] not in ACTIVE:
                return
            con.execute(
                "UPDATE job SET state = 'failed', msg = ?, error = ?, finished = ? WHERE id = ?",
                (msg[:500], detail, now_iso(), jid),
            )
            self._log(con, jid, "error", detail)
            goals.set_state(con, row["type"], row["scope"], row["view"], state="error", error=msg[:2000])
            self._job_event(dict(row), state="failed", msg=msg[:500], error=detail)
            self._plans.pop(jid, None)
            ref = ref_job(row["type"], row["scope"])
            view = row["view"]
        self._fail_waiting(ref, view, msg)

    # ------------------------------------------------------------------------------------------- dispatching

    def _dispatch_loop(self) -> None:
        while not self._stopping.is_set():
            self._wake.wait(0.25)
            self._wake.clear()
            if self._stopping.is_set():
                return
            try:
                while not self._stopping.is_set() and self._dispatch_one():
                    pass
            except Exception:
                log.exception("the job dispatcher failed; it carries on")

    PANE_PRIORITY = 1
    """Jobs at this priority or more urgent (0 the pane in focus, 1 an open pane) may take a host's last free slot;
    the others (a sheet's run chain at 2 and 3, background goals at 5 and up) leave it free, so the panes' rail
    never waits behind them (a host with one slot is not held back)."""

    def _pick(self) -> dict[str, Any] | None:
        rows = self.cache.query("SELECT * FROM job WHERE state = 'queued' AND key IS NOT NULL ORDER BY priority, id")
        with self._later_cond:
            handed = set(self._handed)
        may: bool | None = None
        for r in rows:
            if r["id"] in handed:
                continue  # the background planner has it (_hand_on)
            if int(r["priority"]) > self.PANE_PRIORITY:
                if may is None:
                    may = self._background_may_start()
                if not may:
                    return None  # the rows are in priority order: the rest are background too
            host = self.hosts.get(r["host"])
            if host is None:
                continue
            keep = 1 if int(r["priority"]) > self.PANE_PRIORITY and getattr(host, "capacity", 1) > 1 else 0
            if host.free() > keep:
                return dict(r)
        return None

    def _dispatch_one(self) -> bool:
        with self._lock:
            if self._closed:
                return False
            pick = self._pick()
            if pick is None:
                return False
            plan = self._plans.get(pick["id"])
        jid = pick["id"]
        if plan is None or plan.key != pick["key"]:
            try:
                plan = self.planner.plan(pick["type"], pick["scope"], View.parse(pick["view"]))
            except Exception as e:
                self._fail_row(jid, f"planning failed: {e}", traceback.format_exc())
                return True
            if plan.key != pick["key"]:
                with self._lock:
                    cur = self._row(jid)
                    if cur is None or cur["state"] != "queued" or cur["key"] != pick["key"]:
                        return True
                self._hand_on(("want", plan, int(pick["priority"]), "moved", jid), jid)
                return True
        upstream: dict[str, Output] = {}
        try:
            for ref, k in plan.upstream_keys.items():
                try:
                    upstream[ref] = self._load_output(k)
                except NotFound:
                    # gone, or its row is ok but a blob file was lost: drop what is left of it, so the plan below
                    # waits for the upstream and the upstream is computed again (instead of planning to it for ever)
                    with self._lock:
                        self.cache.drop_result(k)
                    raise
        except NotFound:
            self._hand_on(("replan_job", pick), jid)
            return True
        jt = self.registry.get(pick["type"])
        host = self.hosts[pick["host"]]
        with self._lock:
            if self._closed:
                return False
            cur = self._row(jid)
            if cur is None or cur["state"] != "queued" or cur["key"] != pick["key"]:
                return True
            keep = 1 if int(pick["priority"]) > self.PANE_PRIORITY and getattr(host, "capacity", 1) > 1 else 0
            if host.free() <= keep:
                return False
            t = now_s()
            with self.cache.tx() as con:
                con.execute(
                    "UPDATE job SET state = 'running', started = ?, lease_owner = ?, lease_until = ?, heartbeat = ?, "
                    "progress = 0, msg = '' WHERE id = ? AND state = 'queued'",
                    (now_iso(), self.owner, t + self.lease_s, t, jid),
                )
                con.execute(
                    "UPDATE goal SET state = 'running', updated = ? WHERE type = ? AND want_key = ?",
                    (now_iso(), pick["type"], pick["key"]),
                )
                self._log(con, jid, "info", f"running on {pick['host']}")
            self._plans.pop(jid, None)
            task = Task(
                job_id=jid,
                type_name=pick["type"],
                job_type=jt,
                module=module_of(jt),
                inputs=plan.inputs,
                upstream=upstream,
                timeout_s=float(jt.timeout_s),
                on_end=partial(self._on_end, jid),
                on_progress=partial(self._on_progress, jid),
                on_start=partial(self._on_start, jid),
            )
            run = _Run(
                job_id=jid,
                type=pick["type"],
                scope=pick["scope"],
                view=pick["view"],
                key=pick["key"],
                host=pick["host"],
                plan=plan,
                task=task,
                t0=time.perf_counter(),
                deadline=time.monotonic() + float(jt.timeout_s),
            )
            self._running[jid] = run
            self._job_event({**pick, "state": "running", "progress": 0.0, "msg": ""})
        self._flush()
        with log_context(job_id=jid):
            try:
                host.start(task)
            except Exception:
                # a host that cannot take the task (its pool shut down, no free slot): fail the job rather than
                # leave it running for ever under a lease this scheduler keeps renewing
                self._on_end(jid, "error", f"the {pick['host']} host could not start the job\n{traceback.format_exc()}")
        return True

    def _load_output(self, key: str) -> Output:
        res = self.cache.result_row(key)
        if res is None or res["status"] != "ok":
            raise NotFound(f"upstream result {key} is not in the cache")
        arrays = {}
        for name, spec in res["arrays"].items():
            arrays[name] = decode_array(self.cache.blob_bytes(spec["sha256"]), spec["dtype"], spec["shape"])
        blobs = {name: self.cache.blob_bytes(spec["sha256"]) for name, spec in res["blobs"].items()}
        issues = [
            {**dict(r), "data": json.loads(r["data"]) if r["data"] else None}
            for r in self.cache.query("SELECT rule, sev, c0, c1, msg, data FROM issue WHERE key = ?", (key,))
        ]
        return Output(meta=res["meta"], arrays=arrays, blobs=blobs, issues=issues)

    # ------------------------------------------------------------------------------------------ host callbacks

    def _on_start(self, jid: str, pid: int | None) -> None:
        if pid is None:
            return
        with self._lock:
            if self._closed:
                return
            with self.cache.tx() as con:
                con.execute("UPDATE job SET pid = ? WHERE id = ?", (pid, jid))

    def _on_progress(self, jid: str, f: float, msg: str) -> None:
        with self._lock:
            run = self._running.get(jid)
            if run is None or self._closed:
                return
            now = time.monotonic()
            if now - run.last_progress < 0.2 and f < 1.0:
                return
            run.last_progress = now
            with self.cache.tx() as con:
                con.execute(
                    "UPDATE job SET progress = ?, msg = ? WHERE id = ? AND state = 'running'",
                    (float(f), msg[:200], jid),
                )
            self._emit(
                "job",
                {
                    "id": jid,
                    "type": run.type,
                    "scope": run.scope,
                    "state": "running",
                    "progress": float(f),
                    "msg": msg[:200],
                    "view": run.view,
                    "key": run.key,
                },
            )
        self._flush()

    def _on_end(self, jid: str, outcome: str, value: Any) -> None:
        if self._closed:
            # a run that ended after stop() (an engine call answered while the hub shut down): stop() put the job back
            # in the queue, so the next start runs it; the closed cache cannot take its answer
            return
        try:
            self._finish(jid, outcome, value)
        except Exception:
            if self._closed or self._stopping.is_set():
                # the hub stopped while this run was being committed: stop() re-queued the job for the next start
                log.info("job %s ended while the scheduler stopped; it runs again at the next start", jid)
                return
            log.exception("finishing job %s failed", jid)
            with contextlib.suppress(Exception):
                self._fail_row(jid, "the scheduler failed to commit the result", traceback.format_exc())
        finally:
            self._flush()
            self._wake.set()

    def _owned(self, jid: str) -> dict[str, Any] | None:
        row = self._row(jid)
        if row is None or row["state"] != "running" or row["lease_owner"] != self.owner:
            return None
        return row

    def _finish(self, jid: str, outcome: str, value: Any) -> None:
        with self._lock:
            if self._closed or self._stopping.is_set():
                # stopping: the row stays running and stop() puts it back in the queue
                return
            run = self._running.pop(jid, None)
            row = self._owned(jid)
            if run is not None and row is not None:
                self._finishing.add(jid)
        if run is None or row is None:
            log.info(
                "job %s ended (%s) after it was cancelled, timed out or re-queued; its answer is dropped", jid, outcome
            )
            return
        try:
            self._finish_owned(jid, row, run, outcome, value)
        finally:
            with self._lock:
                self._finishing.discard(jid)

    def _finish_owned(self, jid: str, row: dict[str, Any], run: _Run, outcome: str, value: Any) -> None:
        ms = (time.perf_counter() - run.t0) * 1000.0
        if outcome == "ok":
            try:
                self._commit(row, run.plan, as_output(value), ms)
            except Exception as e:
                self._fail(row, run.plan, "error", f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
        elif outcome == "cancelled":
            with self._lock, self.cache.tx() as con:
                if self._owned(jid) is not None:
                    self._close_row(con, jid, "cancelled", str(value))
        else:
            self._fail(row, run.plan, outcome, str(value), failure=value if isinstance(value, Failure) else None)

    def _fail(
        self, row: dict[str, Any], plan: Plan, outcome: str, text: str, *, failure: Failure | None = None
    ) -> None:
        """Mark the job failed; the job log gets the error, then the engine's stderr tail and zod issues (each a line
        of its own) when the failure carried them."""
        jid, t, s, v, key = row["id"], row["type"], row["scope"], row["view"], row["key"]
        summary = text.strip().splitlines()[-1][:500] if text.strip() else outcome
        with self._lock:
            if self._owned(jid) is None or self._closed:
                return
            with self.cache.tx() as con:
                con.execute(
                    "UPDATE job SET state = 'failed', msg = ?, error = ?, finished = ? WHERE id = ?",
                    (outcome, text, now_iso(), jid),
                )
                self._log(con, jid, "error", f"{outcome}: {text}")
                if failure is not None and failure.stderr_tail.strip():
                    self._log(con, jid, "error", "engine stderr (last lines):\n" + failure.stderr_tail.rstrip())
                if failure is not None and failure.issues:
                    self._log(con, jid, "error", "engine issues: " + json.dumps(failure.issues, ensure_ascii=False))
                ok = con.execute("SELECT 1 FROM result WHERE key = ? AND status = 'ok'", (key,)).fetchone()
                if ok is None:
                    con.execute(
                        "INSERT OR REPLACE INTO result (key, type, scope, view, status, error, job, created, "
                        "last_used, engine_build) VALUES (?, ?, ?, ?, 'error', ?, ?, ?, ?, ?)",
                        (key, t, s, v, text, jid, now_iso(), now_s(), plan.engine_build),
                    )
                wanting = goals.wanting(con, t, key)
                for g in wanting:
                    goals.set_state(con, g["type"], g["scope"], g["view"], state="error", error=summary)
                self._job_event({**row, "state": "failed", "msg": outcome, "error": text})
                for g in wanting:
                    self._emit(
                        "result",
                        {
                            "key": key,
                            "type": t,
                            "scope": g["scope"],
                            "view": g["view"],
                            "status": "error",
                            "changed": [],
                        },
                    )
        self._fail_waiting(ref_job(t, s), v, summary)

    def _commit(self, row: dict[str, Any], plan: Plan, output: Output, ms: float) -> None:
        jid, t, s, v, key = row["id"], row["type"], row["scope"], row["view"], row["key"]
        jt = self.registry.get(t)
        enc = encode_output(output)
        view = View.parse(v)
        replan = self.planner.plan(t, s, view)
        own_valid = replan.key == key
        truth = getattr(jt, "effect", None) == "truth"
        valid = own_valid
        # Every other goal that wants this key is planned again as well. The result is valid while any of them
        # still plans to it; each goal whose content moved during the run gets the work for its new key queued, so
        # a goal is never left holding a result its content no longer matches.
        moved_others: list[tuple[Plan, int]] = []
        # goals whose content moved off this key during the run: they never get it as their latest result (nor a
        # result event for it), only the work for their new key
        moved_goals: set[tuple[str, str]] = set() if own_valid else {(s, v)}
        with self._lock, self.cache.tx() as con:
            others = [g for g in goals.wanting(con, t, key) if not (g["scope"] == s and g["view"] == v)]
        for g in others:
            try:
                p = self.planner.plan(t, g["scope"], View.parse(g["view"]))
            except Exception as e:
                log.warning("re-planning %s/%s in %s failed: %s", t, g["scope"], g["view"], e)
                continue
            if p.key != key:
                moved_goals.add((g["scope"], g["view"]))
            if p.key == key and (own_valid or not truth):
                valid = True
            else:
                # moved, or a job that changes the truth whose own goal moved (it commits only for its own goal):
                # this goal gets a job of its own
                moved_others.append((p, int(g["priority"])))
        if valid and not own_valid:
            moved_others.append((replan, int(row["priority"])))
        if valid and truth:
            with self._lock:
                if self._owned(jid) is None:
                    return
            applied = jt.apply(self.store, s, view, output)
            output = Output(
                meta={**(output.meta or {}), "applied": applied},
                arrays=output.arrays,
                blobs=output.blobs,
                issues=output.issues,
            )
            enc = encode_output(output)
        if valid:
            for raw in enc.data.values():
                self.cache.put_blob(raw)
        follow: list[tuple] = []
        updated: list[tuple[dict[str, Any], str | None, str | None]] = []
        with self._lock:
            if self._owned(jid) is None or self._closed:
                return
            with self.cache.tx() as con:
                now, stamp = now_s(), now_iso()
                if valid:
                    self.cache.ensure_blobs(enc.data)
                    con.execute(
                        "INSERT OR REPLACE INTO result (key, type, scope, view, status, output_hash, meta, arrays, "
                        "blobs, error, engine_build, job, ms, created, last_used, pinned) "
                        "VALUES (?, ?, ?, ?, 'ok', ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, "
                        "COALESCE((SELECT pinned FROM result WHERE key = ?), 0))",
                        (
                            key,
                            t,
                            s,
                            v,
                            enc.output_hash,
                            json.dumps(enc.meta, ensure_ascii=False),
                            json.dumps(enc.arrays),
                            json.dumps(enc.blobs),
                            plan.engine_build,
                            jid,
                            ms,
                            stamp,
                            now,
                            key,
                        ),
                    )
                    con.execute("DELETE FROM result_dep WHERE key = ?", (key,))
                    con.executemany(
                        # OR IGNORE: a ref read twice with two hashes (the store moved during the plan) is one row
                        "INSERT OR IGNORE INTO result_dep (key, ref, ref_hash, kind) VALUES (?, ?, ?, ?)",
                        [(key, ref, h, kind) for ref, h, kind in iter_deps(plan)],
                    )
                    con.execute("DELETE FROM result_blob WHERE key = ?", (key,))
                    for spec in [*enc.arrays.values(), *enc.blobs.values()]:
                        con.execute(
                            "INSERT OR IGNORE INTO blob (sha256, size, created, last_used) VALUES (?, ?, ?, ?)",
                            (spec["sha256"], spec["size"], stamp, now),
                        )
                        con.execute("UPDATE blob SET last_used = ? WHERE sha256 = ?", (now, spec["sha256"]))
                        con.execute(
                            "INSERT OR IGNORE INTO result_blob (key, sha256) VALUES (?, ?)", (key, spec["sha256"])
                        )
                    con.execute("DELETE FROM issue WHERE key = ?", (key,))
                    for issue in enc.issues:
                        con.execute(
                            "INSERT OR IGNORE INTO issue (key, rule, sev, c0, c1, msg, data, dedupe) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                key,
                                issue.get("rule"),
                                issue.get("sev"),
                                issue.get("c0"),
                                issue.get("c1"),
                                issue.get("msg"),
                                json.dumps(issue.get("data")),
                                fsio.content_hash(issue),
                            ),
                        )
                    con.execute(
                        "UPDATE job SET state = 'done', progress = 1, msg = '', finished = ?, lease_owner = NULL "
                        "WHERE id = ?",
                        (stamp, jid),
                    )
                    self._log(con, jid, "info", f"done in {ms:.0f} ms; output {enc.output_hash}")
                    for g in goals.wanting(con, t, key):
                        if (g["scope"], g["view"]) in moved_goals:
                            continue
                        prev = g.get("latest_key")
                        prev_hash = None
                        if prev and prev != key:
                            r = con.execute("SELECT output_hash FROM result WHERE key = ?", (prev,)).fetchone()
                            prev_hash = r[0] if r else None
                        goals.set_state(con, g["type"], g["scope"], g["view"], latest_key=key, state="ok", error=None)
                        updated.append((g, prev, prev_hash))
                    self._job_event({**row, "state": "done", "progress": 1.0, "msg": ""})
                else:
                    ok = con.execute("SELECT 1 FROM result WHERE key = ? AND status = 'ok'", (key,)).fetchone()
                    if ok is None:
                        con.execute(
                            "INSERT OR REPLACE INTO result (key, type, scope, view, status, output_hash, meta, job, "
                            "ms, created, last_used, engine_build) VALUES (?, ?, ?, ?, 'stale', ?, ?, ?, ?, ?, ?, ?)",
                            (
                                key,
                                t,
                                s,
                                v,
                                enc.output_hash,
                                json.dumps(enc.meta, ensure_ascii=False),
                                jid,
                                ms,
                                stamp,
                                now,
                                plan.engine_build,
                            ),
                        )
                    self._log(con, jid, "info", f"inputs moved during the run (now {replan.key}); result stored stale")
            if valid:
                changed_output = False
                moved_views: set[str] = set()
                for g, prev, prev_hash in updated:
                    if prev != key:
                        self._result_event(g["type"], g["scope"], g["view"], key, "ok", prev)
                        if prev_hash != enc.output_hash:
                            changed_output = True
                            moved_views.add(g["view"])
                follow.append(("ready", t, s, changed_output or not updated, moved_views if updated else None))
            else:
                follow.append(("want", replan, int(row["priority"]), "stale", jid))
        follow += [("want", p, pr, "stale", None) for p, pr in moved_others]
        self._drain(follow, defer=True)

    # --------------------------------------------------------------------------------------------- monitor

    def _monitor_loop(self) -> None:
        tick = max(0.02, min(0.1, self.heartbeat_s / 2))
        next_beat = 0.0
        while not self._stopping.wait(tick):
            try:
                self._check_timeouts()
                if time.monotonic() >= next_beat:
                    self._heartbeat()
                    self._sweep_leases()
                    next_beat = time.monotonic() + self.heartbeat_s
            except Exception:
                log.exception("the job monitor failed; it carries on")
            self._flush()

    def _check_timeouts(self) -> None:
        now = time.monotonic()
        with self._lock:
            runs = [r for r in self._running.values() if r.host != "process" and not r.expired and now > r.deadline]
        for run in runs:
            run.expired = True
            run.task.cancel.set()
            row = self._owned(run.job_id)
            if row is not None:
                timeout = float(self.registry.get(run.type).timeout_s)
                self._fail(row, run.plan, "timeout", f"timed out after {timeout:g} s; cancelled and its answer dropped")

    def _live(self) -> set[str]:
        """The jobs this scheduler is running or committing now (call with the lock held)."""
        return set(self._running) | self._finishing

    def _heartbeat(self) -> None:
        """Renew the leases of the jobs this scheduler is running or committing, and only those: a row left
        ``running`` because its end could not be recorded (the cache refused every write for a while) then loses its
        lease and is re-queued, instead of being kept alive for ever."""
        with self._lock:
            if self._closed:
                return
            live = sorted(self._live())
            if not live:
                return
            t = now_s()
            with self.cache.tx() as con:
                for i in range(0, len(live), 400):
                    chunk = live[i : i + 400]
                    marks = ",".join("?" * len(chunk))
                    con.execute(
                        "UPDATE job SET lease_until = ?, heartbeat = ? "
                        f"WHERE state = 'running' AND lease_owner = ? AND id IN ({marks})",
                        (t + self.lease_s, t, self.owner, *chunk),
                    )

    def _sweep_leases(self) -> None:
        requeued = False
        failed: list[tuple[str, str]] = []
        with self._lock:
            if self._closed:
                return
            t = now_s()
            with self.cache.tx() as con:
                rows = con.execute(
                    "SELECT * FROM job WHERE state = 'running' AND (lease_until IS NULL OR lease_until < ?)", (t,)
                ).fetchall()
                for r in rows:
                    r = dict(r)
                    if r["lease_owner"] == self.owner and r["id"] in self._live():
                        continue
                    if r["requeues"] >= self.max_requeue:
                        failed.append((r["id"], f"its lease expired {r['requeues'] + 1} times (the scheduler died)"))
                        continue
                    con.execute(
                        "UPDATE job SET state = 'queued', requeues = requeues + 1, reason = 'lease', "
                        "lease_owner = NULL, lease_until = NULL, heartbeat = NULL, pid = NULL, progress = 0, "
                        "msg = 'lease expired' "
                        "WHERE id = ?",
                        (r["id"],),
                    )
                    self._log(con, r["id"], "warning", f"lease of {r['lease_owner']} expired; re-queued")
                    self._job_event({**r, "state": "queued", "msg": "lease expired", "progress": 0.0})
                    requeued = True
        for jid, why in failed:
            with self._lock, self.cache.tx() as con:
                con.execute("UPDATE job SET lease_owner = ? WHERE id = ?", (self.owner, jid))
            row = self._owned(jid)
            if row is not None:
                self._fail(row, _NO_PLAN, "lease", why)
        if requeued:
            self._wake.set()

    # ----------------------------------------------------------------------------------------- invalidator

    FILE_CHECK_S = 5.0

    def _invalidate_loop(self) -> None:
        files_at = time.monotonic()
        while not self._stopping.is_set():
            self._inval_wake.wait(self.poll_s)
            self._inval_wake.clear()
            if self._stopping.is_set():
                return
            try:
                self._invalidate_once()
                if time.monotonic() - files_at >= self.FILE_CHECK_S:
                    files_at = time.monotonic()
                    self.check_files()
            except Exception:
                log.exception("the invalidator failed; it carries on")

    def _watched_file_refs(self) -> list[tuple[str, str | None]]:
        """``(ref, hash)`` of every ``file:`` dependency of a watched goal's latest or wanted key."""
        return [
            (r[0], r[1])
            for r in self.cache.query(
                "SELECT DISTINCT d.ref, d.ref_hash FROM result_dep d JOIN goal g "
                "ON (g.latest_key = d.key OR g.want_key = d.key) "
                "WHERE g.watch = 1 AND (g.expires IS NULL OR g.expires > ?) AND d.ref >= 'file:' AND d.ref < 'file;'",
                (time.time(),),
            )
        ]

    def check_files(self, only: set[str] | None = None) -> set[str]:
        """The ``file:`` refs of watched goals whose file no longer hashes as their result (or their wanted key)
        recorded (a golden baseline rewritten, a tier's handshake turned done): exactly those goals are planned
        again. Hashes come from the cache's size-and-mtime cache, so an unchanged file costs one ``stat``. ``only``
        limits the check to those refs. Returns the refs that moved."""
        moved = set()
        for ref, h in self._watched_file_refs():
            if only is not None and ref not in only:
                continue
            try:
                now = self.cache.file_sha256(paths.resolve(ref[len("file:") :]))
            except HubError:
                now = None
            if now != h:
                moved.add(ref)
        if moved:
            self.invalidate(moved)
        return moved

    def files_changed(self, changed: Iterable[Path | str]) -> set[str]:
        """The live watcher saw these paths (files, or folders whose contents moved) change: check the ``file:``
        refs that name them or a file under them, and re-plan exactly the watched goals whose file now hashes
        differently. A re-save of the same bytes moves no key and runs nothing. Returns the refs that moved."""
        import os

        targets = [os.path.normcase(os.path.realpath(p)) for p in changed]
        if not targets:
            return set()
        hit: set[str] = set()
        for ref, _h in self._watched_file_refs():
            try:
                local = os.path.normcase(os.path.realpath(paths.resolve(ref[len("file:") :])))
            except HubError:
                continue
            for t in targets:
                if local == t or local.startswith(t.rstrip(os.sep) + os.sep) or t.startswith(local + os.sep):
                    hit.add(ref)
                    break
        return self.check_files(hit) if hit else set()

    def _store_epoch(self) -> str | None:
        epoch = getattr(self.store, "epoch", None)  # Store.epoch; a fake without it skips the check
        return str(epoch()) if callable(epoch) else None

    def _invalidate_once(self) -> None:
        cursor = self.cache.cursor("invalidator") or 0
        epoch = self._store_epoch()
        last_seq = getattr(self.store, "last_seq", None)  # Store.last_seq; getattr keeps older fakes working
        if epoch is not None and epoch != self._epoch:
            seen, self._epoch = self._epoch, epoch
            if seen is not None:
                # a new epoch is a restored truth DB: its outbox is another history, so start from its end and plan
                # every goal (seq comparisons alone miss a restore followed by new writes before this poll)
                last = int(last_seq()) if callable(last_seq) else 0
                log.warning("the truth DB has a new epoch (%s, was %s); re-planning every goal", epoch, seen)
                self.cache.set_cursor("invalidator", last)
                cursor = last
                self._fg_rewound(last)
                self.replan_all(defer=True)
        if cursor and callable(last_seq):
            last = int(last_seq())
            if last < cursor:
                # the outbox went backwards (a restored truth DB): what changed is unknown, so plan every goal
                log.warning("the outbox ends at %s, before the cache's cursor %s; re-planning every goal", last, cursor)
                self.cache.set_cursor("invalidator", last)
                cursor = last
                self._fg_rewound(last)
                self.replan_all(defer=True)
        min_seq = getattr(self.store, "min_seq", None)  # Store.min_seq, as above
        if cursor and callable(min_seq):
            first = int(min_seq())
            if first > cursor + 1:
                # events after the cursor were pruned from the outbox: what they changed is unknown
                log.warning("the outbox starts at %s, past the cursor %s; re-planning every goal", first, cursor)
                self.replan_all(defer=True)
                self.cache.set_cursor("invalidator", first - 1)
                cursor = first - 1
        while not self._stopping.is_set():
            events = self.store.events_since(cursor, 1000)
            if not events:
                return
            rec_refs: set[str] = set()
            kinds: set[str] = set()
            bulk: set[str] = set()
            by_kind: dict[str, set[str]] = {}
            params = False
            # the layers written (None when an event does not say): only views that read one of them can change
            layers: set[str] | None = set()
            for ev in events:
                data = ev.get("data") or {}
                counted = False
                if ev.get("type") == "record":
                    rec_refs.add(f"rec:{data.get('id')}")
                    kinds.add(str(data.get("kind")))
                    by_kind.setdefault(str(data.get("kind")), set()).add(str(data.get("id")))
                    counted = True
                elif ev.get("type") == "changeset" and data.get("summary"):
                    bulk.update((data.get("kinds") or {}).keys())
                    counted = True
                if counted and layers is not None:
                    if data.get("layer"):
                        layers.add(str(data["layer"]))
                    else:
                        layers = None
            params = PARAM_KIND in kinds or PARAM_KIND in bulk
            items = self._affected(rec_refs, kinds, bulk, params, by_kind=by_kind, layers=layers)
            if items:
                self._drain(items, defer=True)
            cursor = int(events[-1]["seq"])
            self.cache.set_cursor("invalidator", cursor)
            if len(events) < 1000:
                return

    def _parents(self, ids: set[str]) -> set[str] | None:
        """The ``parent`` column of these records in any layer (``None`` when the store cannot say)."""
        reader = getattr(self.store, "_reader", None)
        if not callable(reader) or not ids:
            return None
        out: set[str] = set()
        id_list = sorted(ids)
        try:
            con = reader()
            for i in range(0, len(id_list), 400):
                chunk = id_list[i : i + 400]
                marks = ",".join("?" * len(chunk))
                out.update(
                    r[0]
                    for r in con.execute(f"SELECT DISTINCT parent FROM rec WHERE id IN ({marks})", chunk).fetchall()
                    if r[0] is not None
                )
        except Exception:
            return None
        return out

    def _query_keys(self, kind: str, ids: set[str] | None) -> set[str]:
        """The keys whose plans listed ``kind`` and whose answer a change to the records ``ids`` can alter.

        A list query is ``rec:<kind>?<filters>``. A record that was in the answer is a ``rec:<id>`` ref of its own,
        so a change to it, or its leaving the answer, is found by that ref. A record can join only an answer whose
        filters it matches now; for a query filtered by ``parent`` alone (a section's stops, platforms, profile,
        ground) that is the query on its current parent, so a profile saved on Line 6 re-plans Line 6's goals and
        not the 15 others. Any other query (no filter, a bbox, a text search) is affected by every change."""
        lo, hi = query_prefix(kind)
        rows = self.cache.query("SELECT DISTINCT ref, key FROM result_dep WHERE ref >= ? AND ref < ?", (lo, hi))
        parents = self._parents(ids) if ids else None
        found: set[str] = set()
        for ref, key in rows:
            if parents is not None:
                try:
                    filters = json.loads(ref[len(lo) :])
                except ValueError:
                    filters = None
                if isinstance(filters, dict) and set(filters) == {"parent"} and filters["parent"] not in parents:
                    continue
            found.add(key)
        return found

    def _affected(
        self,
        refs: set[str],
        kinds: set[str],
        bulk: set[str],
        params: bool,
        *,
        by_kind: dict[str, set[str]] | None = None,
        layers: set[str] | None = None,
    ) -> list[tuple]:
        """The watched goals whose wanted or latest key depends on any changed ref, as ``replan`` items. With
        ``layers`` (the layers the changes were written in), only the goals of views whose layer chain holds one of
        them: results are keyed by content, so scenarios holding the same records share keys, and a write in one
        scenario cannot change what another reads."""
        found: set[str] = set()
        ref_list = sorted(refs)
        for i in range(0, len(ref_list), 400):
            chunk = ref_list[i : i + 400]
            marks = ",".join("?" * len(chunk))
            found.update(
                r[0] for r in self.cache.query(f"SELECT DISTINCT key FROM result_dep WHERE ref IN ({marks})", chunk)
            )
        for kind in kinds | bulk:
            ids = None if (kind in bulk or by_kind is None) else by_kind.get(kind)
            found.update(self._query_keys(kind, ids))
        for kind in bulk:
            found.update(r[0] for r in self.cache.query("SELECT DISTINCT key FROM result_dep WHERE kind = ?", (kind,)))
        if params:
            found.update(
                r[0]
                for r in self.cache.query(
                    "SELECT DISTINCT key FROM result_dep WHERE ref >= 'param:' AND ref < 'param;'"
                )
            )
        with self._lock, self.cache.tx() as con:
            hit = goals.watched(con, keys=found, errors=True)
        if layers is not None:
            seen: dict[str, bool] = {}
            hit = [g for g in hit if self._sees(g["view"], layers, seen)]
        return [("replan", g, "invalidated") for g in hit]

    def _sees(self, token: str, layers: set[str], seen: dict[str, bool]) -> bool:
        """Whether a read in the view ``token`` looks through any of ``layers`` (True when the store cannot say);
        ``seen`` keeps the answers of one pass."""
        if token in seen:
            return seen[token]
        chain = getattr(self.store, "chain", None)
        ok = True
        if callable(chain):
            try:
                ok = not layers.isdisjoint(chain(View.parse(token).layer))
            except Exception:  # noqa: BLE001 - a view the store cannot resolve now: plan it, which says why
                ok = True
        seen[token] = ok
        return ok


class _NoPlan:
    engine_build = None


_NO_PLAN: Any = _NoPlan()


__all__ = ["Scheduler", "changed_ranges"]
