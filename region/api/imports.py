"""Importer routes: ``GET /importers``, ``POST /imports`` (a dry run by default), ``GET /imports/{run}`` (the stored
report) and ``POST /imports/{run}/apply`` (apply a dry run, refused when its sources changed since).

The runner is the one ``crhub imports`` and ``crhub setup`` use (``region.cli.imports.run_one``, WP5): it resolves
the importer's sources (the line files from git's ``HEAD``, decision 9.27), records every file's sha256, gives the
importer an ``IdLookupImpl`` per namespace, and calls ``store.apply_import``, which diffs by content hash and
commits in one short transaction (9.28). A dry run writes only its ``import_run`` row. When that module cannot be
loaded, a plain runner here does the same without the git step.

An import runs on one of the server's worker threads for the length of the request (the 16 Metro routes take a few
seconds), and only one import runs at a time. Importers are found in the features (``IMPORTERS`` of
``region/ext/<f>/importers.py``).
"""

from __future__ import annotations

import hashlib
import logging
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response

from region.core import features, fsio, paths
from region.core.errors import Conflict, NotFound
from region.core.protocols import ImportRun

from . import models as M
from .context import hub_of, writer_of
from .http import json_response

log = logging.getLogger("region.api")
router = APIRouter(tags=["imports"])
_one_at_a_time = threading.Lock()


def discover_importers() -> list[tuple[str, Any]]:
    """``[(feature, importer)]`` of every feature (a feature whose importers fail to load is logged and skipped)."""
    out = []
    for f in features.discover():
        if not f.has("importers"):
            continue
        try:
            for imp in f.importers():
                out.append((f.name, imp))
        except Exception:
            log.exception("feature %s: importers.py failed to load; its importers are skipped", f.name)
    return out


def describe(feature: str, imp: Any) -> dict[str, Any]:
    return {
        "name": imp.name,
        "version": str(imp.version),
        "namespace": imp.namespace,
        "layer": imp.layer,
        "feature": feature,
    }


def _runner() -> Any | None:
    """``region.cli.imports`` (the shared runner), or ``None`` when it cannot be loaded."""
    try:
        from region.cli import imports as runner
    except Exception:
        log.exception("region.cli.imports failed to load; the server's plain import runner is used")
        return None
    return runner if hasattr(runner, "run_one") and hasattr(runner, "resolve_sources") else None


def find(name: str) -> Any:
    """The importer called ``name``: a feature's, else one the shared runner knows (``region.cli.imports.importers``,
    the list ``crhub imports`` and the start-up source check use)."""
    for _feature, imp in discover_importers():
        if imp.name == name:
            return imp
    runner = _runner()
    if runner is not None and hasattr(runner, "importers"):
        found = runner.importers().get(name)
        if found is not None:
            return found
    raise NotFound(f"no importer {name!r}")


def current_sources(imp: Any) -> dict[str, Any]:
    """The ``sources`` an import run of ``imp`` would record now."""
    runner = _runner()
    if runner is not None:
        return dict(runner.resolve_sources(imp).entries)
    return resolve_sources(imp)[0]


def source_sha256(path: Path) -> str:
    """The sha256 of a file's bytes, or of a folder's sorted ``<relpath> <sha256>`` lines (hidden files skipped)."""
    if path.is_file():
        return fsio.sha256_file(path)
    if path.is_dir():
        lines = []
        for p in sorted(path.rglob("*")):
            rel = p.relative_to(path)
            if p.is_file() and not any(part.startswith(".") for part in rel.parts):
                lines.append(f"{rel.as_posix()} {fsio.sha256_file(p)}\n")
        return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
    raise NotFound(f"import source {path} does not exist")


def resolve_sources(imp: Any) -> tuple[dict[str, dict[str, str]], dict[str, Path]]:
    """``({name: {uri, sha256}}, {name: local path})`` of an importer's sources."""
    named = imp.sources(paths)
    hashed: dict[str, dict[str, str]] = {}
    local: dict[str, Path] = {}
    for name, uri in sorted(named.items()):
        p = paths.resolve(uri)
        hashed[name] = {"uri": uri, "sha256": source_sha256(p)}
        local[name] = p
    return hashed, local


def run_import(store: Any, imp: Any, *, dry_run: bool, by: str | None = None) -> dict[str, Any]:
    """Run one importer against the store; return the report as JSON (``run`` is the ``import_run`` id)."""
    import dataclasses

    runner = _runner()
    if runner is not None:
        with _one_at_a_time:
            done = runner.run_one(store, imp, dry_run=dry_run)
        out = dataclasses.asdict(done.report)
        out["notes"] = list(getattr(done.sources, "notes", []) or [])
        return out
    with _one_at_a_time:
        sources, local = resolve_sources(imp)
        run = ImportRun(imp.name, str(imp.version), imp.layer, imp.namespace, sources=sources, by=by or "")
        ids = store.id_lookup(layer=imp.layer, namespace=imp.namespace)
        records = list(imp.records(local, ids))
        rep = store.apply_import(run, records, dry_run=dry_run, ids=ids)
    return dataclasses.asdict(rep)


@router.get("/importers", response_model=M.ImporterList, summary="The importers of every feature")
def importers() -> Response:
    return json_response({"items": [describe(f, imp) for f, imp in discover_importers()]})


@router.post("/imports", response_model=M.ImportRunOut, responses=M.problems(404, 409, 422))
def post_import(request: Request, body: M.ImportIn) -> Response:
    """Run an importer: a dry run (the default) reports counts and changes and writes nothing but its run row."""
    writer_of(request)
    imp = find(body.importer)
    rep = run_import(hub_of(request).store, imp, dry_run=body.dry_run)
    return json_response({"id": rep.get("run"), "state": "planned" if body.dry_run else "applied", **rep})


@router.get("/imports/{run}", response_model=M.ImportRunOut, responses=M.problems(404))
def get_import(request: Request, run: int) -> Response:
    return json_response(hub_of(request).store.import_run(run))


@router.post("/imports/{run}/apply", response_model=M.ImportRunOut, responses=M.problems(404, 409, 422))
def apply_import(request: Request, run: int) -> Response:
    """Apply a dry run: the importer runs again, and only when every source still hashes as it did."""
    writer_of(request)
    store = hub_of(request).store
    planned = store.import_run(run)
    if not planned.get("dry_run"):
        raise Conflict(
            f"import run {run} was not a dry run", reason="layer", conflicts=[{"kind": "import_run", "id": run}]
        )
    imp = find(planned["importer"])
    now = current_sources(imp)
    before = planned.get("sources") or {}
    if now != before:
        changed = sorted(k for k in set(now) | set(before) if now.get(k) != before.get(k))
        raise Conflict(
            f"the sources of import run {run} changed since the dry run ({', '.join(changed)}); run a new dry run",
            reason="rebase",
            conflicts=[{"kind": "source", "id": k} for k in changed],
        )
    rep = run_import(store, imp, dry_run=False)
    return json_response({"id": rep.get("run"), "state": "applied", "planned": run, **rep})


__all__ = [
    "current_sources",
    "describe",
    "discover_importers",
    "find",
    "resolve_sources",
    "router",
    "run_import",
    "source_sha256",
]
