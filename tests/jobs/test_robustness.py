"""Failure paths of the scheduler and the cache found in review: each test names the way things went wrong before.

- A process job that reports progress more often than the host polls its pipe was never timed out or killed.
- A result row whose blob file was gone made a downstream job loop for ever (plan, load, fail, plan again).
- Eviction could delete a blob file that a commit had just found and was about to name in its rows.
- A commit whose content had moved for its own goal, while another view still wanted the old key, left its goal with
  no job for the new content; a view that shared a running job and moved was never planned again.
- A failed ``COMMIT`` left the cache connection inside a transaction, so every later write failed.
- A host that refused to start a task left its job running for ever.
- Two connections creating the same fresh ``cache.db`` at once made one of them fail.
- A key holds what a plan read, not the scope id: ``noop`` echoed its scope, so a second free-text scope was shown the
  first one's text, and two seed scopes whose folders held the same files shared one result (one import skipped).
- Events pruned from the outbox past the cursor were never noticed, so the goals they touched stayed stale.
- A job whose end could not be recorded at all stayed ``running`` for ever: the heartbeat renewed every running row
  of its scheduler, whether or not it was still running anything.
"""

from __future__ import annotations

import sqlite3
import threading

from region.core.view import View
from region.jobs import cache as cache_mod
from tests.jobs import jobtypes as jt
from tests.jobs.fakes import FakeStore
from tests.jobs.test_scheduler import running, settle, until

MAIN = View()
TRY = View("try")


def test_chatty_process_job_still_times_out(make_sched):
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store)
    out = sched.submit("t.proc_chatty", "A", MAIN)
    until(lambda: sched.job(out["job"])["msg"] == "chatting", timeout=30, what="its progress to arrive")
    job = sched.wait_job(out["job"], timeout=15)
    assert job["state"] == "failed" and "timed out after 1 s" in (job["error"] or ""), job


def test_chatty_process_job_is_killed_after_cancel(make_sched):
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store)
    out = sched.submit("t.proc_chatty", "A", MAIN)
    until(lambda: (running(sched, "t.proc_chatty", "A") or {}).get("pid"), timeout=30, what="the worker to start")
    pid = sched.job(out["job"])["pid"]
    from region.jobs.hosts import pid_alive

    sched.cancel(out["job"])
    until(lambda: not pid_alive(pid), timeout=0.9 + 5, what="the chatty worker to be killed")
    assert sched.job(out["job"])["state"] == "cancelled"


def test_missing_upstream_blob_recomputes_upstream(make_sched):
    store = FakeStore()
    store.set("thing", "P", {"v": 3})
    store.set("note", "N", {"text": "n"})
    sched = make_sched(store)
    up = sched.submit("t.up", "P:N", MAIN)
    assert sched.wait_job(up["job"])["state"] == "done"
    sha = sched.result_meta(up["key"])["arrays"]["x"]["sha256"]
    sched.cache.blob_path(sha).unlink()  # lost behind the cache's back (a crash, a person, a race)

    down = sched.submit("t.down", "P:N", MAIN)
    assert down["job"] is not None
    settle(sched, timeout=20)
    assert sched.job(down["job"])["state"] == "done"
    assert sched.result_meta(sched.result("t.down", "P:N", MAIN))["meta"]["double"] == 6
    assert jt.RUNS[("t.up", "P:N")] == 2, "the upstream whose blob was lost ran again"
    assert sched.cache.blob_path(sha).is_file()


def test_eviction_between_blob_write_and_commit_keeps_the_blob(make_sched):
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    store.set("thing", "B", {"v": 1})  # the same array bytes as A
    sched = make_sched(store)
    first = sched.submit("t.sum", "A", MAIN)
    assert sched.wait_job(first["job"])["state"] == "done"

    real_put = sched.cache.put_blob
    evicted: list[dict] = []

    def put_then_evict(data: bytes):
        out = real_put(data)  # the file is there (A's), so nothing is written
        if not evicted:
            evicted.append(sched.evict(0))  # A goes, and with it the only row that kept the file
        return out

    sched.cache.put_blob = put_then_evict
    second = sched.submit("t.sum", "B", MAIN)
    assert sched.wait_job(second["job"])["state"] == "done"
    assert evicted and evicted[0]["results"] == 1
    assert sched.read_array(second["key"], "v").tolist() == [1.0]


def test_moved_own_goal_is_requeued_when_another_view_keeps_the_key(make_sched):
    store = FakeStore()
    store.add_layer("try")
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store)
    a = sched.submit("t.gated", "A", TRY)
    until(lambda: running(sched, "t.gated", "A"), what="the job to run")
    b = sched.submit("t.gated", "A", MAIN)
    assert b["job"] == a["job"]
    # the job's own view (try) moves; main still wants the key being computed
    store.set("thing", "A", {"v": 7}, layer="try")
    jt.gate("A").set()
    settle(sched)
    assert sched.result("t.gated", "A", MAIN) == a["key"]
    fresh = sched.result("t.gated", "A", TRY)
    assert fresh is not None and fresh != a["key"], "try's new content was computed"
    assert sched.result_meta(fresh)["meta"]["sum"] == 7


def test_moved_other_goal_is_requeued(make_sched):
    store = FakeStore()
    store.add_layer("try")
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store)
    a = sched.submit("t.gated", "A", MAIN)
    until(lambda: running(sched, "t.gated", "A"), what="the job to run")
    b = sched.submit("t.gated", "A", TRY)
    assert b["job"] == a["job"]
    # a view that shares the running job moves; the job's own view does not
    store.set("thing", "A", {"v": 7}, layer="try")
    jt.gate("A").set()
    settle(sched)
    assert sched.result("t.gated", "A", MAIN) == a["key"]
    fresh = sched.result("t.gated", "A", TRY)
    assert fresh is not None and fresh != a["key"], "try's new content was computed"
    assert sched.result_meta(fresh)["meta"]["sum"] == 7


class _FailCommitOnce:
    """Wraps a sqlite3 connection; the first ``COMMIT`` raises ``OperationalError``."""

    def __init__(self, con: sqlite3.Connection) -> None:
        self._con = con
        self.failed = False

    def execute(self, sql: str, *args):
        if sql == "COMMIT" and not self.failed:
            self.failed = True
            raise sqlite3.OperationalError("disk I/O error (injected)")
        return self._con.execute(sql, *args)

    def __getattr__(self, name: str):
        return getattr(self._con, name)


def test_failed_commit_does_not_wedge_the_cache(write_root):
    cache = cache_mod.Cache(write_root / "cache" / "cache.db")
    real = cache.con
    cache.con = _FailCommitOnce(real)
    try:
        with cache.tx() as con:
            con.execute("INSERT INTO cursor (name, seq, updated) VALUES ('x', 1, 'now')")
    except sqlite3.OperationalError:
        pass
    assert cache.con.failed
    assert not real.in_transaction
    cache.set_cursor("y", 2)  # a later write works
    assert cache.cursor("y") == 2 and cache.cursor("x") is None
    cache.con = real
    cache.close()


def test_host_that_cannot_start_fails_the_job(make_sched):
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    store.set("thing", "B", {"v": 2})
    sched = make_sched(store)
    host = sched.hosts["thread"]
    real_start = host.start
    calls: list[str] = []

    def refuse_once(task):
        if not calls:
            calls.append(task.job_id)
            raise RuntimeError("cannot start (injected)")
        return real_start(task)

    host.start = refuse_once
    bad = sched.wait_job(sched.submit("t.sum", "A", MAIN)["job"], timeout=10)
    assert bad["state"] == "failed" and "cannot start" in (bad["error"] or ""), bad
    good = sched.wait_job(sched.submit("t.sum", "B", MAIN)["job"], timeout=10)
    assert good["state"] == "done"


def test_concurrent_migrate_of_a_fresh_cache(write_root):
    errors: list[str] = []
    for trial in range(25):
        path = write_root / f"t{trial}" / "cache.db"
        barrier = threading.Barrier(6)

        def go(path=path, barrier=barrier) -> None:
            barrier.wait()
            try:
                assert cache_mod.migrate(path) == cache_mod.SCHEMA_VERSION
            except Exception as e:  # noqa: BLE001
                errors.append(repr(e))

        threads = [threading.Thread(target=go) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    assert errors == []


class _EchoScope:
    """Reads nothing and copies its scope id into its inputs: two scopes would share one key and one result."""

    name = "t.echo_scope"
    version = "1"
    scope = "any"
    host = "inline"
    priority = 9
    timeout_s = 5.0

    def plan(self, ctx, scope_id):
        return {"scope": scope_id}

    def run(self, inputs, rt):
        from region.core.protocols import Output

        return Output(meta=dict(inputs))


def test_contract_catches_inputs_the_key_does_not_hold():
    import pytest

    from region.jobs.contract import check_contract

    with pytest.raises(AssertionError, match="same key but different inputs"):
        check_contract(_EchoScope(), FakeStore(), "x")


def test_noop_scopes_that_read_nothing_share_a_result_that_names_no_scope(make_sched):
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store)
    x = sched.submit("noop", "hello x", MAIN)
    sched.wait_job(x["job"])
    y = sched.submit("noop", "hello y", MAIN)
    assert y["state"] == "hit" and y["key"] == x["key"]
    assert sched.result_meta(y["key"])["meta"] == {"hash": None}
    a = sched.submit("noop", "thing/A", MAIN)
    sched.wait_job(a["job"])
    assert sched.result_meta(a["key"])["meta"] == {"hash": store.get("thing", "A", MAIN)["hash"]}


def test_seed_import_scopes_with_equal_files_do_not_share(make_sched, hub_var):
    from region.jobs.registry import Registry
    from region.jobs.types.seed import SeedImport
    from tests.jobs.test_registry import FakeSeedApi

    (hub_var / "seed" / "main").mkdir(parents=True)
    (hub_var / "seed" / "proposals" / "x").mkdir(parents=True)
    api = FakeSeedApi()
    sched = make_sched(FakeStore(), registry=Registry([SeedImport(seed_api=api, seed_uri="var://seed")]))
    main = sched.submit("seed.import", "main", MAIN)
    assert sched.wait_job(main["job"])["state"] == "done"
    other = sched.submit("seed.import", "proposal:x", MAIN)
    assert other["state"] == "queued" and other["key"] != main["key"], "two empty folders are two inputs"
    assert sched.wait_job(other["job"])["state"] == "done"
    assert [c[2] for c in api.calls] == ["main", "proposal:x"]


def test_pruned_outbox_replans_every_goal(make_sched, cache_path):
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store)
    sched.watch_goal("t.sum", "A", MAIN)
    settle(sched)
    sched.stop()
    # while no scheduler follows the outbox, A changes and the event saying so is pruned
    store.set("thing", "A", {"v": 2})
    store.set("thing", "B", {"v": 9})
    store.prune(store.last_seq() - 1)
    assert store.min_seq() > 2
    again = make_sched(store, path=cache_path)
    settle(again)
    key = again.result("t.sum", "A", MAIN)
    assert again.result_meta(key)["meta"]["sum"] == 2


def test_job_whose_end_could_not_be_recorded_is_requeued(make_sched):
    # the cache could not take the result nor the failure (a long truth-DB write holding cache.db, say): the job
    # must not stay "running" for ever under a lease this scheduler keeps renewing
    store = FakeStore()
    store.set("thing", "A", {"v": 3})
    sched = make_sched(store, lease_s=1.0, heartbeat_s=0.2)
    real_commit, real_fail = sched._commit, sched._fail
    broken: list[str] = []

    def commit_once(row, *args):
        if not broken:
            broken.append(row["id"])
            raise RuntimeError("database is locked (injected)")
        return real_commit(row, *args)

    def fail_once(row, *args):
        if len(broken) == 1:
            broken.append("fail")
            raise RuntimeError("database is locked (injected)")
        return real_fail(row, *args)

    real_fail_row = sched._fail_row

    def fail_row_once(jid, *args):
        if len(broken) == 2:
            broken.append("fail_row")
            raise RuntimeError("database is locked (injected)")
        return real_fail_row(jid, *args)

    sched._commit, sched._fail, sched._fail_row = commit_once, fail_once, fail_row_once
    out = sched.submit("t.sum", "A", MAIN)
    job = sched.wait_job(out["job"], timeout=20)
    assert broken == [out["job"], "fail", "fail_row"]
    assert job["state"] == "done" and job["requeues"] == 1 and job["reason"] == "lease", job
    assert sched.result_meta(job["key"])["meta"]["sum"] == 3
