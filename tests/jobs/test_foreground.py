"""A live import and the panes' own work come first (I2.1, found by ``app/e2e/live.spec.ts``).

On a fresh hub the line sheet asks for its run as it opens. The run's cold chain (the crossing lines, the structure,
the fit, the assemble and the run) was planned and run while Ben's saved line file was imported: the import and the
focused section's solve shared the hub's time with it, and the file took 2.5 to 4.3 s to reach the open sheet
against its 3 s budget (2.0 to 2.2 s before the run times).

Now a live import holds the foreground (``Scheduler.foreground``). While it does, and until the invalidator has taken
in what it wrote, work at priority 2 and up waits: no such job starts, its planning stops at the next step, and the
invalidator and the job commits hand it to the background planner instead of planning it themselves. No such job
starts either while a job at the panes' priority (0 or 1) is queued or running."""

from __future__ import annotations

import threading
import time

from region.core.view import View
from tests.jobs import jobtypes as jt
from tests.jobs.fakes import FakeStore
from tests.jobs.test_scheduler import running, settle, until

MAIN = View()


def _sum(sched, scope: str) -> float | None:
    key = sched.result("t.sum", scope, MAIN)
    return None if key is None else sched.result_meta(key)["meta"]["sum"]


def test_background_jobs_wait_while_an_import_holds_the_foreground(make_sched):
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store, threads=2)
    with sched.foreground():
        sched.submit("t.sum", "A", MAIN, priority=2)
        time.sleep(0.3)
        assert jt.RUNS[("t.sum", "A")] == 0
    settle(sched)
    assert _sum(sched, "A") == 1.0


def test_a_pane_job_runs_during_the_import_and_background_work_waits_for_it(make_sched):
    store = FakeStore()
    for k in ("P", "B"):
        store.set("thing", k, {"v": 1})
    sched = make_sched(store, threads=3)
    with sched.foreground():
        sched.submit("t.gated", "P", MAIN, priority=0)
        until(lambda: running(sched, "t.gated", "P"), what="the pane's job to run during the import")
    th = threading.Thread(target=lambda: sched.submit("t.sum", "B", MAIN, priority=2))
    th.start()
    time.sleep(0.3)
    # the import is over, but the pane's job is still running: the background job waits for it
    assert jt.RUNS[("t.sum", "B")] == 0
    jt.gate("P").set()
    th.join(5)
    settle(sched)
    assert jt.RUNS[("t.sum", "B")] == 1
    assert jt.ORDER.index(("t.gated", "P")) < jt.ORDER.index(("t.sum", "B"))


def test_background_planning_stops_while_the_foreground_is_held(make_sched):
    store = FakeStore()
    store.set("thing", "C", {"v": 1})
    sched = make_sched(store)
    done = threading.Event()

    def ask() -> None:
        sched.submit("t.sum", "C", MAIN, priority=2)  # the sheet's run, asked over HTTP
        done.set()

    with sched.foreground():
        th = threading.Thread(target=ask)
        th.start()
        time.sleep(0.3)
        assert jt.PLANS[("t.sum", "C")] == 0 and not done.is_set()
    assert done.wait(5)
    th.join()
    settle(sched)
    assert _sum(sched, "C") == 1.0


def test_a_pane_asks_at_once_during_the_import(make_sched):
    store = FakeStore()
    store.set("thing", "D", {"v": 1})
    sched = make_sched(store)
    with sched.foreground():
        t0 = time.monotonic()
        out = sched.submit("t.sum", "D", MAIN, priority=0)
        assert time.monotonic() - t0 < 1.0 and out["state"] in ("queued", "running", "hit")
        settle(sched)
    assert _sum(sched, "D") == 1.0


def test_an_edit_re_plans_the_panes_goal_first_and_the_background_after_the_import(make_sched):
    store = FakeStore()
    for k in ("X", "A", "B"):
        store.set("thing", k, {"v": 1})
    sched = make_sched(store)
    sched.watch_goal("t.sum", "X+A", MAIN, priority=0)
    sched.watch_goal("t.sum", "X+B", MAIN, priority=5)
    settle(sched)
    jt.reset()
    with sched.foreground():
        store.set("thing", "X", {"v": 5})  # what the import writes
        sched.notify()
        until(lambda: _sum(sched, "X+A") == 6.0, what="the pane's goal to follow the import")
        time.sleep(0.3)
        # the background goal is not even planned again while the import holds the foreground
        assert jt.PLANS[("t.sum", "X+B")] == 0
    settle(sched)
    assert _sum(sched, "X+B") == 6.0


def test_background_work_goes_on_once_the_foreground_is_free(make_sched):
    store = FakeStore()
    store.set("thing", "E", {"v": 1})
    sched = make_sched(store)
    sched.watch_goal("t.sum", "E", MAIN, priority=5)
    settle(sched)
    store.set("thing", "E", {"v": 2})
    settle(sched)
    assert _sum(sched, "E") == 2.0
