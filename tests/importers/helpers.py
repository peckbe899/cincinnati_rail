"""Shared steps of the importer and profile tests: the repo's sources, a fresh store, a full import, and one fully
imported database per test process that read-only tests share and writing tests copy."""

from __future__ import annotations

import atexit
import json
import shutil
import sqlite3
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

from region.core import fsio, paths
from region.core.view import View

REPO = paths.repo_root()
LINES = REPO / "data" / "profile" / "lines"
SEED = REPO / "hub" / "seed"
REGISTRY = REPO / "rules" / "registry.yaml"
LEDGERS = REPO / "region" / "ids"
ALIGNMENTS = SEED / "alignments"
METRO = [e["id"] for e in json.loads((LINES / "index.json").read_text(encoding="utf-8"))]
DOCLESS = ["Line_10", "Line_11", "Line_13"]
DOCS = [r for r in METRO if r not in DOCLESS]
MAIN = View()


def copy_ledgers(dest: Path) -> Path:
    """The committed id ledgers copied into ``dest`` (so a test run never appends to region/ids)."""
    dest.mkdir(parents=True, exist_ok=True)
    for f in LEDGERS.glob("*.tsv"):
        shutil.copyfile(f, dest / f.name)
    return dest


def open_fresh(root: Path, name: str = "region.db") -> Any:
    from region.model import open_store

    return open_store(root / name)


def import_all(store: Any, root: Path, names: list[str] | None = None, **kw: Any) -> dict[str, Any]:
    """Run the importers (default all, in order) with scratch ledgers and work folders under ``root``;
    ``{name: Run}``."""
    from region.cli import imports as I

    kw.setdefault("ledger_dir", root / "ids")
    kw.setdefault("work", root / "work")
    return {r.report.importer: r for r in I.run_all(store, names, **kw)}


def copy_db(src: Path, dest: Path) -> Path:
    """A consistent copy of a database file (the backup API)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    a = sqlite3.connect(src)
    try:
        b = sqlite3.connect(dest)
        try:
            a.backup(b)
        finally:
            b.close()
    finally:
        a.close()
    return dest


@lru_cache(maxsize=1)
def imported() -> Path:
    """A database with every importer applied once over the repo's sources, built once per process. Tests that only
    read open it read-only; tests that write take ``copy_db`` of it."""
    root = Path(tempfile.mkdtemp(prefix="crhub-imported-"))
    atexit.register(shutil.rmtree, root, True)
    with fsio.allow_writes(root):
        copy_ledgers(root / "ids")
        store = open_fresh(root)
        try:
            import_all(store, root)
        finally:
            store.close()
    return root / "region.db"


def fresh_copy(tmp: Path) -> Any:
    """A writable store over a copy of the imported database in ``tmp`` (writes must be allowed there)."""
    from region.model import open_store

    copy_ledgers(tmp / "ids")
    return open_store(copy_db(imported(), tmp / "region.db"))


def read_only() -> Any:
    from region.model import open_store

    return open_store(imported(), readonly=True)


def all_records(store: Any, kind: str, view: View = MAIN, **filters: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    after = None
    while True:
        page, after = store.list(kind, view, **filters, limit=500, after=after)
        out.extend(page)
        if after is None:
            return out


def section_of(store: Any, route: str) -> dict[str, Any]:
    sid = store.legacy("section", route)
    assert sid is not None, f"no section for {route}"
    return store.get("section", sid, MAIN)


def profile_of(store: Any, route: str, view: View = MAIN) -> dict[str, Any]:
    sid = store.legacy("section", route)
    found = all_records(store, "profile", view, parent=sid)
    assert len(found) == 1, f"{route}: {len(found)} profiles"
    return found[0]
