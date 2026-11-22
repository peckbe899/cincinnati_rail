"""Clients of the TypeScript engine: ``Pool``, ``OneShot`` and ``Fake``, each an ``EngineClient`` (decision 9.20).

- ``Pool(size=2, timeout_s=30)`` keeps ``size`` long-lived sidecars (``node engine/src/sidecar.ts``) and gives each
  call the sidecar its key hashes to on a consistent-hash ring: the key is the call's section id (``params
  ["section_id"]``) unless ``key=`` says otherwise, so one section's calls always meet the same warm process. A call
  that times out kills its sidecar; a sidecar that dies fails its open calls with ``EngineUnavailable`` and is
  started again on the next call, after a backoff that doubles with each failure in a row (0.1 s to 5 s). Every
  sidecar must report the engine_build of the first, so ``hello()`` names the code behind every answer.
- ``OneShot()`` runs ``node engine/src/cli.ts <method> -`` once per call, with the params on stdin.
- ``Fake(responses)`` answers from a table, for tests of the jobs and the server.

The protocol is ``engine/PROTOCOL.md``: NDJSON over stdio, a hello first, replies by id. Python refuses an engine
whose hello names a contract major it does not know (``EngineUnavailable(reason="contract")``). An ``ok: false``
reply raises ``EngineError`` with the engine's code. Every error from a process carries the last lines of its stderr
as ``stderr_tail`` (an attribute, never part of the problem body Ben sees), for the job log.

Processes are started with an argument list (no shell), the repo root as working folder, and on Windows without a
console window. A sidecar exits on its own when its stdin closes, so ``close()`` (or this process dying) never
leaves one behind; ``close()`` kills any that do not exit within a second.
"""

from __future__ import annotations

import bisect
import collections
import hashlib
import json
import os
import subprocess
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path
from typing import Any

from region.core import paths
from region.core.errors import EngineError, EngineUnavailable, Invalid

from . import build

ProgressFn = Callable[[float, str], None]

STDERR_LINES = 40
HELLO_TIMEOUT_S = 15.0
CLOSE_WAIT_S = 1.0
BACKOFF_FIRST_S = 0.1
BACKOFF_MAX_S = 5.0
RING_POINTS = 64


def _config_timeout() -> float:
    cfg = paths.config().get("engine") or {}
    try:
        return float(cfg.get("timeout_s", 30.0))
    except (TypeError, ValueError):
        return 30.0


def _config_size() -> int:
    cfg = paths.config().get("pools") or {}
    try:
        return max(1, int(cfg.get("engine", 2)))
    except (TypeError, ValueError):
        return 2


def _engine_error(reply: dict[str, Any], stderr_tail: str = "") -> EngineError:
    err = reply.get("error") if isinstance(reply.get("error"), dict) else {}
    code = str(err.get("code") or "internal")
    message = str(err.get("message") or "the engine answered with an error")
    issues = err.get("issues")
    return EngineError(
        f"engine: {message}",
        engine_code=code,
        stack=str(err.get("stack") or ""),
        stderr_tail=stderr_tail,
        issues=list(issues) if isinstance(issues, list) else None,
    )


def _sidecar_argv(node: str) -> list[str]:
    return [node, str(build.ENGINE_DIR / build.SIDECAR)]


# ------------------------------------------------------------------------------------------------------- a sidecar


class _Sidecar:
    """One sidecar process: a writer under a lock, a reader thread that routes replies by id, and a stderr tail."""

    def __init__(self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str] | None, name: str) -> None:
        self.name = name
        self._tail: collections.deque[str] = collections.deque(maxlen=STDERR_LINES)
        self._pending: dict[int, tuple[Future[dict[str, Any]], ProgressFn | None]] = {}
        self._lock = threading.Lock()  # the open calls and the state
        self._wlock = threading.Lock()  # stdin, apart, so a long write never holds up the reader
        self._next_id = 1
        self._dead: EngineUnavailable | None = None
        self._culprit: int | None = None  # the call whose timeout killed the process; the others were bystanders
        self._hello: Future[dict[str, Any]] = Future()
        try:
            self.proc = subprocess.Popen(
                list(argv),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(cwd),
                env=dict(env) if env is not None else None,
                creationflags=build.NO_WINDOW,
            )
        except FileNotFoundError as e:
            raise EngineUnavailable(f"cannot start the engine: {e}", reason="no_node") from None
        except OSError as e:
            raise EngineUnavailable(f"cannot start the engine: {e}", reason="crashed") from None
        self._reader = threading.Thread(target=self._read, name=f"{name}-stdout", daemon=True)
        self._errreader = threading.Thread(target=self._read_err, name=f"{name}-stderr", daemon=True)
        self._reader.start()
        self._errreader.start()

    # --------------------------------------------------------------------------------------------------- reading

    def stderr_tail(self) -> str:
        return "\n".join(self._tail)

    def _read_err(self) -> None:
        assert self.proc.stderr is not None
        for raw in self.proc.stderr:
            self._tail.append(raw.decode("utf-8", "replace").rstrip("\r\n"))

    def _read(self) -> None:
        assert self.proc.stdout is not None
        try:
            for raw in self.proc.stdout:
                try:
                    msg = json.loads(raw)
                except ValueError:
                    self._tail.append(f"[not a protocol line] {raw[:200]!r}")
                    continue
                if not self._hello.done():
                    self._hello.set_result(msg)
                    continue
                if isinstance(msg, dict):
                    self._route(msg)
        finally:
            self._died()

    def _route(self, msg: dict[str, Any]) -> None:
        rid = msg.get("id")
        with self._lock:
            entry = self._pending.get(rid) if isinstance(rid, int) else None
            if entry is not None and "ok" in msg:
                del self._pending[rid]
        if entry is None:
            if msg.get("ok") is False and rid is None:
                self._tail.append(f"[engine refused a line] {msg.get('error')}")
            return
        fut, progress = entry
        if "ok" not in msg:
            if progress is not None and "progress" in msg:
                try:
                    progress(float(msg["progress"]), str(msg.get("stage", "")))
                except Exception:  # a progress callback must never break the reader
                    pass
            return
        if msg["ok"] is True:
            fut.set_result(msg.get("result"))
        else:
            fut.set_exception(_engine_error(msg, self.stderr_tail()))

    def _died(self) -> None:
        # stdout closed: the process exited or is exiting. Fail what is open. A process that outlives its stdout
        # is killed, so it can never linger without a reader.
        try:
            code = self.proc.wait(timeout=CLOSE_WAIT_S)
        except subprocess.TimeoutExpired:
            code = None
            try:
                self.proc.kill()
            except OSError:
                pass
        self._close_stdin()
        self._errreader.join(timeout=CLOSE_WAIT_S)
        with self._lock:
            if self._dead is None:
                self._dead = EngineUnavailable(
                    f"the engine sidecar {self.name} exited (code {code})",
                    reason="crashed",
                    stderr_tail=self.stderr_tail(),
                )
            dead = self._dead
            culprit = self._culprit
            pending = list(self._pending.items())
            self._pending.clear()
        if not self._hello.done():
            self._hello.set_exception(dead)
        for rid, (fut, _) in pending:
            if fut.done():
                continue
            if culprit is not None and rid != culprit:
                # killed for another call's timeout: this call did nothing wrong, so it is sent again to a fresh
                # sidecar (engine methods are pure) instead of failing, and caching, as that call's timeout
                fut.set_exception(
                    _NotSent(
                        EngineUnavailable(
                            f"the engine sidecar {self.name} was killed when another call timed out",
                            reason="crashed",
                            stderr_tail=dead.stderr_tail,
                        )
                    )
                )
            else:
                fut.set_exception(_copy_unavailable(dead))

    # --------------------------------------------------------------------------------------------------- calls

    @property
    def alive(self) -> bool:
        return self._dead is None and self.proc.poll() is None

    def hello(self, timeout_s: float) -> dict[str, Any]:
        try:
            return self._hello.result(timeout=timeout_s)
        except FutureTimeout:
            self.kill("timeout", f"the engine sidecar {self.name} sent no hello within {timeout_s:.0f} s")
            raise _copy_unavailable(self._dead_or_timeout()) from None

    def _dead_or_timeout(self) -> EngineUnavailable:
        return self._dead or EngineUnavailable("the engine timed out", reason="timeout")

    def call(
        self,
        method: str,
        params: Any,
        timeout_s: float,
        progress: ProgressFn | None,
        cancel: threading.Event | None = None,
    ) -> dict[str, Any]:
        """One call. ``_NotSent`` when the request never reached the process (it was already gone). With ``cancel``,
        a call still open ``CANCEL_GRACE_S`` after the event is set is ended: the process is killed (the other calls
        on it are sent again) and the call fails with ``EngineUnavailable(reason="cancelled")``."""
        fut: Future[dict[str, Any]] = Future()
        with self._lock:
            if self._dead is not None:
                raise _NotSent(self._dead)
            rid = self._next_id
            self._next_id += 1
        try:
            line = json.dumps({"id": rid, "method": method, "params": params}, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as e:
            raise Invalid(f"the params of {method} are not JSON: {e}") from None
        with self._lock:
            # checked again under the lock that _died drains the open calls with: a call registered after the
            # drain would otherwise wait out its whole timeout for a reply that cannot come
            if self._dead is not None:
                raise _NotSent(self._dead)
            self._pending[rid] = (fut, progress)
        try:
            assert self.proc.stdin is not None
            with self._wlock:
                self.proc.stdin.write(line.encode("utf-8") + b"\n")
                self.proc.stdin.flush()
        except (OSError, ValueError):
            with self._lock:
                self._pending.pop(rid, None)
            self.kill("crashed", f"the engine sidecar {self.name} stopped reading")
            self._close_stdin()
            raise _NotSent(self._dead_or_timeout()) from None
        end = time.monotonic() + timeout_s
        cancelled_at: float | None = None
        while True:
            left = end - time.monotonic()
            if cancel is not None and cancelled_at is None and cancel.is_set():
                cancelled_at = time.monotonic()
            if cancelled_at is not None:
                left = min(left, cancelled_at + CANCEL_GRACE_S - time.monotonic())
            if left <= 0:
                break
            try:
                return fut.result(timeout=min(left, CANCEL_POLL_S) if cancel is not None else left)
            except FutureTimeout:
                continue
        if cancelled_at is not None and time.monotonic() < end:
            detail = f"{method} was cancelled; the engine sidecar {self.name} was killed {CANCEL_GRACE_S:g} s later"
            self.kill("cancelled", detail, culprit=rid)
            raise EngineUnavailable(detail, reason="cancelled") from None
        detail = f"{method} took longer than {timeout_s:g} s; the engine sidecar {self.name} was killed"
        self.kill("timeout", detail, culprit=rid)
        raise _copy_unavailable(self._dead_or_timeout()) from None

    def kill(self, reason: str, detail: str, *, culprit: int | None = None) -> None:
        """Kill the process now; open calls fail with ``EngineUnavailable(reason)``. With ``culprit`` (the id of the
        call that timed out), the other open calls are sent again by the pool instead (``_NotSent``)."""
        with self._lock:
            if self._dead is None:
                self._dead = EngineUnavailable(detail, reason=reason, stderr_tail=self.stderr_tail())
                self._culprit = culprit
        try:
            self.proc.kill()
        except OSError:
            pass

    def _close_stdin(self) -> None:
        """Close the pipe to the process, ignoring a broken pipe. A dead process's pipe that still holds unsent
        bytes would otherwise raise BrokenPipeError again when it is garbage-collected, as noise on stderr."""
        try:
            if self.proc.stdin is not None:
                self.proc.stdin.close()
        except (OSError, ValueError):
            pass

    def close(self) -> None:
        """Close stdin (the sidecar exits on EOF); kill it if it has not exited within CLOSE_WAIT_S."""
        with self._lock:
            if self._dead is None:
                self._dead = EngineUnavailable("the engine client was closed", reason="closed")
        self._close_stdin()
        try:
            self.proc.wait(timeout=CLOSE_WAIT_S)
        except subprocess.TimeoutExpired:
            try:
                self.proc.kill()
                self.proc.wait(timeout=CLOSE_WAIT_S)
            except (OSError, subprocess.TimeoutExpired):
                pass
        self._reader.join(timeout=CLOSE_WAIT_S)


# A cancelled call (its job superseded) is ended this long after the cancel, as a process job is (section 6).
CANCEL_GRACE_S = 1.0
CANCEL_POLL_S = 0.05

# Refusals that no waiting changes: the pool answers them at once rather than sleeping out the crash backoff.
PERMANENT = frozenset({"no_node", "node_version", "contract"})


class _NotSent(Exception):
    """A call that never reached its sidecar (already dead): safe to send again to a fresh one."""

    def __init__(self, cause: EngineUnavailable) -> None:
        super().__init__(cause.detail)
        self.cause = cause


def _copy_unavailable(e: EngineUnavailable) -> EngineUnavailable:
    """A fresh exception per caller (one exception object must not be raised in two threads)."""
    return EngineUnavailable(e.detail, reason=e.reason, stderr_tail=e.stderr_tail)


# ------------------------------------------------------------------------------------------------------------ ring


class _Ring:
    """A consistent-hash ring over slots 0 .. size - 1: RING_POINTS points per slot, placed by sha256, so the slot of
    a key is the same in every process and moving to another pool size remaps only the keys it must."""

    def __init__(self, size: int) -> None:
        points = []
        for slot in range(size):
            for v in range(RING_POINTS):
                points.append((self._h(f"slot:{slot}:{v}"), slot))
        points.sort()
        self._keys = [p for p, _ in points]
        self._slots = [s for _, s in points]

    @staticmethod
    def _h(text: str) -> int:
        return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")

    def slot(self, key: str) -> int:
        i = bisect.bisect_left(self._keys, self._h(key))
        return self._slots[i % len(self._slots)]


# ------------------------------------------------------------------------------------------------------------ pool


class Pool:
    """A pool of ``size`` engine sidecars; see the module docstring.

    ``supports_cancel``: ``call`` takes a ``cancel`` event (the scheduler's engine host passes a job's token).

    ``node`` is the Node executable (``engine.node`` of the config by default) and ``argv`` replaces the whole
    sidecar command (tests use it to run a misbehaving sidecar). ``env`` is the children's environment (this
    process's by default). Thread-safe: calls from many threads share the sidecars, each multiplexing its open
    calls by id.
    """

    supports_cancel = True

    def __init__(
        self,
        size: int | None = 2,
        timeout_s: float | None = 30.0,
        *,
        node: str | os.PathLike[str] | None = None,
        argv: Sequence[str] | None = None,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        hello_timeout_s: float = HELLO_TIMEOUT_S,
        backoff_s: tuple[float, float] = (BACKOFF_FIRST_S, BACKOFF_MAX_S),
    ) -> None:
        self.size = int(size) if size is not None else _config_size()
        if self.size < 1:
            raise ValueError("a pool needs at least one sidecar")
        self.timeout_s = float(timeout_s) if timeout_s is not None else _config_timeout()
        self._node = node
        self._argv = list(argv) if argv is not None else None
        self._cwd = Path(cwd) if cwd is not None else paths.REPO
        self._env = env
        self._hello_timeout_s = hello_timeout_s
        self._backoff = backoff_s
        self._ring = _Ring(self.size)
        self._slots: list[_Sidecar | None] = [None] * self.size
        self._failures = [0] * self.size
        self._failed_at = [0.0] * self.size
        self._fail_reason: list[str | None] = [None] * self.size
        self._hellos: list[dict[str, Any] | None] = [None] * self.size
        self._locks = [threading.Lock() for _ in range(self.size)]
        self._build: str | None = None
        self._build_lock = threading.Lock()
        self._closed = False
        self.spawned = 0

    def __enter__(self) -> Pool:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _command(self) -> list[str]:
        if self._argv is not None:
            return list(self._argv)
        return _sidecar_argv(build.check_node(self._node))

    def start(self) -> dict[str, Any]:
        """Start every sidecar now (the server does this at start-up, so first calls are warm); the hello."""
        for slot in range(self.size):
            self._sidecar(slot)
        return self.hello()

    def slot_of(self, key: str) -> int:
        """The sidecar slot a key (a section id) is served by."""
        return self._ring.slot(key)

    def _sidecar(self, slot: int) -> _Sidecar:
        with self._locks[slot]:
            if self._closed:
                raise EngineUnavailable("the engine pool is closed", reason="closed")
            sc = self._slots[slot]
            if sc is not None and sc.alive:
                return sc
            if sc is not None:
                self._slots[slot] = None
            if self._failures[slot] and self._fail_reason[slot] not in PERMANENT:
                # back off after a sidecar that started and crashed; a configuration error (no Node, an old Node, a
                # contract mismatch) is answered at once instead, since waiting does not change it
                first, most = self._backoff
                wait = min(first * 2 ** (self._failures[slot] - 1), most)
                left = self._failed_at[slot] + wait - time.monotonic()
                if left > 0:
                    time.sleep(left)
            try:
                sc = _Sidecar(self._command(), cwd=self._cwd, env=self._env, name=f"engine-{slot}")
                self.spawned += 1
                hello = sc.hello(self._hello_timeout_s)
                try:
                    build.check_hello(hello)
                    self._pin_build(hello)
                except EngineUnavailable as e:
                    sc.kill("contract", e.detail)
                    raise EngineUnavailable(e.detail, reason="contract", stderr_tail=sc.stderr_tail()) from None
            except EngineUnavailable as e:
                self._failed(slot, e.reason)
                raise
            self._slots[slot] = sc
            self._hellos[slot] = hello
            return sc

    def _pin_build(self, hello: dict[str, Any]) -> None:
        """Hold every sidecar of the pool to the engine_build of the first one.

        Job keys carry the engine_build of ``hello()`` (9.19). A sidecar started later reads the engine source as it
        is then, so after a ``git pull`` under a running hub a respawned sidecar could answer with other code under
        the keys of the old build. Such a sidecar is refused (``EngineUnavailable(reason="contract")``) until the
        hub restarts.
        """
        got = str(hello["hello"].get("engine_build"))
        with self._build_lock:
            if self._build is None:
                self._build = got
            elif got != self._build:
                raise EngineUnavailable(
                    f"the engine source changed while the hub was running (engine_build {got[:12]}, "
                    f"started with {self._build[:12]}): restart the hub",
                    reason="contract",
                )

    def _failed(self, slot: int, reason: str | None = None) -> None:
        self._failures[slot] += 1
        self._failed_at[slot] = time.monotonic()
        self._fail_reason[slot] = reason

    def hello(self) -> dict[str, Any]:
        """The hello body of the engine (slot 0's sidecar, started if need be)."""
        self._sidecar(0)
        hello = self._hellos[0]
        assert hello is not None
        return dict(hello["hello"])

    def call(
        self,
        method: str,
        params: dict[str, Any],
        *,
        timeout_s: float | None = None,
        key: str | None = None,
        progress: ProgressFn | None = None,
        cancel: threading.Event | None = None,
    ) -> dict[str, Any]:
        """Call ``method`` on the sidecar of ``key`` (the params' ``section_id`` by default). ``cancel`` ends the call
        ``CANCEL_GRACE_S`` after it is set (see ``_Sidecar.call``)."""
        if key is None:
            sid = params.get("section_id") if isinstance(params, dict) else None
            key = str(sid) if sid is not None else method
        slot = self.slot_of(key)
        t = self.timeout_s if timeout_s is None else timeout_s
        for attempt in (1, 2):
            sc = self._sidecar(slot)
            try:
                result = sc.call(method, params, t, progress, cancel)
            except _NotSent as e:
                # the sidecar was gone before the request was written: start another and send it there, once
                self._failed(slot)
                if attempt == 2:
                    raise _copy_unavailable(e.cause) from None
                continue
            except EngineUnavailable:
                self._failed(slot)
                raise
            self._failures[slot] = 0
            return result
        raise AssertionError("unreachable")

    def pids(self) -> list[int | None]:
        """The process id of each slot's sidecar, or None (for tests and doctor)."""
        return [sc.proc.pid if sc is not None and sc.alive else None for sc in self._slots]

    def close(self) -> None:
        """Stop every sidecar: close its stdin, then kill it if it lingers."""
        self._closed = True
        for slot in range(self.size):
            with self._locks[slot]:
                sc, self._slots[slot] = self._slots[slot], None
            if sc is not None:
                sc.close()


# --------------------------------------------------------------------------------------------------------- oneshot


class OneShot:
    """One CLI process per call: ``node engine/src/cli.ts <method> -`` with the params on stdin.

    ``hello()`` starts the sidecar with its stdin already closed: it writes its hello and exits. The hello is read
    once and its contract majors checked before the first call. Each call runs the source as it is then, so a result
    stamped with another engine_build than the hello's (the source changed in between) is refused.
    """

    def __init__(
        self,
        timeout_s: float | None = 30.0,
        *,
        node: str | os.PathLike[str] | None = None,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.timeout_s = float(timeout_s) if timeout_s is not None else _config_timeout()
        self._node = node
        self._cwd = Path(cwd) if cwd is not None else paths.REPO
        self._env = dict(env) if env is not None else None
        self._hello: dict[str, Any] | None = None
        self._lock = threading.Lock()

    def __enter__(self) -> OneShot:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _run(self, argv: list[str], stdin: bytes | None, timeout_s: float) -> subprocess.CompletedProcess[bytes]:
        try:
            return subprocess.run(
                argv,
                input=stdin if stdin is not None else b"",
                capture_output=True,
                cwd=str(self._cwd),
                env=self._env,
                timeout=timeout_s,
                creationflags=build.NO_WINDOW,
            )
        except FileNotFoundError as e:
            raise EngineUnavailable(f"cannot start the engine: {e}", reason="no_node") from None
        except subprocess.TimeoutExpired as e:
            tail = (e.stderr or b"").decode("utf-8", "replace")[-4000:]
            raise EngineUnavailable(
                f"the engine took longer than {timeout_s:g} s and was killed", reason="timeout", stderr_tail=tail
            ) from None

    def hello(self) -> dict[str, Any]:
        with self._lock:
            if self._hello is None:
                node = build.check_node(self._node)
                r = self._run([node, str(build.ENGINE_DIR / build.SIDECAR)], None, self.timeout_s)
                tail = r.stderr.decode("utf-8", "replace")
                first = r.stdout.split(b"\n", 1)[0]
                try:
                    msg = json.loads(first)
                except ValueError:
                    raise EngineUnavailable(
                        f"the engine sent no hello (exit {r.returncode})", reason="crashed", stderr_tail=tail
                    ) from None
                try:
                    body = build.check_hello(msg)
                except EngineUnavailable as e:
                    raise EngineUnavailable(e.detail, reason=e.reason, stderr_tail=tail) from None
                self._hello = dict(body)
            return dict(self._hello)

    def call(self, method: str, params: dict[str, Any], *, timeout_s: float | None = None) -> dict[str, Any]:
        self.hello()
        node = build.check_node(self._node)
        payload = json.dumps(params, ensure_ascii=False, allow_nan=False).encode("utf-8")
        t = self.timeout_s if timeout_s is None else timeout_s
        r = self._run([node, str(build.ENGINE_DIR / build.CLI), method, "-"], payload, t)
        tail = r.stderr.decode("utf-8", "replace")
        lines = [ln for ln in r.stdout.split(b"\n") if ln.strip()]
        try:
            reply = json.loads(lines[-1]) if lines else None
        except ValueError:
            reply = None
        if not isinstance(reply, dict) or "ok" not in reply:
            raise EngineUnavailable(
                f"the engine CLI gave no reply (exit {r.returncode})", reason="crashed", stderr_tail=tail
            )
        if reply["ok"] is True:
            result = reply.get("result")
            stamped = result.get("engine_build") if isinstance(result, dict) else None
            if stamped is not None and stamped != self._hello_build():
                raise EngineUnavailable(
                    f"the engine source changed since this client read its hello (engine_build {str(stamped)[:12]}, "
                    f"hello {self._hello_build()[:12]}): make a new client",
                    reason="contract",
                    stderr_tail=tail,
                )
            return result  # type: ignore[return-value]
        raise _engine_error(reply, tail)

    def _hello_build(self) -> str:
        return str((self._hello or {}).get("engine_build"))

    def close(self) -> None:
        """Nothing stays running between calls."""


# ------------------------------------------------------------------------------------------------------------ fake


Response = Any  # a result dict, a callable(params) -> result, or an exception instance to raise


class Fake:
    """An ``EngineClient`` that answers from a table, for tests.

    ``responses`` maps a method (``"vertical.rail"`` or ``"vertical.rail@1"``) to a result, a callable taking the
    params and returning the result, or an exception instance, which is raised. A method missing from the table
    raises ``EngineError(engine_code="unknown_method")``. Every call is recorded in ``calls`` as ``(method, params)``.
    With ``validate=True`` the params of ``vertical.rail`` are checked against the generated SectionInput model and
    a failure raises ``EngineError(engine_code="invalid_input")``, as the engine would.
    """

    FAKE_BUILD = hashlib.sha256(b"region.enginehost.Fake").hexdigest()

    def __init__(
        self,
        responses: Mapping[str, Response] | None = None,
        *,
        hello: dict[str, Any] | None = None,
        validate: bool = False,
    ) -> None:
        self.responses: dict[str, Response] = dict(responses or {})
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.validate = validate
        self.closed = False
        methods = sorted(m if "@" in m else f"{m}@1" for m in self.responses)
        self._hello = hello or {
            "engine_version": "0.0.0-fake",
            "engine_build": self.FAKE_BUILD,
            "contracts": build.known_contracts(),
            "methods": methods,
        }

    def hello(self) -> dict[str, Any]:
        return dict(self._hello)

    def _lookup(self, method: str) -> Response:
        if method in self.responses:
            return self.responses[method]
        base = method.split("@", 1)[0]
        for name, value in self.responses.items():
            if name.split("@", 1)[0] == base and ("@" not in method or "@" not in name):
                return value
        raise EngineError(f"engine: no method {method}", engine_code="unknown_method")

    def call(self, method: str, params: dict[str, Any], *, timeout_s: float = 30.0, **_: Any) -> dict[str, Any]:
        if self.closed:
            raise EngineUnavailable("the fake engine was closed", reason="closed")
        self.calls.append((method, params))
        if self.validate and method.split("@", 1)[0] == "vertical.rail":
            from pydantic import ValidationError

            from region.contract.gen import SectionInput

            try:
                SectionInput.model_validate(params)
            except ValidationError as e:
                detail = f"engine: params do not match section_input: {e}"
                raise EngineError(detail, engine_code="invalid_input") from None
        value = self._lookup(method)
        if isinstance(value, BaseException):
            raise value
        if callable(value):
            return value(params)
        return value

    def close(self) -> None:
        self.closed = True


__all__ = ["Fake", "OneShot", "Pool", "ProgressFn"]
