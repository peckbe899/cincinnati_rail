"""The foreground never holds the background for long (I2.1 review of ``Scheduler.foreground``).

Three ways the background could wait far longer than ``BACKGROUND_WAIT_S``, or spin:

- the dispatcher handed a queued job whose key moved to the background planner, then picked the same job again at
  once, planned it again and handed it on again, over and over, until the background planner got to it;
- after a restore (the outbox back to an older seq), the invalidator's cursor stayed under the seq the last import
  ended at, so the foreground looked busy until that many new writes came;
- a background plan waited ``BACKGROUND_WAIT_S`` at each step it took while the foreground stayed busy, so a long
  plan could wait that long many times over."""

from __future__ import annotations

import threading
import time
from typing import Any

from region.core.view import View
from region.jobs import scheduler as scheduler_mod
from tests.jobs import jobtypes as jt
from tests.jobs.fakes import FakeStore
from tests.jobs.test_scheduler import settle, until

MAIN = View()


class SlowPlan(jt.Sum):
    """A background type whose plan takes a while between its reads (as the run's cold chain does)."""

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        out = []
        for rid in scope_id.split("+"):
            time.sleep(0.05)
            rec = ctx.read("thing", rid)
            out.append(None if rec is None else rec["data"])
        with jt.LOCK:
            jt.PLANS[(self.name, scope_id)] += 1
        return {"scope": scope_id, "data": out}


def _registry() -> Any:
    reg = jt.make_registry()
    reg.register(SlowPlan(name="t.slow_plan", priority=5))
    return reg


def test_the_dispatcher_does_not_pick_again_a_job_it_handed_to_the_background_planner(make_sched):
    store = FakeStore()
    store.set("thing", "M", {"v": 1})
    sched = make_sched(store, start=False)
    sched.submit("t.sum", "M", MAIN, priority=5)
    store.set("thing", "M", {"v": 2})  # the job's key moves; the invalidator has not re-planned it yet
    sched._plans.clear()
    # the background planner is busy with something else: alive, but it takes nothing from its heap
    free = threading.Event()
    busy = threading.Thread(target=free.wait, daemon=True)
    busy.start()
    sched._later_thread = busy
    try:
        jt.reset()
        assert sched._dispatch_one() is True  # planned, found moved, handed on
        for _ in range(5):
            sched._dispatch_one()
        assert jt.PLANS[("t.sum", "M")] == 1
        assert len(sched._later) == 1
    finally:
        free.set()
        busy.join(1)


def test_a_moved_job_handed_on_still_runs_with_its_new_inputs(make_sched):
    store = FakeStore()
    store.set("thing", "N", {"v": 1})
    sched = make_sched(store, start=False)
    sched.submit("t.sum", "N", MAIN, priority=5)
    store.set("thing", "N", {"v": 3})
    sched._plans.clear()
    sched.start()
    settle(sched)
    key = sched.result("t.sum", "N", MAIN)
    assert key is not None and sched.result_meta(key)["meta"]["sum"] == 3.0
    assert not sched._handed


def test_a_restore_after_an_import_does_not_hold_the_background(make_sched):
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store)
    old_revs, old_seq = store.snapshot(), store.last_seq()
    with sched.foreground():  # an import writes three records
        for v in (2, 3, 4):
            store.set("thing", "A", {"v": v})
    sched.notify()
    until(lambda: sched.cache.cursor("invalidator") == store.last_seq(), what="the invalidator to catch up")
    store.restore_db(old_revs, old_seq)  # the outbox goes back to before the import
    sched.notify()
    until(lambda: sched.cache.cursor("invalidator") == old_seq, what="the invalidator to follow the restore")
    store.set("thing", "B", {"v": 7})
    t0 = time.monotonic()
    sched.submit("t.sum", "B", MAIN, priority=5)
    until(lambda: sched.result("t.sum", "B", MAIN) is not None, timeout=30, what="the background job")
    assert time.monotonic() - t0 < 3.0


def test_a_background_plan_waits_for_the_foreground_once_not_at_every_step(make_sched, monkeypatch):
    monkeypatch.setattr(scheduler_mod, "BACKGROUND_WAIT_S", 0.4)
    store = FakeStore()
    scope = "A+B+C+D+E+F+G+H"
    for k in scope.split("+"):
        store.set("thing", k, {"v": 1})
    sched = make_sched(store, registry=_registry())
    held = threading.Event()
    release = threading.Event()

    def hold() -> None:  # a foreground that stays busy for the whole plan
        with sched.foreground():
            held.set()
            release.wait(30)

    th = threading.Thread(target=hold)
    th.start()
    try:
        assert held.wait(5)
        t0 = time.monotonic()
        sched.submit("t.slow_plan", scope, MAIN, priority=5)
        took = time.monotonic() - t0
    finally:
        release.set()
        th.join(5)
    # eight reads 50 ms apart: one wait of 0.4 s, not one at each read (about 3.6 s)
    assert took < 1.6, f"the plan took {took:.2f} s"
    settle(sched)
