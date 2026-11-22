"""What the live hub asks of the scheduler (checklist I2.0): a pane's focus raises its goal and its queued job and
hands them back; a background goal watched for ever stays so when a pane watches it for a while; pending marks; a
changed file re-plans exactly the goals that read it, wanted keys included (compute-5)."""

from __future__ import annotations

from region.core.view import View
from tests.jobs import jobtypes as jt
from tests.jobs.fakes import FakeStore
from tests.jobs.test_scheduler import settle, until

MAIN = View()


def _goal(sched, type_: str, scope: str) -> dict:
    return dict(sched.cache.one("SELECT * FROM goal WHERE type = ? AND scope = ?", (type_, scope)))


def test_focus_raises_a_queued_job_and_hands_it_back(make_sched) -> None:
    store = FakeStore()
    for s in ("A", "B", "C"):
        store.set("thing", s, {"v": 1})
    sched = make_sched(store, threads=1)
    # one job holds the only thread; the next two wait in the queue
    sched.watch_goal("t.gated", "A", MAIN, priority=5)
    until(lambda: any(j["state"] == "running" for j in sched.jobs()), what="A to run")
    sched.watch_goal("t.gated", "B", MAIN, priority=5)
    sched.watch_goal("t.gated", "C", MAIN, priority=5)
    sched.set_priority("t.gated", "C", MAIN, 0)  # Ben looks at C
    assert _goal(sched, "t.gated", "C")["priority"] == 0
    queued = {j["scope"]: j["priority"] for j in sched.jobs() if j["state"] == "queued"}
    assert queued == {"B": 5, "C": 0}
    pend = {(p["scope"], p["state"]) for p in sched.pending()}
    assert {("A", "running"), ("B", "queued"), ("C", "queued")} <= pend
    for s in ("A", "B", "C"):
        jt.gate(s).set()
    settle(sched)
    assert [s for n, s in jt.ORDER if n == "t.gated"] == ["A", "C", "B"]
    sched.set_priority("t.gated", "C", MAIN, 5)  # the pane closed
    assert _goal(sched, "t.gated", "C")["priority"] == 5
    assert sched.pending() == []


def test_a_goal_watched_for_ever_outlives_a_panes_watch(make_sched) -> None:
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store)
    assert sched.ensure_watched("t.sum", "A", MAIN, priority=5) is True
    assert sched.ensure_watched("t.sum", "A", MAIN, priority=5) is False
    sched.watch_goal("t.sum", "A", MAIN, priority=0, ttl_s=0.01)  # a pane, for a while
    g = _goal(sched, "t.sum", "A")
    assert g["expires"] is None and g["watch"] == 1 and g["priority"] == 0


def test_a_changed_file_re_plans_exactly_its_readers_pending_ones_too(make_sched, hub_var) -> None:
    src = hub_var / "t" / "in.txt"
    other = hub_var / "t" / "other.txt"
    src.parent.mkdir()
    src.write_text("one", encoding="utf-8")
    other.write_text("x", encoding="utf-8")
    store = FakeStore()
    sched = make_sched(store)
    sched.FILE_CHECK_S = 3600  # only the watcher's call checks files here
    sched.watch_goal("t.file_len", "t/in.txt", MAIN)
    sched.watch_goal("t.file_len", "t/other.txt", MAIN)
    settle(sched)
    src.write_text("three", encoding="utf-8")
    assert sched.files_changed([src.parent]) == {"file:var://t/in.txt"}
    settle(sched)
    key = sched.result("t.file_len", "t/in.txt", MAIN)
    assert sched.result_meta(key)["meta"]["len"] == 5
    # a re-save of the same bytes moves nothing
    src.write_text("three", encoding="utf-8")
    assert sched.files_changed([src]) == set()
