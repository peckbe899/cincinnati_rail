"""One slot of each host stays free for the panes (I2.1, found by the live budget on a hub running a sheet's run).

The line sheet's run chain (the crossing lines, the structure, the fit, the run) is asked at priority 2 or 3, and
background goals at 5 and up. With every engine sidecar and process slot busy on that chain, the rail of the pane in
focus (priority 0, or 1 for an open pane) waited for a free one: a saved line file reached the open sheet in 3.2 to
3.5 s against the 3 s budget (2.0 s without the run). A job at priority 2 or more now takes a slot only while another
stays free, so the panes' rail never waits behind a run."""

from __future__ import annotations

import time

from region.core.view import View
from tests.jobs import jobtypes as jt
from tests.jobs.fakes import FakeStore
from tests.jobs.test_scheduler import running, settle, until

MAIN = View()


def test_a_pane_job_never_waits_behind_background_work(make_sched):
    store = FakeStore()
    for k in ("A", "B", "C"):
        store.set("thing", k, {"v": 1})
    sched = make_sched(store, threads=2)
    try:
        sched.watch_goal("t.gated", "A", MAIN, priority=2)
        sched.watch_goal("t.gated", "B", MAIN, priority=5)
        until(lambda: running(sched, "t.gated", "A"), what="the run-time job to start")
        # the second background job waits: one slot stays free for the panes
        time.sleep(0.3)
        assert running(sched, "t.gated", "B") is None
        sched.submit("t.gated", "C", MAIN, priority=0)
        until(lambda: running(sched, "t.gated", "C"), what="the pane's job to start at once")
        assert running(sched, "t.gated", "B") is None
    finally:
        for k in ("A", "B", "C"):
            jt.gate(k).set()
    settle(sched)
    assert all(sched.result("t.gated", k, MAIN) for k in ("A", "B", "C"))


def test_a_single_slot_host_still_runs_background_work(make_sched):
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store, threads=1)
    jt.gate("A").set()
    sched.watch_goal("t.gated", "A", MAIN, priority=5)
    settle(sched)
    assert sched.result("t.gated", "A", MAIN)
