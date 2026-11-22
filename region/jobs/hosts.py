"""Where a job's ``run`` executes (section 6, "Hosts"): inline, a thread pool, a spawn process pool, or the engine.

- ``inline``: in the dispatcher thread, for work under 50 ms.
- ``thread``: a thread pool, for I/O. Cancelling sets the job's token (``RunCtx.cancelled``); a thread cannot be
  killed, so a job that ignores its token is abandoned and its answer dropped.
- ``process``: a pool of worker processes started with ``spawn`` (the only start method on Windows), each with its
  own pair of one-way pipes, so one worker can be killed without harming the others. A worker exits after
  ``max_tasks_per_child`` tasks and is replaced. Cancelling sends the token, then kills the worker after
  ``kill_grace_s`` (1 s); a timeout kills it at once. The worker finds the job type by module and name
  (``registry.find``), so a process job type must be a module-level object of an importable module.
- ``engine``: a thread pool whose jobs get the scheduler's ``EngineClient`` as ``rt.engine``, with each call's
  timeout capped by the job's remaining time.

Every host reports the end of a task once, through ``Task.on_end(outcome, value)``: ``ok`` with the ``Output``,
``error`` with a ``Failure`` (the traceback, plus an engine error's stderr tail and zod issues for the job log) or a
traceback string, ``timeout``, ``cancelled`` or ``crashed`` with a message.

``RunContext`` gives ``run`` its engine, progress, cancel token and upstream outputs, and nothing else: no store, no
write method (decision 9.19).
"""

from __future__ import annotations

import contextlib
import multiprocessing
import os
import queue
import threading
import time
import traceback
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from region.core.errors import EngineUnavailable, Invalid
from region.core.protocols import EngineClient, Output


@dataclass(frozen=True)
class Failure:
    """The value of an ``error`` outcome. ``text`` is the traceback; ``stderr_tail`` and ``issues`` are what an
    ``EngineError`` or ``EngineUnavailable`` carried beside it, which the scheduler writes into the job log as lines of
    their own. ``str()`` gives the traceback, so a host that answers with a plain string still works."""

    text: str
    stderr_tail: str = ""
    issues: list[Any] | None = None

    def __str__(self) -> str:
        return self.text


def failure(exc: BaseException) -> Failure:
    """The ``Failure`` for an exception a job raised (it must be picklable: a process worker sends it back)."""
    text = "".join(traceback.format_exception(exc))
    tail = getattr(exc, "stderr_tail", "")
    issues = getattr(exc, "issues", None)
    return Failure(
        text,
        tail if isinstance(tail, str) else "",
        _plain(issues) if isinstance(issues, list) and issues else None,
    )


def _plain(issues: list[Any]) -> list[Any] | None:
    """``issues`` as JSON (zod's issues already are); ``None`` when they cannot be."""
    import json

    try:
        return json.loads(json.dumps(issues, allow_nan=False))
    except (TypeError, ValueError):
        return None


class NoEngine:
    """The ``rt.engine`` of a job that is not an engine job: every call raises ``EngineUnavailable``."""

    def __init__(self, why: str = "this job type does not run on the engine host") -> None:
        self.why = why

    def hello(self) -> dict[str, Any]:
        raise EngineUnavailable(self.why, reason="closed")

    def call(self, method: str, params: dict[str, Any], *, timeout_s: float = 30.0) -> dict[str, Any]:
        raise EngineUnavailable(self.why, reason="closed")

    def close(self) -> None:
        return None


class _DeadlineEngine:
    """The scheduler's engine as one job sees it: calls capped by the job's deadline; ``close`` does nothing (the
    engine is shared)."""

    def __init__(self, engine: EngineClient, deadline: float, cancel: threading.Event | None = None) -> None:
        self._engine = engine
        self._deadline = deadline
        self._cancel = cancel

    def hello(self) -> dict[str, Any]:
        return self._engine.hello()

    def call(self, method: str, params: dict[str, Any], *, timeout_s: float = 30.0) -> dict[str, Any]:
        left = self._deadline - time.monotonic()
        if left <= 0:
            raise EngineUnavailable("the job ran out of time before calling the engine", reason="timeout")
        if self._cancel is not None and getattr(self._engine, "supports_cancel", False):
            # a superseded job's call ends 1 s after the cancel (section 6), freeing its slot and its sidecar
            return self._engine.call(method, params, timeout_s=min(float(timeout_s), left), cancel=self._cancel)  # type: ignore[call-arg]
        return self._engine.call(method, params, timeout_s=min(float(timeout_s), left))

    def close(self) -> None:
        return None


class RunContext:
    """``region.core.protocols.RunCtx``: what ``run`` gets besides its inputs."""

    __slots__ = ("engine", "_progress", "_cancel", "_upstream")

    def __init__(
        self,
        engine: EngineClient,
        progress: Callable[[float, str], None],
        cancel: threading.Event,
        upstream: dict[str, Output],
    ) -> None:
        self.engine = engine
        self._progress = progress
        self._cancel = cancel
        self._upstream = upstream

    def progress(self, f: float, msg: str = "") -> None:
        self._progress(min(1.0, max(0.0, float(f))), str(msg))

    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def upstream(self, ref: str) -> Output:
        try:
            return self._upstream[ref]
        except KeyError:
            raise Invalid(f"{ref} was not declared with need() in plan") from None


def as_output(value: Any) -> Output:
    """Check what ``run`` returned: an ``Output`` (or an object with its four members)."""
    if isinstance(value, Output):
        return value
    if all(hasattr(value, m) for m in ("meta", "arrays", "blobs", "issues")):
        return Output(dict(value.meta), dict(value.arrays), dict(value.blobs), list(value.issues))
    raise Invalid(f"run returned {type(value).__name__}, not an Output")


@dataclass
class Task:
    """One run handed to a host."""

    job_id: str
    type_name: str
    job_type: Any
    module: str
    inputs: Any
    upstream: dict[str, Output]
    timeout_s: float
    on_end: Callable[[str, Any], None]
    on_progress: Callable[[float, str], None] = lambda f, m: None
    on_start: Callable[[int | None], None] = lambda pid: None
    cancel: threading.Event = field(default_factory=threading.Event)
    deadline: float = 0.0


def _run_here(task: Task, engine: EngineClient) -> tuple[str, Any]:
    rt = RunContext(engine, task.on_progress, task.cancel, task.upstream)
    try:
        out = as_output(task.job_type.run(task.inputs, rt))
    except BaseException as e:
        return "error", failure(e)
    return "ok", out


class _InProcess:
    """The thread and engine hosts: a fixed number of workers in this process."""

    def __init__(self, name: str, workers: int, engine: EngineClient | None) -> None:
        self.name = name
        self.capacity = max(1, int(workers))
        self.engine = engine
        self._lock = threading.Lock()
        self._busy = 0
        self._pool = ThreadPoolExecutor(self.capacity, thread_name_prefix=f"jobs-{name}")

    def busy(self) -> int:
        with self._lock:
            return self._busy

    def free(self) -> int:
        return self.capacity - self.busy()

    def _engine_for(self, task: Task) -> EngineClient:
        if self.engine is None:
            return NoEngine()
        return _DeadlineEngine(self.engine, task.deadline, task.cancel)

    def _work(self, task: Task) -> None:
        outcome, value = "error", "the host failed before the job ran"
        try:
            task.on_start(None)
            outcome, value = _run_here(task, self._engine_for(task))
        except BaseException:
            outcome, value = "error", traceback.format_exc()
        finally:
            with self._lock:
                self._busy -= 1
        task.on_end(outcome, value)

    def start(self, task: Task) -> None:
        with self._lock:
            self._busy += 1
        task.deadline = time.monotonic() + task.timeout_s
        try:
            self._pool.submit(self._work, task)
        except BaseException:
            with self._lock:
                self._busy -= 1
            raise

    def close(self, wait: bool = False) -> None:
        self._pool.shutdown(wait=wait, cancel_futures=True)


class ThreadHost(_InProcess):
    def __init__(self, workers: int) -> None:
        super().__init__("thread", workers, None)


class EngineHost(_InProcess):
    def __init__(self, workers: int, engine: EngineClient | None) -> None:
        super().__init__("engine", workers, engine)

    def _engine_for(self, task: Task) -> EngineClient:
        if self.engine is None:
            return NoEngine("no engine is configured for this hub")
        return _DeadlineEngine(self.engine, task.deadline, task.cancel)


class InlineHost:
    """Runs a job in the caller's thread (the dispatcher's): for work under 50 ms."""

    name = "inline"
    capacity = 1

    def __init__(self) -> None:
        self._busy = 0

    def busy(self) -> int:
        return self._busy

    def free(self) -> int:
        return 1 - self._busy

    def start(self, task: Task) -> None:
        self._busy += 1
        task.deadline = time.monotonic() + task.timeout_s
        outcome, value = "error", "the host failed before the job ran"
        try:
            task.on_start(None)
            outcome, value = _run_here(task, NoEngine())
        except BaseException:
            outcome, value = "error", traceback.format_exc()
        finally:
            self._busy -= 1
        task.on_end(outcome, value)

    def close(self, wait: bool = False) -> None:
        return None


# ------------------------------------------------------------------------------------------------ process host


def _worker_main(task_r: Any, res_w: Any) -> None:
    """The body of one worker process: run tasks from ``task_r``, answer on ``res_w``.

    A worker ignores Ctrl+C and Ctrl+Break: the console sends them to every process on it, the hub's workers
    included, and a job cut short that way would be recorded as failed (and its key cached as an error) before the
    hub had begun to stop. The hub stops its workers itself (``retire``)."""
    import signal

    for name in ("SIGINT", "SIGBREAK"):
        sig = getattr(signal, name, None)
        if sig is not None:
            try:
                signal.signal(sig, signal.SIG_IGN)
            except (OSError, ValueError):
                pass
    from . import registry as registry_mod

    tasks: queue.Queue = queue.Queue()
    tokens: dict[str, threading.Event] = {}
    lock = threading.Lock()

    def reader() -> None:
        while True:
            try:
                msg = task_r.recv()
            except (EOFError, OSError):
                # the scheduler died without retiring this worker (Windows does not kill orphans): exit now
                os._exit(0)
            if msg is None:
                tasks.put(None)
                return
            if msg[0] == "cancel":
                with lock:
                    ev = tokens.get(msg[1])
                if ev is not None:
                    ev.set()
            elif msg[0] == "run":
                with lock:
                    tokens[msg[1]] = threading.Event()
                tasks.put(msg)

    threading.Thread(target=reader, name="jobs-worker-reader", daemon=True).start()
    while True:
        msg = tasks.get()
        if msg is None:
            return
        _, job_id, module, name, inputs, upstream = msg
        with lock:
            token = tokens[job_id]

        def progress(f: float, m: str = "") -> None:
            res_w.send(("progress", float(f), str(m)))

        try:
            jt = registry_mod.find(module, name)
            rt = RunContext(NoEngine("process jobs have no engine"), progress, token, upstream)
            out = as_output(jt.run(inputs, rt))
            res_w.send(("done", out))
        except BaseException as e:
            with contextlib.suppress(Exception):
                res_w.send(("error", failure(e)))
        finally:
            with lock:
                tokens.pop(job_id, None)


class _Slot:
    def __init__(self, index: int) -> None:
        self.index = index
        self.proc: Any = None
        self.task_w: Any = None
        self.res_r: Any = None
        self.tasks = 0
        self.send_lock = threading.Lock()
        self.busy = False

    @property
    def pid(self) -> int | None:
        return self.proc.pid if self.proc is not None else None

    def alive(self) -> bool:
        return self.proc is not None and self.proc.is_alive()

    def ensure(self, ctx: Any) -> None:
        if self.alive():
            return
        self.discard()
        task_r, task_w = ctx.Pipe(duplex=False)
        res_r, res_w = ctx.Pipe(duplex=False)
        proc = ctx.Process(target=_worker_main, args=(task_r, res_w), name=f"crhub-job-{self.index}", daemon=True)
        proc.start()
        # the child holds its own ends now
        task_r.close()
        res_w.close()
        self.proc, self.task_w, self.res_r, self.tasks = proc, task_w, res_r, 0

    def send(self, msg: Any) -> None:
        with self.send_lock:
            self.task_w.send(msg)

    def kill(self) -> None:
        if self.proc is not None:
            with contextlib.suppress(Exception):
                self.proc.kill()
            with contextlib.suppress(Exception):
                self.proc.join(5)
        self.discard()

    def retire(self) -> None:
        """Ask the worker to exit (stdin closed), then kill it if it lingers."""
        if self.proc is not None:
            with contextlib.suppress(Exception):
                self.send(None)
            with contextlib.suppress(Exception):
                self.proc.join(2)
        self.kill()

    def discard(self) -> None:
        for conn in (self.task_w, self.res_r):
            if conn is not None:
                with contextlib.suppress(Exception):
                    conn.close()
        if self.proc is not None:
            with contextlib.suppress(Exception):
                self.proc.close()
        self.proc = self.task_w = self.res_r = None


class ProcessHost:
    """A pool of ``spawn`` worker processes (Windows-safe), one task per worker at a time."""

    name = "process"

    def __init__(self, workers: int, *, max_tasks_per_child: int = 50, kill_grace_s: float = 1.0) -> None:
        self.capacity = max(1, int(workers))
        self.max_tasks_per_child = max(1, int(max_tasks_per_child))
        self.kill_grace_s = float(kill_grace_s)
        self._ctx = multiprocessing.get_context("spawn")
        self._slots = [_Slot(i) for i in range(self.capacity)]
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(self.capacity, thread_name_prefix="jobs-process")
        self._closed = False

    def busy(self) -> int:
        with self._lock:
            return sum(1 for s in self._slots if s.busy)

    def free(self) -> int:
        return self.capacity - self.busy()

    def pids(self) -> list[int | None]:
        return [s.pid if s.alive() else None for s in self._slots]

    def start(self, task: Task) -> None:
        with self._lock:
            slot = next((s for s in self._slots if not s.busy), None)
            if slot is None:
                raise RuntimeError("no free process slot")
            slot.busy = True
        try:
            self._pool.submit(self._drive, slot, task)
        except BaseException:
            with self._lock:
                slot.busy = False
            raise

    def _drive(self, slot: _Slot, task: Task) -> None:
        outcome: str = "crashed"
        value: Any = "the worker process ended without an answer"
        try:
            slot.ensure(self._ctx)
            slot.send(("run", task.job_id, task.module, task.type_name, task.inputs, task.upstream))
            task.on_start(slot.pid)
            deadline = time.monotonic() + task.timeout_s
            task.deadline = deadline
            cancel_at: float | None = None
            while True:
                got = False
                try:
                    got = slot.res_r.poll(0.05)
                except (EOFError, OSError):
                    got = True
                if got:
                    try:
                        msg = slot.res_r.recv()
                    except (EOFError, OSError):
                        code = slot.proc.exitcode if slot.proc is not None else None
                        outcome, value = "crashed", f"the worker process died (exit code {code})"
                        slot.kill()
                        break
                    if msg[0] == "done":
                        outcome, value = "ok", msg[1]
                        break
                    if msg[0] != "progress":
                        outcome, value = "error", msg[1]
                        break
                    # a progress message: report it, then still check the token and the deadline below, so a job
                    # that reports more often than the poll interval can be cancelled and timed out
                    task.on_progress(msg[1], msg[2])
                if not slot.alive():
                    code = slot.proc.exitcode if slot.proc is not None else None
                    outcome, value = "crashed", f"the worker process died (exit code {code})"
                    slot.kill()
                    break
                now = time.monotonic()
                if task.cancel.is_set():
                    if cancel_at is None:
                        cancel_at = now
                        with contextlib.suppress(Exception):
                            slot.send(("cancel", task.job_id))
                    elif now - cancel_at >= self.kill_grace_s:
                        slot.kill()
                        outcome, value = "cancelled", f"killed {self.kill_grace_s:g} s after it was cancelled"
                        break
                if now >= deadline:
                    slot.kill()
                    outcome, value = "timeout", f"timed out after {task.timeout_s:g} s; the worker process was killed"
                    break
            if slot.alive():
                slot.tasks += 1
                if slot.tasks >= self.max_tasks_per_child:
                    slot.retire()
        except BaseException:
            outcome, value = "error", traceback.format_exc()
            slot.kill()
        finally:
            with self._lock:
                slot.busy = False
        task.on_end(outcome, value)

    def close(self, wait: bool = False) -> None:
        self._closed = True
        for slot in self._slots:
            if slot.busy:
                slot.kill()
            else:
                slot.retire()
        self._pool.shutdown(wait=wait, cancel_futures=True)


def pid_alive(pid: int | None) -> bool:
    """Whether a process id is running (for tests and doctor; POSIX and Windows)."""
    if not pid:
        return False
    if os.name == "nt":
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:  # a zombie (exited, not yet reaped) is not running
        with open(f"/proc/{pid}/stat", encoding="utf-8") as f:
            return f.read().rpartition(")")[2].split()[0] not in ("Z", "X")
    except (OSError, IndexError):
        return True


__all__ = [
    "EngineHost",
    "InlineHost",
    "NoEngine",
    "ProcessHost",
    "RunContext",
    "Task",
    "ThreadHost",
    "as_output",
    "pid_alive",
]
