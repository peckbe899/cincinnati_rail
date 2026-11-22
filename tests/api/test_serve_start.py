"""``crhub serve``'s start-up steps added after the increment-1 review: backups (data-11), seeds that cannot be read
(data-4, server-2), a restore's banner (data-2), the import source check (spec-5) and imports through the hub."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from region.core import ids, paths
from region.core.view import View
from tests.api.conftest import H, free_port


def _db(var: Path) -> Path:
    from region.model import open_store

    db = var / "region.db"
    open_store(db).close()
    return db


def _serve(**kw: Any):
    from region.api.serve import Serve

    lines: list[str] = []
    kw.setdefault("engine", False)
    srv = Serve(port=free_port(), out=lines.append, **kw)
    return srv, lines


@pytest.fixture
def seed_root(write_root, monkeypatch):
    from region.model import seed

    root = write_root / "seed"
    monkeypatch.setattr(seed, "SEED", root)
    monkeypatch.setattr(seed.export, "__defaults__", (root,))
    return root


class _FakeImporter:
    """An importer of notes on ``import:test`` from one JSON file under var (``{key: text}``)."""

    name = "fake_notes"
    version = "1"
    layer = "import:test"
    namespace = "test"
    from_git = ()

    def sources(self, _paths: Any) -> dict[str, str]:
        return {"notes": "var://src/notes.json"}

    def records(self, local: dict[str, Path], _ids: Any):
        for key, text in json.loads(local["notes"].read_text(encoding="utf-8")).items():
            yield {"kind": "note", "id": ids.stable("test", key), "data": {"text": text}, "geom": None}


@pytest.fixture
def fake_importer(hub_var, monkeypatch):
    from region.cli import imports as I

    src = hub_var / "src" / "notes.json"
    src.parent.mkdir()
    src.write_text(json.dumps({"a": "one"}), encoding="utf-8")
    fake = _FakeImporter()
    monkeypatch.setattr(I, "importers", lambda: {fake.name: fake})
    return src


def _import_layer(db: Path) -> None:
    from region.model import open_store

    with open_store(db) as store:
        store.create_layer("import:test", namespace="test", by="t")


def test_serve_takes_the_daily_and_weekly_backups_and_one_before_a_seed_import(hub_var, seed_root):
    """data-11: serve takes the daily and weekly backups that are due, and a seed import that adds records takes a
    pre-import backup first."""
    from region.model import backup as B
    from region.model import open_store
    from region.model import seed as S

    db = _db(hub_var)
    other = open_store(hub_var / "other.db")
    x = other.put({"kind": "note", "id": None, "data": {"text": "pulled"}, "geom": None}, View(), if_match=None, by="b")
    S.export(other, seed_root)
    other.close()
    srv, lines = _serve(seeds=True, imports=False)
    url = srv.start()
    try:
        assert httpx.get(url + f"/api/v1/k/note/{x['id']}").status_code == 200
    finally:
        srv.stop()
    reasons = sorted(b.reason for b in B.listing(hub_var / "backups"))
    assert reasons == ["daily", "pre-import", "weekly"], reasons
    assert any(line.startswith("backups") for line in lines)
    # a second start the same day takes no new daily or weekly one, and the seed is already in: no pre-import
    srv, lines = _serve(seeds=True, imports=False)
    srv.start()
    srv.stop()
    assert sorted(b.reason for b in B.listing(hub_var / "backups")) == reasons
    assert db.is_file()


def test_an_import_that_changes_records_is_backed_up_first(hub_var, fake_importer):
    """data-11: apply_import takes a pre-import backup when it writes; a dry run and an unchanged run take none."""
    from region.cli import imports as I
    from region.model import backup as B
    from region.model import open_store

    db = _db(hub_var)
    _import_layer(db)
    with open_store(db) as store:
        I.run_one(store, "fake_notes", dry_run=True)
        assert B.listing(hub_var / "backups") == []
        I.run_one(store, "fake_notes")
        assert [b.reason for b in B.listing(hub_var / "backups")] == ["pre-import"]
        I.run_one(store, "fake_notes")  # unchanged
        assert len(B.listing(hub_var / "backups")) == 1


def test_serve_starts_and_reports_a_seed_it_cannot_read(hub_var, seed_root):
    """data-4, server-2: merge-conflict markers in a proposal's _layer.json and a cp1252 record file are reported
    with their paths, the other layers still import, and the hub serves."""
    from region.model import open_store
    from region.model import seed as S

    _db(hub_var)
    other = open_store(hub_var / "other.db")
    other.create_layer("proposal:bridge", by="b")
    other.create_layer("proposal:gate", by="b")
    for slug in ("proposal:bridge", "proposal:gate"):
        other.put({"kind": "note", "id": None, "data": {"text": slug}, "geom": None}, View(layer=slug),
                  if_match=None, by="b")  # fmt: skip
    S.export(other, seed_root)
    other.close()
    (seed_root / "proposals" / "bridge" / "_layer.json").write_text(
        '<<<<<<< HEAD\n{"title": "Ben"}\n=======\n{"title": "cloud"}\n>>>>>>> origin\n', encoding="utf-8"
    )
    gate = next((seed_root / "proposals" / "gate" / "note").glob("*.json"))
    gate.write_bytes(gate.read_bytes().replace(b'"proposal:gate"', b'"caf\xe9"'))
    srv, lines = _serve(seeds=True, imports=False)
    url = srv.start()
    try:
        assert httpx.get(url + "/api/v1/health").status_code == 200
    finally:
        srv.stop()
    said = "\n".join(lines)
    assert "proposal:bridge: NOT imported" in said and "_layer.json" in said, said
    assert "proposal:gate: NOT imported" in said and gate.name in said and "UTF-8" in said, said
    with open_store(hub_var / "region.db", readonly=True) as store:
        assert {la["slug"] for la in store.layers()} >= {"main"}


def test_serve_says_when_a_restore_left_seed_conflicts(hub_var, seed_root):
    """data-2: the start after a restore says that nothing was taken and how to resolve."""
    from region.model import backup as B
    from region.model import open_store
    from region.model import seed as S

    db = _db(hub_var)
    store = open_store(db)
    x = store.put({"kind": "note", "id": None, "data": {"text": "good"}, "geom": None}, View(), if_match=None, by="b")
    S.export(store, seed_root)
    bk = store.backup("manual")
    cur = store.get("note", x["id"], View())
    store.put({"kind": "note", "id": x["id"], "data": {"text": "BAD"}, "geom": None}, View(),
              if_match=f"{cur['layer']}:{cur['version']}", by="b")  # fmt: skip
    S.export(store, seed_root)
    store.close()
    B.restore(bk, db)
    srv, lines = _serve(seeds=True, imports=False)
    url = srv.start()
    try:
        assert httpx.get(url + f"/api/v1/k/note/{x['id']}").json()["data"]["text"] == "good"
    finally:
        srv.stop()
    said = "\n".join(lines)
    assert "restored from a backup" in said and "1 record(s) differ" in said and "conflicts resolve" in said


def test_serve_reports_an_import_whose_sources_changed(hub_var, fake_importer):
    """spec-5: an importer whose sources changed since its last applied run gets a dry run at start, reported with
    the command that applies it; the database is not changed until then."""
    from region.cli import imports as I
    from region.cli import main as cli_main
    from region.model import open_store

    db = _db(hub_var)
    _import_layer(db)
    with open_store(db) as store:
        I.run_one(store, "fake_notes")
        assert I.check_sources(store) == []
    fake_importer.write_text(json.dumps({"a": "one, edited in the old hub", "b": "two"}), encoding="utf-8")
    srv, lines = _serve(seeds=False, imports=True)
    url = srv.start()
    try:
        assert httpx.get(url + f"/api/v1/k/note/{ids.stable('test', 'a')}").json()["data"]["text"] == "one"
        (st,) = srv.stale_imports
        assert st["importer"] == "fake_notes" and st["counts"]["updated"] == 1 and st["counts"]["created"] == 1
        said = "\n".join(lines)
        assert f"crhub imports apply {st['dry_run']}" in said and "fake_notes: notes changed" in said, said
        # 9.28: crhub imports apply goes through the serving hub
        assert cli_main(["imports", "apply", str(st["dry_run"])]) == 0
        got = httpx.get(url + f"/api/v1/k/note/{ids.stable('test', 'a')}").json()
        assert got["data"]["text"] == "one, edited in the old hub"
        assert cli_main(["imports", "run", "fake_notes", "--dry-run"]) == 0
    finally:
        srv.stop()
    with open_store(db, readonly=True) as store:
        assert I.stale_sources(store) == []


def test_setup_applies_imports_only_into_empty_layers(hub_var, fake_importer, capsys):
    """spec-7: the first setup applies; a later one makes a dry run and prints the command that applies it."""
    from region.cli import imports as I
    from region.model import open_store

    db = _db(hub_var)
    _import_layer(db)
    assert I.setup_imports(db) == 0
    with open_store(db, readonly=True) as store:
        assert store.get("note", ids.stable("test", "a"), View(layer="import:test"))["data"]["text"] == "one"
    fake_importer.write_text(json.dumps({"a": "changed"}), encoding="utf-8")
    capsys.readouterr()
    assert I.setup_imports(db) == 0
    out = capsys.readouterr().out
    assert "(dry run)" in out and "crhub imports apply" in out
    with open_store(db, readonly=True) as store:
        assert store.get("note", ids.stable("test", "a"), View(layer="import:test"))["data"]["text"] == "one"


def test_conflicts_cli_lists_and_resolves_a_seed_conflict(hub_var, seed_root, capsys):
    """data-7, spec-11: crhub conflicts lists the seed conflict that blocks export and resolves it, directly and
    through a serving hub; export then goes through."""
    from region.cli import main as cli_main
    from region.model import open_store
    from region.model import seed as S

    db = _db(hub_var)
    store = open_store(db)
    x = store.put({"kind": "note", "id": None, "data": {"text": "v1"}, "geom": None}, View(), if_match=None, by="b")
    S.export(store, seed_root)
    f = seed_root / "main" / "note" / f"{x['id']}.json"
    obj = json.loads(f.read_text(encoding="utf-8"))
    obj["data"]["text"] = "pulled"
    f.write_text(S.seed_text(obj), encoding="utf-8", newline="\n")
    cur = store.get("note", x["id"], View())
    store.put({"kind": "note", "id": x["id"], "data": {"text": "Ben's"}, "geom": None}, View(),
              if_match=f"{cur['layer']}:{cur['version']}", by="b")  # fmt: skip
    (c,) = S.import_seed(store, seed_root)["layers"]["main"]["conflicts"]
    store.close()
    capsys.readouterr()
    assert cli_main(["export"]) == 1
    assert "crhub conflicts" in capsys.readouterr().err
    assert cli_main(["conflicts", "list"]) == 0
    out = capsys.readouterr().out
    assert c["id"] in out and "(seed)" in out and "1 conflict(s) open" in out
    srv, _lines = _serve(seeds=False, imports=False)
    srv.start()
    try:
        assert cli_main(["conflicts", "resolve", "--all", "--seed", "--take", "ours"]) == 0
        assert "1 resolved, 0 not" in capsys.readouterr().out
        assert cli_main(["export"]) == 0
    finally:
        srv.stop()
    assert json.loads(f.read_text(encoding="utf-8"))["data"]["text"] == "Ben's"
    assert cli_main(["conflicts", "list"]) == 0
    assert "0 conflict(s) open" in capsys.readouterr().out
    assert H  # the shared headers stay importable for the other API tests
    assert paths.VAR_ENV


def test_a_failed_engine_warm_start_is_tried_again(hub_var, monkeypatch):
    """server-6: when the first hello takes too long (a cold Windows start), /meta kept the old error for the life of
    the server. The start is tried again in the background, and /meta then shows the engine."""
    import time

    import region.enginehost as EH
    from region.core.errors import EngineUnavailable

    hello = {"engine_version": "0.0.0", "engine_build": "c" * 64, "contracts": {"section_input": 0,
             "vertical_rail": 0}, "methods": ["vertical.rail@1"]}  # fmt: skip
    starts = []

    class Pool:
        size = 1

        def __init__(self, size=None, timeout_s=None):
            pass

        def start(self):
            starts.append(1)
            if len(starts) == 1:
                raise EngineUnavailable("the engine sidecar engine-0 sent no hello within 15 s", reason="timeout")
            return dict(hello)

        def hello(self):
            return dict(hello)

        def close(self):
            pass

    monkeypatch.setattr(EH, "Pool", Pool)
    _db(hub_var)
    srv, _lines = _serve(engine=True, seeds=False, imports=False)
    srv.engine_retry_s = (0.2,)
    url = srv.start()
    try:
        deadline = time.monotonic() + 10
        meta = httpx.get(url + "/api/v1/meta").json()
        while meta["engine"] is None and time.monotonic() < deadline:
            time.sleep(0.05)
            meta = httpx.get(url + "/api/v1/meta").json()
        assert meta["engine"] == hello and meta["engine_error"] is None and len(starts) == 2
    finally:
        srv.stop()
