"""The live hub under the conditions Ben's machine gives it: a half-written line file, a deleted file or a missing
folder, a file another program holds open (Windows, WinError 32), Undo after the import raised review items, and
Undo still offered after a re-save of the same files."""

from __future__ import annotations

import time

from region.core import fsio
from region.core.protocols import etag
from region.core.view import View
from tests.live.conftest import Env, until

LINE = "Line_3"
SRC = "import:profile_lines"


def _move(doc: dict) -> None:
    doc["stations"][2]["c"] += 5.0
    doc["stations"][3]["c"] += 5.0


def _events(env: Env) -> list[dict]:
    return [p for _t, p in env.since("source") if p["source"] == SRC]


def test_a_half_written_file_is_not_taken_in_and_the_all_clear_is_said(env: Env) -> None:
    f = env.line(LINE)
    full = f.read_bytes()
    env.mark()
    f.write_bytes(full[: len(full) // 2])  # the writer stalls past the settle period
    until(lambda: any(p["state"] == "error" for p in _events(env)), what="the half-written file refused")
    assert env.settle()
    assert env.imports() == []
    err = next(p for p in _events(env) if p["state"] == "error")
    assert err["toast"] and "not complete JSON" in err["text"], err["text"]
    f.write_bytes(full)
    until(lambda: _events(env)[-1]["state"] == "idle", what="the finished file looked at")
    assert env.settle()
    assert env.imports() == []
    last = _events(env)[-1]
    assert last["toast"] and last["text"] == "Line files can be read again; nothing changed since the last import"


def test_a_deleted_file_or_a_missing_folder_deletes_nothing(env: Env) -> None:
    sid = env.section(LINE)
    stops = len(env.store.list("stop", View(), parent=sid)[0])
    f = env.line(LINE)
    full = f.read_bytes()
    env.mark()
    f.unlink()
    until(lambda: any(p["state"] == "error" for p in _events(env)), what="the missing file reported")
    assert env.settle()
    assert "Line_3.json is missing" in _events(env)[-1]["text"]
    f.write_bytes(full)
    lines = env.profile / "lines"
    lines.rename(env.profile / "lines_away")  # the tier going missing (a drive unplugged, a sync paused)
    time.sleep(2.0)
    assert env.settle()
    (env.profile / "lines_away").rename(lines)
    time.sleep(2.0)
    assert env.settle()
    assert env.imports() == []
    assert len(env.store.list("stop", View(), parent=sid)[0]) == stops


def test_a_file_held_open_by_another_program_is_looked_at_again(env: Env, monkeypatch) -> None:
    """WinError 32 while reading a line file another program has open: the hub looks again shortly, quietly, and
    takes the change in once the file is free (it does not wait for the next save)."""
    import region.cli.imports as I

    real = fsio.sha256_file
    left = {"n": 2}

    def held(path, **kw):
        if str(path).endswith(f"{LINE}.json") and left["n"] > 0:
            left["n"] -= 1
            e = PermissionError(13, "The process cannot access the file because it is being used by another process")
            e.winerror = 32  # type: ignore[attr-defined]
            e.filename = str(path)
            raise e
        return real(path, **kw)

    monkeypatch.setattr(I.fsio, "sha256_file", held)
    env.mark()
    env.edit(LINE, _move)
    until(lambda: env.imports("profile_lines"), what="the change taken in once the file is free", timeout=30)
    assert env.settle()
    evs = _events(env)
    waits = [p for p in evs if p["state"] == "waiting"]
    assert waits and all(not p["toast"] for p in waits)
    assert "Line_3.json is open in another program" in waits[0]["text"]
    assert [p["state"] in ("applied", "review") for p in evs if p["toast"]] == [True]


def test_undo_this_import_clears_the_review_items_it_raised(env: Env) -> None:
    store = env.store
    store.create_layer("try", by="ben")
    tv = View(layer="try")
    sid = env.section(LINE)
    (prof,) = store.list("profile", tv, parent=sid)[0]
    pvi = prof["data"]["pvi"]
    edit = [{"op": "replace", "path": "/data/pvi/1", "value": [pvi[1][0], pvi[1][1] + 0.5]}]
    store.patch("profile", prof["id"], edit, tv, if_match=etag(prof["layer"], prof["version"]), by="ben")
    mine = store.get("profile", prof["id"], tv)["hash"]
    env.mark()
    env.edit(LINE, _move)
    until(lambda: env.imports("profile_lines"), what="the import")
    assert env.settle()
    assert [c["reason"] for c in store.conflicts(layer="try") if c["state"] == "open"] == ["geometry_under_edit"]
    env.live.undo(SRC, by="ben")
    assert env.settle()
    assert [c for c in store.conflicts(layer="try") if c["state"] == "open"] == []
    assert store.get("profile", prof["id"], tv)["hash"] == mine


def test_undo_stays_offered_after_a_re_save_of_the_same_files(env: Env) -> None:
    env.mark()
    env.edit(LINE, _move)
    until(lambda: env.imports("profile_lines"), what="the import")
    assert env.settle()
    assert _events(env)[-1]["undo"] is True
    f = env.line(LINE)
    f.write_bytes(f.read_bytes())  # an editor's autosave
    until(lambda: _events(env)[-1]["text"].startswith("saved again"), what="the re-save looked at")
    assert env.settle()
    st = next(s for s in env.live.status()["sources"] if s["source"] == SRC)
    assert st["undo"] is True and _events(env)[-1]["undo"] is True
    assert env.live.undo(SRC, by="ben")["state"] == "held"


def _old_hub_db(path, docs: dict) -> None:
    """Ben's old hub database (hub/store.py's docs table) in WAL, as the old hub runs it."""
    import json
    import sqlite3

    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE docs (path TEXT PRIMARY KEY, coll TEXT, data TEXT, version INT, updated REAL, by TEXT)")
    con.executemany(
        "INSERT INTO docs VALUES (?, ?, ?, 1, 0, 'seed')",
        [(p, p.rsplit("/", 1)[0], json.dumps(d, separators=(",", ":"))) for p, d in docs.items()],
    )
    con.commit()
    con.close()


def test_the_old_hubs_live_database_is_taken_in_and_its_open_write_is_not(hub_var, tmp_path, pool, monkeypatch):
    """Ben saves in the old hub (a commit to hub.db): the change arrives through a snapshot, never the live file.
    A write the old hub has not committed yet is not seen and breaks nothing; a commit that changes nothing the
    hub holds runs no job."""
    import json
    import os
    import sqlite3

    from region.core import paths
    from region.ext.legacy.oldhub import read_seed
    from tests.importers.helpers import SEED, imported
    from tests.live.conftest import close_env, make_env

    root = tmp_path / "live"
    root.mkdir()
    imported()
    with monkeypatch.context() as m, fsio.allow_writes(root):
        m.delenv(paths.CONFIG_ENV, raising=False)
        docs = read_seed(SEED)
        _old_hub_db(root / "hub.db", docs)
        env = make_env(root, pool, hub_db=True)
        try:
            assert env.settle(), "the live hub did not settle after its start"
            db = root / "hub.db"
            before = db.read_bytes()
            env.mark()
            hub = sqlite3.connect(db)  # the old hub, running
            edited = dict(docs["roadmap/r00"], title="renamed in the old hub")
            # as hub/store.py saves: the document's version and time move with it
            hub.execute("UPDATE docs SET data = ?, version = version + 1, updated = ? WHERE path = 'roadmap/r00'",
                        (json.dumps(edited), time.time()))  # fmt: skip
            hub.commit()
            until(lambda: env.imports("old_hub"), what="the old hub's save taken in")
            assert env.settle()
            r00 = env.store.get("roadmap_item", env.store.legacy("roadmap_item", "roadmap/r00"), View())
            assert r00["data"]["title"] == "renamed in the old hub"
            # an open write transaction in the old hub while the hub takes a snapshot for a line file's change
            env.mark()
            hub.execute("BEGIN IMMEDIATE")
            hub.execute("UPDATE docs SET data = ? WHERE path = 'roadmap/r00'",
                        (json.dumps(dict(edited, title="not committed")),))  # fmt: skip
            env.edit(LINE, _move)
            until(lambda: env.imports("profile_lines"), what="the line file taken in")
            assert env.settle()
            old = [p for _t, p in env.since("source") if p["source"] == "import:old_hub"]
            assert all(p["state"] != "error" for p in old), [p["text"] for p in old]
            r00 = env.store.get("roadmap_item", r00["id"], View())
            assert r00["data"]["title"] == "renamed in the old hub"
            hub.rollback()
            # a commit of the old hub's own bookkeeping (a pipeline run's log) changes nothing the hub holds
            hub.execute("CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY, log TEXT)")
            hub.execute("INSERT INTO runs (log) VALUES ('tie started')")
            hub.commit()
            env.mark()
            time.sleep(2.5)
            assert env.settle()
            assert env.imports() == [] and env.solves() == []
            runs = env.store._reader().execute("SELECT COUNT(*) FROM import_run WHERE id > ?", (env._run_mark,))
            assert runs.fetchone()[0] == 0  # not even a snapshot and a dry run
            hub.close()
            assert db.read_bytes() != before or os.path.exists(str(db) + "-wal")
        finally:
            close_env(env)
            os.environ.pop(paths.CONFIG_ENV, None)
    paths.reload()


def test_a_file_beside_a_tier_that_changes_nothing_is_not_a_change(env: Env) -> None:
    """A file saved in a tier's folder that moves neither the tier's status nor any result input (on Ben's machine:
    a document saved in the project folder, which is the 3D artifacts tier's root) leaves the pane, its history, the
    chip's count and its "updated" time as they were, and runs nothing."""
    env.mark()
    sid = "tier:profile_lines"
    before = env.live.status()
    row = next(s for s in before["sources"] if s["source"] == sid)
    with fsio.allow_writes(env.profile):
        (env.profile / "notes.txt").write_text("a note beside the line files\n", encoding="utf-8")
    until(lambda: sid in env.live.watcher.pending(), what="the watcher to see the file")
    assert env.live.summary()["pending"] == 0, "a change that may move nothing is counted on the chip"
    assert env.settle()
    after = env.live.status()
    again = next(s for s in after["sources"] if s["source"] == sid)
    assert {k: again[k] for k in ("state", "text", "changed")} == {k: row[k] for k in ("state", "text", "changed")}
    assert after["pending"] == 0 and after["updated"] == before["updated"]
    assert after["history"] == before["history"]
    assert _source_events(env, sid) == []
    assert env.imports() == [] and env.solves() == []


def _source_events(env: Env, source: str) -> list[dict]:
    return [p for _t, p in env.since("source") if p["source"] == source]
