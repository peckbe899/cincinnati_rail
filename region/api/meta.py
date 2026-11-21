"""``/meta``, ``/health`` and ``/tiers``.

- ``/meta``: the kinds with their schemas (each kind file as ``region.model.kinds.Kind.describe`` gives it, plus
  ``kind``), the features, importers and job types, the layers, the engine hello (null without an engine, with
  ``engine_error`` saying why), the schema version, the server ``epoch`` (the SSE hello's) and the database's
  ``db_epoch``, the newest ``seq``, the old hub's address and the state of the app build.
- ``/health``: liveness only, answered without touching the database, so doctor, setup and the e2e harness can poll
  it while the hub starts (``{"ok": true, "service": "crhub", ...}``).
- ``/tiers``: ``region.tiers.as_json(region.tiers.scan())``. Each call scans again and sends a ``tier`` event for
  every tier whose status changed since the last scan.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response

from . import models as M
from .context import hub_of
from .http import json_response
from .imports import describe, discover_importers

router = APIRouter(tags=["meta"])


def _schema_version(store: Any) -> int | None:
    try:
        from region.model.migrate import current_version

        return int(current_version(store._reader()))
    except Exception:
        return None


@router.get("/meta", response_model=M.Meta, summary="What this hub holds and runs")
def meta(request: Request) -> Response:
    hub = hub_of(request)
    store = hub.store
    kinds = []
    for name in store.kinds.names():
        d = store.kinds[name].describe()
        d["kind"] = name
        kinds.append(d)
    hello, engine_error = hub.engine_status()
    registry = getattr(hub.jobs, "registry", None)
    body = {
        "service": "crhub",
        "api": "v1",
        "epoch": hub.epoch,
        "db_epoch": store.epoch(),
        "seq": store.last_seq(),
        "started": hub.started,
        "schema_version": _schema_version(store),
        "kinds": kinds,
        "features": hub.features,
        "importers": [describe(f, imp) for f, imp in discover_importers()],
        "job_types": registry.describe() if registry is not None else [],
        "layers": store.layers(),
        "engine": hello,
        "engine_error": engine_error,
        "old_hub": hub.cfg.get("old_hub") or "http://127.0.0.1:8765",
        "app": hub.app,
        "config": {"host": hub.cfg.get("host"), "port": hub.cfg.get("port"), "old_hub": hub.cfg.get("old_hub")},
    }
    return json_response(body)


@router.get("/health", response_model=M.Health, summary="Liveness")
def health(request: Request) -> Response:
    hub = hub_of(request)
    return json_response(
        {"ok": True, "service": "crhub", "epoch": hub.epoch, "started": hub.started, "pid": os.getpid()},
        headers={"Cache-Control": "no-store"},
    )


@router.get("/tiers", response_model=M.Tiers, summary="The data tiers: missing, partial or present")
def tiers(request: Request) -> Response:
    from region import tiers as T

    hub = hub_of(request)
    reports = hub.events.scan_tiers() if hub.events is not None else T.scan(hub.cfg)
    return json_response(T.as_json(reports))


__all__ = ["router"]
