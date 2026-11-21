"""Job and result routes over the scheduler (section 6): ``/compute``, ``/results``, ``/jobs``.

- ``POST /compute`` plans the job now and answers 200 ``{key, state, job}``: ``hit`` (a result exists, ``job`` is
  null), ``queued`` or ``running``. With ``watch_s`` the goal is also kept fresh for that long.
- ``GET /results?type&scope&view`` answers 200 ``{key}``, ``key`` null when the goal has no result yet (never a 404:
  the app polls it, and Chromium logs every 4xx as a console error).
- ``GET /results/{key}`` and ``/results/{key}/a/{name}`` are immutable: the ETag is the key, a repeat with
  ``If-None-Match`` gets 304, and the array bytes (raw little-endian, C order) carry ``X-Dtype`` and ``X-Shape`` and
  answer ``Range``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from region.core.view import View

from . import models as M
from .context import hub_of, writer_of
from .http import bytes_response, etag_matches, json_response, not_modified

router = APIRouter(tags=["jobs"])

IMMUTABLE = "public, max-age=31536000, immutable"


def parse_view(value: Any) -> View:
    """A view from a token (``"try|1931|canon"``) or a ``ViewIn``."""
    if isinstance(value, M.ViewIn):
        return View(layer=value.layer, year=value.year, month=value.month, timeline=value.tl)
    return View.parse(str(value))


@router.post("/compute", response_model=M.ComputeOut, responses=M.problems(404, 422, 503), summary="Compute")
def compute(request: Request, body: M.ComputeIn) -> Response:
    """Plan a job now: a cache hit answers at once, otherwise one job is queued for the key."""
    writer_of(request)
    jobs = hub_of(request).jobs
    view = parse_view(body.view)
    out = jobs.submit(body.type, body.scope, view, priority=body.priority)
    if body.watch_s is not None:
        jobs.watch_goal(body.type, body.scope, view, priority=body.priority, ttl_s=body.watch_s)
    return json_response({"key": out.get("key"), "state": out.get("state"), "job": out.get("job")})


@router.get("/results", response_model=M.LatestResult, summary="The latest result of a goal")
def latest(
    request: Request,
    type: str = Query(description="the job type"),
    scope: str = Query(description="the scope id"),
    view: str = Query("main|-|canon", description="the view token"),
) -> Response:
    return json_response({"key": hub_of(request).jobs.result(type, scope, View.parse(view))})


@router.get("/results/{key}", response_model=M.ResultMeta, responses=M.problems(404))
def result(request: Request, key: str) -> Response:
    """A result's row, issues and dependencies."""
    tag = f'"{key}"'
    if etag_matches(request.headers.get("if-none-match"), tag):
        return not_modified(tag, cache_control=IMMUTABLE)
    meta = hub_of(request).jobs.result_meta(key)
    return json_response(meta, etag=tag, headers={"Cache-Control": IMMUTABLE})


@router.get(
    "/results/{key}/a/{name}",
    responses={200: {"content": {"application/octet-stream": {}}, "description": "the array's raw bytes"}},
    response_class=Response,
)
def result_array(request: Request, key: str, name: str) -> Response:
    """One output array as raw bytes, with ``X-Dtype`` and ``X-Shape`` (comma-separated)."""
    tag = f'"{key}"'
    if etag_matches(request.headers.get("if-none-match"), tag):
        return not_modified(tag, cache_control=IMMUTABLE)
    data, dtype, shape = hub_of(request).jobs.array_bytes(key, name)
    headers = {"X-Dtype": dtype, "X-Shape": ",".join(str(n) for n in shape)}
    return bytes_response(
        request.headers, data, media_type="application/octet-stream", etag=tag, headers=headers,
        cache_control=IMMUTABLE,
    )


@router.get("/jobs", response_model=M.JobList, summary="Jobs, newest first")
def list_jobs(
    request: Request,
    active: bool = Query(False, description="only queued and running jobs"),
    limit: int = Query(500, ge=1, le=5000),
) -> Response:
    return json_response({"items": hub_of(request).jobs.jobs(active=active, limit=limit)})


@router.get("/jobs/{id}", response_model=M.Job, responses=M.problems(404))
def get_job(request: Request, id: str) -> Response:
    return json_response(hub_of(request).jobs.job(id))


@router.get("/jobs/{id}/log", response_model=M.JobLog, responses=M.problems(404))
def job_log(request: Request, id: str) -> Response:
    return json_response({"items": hub_of(request).jobs.job_log(id)})


@router.post("/jobs/{id}/cancel", status_code=204, responses=M.problems(404), response_class=Response)
def cancel(request: Request, id: str) -> Response:
    writer_of(request)
    hub_of(request).jobs.cancel(id)
    return Response(status_code=204)


__all__ = ["parse_view", "router"]
