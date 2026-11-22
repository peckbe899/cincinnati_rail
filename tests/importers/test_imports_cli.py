"""``crhub imports`` and ``setup_imports(db)``, the runner ``crhub setup`` and the server share (section 10, WP5)."""

from __future__ import annotations

import json

import pytest

from region.core import fsio, lock, paths
from region.core.view import View
from tests.importers.helpers import LINES, METRO, copy_ledgers


def _db(hub_var):
    from region.model import open_store

    db = hub_var / "region.db"
    open_store(db).close()
    return db


def test_setup_imports_applies_every_importer_then_finds_nothing_new(hub_var, capsys):
    from region.cli.imports import setup_imports
    from region.model import open_store

    db = _db(hub_var)
    ledgers = copy_ledgers(hub_var / "ids")
    assert setup_imports(db, ledger_dir=ledgers) == 0
    out = capsys.readouterr().out
    assert "registry" in out and "profile_lines" in out and "old_hub" in out
    with open_store(db, readonly=True) as store:
        assert len(store.list("section", View())[0]) == len(METRO)
        seq = store.last_seq()
    assert setup_imports(db, ledger_dir=ledgers) == 0
    with open_store(db, readonly=True) as store:
        assert store.last_seq() == seq
    for f in ledgers.glob("*.tsv"):
        assert f.read_bytes() == (paths.repo_root() / "region" / "ids" / f.name).read_bytes()


def test_imports_cli_lists_runs_dry_and_refuses_while_a_hub_runs(hub_var, capsys):
    from region.cli import main
    from region.model import open_store

    db = _db(hub_var)
    ledgers = copy_ledgers(hub_var / "ids")
    assert main(["imports", "list"]) == 0
    listed = capsys.readouterr().out.splitlines()
    assert [ln.split("@")[0] for ln in listed] == ["registry", "profile_lines", "old_hub", "ground_layers"]
    assert main(["imports", "run", "profile_lines", "--dry-run", "--json", "--ledger-dir", str(ledgers)]) == 0
    (dry,) = json.loads(capsys.readouterr().out)
    assert dry["dry_run"] and dry["counts"]["created"] == 1405
    with open_store(db, readonly=True) as store:
        assert store.last_seq() == 0  # a dry run writes no record
    held = lock.acquire(hub_var, 8766)
    try:
        assert main(["imports", "run", "--ledger-dir", str(ledgers)]) == 1
        err = capsys.readouterr().err
        assert "crhub serve" in err
    finally:
        held.release()
    assert main(["imports", "run", "registry", "--ledger-dir", str(ledgers)]) == 0
    assert "import:registry" in capsys.readouterr().out
    with open_store(db, readonly=True) as store:
        run = store.import_run(1)
    assert main(["imports", "show", str(run["id"])]) == 0
    assert json.loads(capsys.readouterr().out)["importer"] == "profile_lines"


def test_line_files_are_read_from_git(hub_var):
    """9.27: the line files are read from git's HEAD, so a working copy the Deck tie rewrote is not imported; the
    run says so, and records the sha256 of what it read."""
    from region.cli.imports import git_head, importer, resolve_sources

    if git_head() is None:
        pytest.skip("not a git checkout")
    stale = hub_var / "imports" / "git" / "0123456789ab" / "data" / "profile" / "lines"
    stale.mkdir(parents=True)
    (stale / "index.json").write_text("[]", encoding="utf-8")
    got = resolve_sources(importer("profile_lines"), work=hub_var / "imports")
    local = got.local["lines"]
    assert local.is_relative_to(hub_var / "imports" / "git")
    assert [p.name for p in (hub_var / "imports" / "git").iterdir()] == [git_head()[:12]]  # earlier copies pruned
    for route in METRO:
        assert (local / f"{route}.json").read_bytes().replace(b"\r\n", b"\n") == (
            (LINES / f"{route}.json").read_bytes().replace(b"\r\n", b"\n")
        )
        assert got.entries[f"lines/{route}.json"]["sha256"] == fsio.sha256_file(local / f"{route}.json")
    assert got.entries["lines/index.json"]["uri"] == "tier://profile_lines/lines/index.json"
