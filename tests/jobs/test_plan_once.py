"""Two asks for the same job plan it once (I2.1, found by ``app/e2e/sheet.spec.ts`` "second context updates within
1 s").

Two tabs open on the same line in a new scenario each ask for the line's run as they open (``POST /compute`` with a
watch). Each ask planned the run twice (the submit, then the watch), and the second tab planned it all again: four
plans of the run's cold chain on the hub's one Python thread pool, while Ben saved in one tab and the other was to
show his level within a second. Now a watch needs no submit of its own, and an ask finds the plan the first one kept
while nothing it read has moved (the store's seq and epoch, its files, the engine build and its upstreams, as for an
upstream's plan)."""

from __future__ import annotations

from region.core.view import View
from tests.jobs import jobtypes as jt
from tests.jobs.fakes import FakeStore

MAIN = View()


def test_a_second_ask_for_the_same_job_reuses_its_plan(make_sched):
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store, start=False)
    first = sched.submit("t.sum", "A", MAIN, priority=2)
    assert jt.PLANS[("t.sum", "A")] == 1
    # the other tab's ask, and the watch of each ask
    again = sched.watch_goal("t.sum", "A", MAIN, priority=3, ttl_s=60)
    sched.submit("t.sum", "A", MAIN, priority=3)
    assert jt.PLANS[("t.sum", "A")] == 1
    assert again["key"] == first["key"] and again["job"] == first["job"]


def test_a_watch_answers_as_a_submit_does(make_sched):
    store = FakeStore()
    store.set("thing", "B", {"v": 1})
    sched = make_sched(store, start=False)
    out = sched.watch_goal("t.sum", "B", MAIN, priority=2, ttl_s=60)
    assert out["state"] == "queued" and out["job"] and out["key"]


def test_a_write_plans_the_job_again(make_sched):
    store = FakeStore()
    store.set("thing", "C", {"v": 1})
    sched = make_sched(store, start=False)
    a = sched.submit("t.sum", "C", MAIN, priority=2)
    store.set("thing", "C", {"v": 2})
    b = sched.submit("t.sum", "C", MAIN, priority=2)
    assert jt.PLANS[("t.sum", "C")] == 2
    assert b["key"] != a["key"]
