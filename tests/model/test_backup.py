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
