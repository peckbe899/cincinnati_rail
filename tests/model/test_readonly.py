"""``open_store(readonly=True)``: reads an existing database and changes nothing (no migrate, no namespace layers, no
kind-table sync, no writer), so ``crhub model check`` and ``info`` and ``doctor --data`` are safe beside a server."""

from __future__ import annotations

import argparse
import json
import sqlite3
import threading

import pytest

from region.core import features, fsio
from region.core.errors import NotFound
from region.core.view import View
from tests.model.conftest import KINDS
from tests.model.helpers import note, tag


def _kind_rows(db) -> list[str]:
    con = sqlite3.connect(db)
    try:
        return [r[0] for r in con.execute("SELECT name FROM kind ORDER BY name")]
    finally:
        con.close()


def _extra_kind(tmp_path):
    kinds = tmp_path / "extra_kinds"
    kinds.mkdir()
    text = fsio.read_text(features.CORE_KINDS / "note.yaml").replace("kind: note", "kind: t_extra")
    (kinds / "t_extra.yaml").write_text(text, encoding="utf-8", newline="\n")
    return kinds


def test_readonly_store_reads_and_changes_nothing(make_store, write_root):
    from region.model import open_store
    from region.model.db import ReadOnlyWrite, _writers

    db = write_root / "ro.db"
    rw = make_store("ro.db")
    rec = note(rw, "kept")
    rw.close()
    before, kinds_before = fsio.sha256_file(db), _kind_rows(db)
    writers_before = dict(_writers)

    # a kind file this database has not seen: a read-write open would sync it into the kind table
    with open_store(db, readonly=True, kinds_paths=[*KINDS, _extra_kind(write_root)]) as ro:
        assert ro.readonly and ro.pending_migrations() == []
        assert ro.get("note", rec["id"], View()) == rec
        assert [r["id"] for r in ro.list("note", View())[0]] == [rec["id"]]
        assert ro.last_seq() >= 1 and ro.min_seq() >= 1 and ro.epoch() == ro.meta()["epoch"]
        assert ro.check_data() == [] and ro.quick_check() == []
        with pytest.raises(ReadOnlyWrite):
            note(ro, "refused")
        with pytest.raises(ReadOnlyWrite):
            ro.patch(
                "note", rec["id"], [{"op": "replace", "path": "/data/text", "value": "x"}], View(),
                if_match=tag(rec), by="ben",
            )  # fmt: skip
        ro.checkpoint()  # nothing to do, and no error
        assert dict(_writers) == writers_before, "a read-only store starts no writer thread"
    assert fsio.sha256_file(db) == before
    assert _kind_rows(db) == kinds_before and "t_extra" not in kinds_before
    assert not (write_root / "backups").exists()


def test_readonly_store_refuses_a_missing_database(write_root):
    from region.model import open_store

    with pytest.raises(NotFound):
        open_store(write_root / "none.db", readonly=True, kinds_paths=KINDS)
    with pytest.raises(NotFound):
        open_store(write_root / "none.db", readonly=True, create=True, kinds_paths=KINDS)
    assert not (write_root / "none.db").exists()


def test_readonly_store_needs_no_write_permission(tmp_path_factory):
    """The write guard is for writers: a read-only open of a file outside the write roots is allowed."""
    from region.model import open_store

    outside = tmp_path_factory.mktemp("outside_the_write_roots")
    db = outside / "guarded.db"
    with fsio.allow_writes(outside), open_store(db, kinds_paths=KINDS) as rw:
        rec = note(rw)
    with pytest.raises(fsio.WriteRefused):
        open_store(db, kinds_paths=KINDS)
    with open_store(db, readonly=True, kinds_paths=KINDS) as ro:
        assert ro.get("note", rec["id"], View())["id"] == rec["id"]


def test_readonly_store_reads_while_a_write_transaction_is_open(make_store):
    from region.model import open_store

    rw = make_store("busy.db")
    first = note(rw, "first")
    inside, release = threading.Event(), threading.Event()

    def hold(con):
        con.execute("INSERT INTO meta (key, value) VALUES ('held', 'x')")
        inside.set()
        assert release.wait(10)

    t = threading.Thread(target=lambda: rw._writer.run(hold))
    t.start()
    try:
        assert inside.wait(10)
        with open_store(rw.path, readonly=True, kinds_paths=KINDS) as ro:
            ro._reader().execute("PRAGMA busy_timeout=200")
            assert ro.get("note", first["id"], View())["data"]["text"] == "first"
            assert "held" not in ro.meta()  # the open transaction is not visible yet
    finally:
        release.set()
        t.join(10)


def test_readonly_store_reports_pending_migrations_and_never_migrates(write_root):
    from region.model import open_store
    from region.model.db import connect
    from region.model.migrate import current_version, discover, migrate

    versions = [m.version for m in discover()]
    if len(versions) < 2:
        pytest.skip("only one migration exists, so no database can be older than the newest")
    db = write_root / "old.db"
    con = connect(db)
    migrate(con, target=versions[-2])
    con.close()
    with open_store(db, readonly=True, kinds_paths=KINDS) as ro:
        assert ro.pending_migrations() == versions[-1:]
    con = sqlite3.connect(db)
    try:
        assert current_version(con) == versions[-2]
    finally:
        con.close()
    assert not (write_root / "backups").exists()


def test_model_check_and_info_open_the_database_read_only(make_store, write_root, capsys):
    from region.cli import model as cli

    db = write_root / "cli.db"
    rw = make_store("cli.db")
    note(rw, "one")
    rw.close()
    before = fsio.sha256_file(db)
    # the CLI loads the real kinds: every kind of this checkout differs from the test's, so a read-write open would
    # rewrite the kind table
    assert cli.run(argparse.Namespace(action="check", db=db)) == 0
    assert "0 database problem(s), 0 record problem(s)" in capsys.readouterr().out
    assert cli.run(argparse.Namespace(action="info", db=db, json=True)) == 0
    info = json.loads(capsys.readouterr().out)
    assert info["pending"] == [] and info["records"] == {"main/note": 1}
    assert fsio.sha256_file(db) == before
    assert not (write_root / "backups").exists()


def test_readonly_store_attaches_an_existing_cache_read_only(make_store, write_root):
    from region.jobs import cache as C
    from region.model import open_store

    rw = make_store("withcache.db")
    rw.close()
    cache_db = write_root / "cache" / "cache.db"
    C.migrate(cache_db)
    before = fsio.sha256_file(cache_db)
    with open_store(write_root / "withcache.db", readonly=True, cache=cache_db, kinds_paths=KINDS) as ro:
        con = ro._reader()
        assert con.execute("SELECT max(version) FROM cache.schema_version").fetchone()[0] == C.SCHEMA_VERSION
        with pytest.raises(sqlite3.OperationalError):
            con.execute("INSERT INTO cache.schema_version (version, applied) VALUES (99, 'x')")
    assert fsio.sha256_file(cache_db) == before
