"""``Scheduler.result`` answers the result of the goal's inputs as they are now (compute-1, compute-4): never an
older key after an edit, a failed re-run or an eviction; and eviction spares what watched goals show."""

from __future__ import annotations

from region.core.view import View
from tests.jobs.fakes import FakeStore
from tests.jobs.test_scheduler import settle

MAIN = View()
TRY = View("try")


def test_an_unwatched_goal_is_not_answered_with_a_key_its_inputs_left(make_sched):
    """compute-4 (1): the app submits without watch_s. After an edit, /results must not serve the old key."""
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store)
    first = sched.submit("t.sum", "A", MAIN)
    sched.wait_job(first["job"])
    assert sched.result("t.sum", "A", MAIN) == first["key"]
    store.set("thing", "A", {"v": 2})
    assert sched.result("t.sum", "A", MAIN) is None
    again = sched.submit("t.sum", "A", MAIN)
    sched.wait_job(again["job"])
    assert sched.result("t.sum", "A", MAIN) == again["key"] != first["key"]


def test_a_failed_rerun_is_not_answered_with_the_previous_result(make_sched):
    """compute-4 (2): a watched goal whose new run fails no longer answers the previous inputs' key."""
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store)
    sched.watch_goal("t.raiser", "A", MAIN)
    settle(sched)
    ok = sched.result("t.raiser", "A", MAIN)
    assert ok is not None
    store.set("thing", "A", {"v": 13})  # the raiser fails on 13
    sched.notify()
    settle(sched)
    assert sched.result("t.raiser", "A", MAIN) is None


def test_after_an_eviction_a_scenario_is_not_answered_with_mains_older_result(make_sched):
    """compute-1: try and main share key K1; an edit in try makes K2; K2 is evicted (least recently used). The
    answer for try is None, never K1 (main's rail from before the edit)."""
    store = FakeStore()
    store.add_layer("try")
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store)
    k1 = sched.submit("t.sum", "A", TRY)
    sched.wait_job(k1["job"])
    assert sched.submit("t.sum", "A", MAIN)["state"] == "hit"
    store.set("thing", "A", {"v": 5}, layer="try")
    k2 = sched.submit("t.sum", "A", TRY)
    sched.wait_job(k2["job"])
    sched.cache.touch(k1["key"])  # main's sheet reads K1 last
    sched.evict(8)
    assert sched.result("t.sum", "A", MAIN) == k1["key"]
    assert sched.result("t.sum", "A", TRY) is None


def test_eviction_spares_the_results_of_watched_goals(make_sched):
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    store.set("thing", "B", {"v": 2})
    sched = make_sched(store)
    sched.watch_goal("t.sum", "A", MAIN)
    b = sched.submit("t.sum", "B", MAIN)
    sched.wait_job(b["job"])
    settle(sched)
    watched = sched.result("t.sum", "A", MAIN)
    assert watched is not None
    sched.evict(0)
    assert sched.result("t.sum", "A", MAIN) == watched
    assert sched.result("t.sum", "B", MAIN) is None


def test_ctrl_c_on_the_console_does_not_fail_a_running_process_job(make_sched):
    """windows-9: the console sends Ctrl+C to every process on it, the spawn workers included. A worker running a
    job got KeyboardInterrupt and the job was recorded failed (its key cached as an error) before the hub stopped."""
    import os
    import signal

    from tests.jobs.test_scheduler import running, until

    store = FakeStore()
    store.set("thing", "A", {"v": 3, "wait": 1.5})
    sched = make_sched(store)
    out = sched.submit("t.proc_sleep", "A", MAIN)
    # the job reports progress once its worker runs it (a worker still starting Python is not yet protected)
    until(lambda: ((running(sched, "t.proc_sleep", "A") or {}).get("progress") or 0) > 0, what="the job to run")
    pid = running(sched, "t.proc_sleep", "A")["pid"]
    os.kill(pid, signal.SIGINT)
    job = sched.wait_job(out["job"], timeout=30)
    assert job["state"] == "done", job
    assert sched.result_meta(out["key"])["status"] == "ok"


def test_watched_goals_follow_a_changed_file_and_new_code_after_a_restart(make_sched, hub_var):
    """compute-5: nothing re-planned watched goals after a restart, and file: deps never invalidated. A watched goal
    on a file follows an edit of that file, and a restart re-plans it with the code as it is now."""
    import time as _time

    from tests.jobs.test_scheduler import until

    src = hub_var / "t" / "in.txt"
    src.parent.mkdir()
    src.write_text("one", encoding="utf-8")
    store = FakeStore()
    sched = make_sched(store)
    sched.FILE_CHECK_S = 0.05
    sched.watch_goal("t.file_len", "t/in.txt", MAIN, ttl_s=600)
    settle(sched)
    first = sched.result("t.file_len", "t/in.txt", MAIN)
    assert sched.result_meta(first)["meta"]["len"] == 3
    _time.sleep(0.02)
    src.write_text("three", encoding="utf-8")
    until(
        lambda: (k := sched.result("t.file_len", "t/in.txt", MAIN)) and sched.result_meta(k)["meta"]["len"] == 5,
        what="the watched goal to follow the file",
    )
    sched.stop()
    # a restart with other code for the type (its code hash moves the key): the goal is planned and run again
    from tests.jobs import jobtypes as jt

    jt.FILE_LEN.version = "2"
    try:
        again = make_sched(store)
        until(lambda: again.result("t.file_len", "t/in.txt", MAIN), what="the goal re-planned after the restart")
        assert again.result("t.file_len", "t/in.txt", MAIN) != first
    finally:
        jt.FILE_LEN.version = "1"


def test_a_goal_whose_content_moved_during_a_shared_run_gets_no_old_result_event(make_sched):
    """compute-10: try and main share a running job; Ben edits try before it ends. The commit stays valid through
    main's goal, but try must not get the pre-edit key as its latest nor an ok result event for it."""
    from tests.jobs import jobtypes as jt
    from tests.jobs.test_scheduler import running, until

    store = FakeStore()
    store.add_layer("try")
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store, poll_s=3600)
    events: list[dict] = []
    sched.subscribe(lambda kind, payload: events.append(dict(payload)) if kind == "result" else None)
    a = sched.submit("t.gated", "A", TRY)
    until(lambda: running(sched, "t.gated", "A"), what="the job to run")
    assert sched.submit("t.gated", "A", MAIN)["job"] == a["job"]
    store.set("thing", "A", {"v": 2}, layer="try")
    jt.gate("A").set()
    until(lambda: any(e["view"] == MAIN.token() for e in events), what="main's result event")
    assert not [e for e in events if e["view"] == TRY.token() and e["key"] == a["key"]]
    row = sched.cache.one("SELECT latest_key FROM goal WHERE type = 't.gated' AND view = ?", (TRY.token(),))
    assert row is None or row[0] != a["key"]
