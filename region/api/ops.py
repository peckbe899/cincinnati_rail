"""Ops routes: ``POST /export`` (the seed export, run directly: it imports pulled seeds first and refuses while seed
conflicts are open), ``POST /backup`` (an online, checked backup into the database's backup folder) and
``POST /client-log`` (a browser error into the hub log, under ``region.client``).

``/export`` calls ``region.model.seed.export`` itself rather than as a ``seed.export`` job: a job plans through one
view, so a change made only in a proposal would leave a main export's key unchanged and the export would write
nothing (see ``region/jobs/types/seed.py``)."""

from __future__ import annotations

import threading
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response

from region.core import log as hub_log

from . import models as M
from .context import hub_of, writer_of
from .http import json_response

router = APIRouter(tags=["ops"])
_exporting = threading.Lock()


@router.post("/export", responses=M.problems(409, 422), summary="Export the seeded layers to region/seed")
def export(request: Request) -> Response:
    writer_of(request)
    from region.model import seed

    store = hub_of(request).store
    with _exporting:
        rep: dict[str, Any] = seed.export(store)
    return json_response(rep)


@router.post("/backup", responses=M.problems(409), summary="Back the database up now")
def backup(request: Request) -> Response:
    writer_of(request)
    path = hub_of(request).store.backup("manual")
    return json_response({"path": str(path), "name": path.name})


@router.post("/client-log", status_code=204, response_class=Response, summary="A browser log entry")
def client_log(request: Request, entry: M.ClientLogIn) -> Response:
    raw = entry.model_dump()
    raw["client"] = request.headers.get("x-cr-client")
    plain = {k: v if v is None or isinstance(v, (str, int, float, bool)) else str(v)[:4000] for k, v in raw.items()}
    hub_log.client_log(plain)
    return Response(status_code=204)


__all__ = ["router"]
