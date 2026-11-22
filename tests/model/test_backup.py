"""Backups: an online, checked copy that restores exactly; retention by tier."""

from __future__ import annotations

import datetime as dt
import sqlite3

import pytest

from region.core.errors import Invalid, NotFound
from region.core.view import View
from region.model import open_store
from region.model.backup import auto, backup, listing, prune, quick_check, restore
from tests.model.conftest import KINDS
from tests.model.helpers import note, tag


def test_backup_restore_round_trip(make_store, write_root):
    store = make_store()
    a = note(store, "before the backup")
    path = store.backup("manual")
    assert path.parent == write_root / "backups" and path.name.endswith("-manual.db")
    assert quick_check(path) == []
    b = note(store, "after the backup")
    store.patch(
        "note",
        a["id"],
        [{"op": "replace", "path": "/data/text", "value": "changed"}],
        View(),
        if_match=tag(a),
        by="ben",
    )
    epoch = store.meta()["epoch"]
    db = store.path
    store.close()
    restore(path, db)
    with open_store(db, kinds_paths=KINDS) as again:
        assert again.get("note", a["id"], View()) == a
        with pytest.raises(NotFound):
            again.get("note", b["id"], View())
        assert again.meta()["epoch"] != epoch
    kept = [f.reason for f in listing(write_root / "backups")]
    assert sorted(kept) == ["manual", "pre-restore"]
    # the file-level call, a refused source, and a missing database
    copy = backup(db, write_root / "elsewhere", "manual")
    assert quick_check(copy) == []
    junk = write_root / "junk.db"
    junk.write_bytes(b"not a database at all" * 100)
    with pytest.raises(Invalid):
        restore(junk, db)
    with pytest.raises(NotFound):
        backup(write_root / "absent.db", write_root / "b", "manual")


def test_retention_tiers(write_root):
    db = write_root / "region.db"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE t (x)")
    con.commit()
    con.close()
    dest = write_root / "backups"
    dest.mkdir()
    t0 = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
    made = {}
    for reason, n in (
        ("pre-migrate", 3),
        ("manual", 4),
        ("pre-import", 13),
        ("daily", 20),
        ("weekly", 11),
        ("pre-restore", 2),
        ("odd-reason", 2),
    ):
        for i in range(n):
            stamp = (t0 + dt.timedelta(hours=i)).strftime("%Y%m%dT%H%M%SZ")
            f = dest / f"region-{stamp}-{reason}.db"
            f.write_bytes(b"")
            made.setdefault(reason, []).append(f)
    (dest / "notes.txt").write_text("not a backup", encoding="utf-8")
    removed = prune(dest)
    left = {}
    for b in listing(dest):
        left.setdefault(b.reason, []).append(b.path)
    assert {r: len(v) for r, v in left.items()} == {
        "pre-migrate": 3,
        "manual": 4,
        "pre-import": 10,
        "daily": 14,
        "weekly": 8,
        "pre-restore": 2,
        "odd-reason": 2,
    }
    assert left["daily"] == made["daily"][-14:] and left["pre-import"] == made["pre-import"][-10:]
    assert len(removed) == 3 + 6 + 3 and (dest / "notes.txt").exists()
    # auto takes today's daily and this week's weekly once
    now = dt.datetime(2026, 3, 4, 12, tzinfo=dt.UTC)
    first = auto(db, dest, now=now)
    assert sorted(p.name.rsplit("-", 1)[1] for p in first) == ["daily.db", "weekly.db"]
    assert auto(db, dest, now=now + dt.timedelta(hours=1)) == []
    assert [p.name.rsplit("-", 1)[1] for p in auto(db, dest, now=now + dt.timedelta(days=1))] == ["daily.db"]


def test_epoch_is_the_meta_epoch_and_a_restore_changes_it(make_store, write_root):
    store = make_store("epoch.db")
    note(store, "one")
    first = store.epoch()
    assert first == store.meta()["epoch"] and len(first) == 26
    assert store.min_seq() == 1 and store.last_seq() >= 1
    path = store.backup("manual")
    db = store.path
    store.close()
    restore(path, db)
    with open_store(db, kinds_paths=KINDS) as again:
        assert again.epoch() not in ("", first)
        assert again.epoch() == again.meta()["epoch"]


def test_a_restore_is_not_undone_by_the_next_seed_import(make_store, write_root):
    """data-2, spec-2: after a restore, the seed import takes nothing silently. Each record where region/seed (newer
    exports) and the restored database differ is a listed seed conflict; Ben keeps the restored revision (ours) or
    the seed's (theirs)."""
    from region.model import seed as S

    store = make_store()
    root = write_root / "seed"
    x = note(store, "good")
    S.export(store, root)
    path = store.backup("manual")
    cur = store.get("note", x["id"], View())
    store.patch(
        "note",
        x["id"],
        [{"op": "replace", "path": "/data/text", "value": "BAD bulk edit"}],
        View(),
        if_match=tag(cur),
        by="ben",
    )
    made_after = note(store, "made after the backup")
    S.export(store, root)  # exported (and committed) before Ben noticed
    db = store.path
    store.close()
    rep = restore(path, db)
    assert rep["seed_layers"] == ["main"] and rep["pre_restore"] is not None
    with open_store(db, kinds_paths=KINDS) as again:
        assert S.restore_pending(again) == ["main"]
        assert again.get("note", x["id"], View())["data"]["text"] == "good"
        got = S.import_seed(again, root)  # what crhub serve does at start
        main = got["layers"]["main"]
        assert main["restored"] is True and main["taken"] == 0 and main["added"] == 0
        assert sorted(c["rec_id"] for c in main["conflicts"]) == sorted([x["id"], made_after["id"]])
        assert again.get("note", x["id"], View())["data"]["text"] == "good"
        with pytest.raises(NotFound):
            again.get("note", made_after["id"], View())
        assert S.restore_pending(again) == []
        # a second import (export imports first) keeps them listed, never taken
        assert S.import_seed(again, root)["layers"]["main"]["taken"] == 0
        assert len(S.open_seed_conflicts(again)) == 2
        # Ben keeps the restored state for both; export then writes it into region/seed
        for c in S.open_seed_conflicts(again):
            again.resolve_conflict(c["id"], "ours", by="ben")
        out = S.export(again, root)
        assert out["imported"]["layers"]["main"]["taken"] == 0
        assert out["layers"]["main"]["removed"] == 1
        assert again.get("note", x["id"], View())["data"]["text"] == "good"
        with pytest.raises(NotFound):
            again.get("note", made_after["id"], View())
        files = sorted(p.stem for p in (root / "main" / "note").glob("*.json"))
        assert files == [x["id"]]
        assert S.import_seed(again, root)["layers"]["main"]["conflicts"] == []


def test_after_a_restore_ben_can_take_the_seed_instead(make_store, write_root):
    """data-2: taking theirs on a restore's conflicts brings region/seed's newer state in, the absent record too."""
    from region.model import seed as S

    store = make_store()
    root = write_root / "seed"
    x = note(store, "v1")
    S.export(store, root)
    path = store.backup("manual")
    cur = store.get("note", x["id"], View())
    store.patch(
        "note", x["id"], [{"op": "replace", "path": "/data/text", "value": "v2"}], View(), if_match=tag(cur), by="ben"
    )
    later = note(store, "later")
    S.export(store, root)
    db = store.path
    store.close()
    restore(path, db)
    with open_store(db, kinds_paths=KINDS) as again:
        S.import_seed(again, root)
        for c in S.open_seed_conflicts(again):
            again.resolve_conflict(c["id"], "theirs", by="ben")
        assert again.get("note", x["id"], View())["data"]["text"] == "v2"
        assert again.get("note", later["id"], View())["data"]["text"] == "later"
        rep = S.export(again, root)
        assert rep["layers"]["main"]["written"] == 0 and rep["layers"]["main"]["removed"] == 0


def test_restore_refuses_a_file_that_is_not_this_hub_database(make_store, write_root):
    """data-16: a plain SQLite file (the old hub's hub.db, a cache.db) is refused, and so is a backup of another
    database unless forced; the database stays as it was."""
    store = make_store()
    mine = note(store, "Ben's note")
    db = store.path
    store.close()
    old_hub = write_root / "hub.db"
    con = sqlite3.connect(str(old_hub))
    con.execute("CREATE TABLE docs (id TEXT, body TEXT)")
    con.commit()
    con.close()
    with pytest.raises(Invalid, match="not a hub database"):
        restore(old_hub, db)
    other = make_store("other.db")
    note(other, "someone else's")
    foreign = other.backup("manual", dest=write_root / "other_backups")
    other.close()
    with pytest.raises(Invalid, match="another database"):
        restore(foreign, db)
    with open_store(db, kinds_paths=KINDS) as again:
        assert again.get("note", mine["id"], View())["data"]["text"] == "Ben's note"
    assert not list((write_root / "backups").glob("*-pre-restore.db"))
    rep = restore(foreign, db, force=True)
    assert rep["replaced"]["records"] >= 1 and rep["restored"]["db_id"] != rep["replaced"]["db_id"]
