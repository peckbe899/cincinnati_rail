"""The live hub's routes and words: GET /live, Pause live, Undo this import, pane focus, the source event over SSE,
and what a change is called in Ben's terms."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from region.core import ids
from region.core.view import View
from region.live import words as W
from tests.api.conftest import BASE, Api, H, Live
from tests.api.sse import Stream


class Notes:
    """An importer of notes on ``import:test`` from one JSON file (``{key: text}``)."""

    name = "fake_notes"
    version = "1"
    layer = "import:test"
    namespace = "test"
    from_git = ()

    def __init__(self, src: Path) -> None:
        self.src = src

    def sources(self, _paths: Any) -> dict[str, str]:
        return {"notes": "var://src/notes.json"}

    def records(self, local: dict[str, Path], _ids: Any):
        for key, text in json.loads(Path(local["notes"]).read_text(encoding="utf-8")).items():
            yield {"kind": "note", "id": ids.stable("test", key), "data": {"text": text}, "geom": None}


@pytest.fixture
def live_api(api: Api, hub_var: Path):
    from region.live import Live as LiveHub
    from region.live.sources import import_source

    src = hub_var / "src" / "notes.json"
    src.parent.mkdir()
    src.write_text(json.dumps({"a": "one"}), encoding="utf-8")
    api.store.create_layer("import:test", namespace="test", by="t")
    imp = Notes(src)
    cfg = {**api.cfg, "live": {"old_hub_db": None}}
    app = api.app()
    hub = app.state.hub
    live = LiveHub(api.store, api.jobs, cfg=cfg, publish=hub.events.publish, importers={imp.name: imp},
                   sources=[import_source(imp, cfg)], settle_s=0.2, poll_s=0.05, watch_sections=False,
                   ledger_dir=hub_var / "ids", work=hub_var / "imports",
                   state_path=hub_var / "live" / "state.json")  # fmt: skip
    hub.live = live
    server = Live(app)
    live.start()
    assert live.wait_idle(10)
    try:
        yield server, live, src
    finally:
        live.stop()
        server.stop()


def _until(fn, timeout: float = 10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        got = fn()
        if got:
            return got
        time.sleep(0.02)
    raise AssertionError("timed out")


def test_live_routes_pause_undo_and_the_source_event(live_api) -> None:
    import httpx

    server, live, src = live_api
    url = server.url + "/api/v1"
    st = httpx.get(url + "/live").json()
    assert st["enabled"] is True and st["paused"] is False and st["sources"][0]["source"] == "import:fake_notes"
    note = ids.stable("test", "a")
    # the start took the file in as it is now
    assert live.store.get("note", note, View())["data"]["text"] == "one"
    with Stream(server.url) as s:
        s.next()  # hello
        src.write_text(json.dumps({"a": "two"}), encoding="utf-8")
        msg = s.until(lambda m: m["event"] == "source" and m["data"]["toast"], timeout=10)
    data = msg["data"]
    assert data["undo"] is True and data["text"] == "fake notes updated: 1 note changed", data["text"]
    assert live.store.get("note", note, View())["data"]["text"] == "two"
    # Undo this import
    r = httpx.post(url + "/live/sources/import:fake_notes/undo", headers=H)
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "held"
    assert live.store.get("note", note, View())["data"]["text"] == "one"
    # undoing twice is a plain 409
    r = httpx.post(url + "/live/sources/import:fake_notes/undo", headers=H)
    assert r.status_code == 409
    # Pause live: a change waits; resume takes it in
    assert httpx.post(url + "/live/pause", headers=H).json()["paused"] is True
    src.write_text(json.dumps({"a": "three"}), encoding="utf-8")
    _until(lambda: httpx.get(url + "/live").json()["pending"] >= 1)
    time.sleep(0.5)
    assert live.store.get("note", note, View())["data"]["text"] == "one"
    assert httpx.post(url + "/live/resume", headers=H).json()["paused"] is False
    _until(lambda: live.store.get("note", note, View())["data"]["text"] == "three")
    # writes need X-CR-Client
    assert httpx.post(url + "/live/pause").status_code in (400, 403, 428)
    # a pane's focus is a hint the hub takes without an answer body
    r = httpx.post(url + "/live/focus", json={"type": "t.api_arr", "scope": "note/x", "view": "main|-|canon",
                                              "priority": 0}, headers=H)  # fmt: skip
    assert r.status_code == 204
    assert httpx.get(url + "/live/pending").json() == {"items": []}


def test_live_off_answers_enabled_false(client) -> None:
    st = client.get(f"{BASE}/api/v1/live").json()
    assert st == {"enabled": False, "paused": False, "pending": 0, "updated": None}
    assert client.post(f"{BASE}/api/v1/live/pause", headers=H).status_code == 409


def test_words_say_what_moved_in_bens_terms() -> None:
    sec, stop1, stop2, prof = "S1", "T1", "T2", "P1"
    said = W.describe(
        label="Old hub",
        origin="the old hub",
        changes=[
            {"op": "put", "kind": "profile", "id": prof, "fields": ["data.so"]},
        ],
        records={prof: {"kind": "profile", "parent": sec}},
        names={sec: "Line 3"},
        bodies={prof: ({"so": {"a": 0, "b": 0}, "pvi": [[0, 1]]}, {"so": {"a": 5, "b": -3}, "pvi": [[0, 1]]})},
    )
    assert said.text == "Line 3 updated from the old hub: 2 stations moved, re-solving"
    said = W.describe(
        label="Line files",
        origin="the line files",
        changes=[
            {"op": "put", "kind": "stop", "id": stop1, "fields": ["data.c", "geom"]},
            {"op": "create", "kind": "stop", "id": stop2, "fields": []},
            {"op": "put", "kind": "ground_profile", "id": "G", "fields": ["data.z_dm"]},
        ],
        records={
            stop1: {"kind": "stop", "parent": sec},
            stop2: {"kind": "stop", "parent": sec},
            "G": {"kind": "ground_profile", "parent": sec},
        },  # fmt: skip
        names={sec: "Line 3"},
        review=1,
    )
    assert said.text == (
        "Line 3 updated from the line files: 1 station moved, 1 station added, ground changed, re-solving; "
        "1 change touches your edits and waits in Review"
    )
    said = W.describe(label="Rule registry", origin="the rule registry",
                      changes=[{"op": "put", "kind": "param", "id": "x", "fields": ["data.value"]}] * 3,
                      records={}, names={})  # fmt: skip
    assert said.text == "Rule registry updated: 3 params changed" and said.sections == []
    assert W.tier_text("1912 ground", {"handshake": {"detail": "contours", "done": False}},
                       {"handshake": {"detail": "surface", "done": True}}, []) == (
        "1912 ground: stage contours to surface, ready to use")  # fmt: skip
    assert W.tier_text("Deck files", {"status": "present", "handshake": None}, {"status": "present"},
                       ["plots.json", "basin.json"]) == "Deck files: plots.json and basin.json changed"  # fmt: skip
