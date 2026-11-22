"""A big import committed in parts (a Deck tie rewriting every line file) never leaves Ben's edits unguarded: when a
later part fails, or the hub stops between parts, the parts already written are closed as one changeset and Ben's
revisions over them are rebased, so a station moved under his profile is a review item as it is when the whole
import lands."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from region.cli import imports as I
from region.core.errors import Invalid
from region.core.protocols import etag
from region.core.view import View
from region.model import imports as MI
from tests.importers import helpers as H
from tests.live.conftest import REPO

TRY = View(layer="try")


class Killed(BaseException):
    """The process dying between two parts (no handler runs)."""


def _setup(root: Path) -> tuple[Any, Path, dict[str, str]]:
    store = H.fresh_copy(root)
    lines = root / "lines"
    shutil.copytree(REPO / "data" / "profile" / "lines", lines)
    store.create_layer("try", by="ben")
    mine: dict[str, str] = {}
    for f in sorted(lines.glob("*.json")):
        if f.name == "index.json":
            continue
        # every station's offset shifted (over 200 changes: the import is written in parts), two moved
        doc = json.loads(f.read_text(encoding="utf-8"))
        for s in doc["stations"]:
            s["offset"] = (s.get("offset") or 0) + 0.1
        for s in doc["stations"][1:3]:
            s["c"] += 5.0
        f.write_text(json.dumps(doc), encoding="utf-8")
        sid = H.section_of(store, f.stem)["id"]
        (prof,) = store.list("profile", TRY, parent=sid)[0]
        pvi = prof["data"].get("pvi") or []
        if len(pvi) < 2:
            continue
        edit = [{"op": "replace", "path": "/data/pvi/1", "value": [pvi[1][0], pvi[1][1] + 0.5]}]
        store.patch("profile", prof["id"], edit, TRY, if_match=etag(prof["layer"], prof["version"]), by="ben")
        mine[prof["id"]] = store.get("profile", prof["id"], TRY)["hash"]
    return store, lines, mine


def _run(store: Any, root: Path, lines: Path) -> Any:
    return I.run_one(
        store, "profile_lines", overrides={"lines": lines}, ledger_dir=root / "ids", work=root / "work", use_git=False
    )


def _guarded(store: Any, mine: dict[str, str]) -> set[str]:
    """The profiles of Ben's with an open geometry_under_edit item."""
    return {
        c["rec_id"]
        for c in store.conflicts(layer="try")
        if c["state"] == "open" and c["reason"] == "geometry_under_edit" and c["rec_id"] in mine
    }


def _fail_part(store: Any, monkeypatch: pytest.MonkeyPatch, nth: int, exc: BaseException) -> None:
    real = store._writer.run
    seen = {"n": 0}

    def run(fn: Any) -> Any:
        if getattr(fn, "__name__", "") == "one":
            seen["n"] += 1
            if seen["n"] == nth:
                raise exc
        return real(fn)

    monkeypatch.setattr(store._writer, "run", run)


def _written_profiles(store: Any, cs: str, mine: dict[str, str]) -> set[str]:
    """Ben's profiles whose section's stops the changeset ``cs`` moved."""
    con = store._reader()
    stops = {r[0] for r in con.execute("SELECT id FROM rec_hist WHERE changeset = ?", (cs,)).fetchall()}
    out = set()
    for pid in mine:
        sid = con.execute("SELECT parent FROM rec WHERE id = ? AND parent IS NOT NULL", (pid,)).fetchone()[0]
        if any(s["id"] in stops for s in store.list("stop", TRY, parent=sid)[0]):
            out.add(pid)
    return out


def test_a_part_that_fails_leaves_the_parts_before_it_rebased(write_root: Path, monkeypatch) -> None:
    store, lines, mine = _setup(write_root)
    try:
        with monkeypatch.context() as m:
            _fail_part(store, m, 3, Invalid("the disk is full"))
            with pytest.raises(Invalid):
                _run(store, write_root, lines)
        row = (
            store._reader()
            .execute(
                "SELECT state, changeset FROM import_run WHERE importer = 'profile_lines' ORDER BY id DESC LIMIT 1"
            )
            .fetchone()
        )
        assert row[0] == "failed" and row[1]
        assert store._reader().execute("SELECT count FROM changeset WHERE id = ?", (row[1],)).fetchone()[0] > 0
        moved = _written_profiles(store, row[1], mine)
        assert moved and _guarded(store, mine) == moved
        for pid, h in mine.items():
            assert store.get("profile", pid, TRY)["hash"] == h
        # the next run writes the rest, and every profile Ben edited is guarded
        rep = _run(store, write_root, lines).report
        assert rep.errors == [] and rep.changeset
        assert _guarded(store, mine) == set(mine)
        for pid, h in mine.items():
            assert store.get("profile", pid, TRY)["hash"] == h
    finally:
        store.close()


def test_a_hub_stopped_between_parts_is_closed_and_rebased_by_the_next_import(write_root: Path, monkeypatch) -> None:
    store, lines, mine = _setup(write_root)
    try:
        with monkeypatch.context() as m:
            _fail_part(store, m, 2, Killed())
            with pytest.raises(Killed):
                _run(store, write_root, lines)
        con = store._reader()
        run_id, state, cs = con.execute(
            "SELECT id, state, changeset FROM import_run WHERE importer = 'profile_lines' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert state == "running" and cs
        assert con.execute("SELECT 1 FROM changeset WHERE id = ?", (cs,)).fetchone() is None
        assert con.execute("SELECT COUNT(*) FROM rec_hist WHERE changeset = ?", (cs,)).fetchone()[0] > 0
        # a new process: the cut-off run started before it
        monkeypatch.setattr(MI, "STARTED", "9999")
        rep = _run(store, write_root, lines).report
        assert rep.errors == [] and rep.changeset
        con = store._reader()
        assert con.execute("SELECT state FROM import_run WHERE id = ?", (run_id,)).fetchone()[0] == "failed"
        assert con.execute("SELECT count FROM changeset WHERE id = ?", (cs,)).fetchone()[0] > 0
        assert _guarded(store, mine) == set(mine)
        for pid, h in mine.items():
            assert store.get("profile", pid, TRY)["hash"] == h
        # no record of the layer was minted twice: the ids of the first part were in the index before the stop
        dup = con.execute(
            "SELECT key, COUNT(DISTINCT id) FROM legacy GROUP BY lkind, key HAVING COUNT(DISTINCT id) > 1"
        ).fetchall()
        assert dup == []
    finally:
        store.close()
