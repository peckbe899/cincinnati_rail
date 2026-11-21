"""Job types for the jobs tests. Module-level objects, so the process host's spawned workers find them by name.

Records are of kind ``thing`` with ``data.v`` (a number) and, for the slow types, ``data.wait`` (seconds). A scope
names records joined by ``+`` (``"A+B"``). Counters (``PLANS``, ``RUNS``, ``ORDER``) are per process: only the
in-process hosts (inline, thread, engine) can count runs here; process jobs report through their output.
"""

from __future__ import annotations

import os
import threading
import time
from collections import Counter
from typing import Any

import numpy as np

from region.core.protocols import Output

LOCK = threading.Lock()
PLANS: Counter = Counter()
RUNS: Counter = Counter()
ORDER: list[tuple[str, str]] = []
CANCELLED: Counter = Counter()
GATES: dict[str, threading.Event] = {}
FOUND: dict[str, Any] = {}


def reset() -> None:
    with LOCK:
        PLANS.clear()
        RUNS.clear()
        ORDER.clear()
        CANCELLED.clear()
        GATES.clear()
        FOUND.clear()


def gate(name: str) -> threading.Event:
    with LOCK:
        return GATES.setdefault(name, threading.Event())


def _values(ctx: Any, scope_id: str) -> list[Any]:
    out = []
    for rid in scope_id.split("+"):
        rec = ctx.read("thing", rid)
        out.append(None if rec is None else rec["data"])
    return out


class Sum:
    """Sums ``v`` of the scope's records; one array ``v`` on a 2 m grid."""

    version = "1"
    scope = "thing"

    def __init__(
        self,
        name: str = "t.sum",
        host: str = "thread",
        priority: int = 1,
        timeout_s: float = 30.0,
        axes: tuple[str, ...] = (),
    ) -> None:
        self.name = name
        self.host = host
        self.priority = priority
        self.timeout_s = timeout_s
        self.axes = axes

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        with LOCK:
            PLANS[(self.name, scope_id)] += 1
        return {"scope": scope_id, "data": _values(ctx, scope_id)}

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        with LOCK:
            RUNS[(self.name, inputs["scope"])] += 1
            ORDER.append((self.name, inputs["scope"]))
        vals = [float(d["v"]) if d else 0.0 for d in inputs["data"]]
        return Output(meta={"sum": sum(vals), "grid": {"c0": 0.0, "step_m": 2.0}}, arrays={"v": np.array(vals)})


class Timed(Sum):
    """Reads the timeline axis in plan."""

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        out = super().plan(ctx, scope_id)
        out["timeline"] = ctx.axis("timeline")
        return out


class Gated(Sum):
    """Waits for ``GATES[scope]`` (or a cancel) before summing."""

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        ev = gate(inputs["scope"])
        while not ev.wait(0.01):
            if rt.cancelled():
                with LOCK:
                    CANCELLED[(self.name, inputs["scope"])] += 1
                return Output(meta={"cancelled": True})
        return super().run(inputs, rt)


class Slow(Sum):
    """Runs ``wait`` seconds of its first record, checking its cancel token every 10 ms."""

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        with LOCK:
            RUNS[(self.name, inputs["scope"])] += 1
        wait = float((inputs["data"][0] or {}).get("wait", 0))
        end = time.monotonic() + wait
        while time.monotonic() < end:
            if rt.cancelled():
                with LOCK:
                    CANCELLED[(self.name, inputs["scope"])] += 1
                return Output(meta={"cancelled": True})
            time.sleep(0.01)
        vals = [float(d["v"]) if d else 0.0 for d in inputs["data"]]
        return Output(meta={"sum": sum(vals)}, arrays={"v": np.array(vals)})


class Raiser(Sum):
    """Raises when the first record's ``v`` is 13."""

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        if (inputs["data"][0] or {}).get("v") == 13:
            raise RuntimeError("thirteen is unlucky")
        return super().run(inputs, rt)


class PlanFails(Sum):
    """Its plan raises when the first record's ``v`` is negative."""

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        out = super().plan(ctx, scope_id)
        if (out["data"][0] or {}).get("v", 0) < 0:
            raise ValueError("negative v cannot be planned")
        return out


class ProcSleep(Sum):
    """A process job: sleeps ``wait`` seconds without looking at its token, then returns its pid."""

    def __init__(self, name: str, timeout_s: float) -> None:
        super().__init__(name=name, host="process", timeout_s=timeout_s)

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        wait = float((inputs["data"][0] or {}).get("wait", 0))
        rt.progress(0.1, "sleeping")
        time.sleep(wait)
        vals = [float(d["v"]) if d else 0.0 for d in inputs["data"]]
        return Output(meta={"sum": sum(vals), "pid": os.getpid()}, arrays={"v": np.array(vals)})


class ProcCrash(Sum):
    """A process job whose worker dies when ``v`` is 13."""

    def __init__(self) -> None:
        super().__init__(name="t.proc_crash", host="process", timeout_s=30.0)

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        if (inputs["data"][0] or {}).get("v") == 13:
            os._exit(3)
        return Output(meta={"pid": os.getpid()})


class ProcChatty(Sum):
    """A process job that reports progress every 5 ms for ever and never looks at its token."""

    def __init__(self) -> None:
        super().__init__(name="t.proc_chatty", host="process", timeout_s=1.0)

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        while True:
            rt.progress(0.5, "chatting")
            time.sleep(0.005)


class Up:
    """Upstream of ``t.down``. Scope ``"P:N"``: reads thing P and note N, but its output depends on P only."""

    name = "t.up"
    version = "1"
    scope = "thing"
    host = "thread"
    priority = 1
    timeout_s = 30.0

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        p, n = scope_id.split(":")
        rec = ctx.read("thing", p)
        note = ctx.read("note", n)
        with LOCK:
            PLANS[(self.name, scope_id)] += 1
        return {"scope": scope_id, "v": rec["data"]["v"] if rec else 0, "note": note["data"] if note else None}

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        with LOCK:
            RUNS[(self.name, inputs["scope"])] += 1
        return Output(meta={"p": inputs["v"]}, arrays={"x": np.array([inputs["v"]], dtype=float)})


class Down:
    """Doubles ``t.up``'s output: depends on the upstream only through its output hash."""

    name = "t.down"
    version = "1"
    scope = "thing"
    host = "thread"
    priority = 1
    timeout_s = 30.0

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        with LOCK:
            PLANS[(self.name, scope_id)] += 1
        return {"scope": scope_id, "ref": ctx.need("t.up", scope_id)}

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        with LOCK:
            RUNS[(self.name, inputs["scope"])] += 1
        up = rt.upstream(inputs["ref"])
        return Output(meta={"double": up.meta["p"] * 2, "x": float(up.arrays["x"][0])})


class Vandal:
    """Tries every way to write the store from plan and from run, and reports what it found."""

    name = "t.vandal"
    version = "1"
    scope = "thing"
    host = "thread"
    priority = 1
    timeout_s = 30.0

    @staticmethod
    def _attempt(obj: Any, label: str, out: dict[str, str]) -> None:
        from region.core.protocols import Op
        from region.core.view import View

        for method in ("write", "put", "patch", "delete", "revert", "restore", "apply_import"):
            fn = getattr(obj, method, None)
            if fn is None:
                continue
            try:
                if method == "write":
                    fn(
                        [Op("create", "thing", "EVIL", None, body={"data": {"v": 666}, "geom": None})],
                        View(),
                        by="vandal",
                        message="vandal",
                    )
                elif method == "put":
                    fn(
                        {"kind": "thing", "id": "EVIL", "data": {"v": 666}, "geom": None},
                        View(),
                        if_match=None,
                        by="vandal",
                    )
                else:
                    fn("thing", "A", [], View(), if_match='"main:1"', by="vandal")
                out[f"{label}.{method}"] = "WROTE"
            except Exception as e:
                out[f"{label}.{method}"] = type(e).__name__

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        found: dict[str, str] = {}
        self._attempt(ctx, "ctx", found)
        for name in dir(ctx):
            if name.startswith("__"):
                continue
            try:
                value = getattr(ctx, name)
            except Exception:
                continue
            self._attempt(value, f"ctx.{name}", found)
            for inner in dir(value):
                if inner.startswith("__"):
                    continue
                try:
                    self._attempt(getattr(value, inner), f"ctx.{name}.{inner}", found)
                except Exception:
                    continue
        rec = ctx.read("thing", scope_id)
        return {"scope": scope_id, "v": rec["data"]["v"] if rec else None, "plan": found}

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        found: dict[str, str] = {}
        self._attempt(rt, "rt", found)
        for name in dir(rt):
            if name.startswith("__"):
                continue
            try:
                self._attempt(getattr(rt, name), f"rt.{name}", found)
            except Exception:
                continue
        with LOCK:
            FOUND["run_attrs"] = sorted(n for n in dir(rt) if not n.startswith("__"))
        try:
            rt.engine.call("vertical.rail", {})
            engine = "answered"
        except Exception as e:
            engine = type(e).__name__
        return Output(meta={"plan": inputs["plan"], "run": found, "engine": engine, "v": inputs["v"]})


class EngineJob:
    """An engine job: sends ``v`` to the engine and returns its answer."""

    name = "t.engine"
    version = "1"
    scope = "thing"
    host = "engine"
    priority = 1
    timeout_s = 30.0

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        rec = ctx.read("thing", scope_id)
        return {"v": rec["data"]["v"] if rec else None}

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        return Output(meta={"answer": rt.engine.call("vertical.rail", {"v": inputs["v"]})})


SUM = Sum()
INLINE_SUM = Sum(name="t.inline_sum", host="inline")
TIMELESS = Sum(name="t.timeless")
TIMED = Timed(name="t.timed")
YEARLY = Sum(name="t.yearly", axes=("year",))
GATED = Gated(name="t.gated")
SLOW = Slow(name="t.slow")
RAISER = Raiser(name="t.raiser")
PLAN_FAILS = PlanFails(name="t.plan_fails")
PROC_SLEEP = ProcSleep("t.proc_sleep", timeout_s=30.0)
PROC_TIMEOUT = ProcSleep("t.proc_timeout", timeout_s=1.0)
PROC_CRASH = ProcCrash()
PROC_CHATTY = ProcChatty()
UP = Up()
DOWN = Down()
VANDAL = Vandal()
ENGINE_JOB = EngineJob()

JOB_TYPES = [
    SUM,
    INLINE_SUM,
    TIMELESS,
    TIMED,
    YEARLY,
    GATED,
    SLOW,
    RAISER,
    PLAN_FAILS,
    PROC_SLEEP,
    PROC_TIMEOUT,
    PROC_CRASH,
    PROC_CHATTY,
    UP,
    DOWN,
    VANDAL,
    ENGINE_JOB,
]


def make_registry():
    """The built-in job types plus every type of this module."""
    from region.jobs.registry import Registry, builtin_types

    return Registry([*builtin_types(), *JOB_TYPES])
