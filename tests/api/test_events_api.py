"""SSE (section 5, Events; decision 9.28): replay from Last-Event-ID, resync after a prune or a new epoch, writes
from another process within a second, ephemeral job and result events, heartbeats and the polling fallback."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import textwrap
import time

import httpx

from region.core import paths
from region.core.events import required_keys
from tests.api.conftest import KINDS, H, Live
from tests.api.sse import Stream


def _durable(s: Stream, n: int, timeout: float = 5.0) -> list[dict]:
    out = []
    while len(out) < n:
        m = s.until(lambda m: m["event"] in ("record", "changeset"), timeout)
        out.append(m)
    return out


def test_sse_replays_from_last_event_id(api, live):
    for t in ("a", "b", "c"):
        api.note(t)
    assert api.store.last_seq() == 6  # a record and a changeset event per note
    with Stream(live.url, last_event_id=2) as s:
        assert s.status == 200 and s.content_type.startswith("text/event-stream")
        hello = s.next()
        assert hello["event"] == "hello"
        assert required_keys("hello") <= set(hello["data"])
        assert hello["data"]["seq"] == 6
        replayed = _durable(s, 4)
        assert [m["id"] for m in replayed] == [3, 4, 5, 6]
        assert [m["event"] for m in replayed] == ["record", "changeset", "record", "changeset"]
        assert replayed[0]["data"]["seq"] == 3 and replayed[0]["data"]["kind"] == "note"
        # then live: the next write follows, once, with the next seq
        rec = api.note("d")
        live_msgs = _durable(s, 2)
        assert [m["id"] for m in live_msgs] == [7, 8]
        assert live_msgs[0]["data"]["id"] == rec["id"]
        assert not [m for m in s.drain(0.4) if m["event"] in ("record", "changeset")]


def test_stream_without_last_event_id_starts_at_the_hello(api, live):
    api.note("old")
    with Stream(live.url) as s:
        hello = s.next()
        assert hello["event"] == "hello" and hello["data"]["seq"] == 2
        assert hello["data"]["epoch"] == api.apps[-1].state.hub.epoch
        api.note("new")
        first = _durable(s, 1)[0]
        assert first["id"] == 3


def test_resync_after_prune_or_new_epoch(api, live):
    for t in ("a", "b", "c", "d"):
        api.note(t)  # events 1..8
    db = api.store.path
    con = sqlite3.connect(db, isolation_level=None)
    try:
        con.execute("DELETE FROM event WHERE seq <= 5")  # as maint.prune would
        # a client whose cursor (seq 2) was pruned away resyncs instead of replaying a gap
        with Stream(live.url, last_event_id=2) as s:
            assert s.next()["event"] == "hello"
            r = s.next()
            assert r["event"] == "resync" and r["data"] == {"reason": "pruned", "seq": 8}
            assert not [m for m in s.drain(0.3) if m["event"] in ("record", "changeset")]
        # a client whose cursor is still in the outbox replays (seq 5 is gone, 6 to 8 remain)
        with Stream(live.url, last_event_id=5) as s:
            assert s.next()["event"] == "hello"
            assert [m["id"] for m in _durable(s, 3)] == [6, 7, 8]
        # a new database epoch (a restore) under an open stream: resync, and the next hello names a new epoch
        with Stream(live.url) as s:
            first = s.next()
            assert first["event"] == "hello"
            con.execute("UPDATE meta SET value = '01NEWEPOCH0000000000000000' WHERE key = 'epoch'")
            r = s.until(lambda m: m["event"] == "resync", 3)
            assert r["data"] == {"reason": "epoch", "seq": 8}
        with Stream(live.url, last_event_id=8) as s:
            again = s.next()
            assert again["event"] == "hello" and again["data"]["epoch"] != first["data"]["epoch"]
        # a cursor past the end of this database (another database, or one restored to an older state)
        with Stream(live.url, last_event_id=50) as s:
            assert s.next()["event"] == "hello"
            assert s.next()["data"] == {"reason": "epoch", "seq": 8}
    finally:
        con.close()


def test_open_stream_resyncs_on_a_live_prune_and_on_overflow(api):
    from region.core.protocols import Op
    from region.core.view import View
    from region.model import open_store

    # a long poll, so the tailer moves only when poked; a queue of 4, so a burst overflows it
    live = Live(api.app(events={"poll_s": 30.0, "heartbeat_s": 15.0, "tiers_s": 3600, "queue": 4}))
    hub = live.app.state.hub
    try:
        with Stream(live.url) as s:
            assert s.next()["event"] == "hello"
            # writes the server's store does not hear of (another store on the file), then a prune past its cursor
            other = open_store(api.store.path, kinds_paths=KINDS, create=False)
            try:
                for t in ("a", "b", "c"):
                    other.put({"kind": "note", "id": None, "data": {"text": t}, "geom": None}, View(),
                              if_match=None, by="script")
            finally:
                other.close()
            last = api.store.last_seq()
            con = sqlite3.connect(api.store.path, isolation_level=None)
            try:
                con.execute("DELETE FROM event WHERE seq < ?", (last,))
            finally:
                con.close()
            hub.events.poke()
            r = s.until(lambda m: m["event"] in ("resync", "record", "changeset"), 5)
            assert r["event"] == "resync" and r["data"] == {"reason": "pruned", "seq": last}
            # a burst of 101 events into a queue of 4: the stream says resync instead of dropping events silently
            ops = [Op("create", "note", None, None, body={"data": {"text": str(i)}, "geom": None}) for i in range(100)]
            res = api.store.write(ops, View(), by="test", message="burst")
            msgs = s.drain(1.5)
            resyncs = [m for m in msgs if m["event"] == "resync"]
            assert resyncs and resyncs[0]["data"]["reason"] == "overflow", [m["event"] for m in msgs]
            assert resyncs[-1]["data"]["seq"] == res.seq
            tail = msgs[msgs.index(resyncs[-1]) + 1 :]
            assert not [m for m in tail if m["event"] in ("record", "changeset") and m["id"] <= res.seq]
            # and the stream goes on live after it
            rec = api.note("after")
            m = s.until(lambda m: m["event"] == "record", 5)
            assert m["data"]["id"] == rec["id"] and m["id"] == res.seq + 1
    finally:
        live.stop()


WRITER = textwrap.dedent(
    """
    import json, sys, time
    from pathlib import Path
    sys.path.insert(0, sys.argv[3])  # this checkout's region, whatever the interpreter has installed
    from region.core import fsio
    from region.core.view import View
    from region.model import open_store
    db, kinds = Path(sys.argv[1]), [Path(p) for p in json.loads(sys.argv[2])]
    with fsio.allow_writes(db.parent):
        store = open_store(db, kinds_paths=kinds, create=False)
        rec = store.put({"kind": "note", "id": None, "data": {"text": "from afar"}, "geom": None}, View(),
                        if_match=None, by="script")
        print(json.dumps({"id": rec["id"], "at": time.time()}), flush=True)
        store.close()
    """
)


def test_out_of_process_write_reaches_sse_within_1s(api, tmp_path):
    script = tmp_path / "writer.py"
    script.write_text(WRITER, encoding="utf-8")
    # the server's own timing (a 500 ms data_version check), not the shorter poll of the other tests here
    live = Live(api.app(events={"poll_s": 0.5, "heartbeat_s": 15.0, "tiers_s": 3600}))
    try:
        with Stream(live.url) as s:
            assert s.next()["event"] == "hello"
            for _ in range(3):
                out = subprocess.run(
                    [sys.executable, str(script), str(api.store.path), json.dumps([str(k) for k in KINDS]),
                     str(paths.REPO)],
                    cwd=paths.REPO,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                assert out.returncode == 0, out.stderr
                wrote = json.loads(out.stdout.strip().splitlines()[-1])
                m = s.until(lambda m, w=wrote: m["event"] == "record" and m["data"]["id"] == w["id"], 5)
                assert m["data"]["by"] == "script"
                assert m["at"] - wrote["at"] < 1.0, f"the event took {m['at'] - wrote['at']:.2f} s"
    finally:
        live.stop()


def test_job_and_result_events_and_heartbeat(api, live):
    rec = api.note("hello")
    with Stream(live.url) as s:
        assert s.next()["event"] == "hello"
        r = httpx.post(
            live.url + "/api/v1/compute",
            json={"type": "t.api_arr", "scope": f"note/{rec['id']}", "view": "main|-|canon"},
            headers=H,
        )
        assert r.status_code == 200 and r.json()["state"] in ("queued", "running", "hit")
        job = s.until(lambda m: m["event"] == "job", 5)
        assert job["id"] is None and job["data"]["type"] == "t.api_arr"
        res = s.until(lambda m: m["event"] == "result", 5)
        assert res["data"]["status"] == "ok" and res["data"]["key"] == r.json()["key"]
        assert res["data"]["changed"] == [[0.0, 18.0]]
        time.sleep(1.2)
        assert s.pings >= 1  # heartbeat_s is 0.5 in these tests


def test_tier_event_when_a_tier_appears(api):
    live = Live(api.app(events={"poll_s": 0.1, "heartbeat_s": 15.0, "tiers_s": 0.2}))
    hub = live.app.state.hub
    try:
        with Stream(live.url) as s:
            assert s.next()["event"] == "hello"
            deadline = time.monotonic() + 5
            while hub.events._tiers is None and time.monotonic() < deadline:  # the start-up scan is the baseline
                time.sleep(0.02)
            (api.root / "absent").mkdir()  # the root of tier "gone"
            (api.root / "absent" / "x.json").write_text("{}", encoding="utf-8")
            m = s.until(lambda m: m["event"] == "tier" and m["data"]["tier"] == "gone", 5)
            assert m["id"] is None and m["data"]["status"] in ("partial", "present")
            assert required_keys("tier") <= set(m["data"])
    finally:
        live.stop()


def test_poll_fallback(api, client):
    api.note("a")
    r = client.get("/api/v1/events/poll", params={"since": 0})
    body = r.json()
    assert r.status_code == 200 and body["seq"] == 2 and body["epoch"]
    assert [e["seq"] for e in body["events"]] == [1, 2]
    assert client.get("/api/v1/events/poll", params={"since": 2}).json()["events"] == []
    gone = client.get("/api/v1/events/poll", params={"since": 9}).json()["events"]
    assert gone == [{"seq": None, "type": "resync", "data": {"reason": "epoch", "seq": 2}}]
