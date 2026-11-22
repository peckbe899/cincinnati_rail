"""The scheduler (WP3 exit tests ``test_scheduler.py``): invalidation, early cutoff, coalescing, supersession,
priorities, failures, process timeouts, leases, no writes to inputs, and inputs that move during a run."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import threading
import time
from collections import Counter
from pathlib import Path

import pytest

from region.core.protocols import Op
from region.core.view import View
from region.jobs.hosts import RunContext, pid_alive
from region.jobs.plan import JobWriteRefused, PlanContext, ReadOnlyStore
from tests.jobs import jobtypes as jt
from tests.jobs.fakes import FakeEngine, FakeStore

REPO = Path(__file__).resolve().parents[2]
MAIN = View()


def settle(sched, timeout: float = 30.0) -> None:
    assert sched.wait_idle(timeout), f"not idle: {sched.jobs(active=True)}"


def until(cond, timeout: float = 20.0, what: str = "condition") -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cond():
            return
        time.sleep(0.01)
    raise AssertionError(f"timed out waiting for {what}")


def running(sched, type_: str, scope: str) -> dict | None:
    for j in sched.jobs(active=True):
        if j["type"] == type_ and j["scope"] == scope and j["state"] == "running":
            return j
    return None


def meta(sched, type_: str, scope: str, view: View = MAIN) -> dict:
    key = sched.result(type_, scope, view)
    assert key is not None, f"no result for {type_}/{scope}"
    return sched.result_meta(key)["meta"]


def test_edit_invalidates_exact_dependants(make_sched):
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    store.set("thing", "B", {"v": 2})
    sched = make_sched(store)
    events = []
    sched.subscribe(lambda kind, payload: events.append((kind, payload)))
    for scope in ("A", "B", "A+B"):
        sched.watch_goal("t.sum", scope, MAIN)
    settle(sched)
    assert jt.RUNS == Counter({("t.sum", "A"): 1, ("t.sum", "B"): 1, ("t.sum", "A+B"): 1})

    plans = Counter(jt.PLANS)
    events.clear()
    store.set("thing", "A", {"v": 10})
    sched.notify()
    settle(sched)
    assert jt.RUNS == Counter({("t.sum", "A"): 2, ("t.sum", "B"): 1, ("t.sum", "A+B"): 2})
    replanned = {scope for (name, scope), n in jt.PLANS.items() if n > plans[(name, scope)]}
    assert replanned == {"A", "A+B"}, "only the goals that read A are planned again"
    assert sched.read_array(sched.result("t.sum", "A+B", MAIN), "v").tolist() == [10.0, 2.0]
    assert meta(sched, "t.sum", "B")["sum"] == 2

    results = {p["scope"]: p for kind, p in events if kind == "result"}
    assert set(results) == {"A", "A+B"}
    assert results["A+B"]["changed"] == [[0.0, 0.0]] and results["A+B"]["view"] == "main|-|canon"
    assert all(p["status"] == "ok" for p in results.values())

    # a record nobody read, or a record of another kind, plans nothing
    plans = Counter(jt.PLANS)
    store.set("thing", "C", {"v": 5})
    store.set("note", "N", {"text": "x"})
    sched.notify()
    settle(sched)
    assert jt.PLANS == plans


def test_early_cutoff(make_sched):
    store = FakeStore()
    store.set("thing", "P", {"v": 3})
    store.set("note", "N", {"text": "first"})
    sched = make_sched(store)
    sched.watch_goal("t.down", "P:N", MAIN)
    settle(sched)
    assert jt.RUNS[("t.up", "P:N")] == 1 and jt.RUNS[("t.down", "P:N")] == 1
    assert meta(sched, "t.down", "P:N")["double"] == 6
    down_key = sched.result("t.down", "P:N", MAIN)

    # a note edit reruns the upstream (it read the note) but its output is the same: the downstream is a hit
    store.set("note", "N", {"text": "second"})
    sched.notify()
    settle(sched)
    assert jt.RUNS[("t.up", "P:N")] == 2
    assert jt.RUNS[("t.down", "P:N")] == 1
    assert sched.result("t.down", "P:N", MAIN) == down_key

    # a change the upstream's output shows reruns the downstream
    store.set("thing", "P", {"v": 4})
    sched.notify()
    settle(sched)
    assert jt.RUNS[("t.up", "P:N")] == 3 and jt.RUNS[("t.down", "P:N")] == 2
    assert meta(sched, "t.down", "P:N")["double"] == 8


def test_coalesce_burst(make_sched):
    store = FakeStore()
    store.set("thing", "G", {"v": 0})
    store.set("thing", "A", {"v": 0})
    sched = make_sched(store, threads=1)
    # the only thread is busy, so the goal's job stays queued while the burst arrives
    sched.submit("t.gated", "G", MAIN, priority=0)
    until(lambda: running(sched, "t.gated", "G"), what="the gate job to run")
    sched.watch_goal("t.sum", "A", MAIN)

    goal_view = MAIN.token()
    seen: list[int] = []
    stop = threading.Event()

    def watch_queue() -> None:
        while not stop.is_set():
            pending = [
                j
                for j in sched.jobs(active=True)
                if j["type"] == "t.sum" and j["scope"] == "A" and j["view"] == goal_view
            ]
            seen.append(len(pending))
            time.sleep(0.002)

    watcher = threading.Thread(target=watch_queue)
    watcher.start()
    try:
        for i in range(1, 21):
            store.set("thing", "A", {"v": i})
            sched.notify()
            time.sleep(0.003)
        final = sched.planner.plan("t.sum", "A", MAIN).key
        until(
            lambda: any(j["key"] == final for j in sched.jobs(active=True) if j["type"] == "t.sum"),
            what="the newest key to be queued",
        )
    finally:
        stop.set()
        watcher.join()
    assert seen and max(seen) == 1, "never more than one pending job per (type, scope, view)"
    superseded = [j for j in sched.jobs(active=False) if j["type"] == "t.sum" and j["state"] == "cancelled"]
    assert superseded, "older queued jobs were cancelled by newer ones"
    assert jt.RUNS[("t.sum", "A")] == 0

    jt.gate("G").set()
    settle(sched)
    assert jt.RUNS[("t.sum", "A")] == 1, "only the newest inputs ran"
    assert meta(sched, "t.sum", "A")["sum"] == 20


def test_supersede_cancels(make_sched):
    store = FakeStore()
    store.set("thing", "A", {"v": 1, "wait": 30})
    store.set("thing", "B", {"v": 1, "wait": 30})
    sched = make_sched(store)

    # a running thread job is cancelled by its token
    sched.watch_goal("t.slow", "A", MAIN)
    until(lambda: running(sched, "t.slow", "A"), what="the slow job to run")
    old = running(sched, "t.slow", "A")
    t0 = time.monotonic()
    store.set("thing", "A", {"v": 2, "wait": 0})
    sched.notify()
    settle(sched)
    assert time.monotonic() - t0 < 10
    assert sched.job(old["id"])["state"] == "cancelled"
    until(lambda: jt.CANCELLED[("t.slow", "A")] == 1, what="the old run to see its token")
    assert meta(sched, "t.slow", "A")["sum"] == 2

    # a running process job is killed 1 s after it is cancelled
    sched.watch_goal("t.proc_sleep", "B", MAIN)
    until(lambda: (running(sched, "t.proc_sleep", "B") or {}).get("pid"), what="the process job to start")
    old = running(sched, "t.proc_sleep", "B")
    pid = old["pid"]
    assert pid_alive(pid)
    t0 = time.monotonic()
    store.set("thing", "B", {"v": 5, "wait": 0})
    sched.notify()
    until(lambda: not pid_alive(pid), timeout=15, what="the worker to be killed")
    killed_after = time.monotonic() - t0
    assert 0.9 <= killed_after < 10
    settle(sched)
    assert sched.job(old["id"])["state"] == "cancelled"
    done = meta(sched, "t.proc_sleep", "B")
    assert done["sum"] == 5 and done["pid"] != pid


def test_priority_order(make_sched):
    store = FakeStore()
    store.set("thing", "G", {"v": 0})
    sched = make_sched(store, threads=1)
    sched.submit("t.gated", "G", MAIN, priority=0)
    until(lambda: running(sched, "t.gated", "G"), what="the gate job to run")
    for priority, scope in [(9, "P9"), (5, "P5"), (1, "P1"), (0, "P0"), (5, "P5b")]:
        store.set("thing", scope, {"v": priority})
        out = sched.submit("t.sum", scope, MAIN, priority=priority)
        assert out["state"] == "queued"
    jt.gate("G").set()
    settle(sched)
    order = [scope for name, scope in jt.ORDER if name == "t.sum"]
    assert order == ["P0", "P1", "P5", "P5b", "P9"]


def test_failure_does_not_stop_scheduler(make_sched):
    store = FakeStore()
    for rid, v in (("A", 13), ("B", 1), ("C", 13), ("D", -1)):
        store.set("thing", rid, {"v": v})
    sched = make_sched(store)
    sched.subscribe(lambda kind, payload: 1 / 0)  # a broken subscriber is logged, never fatal

    failed = sched.wait_job(sched.submit("t.raiser", "A", MAIN)["job"])
    assert failed["state"] == "failed" and "thirteen is unlucky" in failed["error"]
    assert sched.result_meta(failed["key"])["status"] == "error"
    assert sched.result("t.raiser", "A", MAIN) is None
    ok = sched.wait_job(sched.submit("t.raiser", "B", MAIN)["job"])
    assert ok["state"] == "done"

    # a worker process that dies fails its job; the next process job gets a fresh worker
    crashed = sched.wait_job(sched.submit("t.proc_crash", "C", MAIN)["job"], timeout=60)
    assert crashed["state"] == "failed" and "died" in crashed["error"]
    fine = sched.wait_job(sched.submit("t.proc_crash", "B", MAIN)["job"], timeout=60)
    assert fine["state"] == "done"

    # a plan that raises refuses the goal; once the input is fixed the invalidator plans it again
    with pytest.raises(ValueError):
        sched.watch_goal("t.plan_fails", "D", MAIN)
    store.set("thing", "D", {"v": 4})
    sched.notify()
    settle(sched)
    assert meta(sched, "t.plan_fails", "D")["sum"] == 4

    # the scheduler still answers
    store.set("thing", "A", {"v": 2})
    assert sched.wait_job(sched.submit("t.raiser", "A", MAIN)["job"])["state"] == "done"
    for name in ("jobs-dispatch", "jobs-invalidate", "jobs-monitor"):
        assert any(t.name == name and t.is_alive() for t in threading.enumerate())


def test_timeout_kills_process_job(make_sched):
    store = FakeStore()
    store.set("thing", "A", {"v": 1, "wait": 60})
    store.set("thing", "B", {"v": 2, "wait": 0})
    sched = make_sched(store)
    submitted = sched.submit("t.proc_timeout", "A", MAIN)
    until(lambda: (running(sched, "t.proc_timeout", "A") or {}).get("pid"), timeout=30, what="the worker to start")
    pid = sched.job(submitted["job"])["pid"]
    t0 = time.monotonic()
    job = sched.wait_job(submitted["job"], timeout=30)
    assert job["state"] == "failed" and "timed out after 1 s" in job["error"]
    assert time.monotonic() - t0 < 10
    until(lambda: not pid_alive(pid), timeout=10, what="the worker to be gone")

    nxt = sched.wait_job(sched.submit("t.proc_timeout", "B", MAIN)["job"], timeout=60)
    assert nxt["state"] == "done"
    assert meta(sched, "t.proc_timeout", "B")["pid"] != pid


def test_lease_expiry_requeues(make_sched, cache_path, write_root):
    # a scheduler in another process starts a job, then dies without a word
    child = subprocess.Popen(
        [sys.executable, "-m", "tests.jobs.lease_child", str(cache_path), str(write_root)],
        cwd=REPO,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        line = child.stdout.readline().strip()
        assert line.startswith("RUNNING "), child.stderr.read() if child.poll() is not None else line
        job_id = line.split()[1]
    finally:
        child.kill()
        child.wait(30)

    con = sqlite3.connect(cache_path)
    row = con.execute("SELECT state, lease_owner, requeues FROM job WHERE id = ?", (job_id,)).fetchone()
    assert row[0] == "running" and row[2] == 0
    # and a job whose lease already expired twice before
    con.execute(
        "INSERT INTO job (id, type, scope, view, key, state, priority, host, requeues, lease_owner, lease_until, "
        "created) VALUES ('01JOBTHATDIEDTHRICE0000000', 't.sum', 'Z', 'main|-|canon', ?, 'running', 1, 'thread', 2, "
        "'dead', 1.0, '2026-11-21T00:00:00Z')",
        ("d" * 64,),
    )
    con.commit()
    con.close()

    # the next scheduler finds the expired leases: the first job runs again here, the second fails
    jt.gate("A").set()
    store = FakeStore()
    store.set("thing", "A", {"v": 7, "wait": 600})  # the content the dead scheduler planned
    store.set("thing", "L", {"v": 1})
    sched = make_sched(store, lease_s=1.0, heartbeat_s=0.2)
    job = sched.wait_job(job_id, timeout=30)
    assert job["state"] == "done" and job["requeues"] == 1 and job["reason"] == "lease"
    assert sched.result_meta(job["key"])["meta"]["sum"] == 7
    dead = sched.wait_job("01JOBTHATDIEDTHRICE0000000", timeout=30)
    assert dead["state"] == "failed" and "lease expired 3 times" in dead["error"]

    # a live job's heartbeat keeps its lease: a job longer than the lease is not taken from it
    out = sched.submit("t.gated", "L", MAIN)
    until(lambda: running(sched, "t.gated", "L"), what="the long job to run")
    time.sleep(2.5)
    assert sched.job(out["job"])["requeues"] == 0 and sched.job(out["job"])["state"] == "running"
    jt.gate("L").set()
    assert sched.wait_job(out["job"], timeout=30)["state"] == "done"
    assert sched.job(out["job"])["requeues"] == 0


def test_jobs_cannot_write_inputs(make_sched):
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    store.set("thing", "P", {"v": 2})
    store.set("note", "N", {"text": "n"})
    before, writes = store.snapshot(), len(store.writes)
    sched = make_sched(store, engine=FakeEngine())

    job = sched.wait_job(sched.submit("t.vandal", "A", MAIN)["job"])
    assert job["state"] == "done", job
    found = sched.result_meta(job["key"])["meta"]
    assert found["v"] == 1
    assert "WROTE" not in found["plan"].values() and "WROTE" not in found["run"].values()
    # the vandal did reach the read-only store through the plan context, and every write was refused
    refused = {k: v for k, v in found["plan"].items() if k.endswith(".write")}
    assert refused and set(refused.values()) == {"JobWriteRefused"}
    # run sees an engine (none for a thread job), progress, its token and upstream outputs: nothing else
    assert jt.FOUND["run_attrs"] == ["_cancel", "_progress", "_upstream", "cancelled", "engine", "progress", "upstream"]
    assert found["engine"] == "EngineUnavailable"
    for name in ("write", "put", "patch", "delete", "revert", "restore", "apply_import", "store"):
        assert not hasattr(PlanContext, name) and not hasattr(RunContext, name)

    ro = ReadOnlyStore(store)
    assert ro.get("thing", "A", MAIN)["data"] == {"v": 1}
    with pytest.raises(JobWriteRefused):
        ro.write([Op("create", "thing", "X", None, body={"data": {}, "geom": None})], MAIN, by="x", message="x")
    with pytest.raises(JobWriteRefused):
        ro.patch("thing", "A", [], MAIN, if_match='"main:1"', by="x")
    with pytest.raises(JobWriteRefused):
        ro.store = store

    # a whole working session (goals, edits, invalidation, upstream jobs, commits) adds no write of its own
    sched.watch_goal("t.sum", "A+P", MAIN)
    sched.watch_goal("t.down", "P:N", MAIN)
    settle(sched)
    store.set("thing", "P", {"v": 3})
    sched.notify()
    settle(sched)
    assert meta(sched, "t.down", "P:N")["double"] == 6
    assert len(store.writes) == writes + 1, "the only write is the test's own edit"
    after = store.snapshot()
    after["main"].pop("P")
    before["main"].pop("P")
    assert after == before


def test_moved_inputs_mark_stale_and_requeue(make_sched):
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store)
    out = sched.submit("t.gated", "A", MAIN)
    until(lambda: running(sched, "t.gated", "A"), what="the job to run")
    first_key = out["key"]
    # the input moves while the job runs (a submit, not a watched goal, so nothing supersedes it)
    store.set("thing", "A", {"v": 2})
    jt.gate("A").set()
    settle(sched)

    stale = sched.result_meta(first_key)
    assert stale["status"] == "stale"
    new_key = sched.result("t.gated", "A", MAIN)
    assert new_key is not None and new_key != first_key
    fresh = sched.result_meta(new_key)
    assert fresh["status"] == "ok" and fresh["meta"]["sum"] == 2
    job = sched.job(out["job"])
    assert job["state"] == "done" and job["key"] == new_key, "the same job was re-queued with the new key"
    log = "\n".join(line["msg"] for line in sched.job_log(out["job"]))
    assert "inputs moved during the run" in log and "re-queued (stale)" in log
    assert jt.RUNS[("t.gated", "A")] == 2


def test_engine_host_and_inline_host(make_sched):
    store = FakeStore()
    store.set("thing", "A", {"v": 4})
    engine = FakeEngine(answer=lambda method, params: {"twice": params["v"] * 2})
    sched = make_sched(store, engine=engine)
    job = sched.wait_job(sched.submit("t.engine", "A", MAIN)["job"])
    assert job["state"] == "done"
    assert meta(sched, "t.engine", "A")["answer"] == {"twice": 8}
    method, params, timeout = engine.calls[-1]
    assert method == "vertical.rail" and params == {"v": 4} and 0 < timeout <= 30
    assert sched.result_meta(job["key"])["engine_build"] == engine.build

    inline = sched.wait_job(sched.submit("t.inline_sum", "A", MAIN)["job"])
    assert inline["state"] == "done" and meta(sched, "t.inline_sum", "A")["sum"] == 4

    # without an engine, an engine job cannot even be planned (no build for its key)
    from region.core.errors import EngineUnavailable

    bare = make_sched(store, path=sched.cache.path.parent / "other" / "cache.db")
    with pytest.raises(EngineUnavailable):
        bare.submit("t.engine", "A", MAIN)


def test_engine_stderr_tail_and_issues_reach_the_job_log(make_sched):
    from region.core.errors import EngineError, EngineUnavailable

    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    store.set("thing", "B", {"v": 2})
    issues = [{"code": "invalid_type", "path": ["stations", 0, "z_m"], "message": "Expected number"}]

    def answer(method, params):
        if params["v"] == 1:
            raise EngineError(
                "engine: invalid input", engine_code="invalid_input", stderr_tail="zod said no\n", issues=issues
            )
        raise EngineUnavailable("the engine died", reason="crashed", stderr_tail="Segmentation fault\n")

    sched = make_sched(store, engine=FakeEngine(answer=answer))
    bad = sched.wait_job(sched.submit("t.engine", "A", MAIN)["job"])
    assert bad["state"] == "failed"
    lines = [line["msg"] for line in sched.job_log(bad["id"])]
    assert any(m.startswith("error: ") and "EngineError" in m for m in lines)
    assert "engine stderr (last lines):\nzod said no" in lines
    assert any(m.startswith("engine issues: ") and '"Expected number"' in m for m in lines)

    dead = sched.wait_job(sched.submit("t.engine", "B", MAIN)["job"])
    assert dead["state"] == "failed"
    lines = [line["msg"] for line in sched.job_log(dead["id"])]
    assert "engine stderr (last lines):\nSegmentation fault" in lines
    assert not any(m.startswith("engine issues: ") for m in lines)

    # the same from a process worker: the failure crosses the pipe with its tail and issues
    proc = sched.wait_job(sched.submit("t.proc_engine_error", "A", MAIN)["job"], timeout=60)
    assert proc["state"] == "failed"
    lines = [line["msg"] for line in sched.job_log(proc["id"])]
    assert any(m.startswith("engine stderr (last lines):\nworker ") for m in lines)
    assert any(m.startswith("engine issues: ") and "from the worker" in m for m in lines)


def test_new_epoch_replans_every_goal_even_when_the_seqs_caught_up(make_sched):
    """A restore followed by new writes before the next poll leaves the outbox at the cursor again: only the store's
    new epoch shows that its history is another one."""
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    store.set("thing", "B", {"v": 1})
    sched = make_sched(store)
    old_revs, old_seq = store.snapshot(), store.last_seq()
    sched.watch_goal("t.sum", "A", MAIN)
    sched.watch_goal("t.sum", "B", MAIN)
    store.set("thing", "A", {"v": 2})
    store.set("thing", "B", {"v": 2})
    sched.notify()
    settle(sched)
    until(lambda: sched.cache.cursor("invalidator") == store.last_seq(), what="the invalidator to catch up")
    assert (meta(sched, "t.sum", "A")["sum"], meta(sched, "t.sum", "B")["sum"]) == (2, 2)
    cursor = sched.cache.cursor("invalidator")
    with store._lock:  # one step as the invalidator sees it: the restore, then two writes
        store.restore_db(old_revs, old_seq)
        store.set("thing", "A", {"v": 5})
        store.set("thing", "A", {"v": 6})
        assert store.last_seq() == cursor and store.events_since(cursor) == []  # the seqs alone show nothing
    sched.notify()

    def sums() -> tuple[int | None, int | None]:
        # a goal whose inputs moved has no result until its new key is computed (Scheduler.result plans again)
        keys = [sched.result("t.sum", s, MAIN) for s in ("A", "B")]
        return tuple(sched.result_meta(k)["meta"]["sum"] if k else None for k in keys)  # type: ignore[return-value]

    until(lambda: sums() == (6, 1), what="every goal re-planned after the new epoch")


def test_restored_outbox_replans_every_goal(make_sched):
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store)
    old_revs, old_seq = store.snapshot(), store.last_seq()
    store.set("thing", "A", {"v": 2})
    sched.watch_goal("t.sum", "A", MAIN)
    settle(sched)
    assert meta(sched, "t.sum", "A")["sum"] == 2
    # the truth DB is restored to before the edit: no event says so, the outbox just ends earlier
    store.restore_db(old_revs, old_seq)
    sched.notify()
    until(lambda: sched.result("t.sum", "A", MAIN) and meta(sched, "t.sum", "A")["sum"] == 1, what="a re-plan")
    settle(sched)
    # and the cursor follows the restored outbox from there
    store.set("thing", "A", {"v": 3})
    sched.notify()
    settle(sched)
    assert meta(sched, "t.sum", "A")["sum"] == 3


def test_worker_exits_when_its_scheduler_dies(cache_path, write_root):
    # Windows does not kill orphans: a worker whose scheduler is killed must leave by itself (task pipe EOF)
    child = subprocess.Popen(
        [sys.executable, "-m", "tests.jobs.lease_child", str(cache_path), str(write_root), "t.proc_sleep"],
        cwd=REPO,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        line = child.stdout.readline().strip()
        assert line.startswith("RUNNING "), child.stderr.read() if child.poll() is not None else line
        worker = int(line.split()[2])
        assert pid_alive(worker)
    finally:
        child.kill()
        child.wait(30)
    until(lambda: not pid_alive(worker), timeout=15, what="the orphaned worker to exit")
