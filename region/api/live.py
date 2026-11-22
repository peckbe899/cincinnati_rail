"""The live hub's routes (``region/live``): its state, Pause live, Undo this import, and pane focus.

- ``GET /live``: ``{enabled, paused, pending, updated, sources, history, counts, marks}`` (``enabled`` false and
  nothing else when the hub serves with ``--no-live``);
- ``POST /live/pause`` and ``POST /live/resume``: stop and restart acting on changes (the watcher keeps counting);
- ``POST /live/sources/{source}/undo``: revert the source's last import changeset and hold its files until they
  change again; ``.../apply``: take held files anyway; ``.../check``: look at the source now;
- ``GET /live/pending``: the sections being imported or re-solved;
- ``POST /live/focus``: ``{type, scope, view, priority}``, a pane's goal made more or less urgent (0 for the pane in
  focus, 1 for an open pane, 5 once it closes), its queued job with it.

Every write requires ``X-CR-Client`` (the security middleware) and is answered with the source's or the hub's new
state; the same arrives over SSE as ``source`` and ``live`` events.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response

from region.core.errors import HubError
from region.core.view import View

from . import models as M
from .context import hub_of, writer_of
from .http import json_response

router = APIRouter(tags=["live"])


class LiveOff(HubError):
    status = 409
    code = "live_off"
    title = "Live is off"


def _live(request: Request) -> Any:
    live = getattr(hub_of(request), "live", None)
    if live is None:
        raise LiveOff("the hub serves without live updates (crhub serve --no-live)")
    return live


@router.get("/live", response_model=M.LiveStatus, summary="The live hub: sources, their state, Pause live")
def live_status(request: Request) -> Response:
    live = getattr(hub_of(request), "live", None)
    if live is None:
        return json_response({"enabled": False, "paused": False, "pending": 0, "updated": None})
    return json_response({"enabled": True, **live.status()})


@router.post("/live/pause", response_model=M.LiveSummary, responses=M.problems(409), summary="Pause live")
def live_pause(request: Request) -> Response:
    w = writer_of(request)
    return json_response(_live(request).pause(by=w.by))


@router.post("/live/resume", response_model=M.LiveSummary, responses=M.problems(409), summary="Resume live")
def live_resume(request: Request) -> Response:
    w = writer_of(request)
    return json_response(_live(request).resume(by=w.by))


@router.post(
    "/live/sources/{source}/undo",
    response_model=M.LiveSource,
    responses=M.problems(404, 409),
    summary="Undo this import",
)
def live_undo(request: Request, source: str) -> Response:
    w = writer_of(request)
    return json_response(_live(request).undo(source, by=w.by, client=w.client))


@router.post(
    "/live/sources/{source}/apply",
    response_model=M.LiveSource,
    responses=M.problems(404, 409),
    summary="Import held files anyway",
)
def live_apply(request: Request, source: str) -> Response:
    writer_of(request)
    return json_response(_live(request).apply_held(source))


@router.post(
    "/live/sources/{source}/check",
    response_model=M.LiveSource,
    responses=M.problems(404, 409),
    summary="Look at a source now",
)
def live_check(request: Request, source: str) -> Response:
    writer_of(request)
    return json_response(_live(request).check(source))


@router.get("/live/pending", response_model=M.PendingList, summary="Sections being imported or re-solved")
def live_pending(request: Request) -> Response:
    live = getattr(hub_of(request), "live", None)
    return json_response({"items": live.marks() if live is not None else []})


@router.post("/live/focus", status_code=204, response_class=Response, summary="A pane's goal priority")
def live_focus(request: Request, body: M.FocusIn) -> Response:
    writer_of(request)
    jobs = hub_of(request).jobs
    setter = getattr(jobs, "set_priority", None)
    if callable(setter):
        setter(body.type, body.scope, View.parse(body.view), body.priority)
    return Response(status_code=204)


__all__ = ["LiveOff", "router"]
