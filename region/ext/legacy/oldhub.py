"""The old hub's records, read from its seed folder or from a snapshot of its database, never the live file.

The old hub (``hub/hub.py``) keeps one document per record path (``alignments/Line_6``, ``roadmap/r00``,
``data/users/local/camera_region``). Its export writes each to ``hub/seed/<path>.json``; its database holds them in
``docs(path, coll, data, version, updated, by)``. ``read_seed`` and ``read_db`` give the same ``{path: data}``
mapping from either, so the importer does not care which it was given.

``snapshot(live, dest)`` copies Ben's ``hub\\hub.db`` with SQLite's online backup API, opening the live file
read-only: a hub that is running keeps writing, and the copy is a consistent state of it (decision 9.23). Only the
copy is ever read.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from region.core import fsio
from region.core.errors import Invalid, NotFound

PREFIXES = ("alignments/", "roadmap/", "data/users/", "views/")
"""The record paths the importer reads."""


def read_seed(folder: Path) -> dict[str, Any]:
    """``{path: data}`` of the seed files under ``folder`` whose path starts with one of ``PREFIXES``."""
    folder = Path(folder)
    if not folder.is_dir():
        raise NotFound(f"no old hub seed at {folder}")
    out: dict[str, Any] = {}
    for f in sorted(folder.rglob("*.json")):
        rel = f.relative_to(folder).as_posix()[: -len(".json")]
        if not rel.startswith(PREFIXES):
            continue
        with open(f, encoding="utf-8-sig") as fh:
            try:
                out[rel] = json.load(fh)
            except json.JSONDecodeError as e:
                raise Invalid(f"old hub seed {f} is not JSON (a merge conflict?): {e}") from None
    return out


def read_db(path: Path) -> dict[str, Any]:
    """``{path: data}`` of the documents in an old hub database (a snapshot), for the paths in ``PREFIXES``."""
    con = sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT path, data FROM docs ORDER BY path").fetchall()
    except sqlite3.DatabaseError as e:
        raise Invalid(f"{path} is not an old hub database: {e}") from None
    finally:
        con.close()
    out: dict[str, Any] = {}
    for p, data in rows:
        if isinstance(p, str) and p.startswith(PREFIXES) and data is not None:
            out[p] = json.loads(data)
    return out


def snapshot(live: Path, dest: Path) -> Path:
    """Copy the old hub database ``live`` to ``dest`` with the online backup API (``live`` opened read-only) and
    return ``dest``. ``dest`` must pass the write guard."""
    live, dest = Path(live), Path(dest)
    if not live.is_file():
        raise NotFound(f"no old hub database at {live}")
    fsio.check_write(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    if part.exists():
        part.unlink()
    src = sqlite3.connect(f"{live.resolve().as_uri()}?mode=ro", uri=True)
    try:
        out = sqlite3.connect(part)
        try:
            src.backup(out)
            out.execute("PRAGMA journal_mode=DELETE")
        finally:
            out.close()
    finally:
        src.close()
    _replace(part, dest)
    return dest


def _replace(src: Path, dst: Path) -> None:
    """``os.replace`` with the write guard's retry on WinError 5 and 32 (a scanner holding the new file)."""
    deadline = time.monotonic() + fsio.RETRY_TOTAL_S
    delay = 0.01
    while True:
        try:
            os.replace(src, dst)
            return
        except OSError as e:
            if getattr(e, "winerror", None) not in fsio.RETRY_WINERRORS or time.monotonic() >= deadline:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 0.2)


__all__ = ["PREFIXES", "read_db", "read_seed", "snapshot"]
