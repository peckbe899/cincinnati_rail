"""The cache (WP3 exit tests ``test_cache.py``): shared results, undo hits, LRU eviction, and a wiped cache.db."""

from __future__ import annotations

import sqlite3

import numpy as np
import pytest

from region.core.errors import Invalid, NotFound
from region.core.view import View
from region.jobs import cache as cache_mod
from region.jobs.cache import Cache, decode_array, encode_array, remove_cache_files
from tests.jobs import jobtypes as jt
from tests.jobs.fakes import FakeStore
from tests.jobs.test_scheduler import running, settle, until

MAIN = View()
TRY = View("try")


def test_equal_scenario_content_shares_result(make_sched):
    store = FakeStore()
    store.add_layer("try")
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store)
    first = sched.submit("t.sum", "A", MAIN)
    assert sched.wait_job(first["job"])["state"] == "done"

    # the scenario holds nothing of its own: the same content, the same key, no run
    hit = sched.submit("t.sum", "A", TRY)
    assert hit == {"key": first["key"], "state": "hit", "job": None}
    assert jt.RUNS[("t.sum", "A")] == 1
    assert sched.result("t.sum", "A", TRY) == first["key"]

    # the scenario gets its own revision, then main reaches the same content: one result serves both
    store.set("thing", "A", {"v": 5}, layer="try")
    edited = sched.submit("t.sum", "A", TRY)
    assert sched.wait_job(edited["job"])["state"] == "done"
    store.set("thing", "A", {"v": 5})
    caught_up = sched.submit("t.sum", "A", MAIN)
    assert caught_up["state"] == "hit" and caught_up["key"] == edited["key"]
    assert jt.RUNS[("t.sum", "A")] == 2
    assert sched.result("t.sum", "A", MAIN) == sched.result("t.sum", "A", TRY) == edited["key"]

    # work in flight is shared too: the second view joins the running job
    store.set("thing", "B", {"v": 2})
    a = sched.submit("t.gated", "B", MAIN)
    until(lambda: running(sched, "t.gated", "B"), what="the job to run")
    b = sched.submit("t.gated", "B", TRY)
    assert b["state"] == "running" and b["job"] == a["job"] and b["key"] == a["key"]
    jt.gate("B").set()
    settle(sched)
    assert jt.RUNS[("t.gated", "B")] == 1
    assert sched.result("t.gated", "B", MAIN) == sched.result("t.gated", "B", TRY) == a["key"]


def test_undo_is_hit(make_sched):
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store)
    sched.watch_goal("t.sum", "A", MAIN)
    settle(sched)
    k1 = sched.result("t.sum", "A", MAIN)
    store.set("thing", "A", {"v": 2})
    sched.notify()
    settle(sched)
    k2 = sched.result("t.sum", "A", MAIN)
    assert k2 != k1 and jt.RUNS[("t.sum", "A")] == 2

    events = []
    sched.subscribe(lambda kind, payload: events.append((kind, payload)))
    store.set("thing", "A", {"v": 1})  # the undo
    sched.notify()
    settle(sched)
    assert sched.result("t.sum", "A", MAIN) == k1
    assert jt.RUNS[("t.sum", "A")] == 2, "the undo is a cache hit"
    results = [p for kind, p in events if kind == "result"]
    assert results == [
        {"key": k1, "type": "t.sum", "scope": "A", "view": "main|-|canon", "status": "ok", "changed": [[0.0, 0.0]]}
    ]
    assert not [p for kind, p in events if kind == "job" and p["state"] == "running"]


def test_lru_spares_pinned(make_sched):
    store = FakeStore()
    for i in range(4):
        store.set("thing", f"R{i}", {"v": i})
    sched = make_sched(store)
    keys = {}
    for i in range(4):
        out = sched.submit("t.sum", f"R{i}", MAIN)
        assert sched.wait_job(out["job"])["state"] == "done"
        keys[i] = out["key"]
    sched.pin("t.sum", "R1", MAIN)
    sched.read_array(keys[0], "v")  # R0 is now the most recently used
    assert sched.cache.total_bytes() == 4 * 8

    blob = {i: sched.cache.blob_path(sched.result_meta(keys[i])["arrays"]["v"]["sha256"]) for i in range(4)}
    assert all(p.is_file() for p in blob.values())
    out = sched.evict(16)
    assert out == {"results": 2, "blobs": 2, "bytes": 16}
    # R1 is pinned and R0 was used last: R2 and R3, the least recently used, are gone
    assert sched.read_array(keys[1], "v").tolist() == [1.0]
    assert sched.read_array(keys[0], "v").tolist() == [0.0]
    for i in (2, 3):
        with pytest.raises(NotFound):
            sched.read_array(keys[i], "v")
        assert not blob[i].exists()
        assert sched.result("t.sum", f"R{i}", MAIN) is None
    assert sched.result("t.sum", "R1", MAIN) == keys[1]

    # nothing pinned is evicted even when the budget asks for everything
    sched.evict(0)
    assert sched.read_array(keys[1], "v").tolist() == [1.0]
    with pytest.raises(NotFound):
        sched.read_array(keys[0], "v")

    # an evicted result is computed again on request
    again = sched.submit("t.sum", "R2", MAIN)
    assert again["state"] == "queued" and again["key"] == keys[2]
    assert sched.wait_job(again["job"])["state"] == "done"
    assert sched.read_array(keys[2], "v").tolist() == [2.0]


def test_cache_db_wipe_recomputes(make_sched, cache_path):
    store = FakeStore()
    store.set("thing", "A", {"v": 3})
    sched = make_sched(store)
    first = sched.submit("t.sum", "A", MAIN)
    sched.wait_job(first["job"])
    output_hash = sched.result_meta(first["key"])["output_hash"]
    blobs_dir = sched.cache.blobs_dir
    assert len([p for p in blobs_dir.rglob("*") if p.is_file()]) == 1
    sched.stop()

    removed = remove_cache_files(cache_path)
    assert cache_path in removed and not cache_path.exists()
    # a temp file a crash left behind
    (blobs_dir / "ab").mkdir(exist_ok=True)
    (blobs_dir / "ab" / ".abcd.123.tmp").write_bytes(b"partial")

    again = make_sched(store)
    # the sweep at start removed every blob without a row (all of them) and the temp file
    assert [p for p in blobs_dir.rglob("*") if p.is_file()] == []
    assert again.result("t.sum", "A", MAIN) is None
    out = again.submit("t.sum", "A", MAIN)
    assert out["state"] == "queued" and out["key"] == first["key"]
    assert again.wait_job(out["job"])["state"] == "done"
    assert again.result_meta(out["key"])["output_hash"] == output_hash
    assert again.read_array(out["key"], "v").tolist() == [3.0]
    assert cache_mod.read_array(out["key"], "v").tolist() == [3.0]
    assert jt.RUNS[("t.sum", "A")] == 2


def test_cache_attaches_and_arrays_round_trip(write_root, cache_path):
    cache = Cache(cache_path)
    truth = sqlite3.connect(write_root / "region.db")
    cache_mod.attach(truth, cache_path)
    assert truth.execute("SELECT COUNT(*) FROM cache.result").fetchone()[0] == 0
    assert truth.execute("SELECT MAX(version) FROM cache.schema_version").fetchone()[0] == cache_mod.SCHEMA_VERSION
    truth.close()

    for arr in (np.arange(6, dtype=">f8").reshape(2, 3), np.array([True, False]), np.zeros(0, dtype="<i4")):
        raw, dtype, shape = encode_array(arr)
        back = decode_array(raw, dtype, shape)
        assert back.dtype.byteorder in "<|=" and back.shape == arr.shape
        assert np.array_equal(back, arr)
    with pytest.raises(Invalid):
        encode_array(np.array([object()]))

    sha, size = cache.put_blob(b"hello")
    assert cache.blob_path(sha).read_bytes() == b"hello" and size == 5
    assert cache.put_blob(b"hello") == (sha, size)
    assert [p.name for p in cache.blob_path(sha).parent.iterdir()] == [sha]
    cache.close()
