"""Migrations: 0002 from empty and from 0001, one transaction each, a checked backup first, the schema snapshot."""

from __future__ import annotations

import importlib
import shutil
import sqlite3
import sys

import pytest

from region.cli.model import SCHEMA_FILE, schema_text
from region.core import fsio
from region.core.errors import Invalid
from region.model.backup import listing, quick_check
from region.model.db import connect, dump_schema

M = importlib.import_module("region.model.migrate")


def _schema(con) -> str:
    return dump_schema(con)


def test_0002_applies_to_empty_and_0001_db(write_root):
    fresh = connect(write_root / "fresh.db")
    assert M.migrate(fresh) == [1, 2]
    assert M.migrate(fresh) == []
    old = connect(write_root / "old.db")
    assert M.migrate(old, target=1) == [1]
    assert {"section", "platform", "node_rtree"} <= {
        r[0] for r in old.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert M.migrate(old) == [2]
    assert _schema(old) == _schema(fresh)
    assert M.applied(old) == [1, 2]
    layers = [r[0] for r in old.execute("SELECT slug FROM layer ORDER BY id")]
    assert layers == ["main", "import:profiles", "import:registry", "legacy:old_hub"]
    meta = dict(old.execute("SELECT key, value FROM meta").fetchall())
    assert {"db_id", "epoch", "created"} <= set(meta)
    # 0002 refuses to drop 0001 tables that hold rows, and changes nothing
    full = connect(write_root / "full.db")
    M.migrate(full, target=1)
    full.execute("INSERT INTO era (id, created, updated, name, year_from) VALUES ('e', 'x', 'x', 'Era', 1900)")
    before = _schema(full)
    with pytest.raises(Invalid, match="era"):
        M.migrate(full)
    assert _schema(full) == before and M.applied(full) == [1]
    for c in (fresh, old, full):
        c.close()


def test_injected_failure_leaves_schema_unchanged(write_root):
    folder = write_root / "migrations"
    folder.mkdir()
    for f in M.discover():
        for p in (f.sql, f.py):
            if p is not None:
                shutil.copy(p, folder / p.name)
    sql = (folder / "0002_store.sql").read_text(encoding="utf-8")
    # fail at the very end, after every table and trigger was made
    (folder / "0002_store.sql").write_text(sql + "\nINSERT INTO no_such_table VALUES (1);\n", encoding="utf-8")
    con = connect(write_root / "x.db")
    assert M.migrate(con, folder=folder, target=1) == [1]
    before = _schema(con)
    rows_before = con.execute("SELECT count(*) FROM schema_version").fetchone()[0]
    with pytest.raises(sqlite3.OperationalError, match="no_such_table"):
        M.migrate(con, folder=folder)
    assert _schema(con) == before
    assert con.execute("SELECT count(*) FROM schema_version").fetchone()[0] == rows_before
    assert not con.in_transaction
    # a failing Python step rolls back too
    (folder / "0002_store.sql").write_text(sql, encoding="utf-8")
    (folder / "0002_store.py").write_text(
        (folder / "0002_store.py").read_text(encoding="utf-8")
        + "\n\ndef _boom(con):\n    raise RuntimeError('injected')\n\n\nafter = _boom\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="injected"):
        M.migrate(con, folder=folder)
    assert _schema(con) == before and M.applied(con) == [1]
    con.close()


def test_backup_checked_before_migrate(write_root, monkeypatch):
    db = write_root / "region.db"
    con = connect(db)
    M.migrate(con, target=1)
    con.execute("INSERT INTO schema_version (version, applied) VALUES (0, 'marker')")
    dest = write_root / "backups"
    assert M.migrate(con, backup_dir=dest) == [2]
    (b,) = listing(dest)
    assert b.reason == "pre-migrate" and quick_check(b.path) == []
    copy = sqlite3.connect(str(b.path))
    assert sorted(r[0] for r in copy.execute("SELECT version FROM schema_version")) == [0, 1]
    copy.close()
    con.close()
    # a backup that fails its check stops the migration before anything changes
    db2 = write_root / "two.db"
    con2 = connect(db2)
    M.migrate(con2, target=1)
    monkeypatch.setattr(sys.modules["region.model.backup"], "quick_check", lambda target: ["injected corruption"])
    with pytest.raises(Invalid, match="quick_check"):
        M.migrate(con2, backup_dir=write_root / "backups2")
    assert M.applied(con2) == [1] and listing(write_root / "backups2") == []
    con2.close()
    # a new, empty database needs no backup
    con3 = connect(write_root / "three.db")
    M.migrate(con3, backup_dir=write_root / "backups3")
    assert listing(write_root / "backups3") == []
    con3.close()


def test_schema_snapshot_matches():
    text = schema_text()
    committed = fsio.read_text(SCHEMA_FILE)
    assert text == committed, "region/model/schema.sql is stale: run python -m region.model schema --write"
    assert "CREATE TRIGGER rec_version_steps" in text and "CREATE VIRTUAL TABLE rec_rtree" in text
