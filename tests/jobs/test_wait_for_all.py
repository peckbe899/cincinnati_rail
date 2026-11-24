"""A job waiting on several upstreams is planned again once the last of them lands, not after each (I2.1, found on
a live hub).

The structure solve of a line waits on the crossing lines' solves (eleven for Line 6). Each one that landed planned
the waiting structure solve again (and with it the run chain's plans), eleven times in a row while the rest were
still running: on a cold hub that held the interpreter for seconds, and a saved line file reached the open sheet
in 2.7 s instead of 2.0 s. An upstream that lands while others the job waits on are still on their way now only
leaves the job waiting; the last one to land plans it."""

from __future__ import annotations

from typing import Any

from region.core.protocols import Output
from region.core.view import View
from region.jobs.registry import Registry, builtin_types
from tests.jobs import jobtypes as jt
from tests.jobs.fakes import FakeStore
from tests.jobs.test_scheduler import meta, running, settle, until

MAIN = View()


class Fan:
    """Needs ``t.gated`` of each record in its scope (``"A+B"``) and sums their sums."""

    name = "t.fan"
    version = "1"
    scope = "thing"
    host = "thread"
    priority = 1
    timeout_s = 30.0

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        return {"refs": [ctx.need("t.gated", k) for k in scope_id.split("+")]}

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        return Output(meta={"sum": sum(rt.upstream(r).meta["sum"] for r in inputs["refs"])})


FAN = Fan()


def test_a_waiting_job_is_planned_again_when_its_last_upstream_lands(make_sched):
    store = FakeStore()
    for k in ("A", "B", "C"):
        store.set("thing", k, {"v": 1})
    sched = make_sched(store, registry=Registry([*builtin_types(), *jt.JOB_TYPES, FAN]))
    replans: list[str] = []
    real = sched._ready

    def spy(*a, **kw):
        items = real(*a, **kw)
        replans.extend(it[1]["type"] for it in items if it[0] == "replan_job")
        return items

    sched._ready = spy
    try:
        sched.watch_goal("t.fan", "A+B+C", MAIN, priority=1)
        until(lambda: running(sched, "t.gated", "A") and running(sched, "t.gated", "B"), what="the upstreams")
        jt.gate("A").set()
        until(lambda: sched.result("t.gated", "A", MAIN) is not None, what="A to land")
        jt.gate("B").set()
        until(lambda: sched.result("t.gated", "B", MAIN) is not None, what="B to land")
        assert replans.count("t.fan") == 0, "A and B landed while C was still on its way"
        jt.gate("C").set()
        settle(sched)
    finally:
        for k in ("A", "B", "C"):
            jt.gate(k).set()
    assert replans.count("t.fan") == 1
    assert meta(sched, "t.fan", "A+B+C")["sum"] == 3
