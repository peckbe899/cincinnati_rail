"""The railsim feature's API, mounted under ``/api/v1/x/railsim/`` (plan section 1.5).

Saved runs need no route of their own: the sheet asks ``POST /compute {type: "railsim.run", scope: <route>}`` and
reads ``GET /results/{key}`` (the RunResult in ``meta``) and its arrays, as for every job. This router adds:

- ``POST /sections/{id}/draft``: railsim on the sheet's unsaved edit (``draft.py``). The body is the SectionInput of
  the draft (what the sheet's worker solves), the draft's ``type_runs`` when the sheet has them for this edit, and
  its edit revision. The hub solves the rail with ``vertical.rail@1`` on its own engine, lays it with the types and
  the draft's stations on the route's warm ``route.assemble`` and ``route.horizontal`` results (a cache read, never a
  plan), and runs the same ``adapter.run_route`` as ``railsim.run`` in the draft worker. 200 ``DraftOut``; 409
  ``pending`` while the route has no assemble or fit yet (the sheet asks again on their next ``result`` event); 409
  ``superseded`` when a newer draft of the same client and section arrived while this one waited; 422 for a
  SectionInput of another section, length or step.
- ``GET /routes/{id}/input``: the route's warm RouteInput (meta, and its arrays as lists), or 409 ``pending``.

Both read in the view of the query (``layer``, ``year``, ``month``, ``tl``) and write nothing. ``router`` is a
function of the ``Hub`` (``mount_features`` calls it), so the draft worker ends with the hub; the routes are built
even when the hub has no store, scheduler or engine (``openapi.json`` is made that way) and then answer 409
``pending``.
"""

from __future__ import annotations

import json
import weakref
from typing import Any

from fastapi import APIRouter, Request

from region.core import fsio
from region.core.errors import Conflict, Invalid, NotFound
from region.core.protocols import Output
from region.core.view import View

from .contract import DraftIn, DraftOut, RouteInput

ASSEMBLE = "route.assemble"
HORIZONTAL = "route.horizontal"
RUN = "railsim.run"
SOLVE_STRUCTURE = "profiles.solve_structure"
VERTICAL = "vertical.rail"


def _pending(what: str) -> Conflict:
    return Conflict(f"{what}; ask again on its next result event", reason="pending", code="pending")


def warm(jobs: Any, type_name: str, scope: str, view: View) -> tuple[str, dict[str, Any]] | None:
    """``(key, meta)`` of the newest ok result of a goal (a cache read: no plan, no job), or None."""
    cache = getattr(jobs, "cache", None)
    if cache is None:
        return None
    try:
        row = cache.one(
            "SELECT r.key, r.meta FROM goal g JOIN result r ON r.key = g.latest_key "
            "WHERE g.type = ? AND g.scope = ? AND g.view = ? AND r.status = 'ok'",
            (type_name, scope, view.token()),
        )
    except Exception:  # noqa: BLE001 - a cache this cannot read: nothing warm
        return None
    if row is None:
        return None
    meta = json.loads(row[1]) if isinstance(row[1], str) else (row[1] or {})
    return str(row[0]), meta if isinstance(meta, dict) else {}


def _arrays(jobs: Any, key: str) -> dict[str, Any]:
    return dict(jobs.cache.read_arrays(key))


def _route_of_section(ctx: Any, section_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    sec = ctx.read("section", section_id)
    if sec is None:
        raise NotFound(f"no section {section_id}", kind="section", id=section_id)
    rid = str((sec.get("data") or {}).get("route"))
    route = ctx.read("route", rid)
    if route is None:
        raise NotFound(f"no route {rid}", kind="route", id=rid)
    return sec, route


def _check_input(si: dict[str, Any], sec: dict[str, Any]) -> None:
    d = sec.get("data") or {}
    errors = []
    if si.get("section_id") != sec["id"]:
        errors.append({"path": "/section_input/section_id", "message": f"the draft is of {si.get('section_id')!r}"})
    for name in ("length_m", "step_m"):
        try:
            ok = abs(float(si.get(name)) - float(d[name])) < 1e-6
        except (TypeError, ValueError):
            ok = False
        if not ok:
            errors.append(
                {"path": f"/section_input/{name}", "message": f"{si.get(name)!r} is not the section's {d[name]}"}
            )
    if not isinstance(si.get("stations"), list):
        errors.append({"path": "/section_input/stations", "message": "a SectionInput has a list of stations"})
    if errors:
        raise Invalid("this draft is not of this section", errors=errors)


def _key(settings: dict[str, Any], meta: dict[str, Any], arrays: dict[str, Any]) -> str:
    """sha256 of the run's code, its settings (every file it read, parsed), the year and the draft RouteInput's
    content: equal drafts have equal keys."""
    from region.jobs.cache import output_hash
    from region.jobs.keys import code_hash

    from .jobs import RAILSIM_RUN

    body = {
        "code": code_hash(RAILSIM_RUN),
        "settings": fsio.sha256_hex(json.dumps(settings, sort_keys=True, default=str)),
        "year": settings.get("year"),
        "input": output_hash(Output(meta=meta, arrays=arrays)),
    }
    return fsio.sha256_hex(fsio.canonical_json(body))


def make_router(hub: Any = None) -> APIRouter:
    """The feature's routes, with a draft runner of their own (its worker starts on the first draft; closed with
    ``hub``)."""
    from .draft import DraftRunner

    r = APIRouter(tags=["railsim"])
    draft_runner = DraftRunner()
    if hub is not None:
        weakref.finalize(hub, draft_runner.close)

    def runner() -> DraftRunner:
        return draft_runner

    def _reads(request: Request) -> Any:
        from region.ext.profiles.inputs import StoreReads

        app_state = request.app.state
        store = getattr(app_state, "store", None)
        if store is None:
            raise _pending("this hub has no store")
        return StoreReads(store, View.from_query(request.query_params), getattr(app_state, "params", None))

    @r.post(
        "/sections/{section_id}/draft",
        summary="Run times of the sheet's unsaved edit of a section",
        response_model=DraftOut,
        response_model_by_alias=True,
    )
    def post_draft(section_id: str, body: DraftIn, request: Request) -> dict[str, Any]:
        from .draft import draft_input, plain_arrays
        from .legacy import run_settings

        ctx = _reads(request)
        jobs = getattr(request.app.state, "jobs", None)
        engine = getattr(request.app.state, "engine", None)
        sec, route = _route_of_section(ctx, section_id)
        si = dict(body.section_input)
        _check_input(si, sec)
        if jobs is None or engine is None:
            raise _pending("this hub runs no jobs or no engine")
        view = ctx.view
        asm = warm(jobs, ASSEMBLE, route["id"], view)
        fit = warm(jobs, HORIZONTAL, section_id, view)
        if asm is None or fit is None:
            raise _pending("the route has no route.assemble or route.horizontal result yet")
        out = engine.call(VERTICAL, {k: v for k, v in si.items() if k != "ground"})
        rail = {"c0": out["grid"]["c0"], "step_m": out["grid"]["step_m"], "rail_m": out["rail_m"]}
        if body.type_runs is not None:
            types, source = [list(t) for t in body.type_runs], "draft"
        else:
            st = warm(jobs, SOLVE_STRUCTURE, section_id, view)
            if st is None:
                raise _pending("the section has no structure solve yet")
            types, source = list(st[1].get("type_runs") or []), "saved"
        meta, arrays = draft_input(
            asm[1], {"meta": fit[1], "arrays": _arrays(jobs, fit[0])}, rail, types, si["stations"]
        )
        settings = run_settings(ctx, route, view.year)
        key = _key(settings, meta, arrays)
        client = request.headers.get("X-CR-Client") or "anonymous"
        run_meta, run_arrays, cached, ms = runner().run(
            client, section_id, key, {"meta": meta, "arrays": arrays, "settings": settings}
        )
        saved = warm(jobs, RUN, route["id"], view)
        return {
            **run_meta,
            "arrays": plain_arrays(run_arrays),
            "draft": True,
            "key": key,
            "cached": cached,
            "ms": round(ms, 1),
            "types": source,
            "base": {"assemble": asm[0], "run": saved[0] if saved else None},
            "edit_rev": body.edit_rev,
        }

    @r.get(
        "/routes/{route_id}/input",
        summary="The warm RouteInput of a route (route.assemble), never planned",
        response_model=RouteInput,
        response_model_by_alias=True,
    )
    def get_route_input(route_id: str, request: Request) -> dict[str, Any]:
        from .draft import plain_arrays

        ctx = _reads(request)
        if ctx.read("route", route_id) is None:
            raise NotFound(f"no route {route_id}", kind="route", id=route_id)
        jobs = getattr(request.app.state, "jobs", None)
        asm = warm(jobs, ASSEMBLE, route_id, ctx.view) if jobs is not None else None
        if asm is None:
            raise _pending("the route has no route.assemble result yet")
        return {**asm[1], "arrays": plain_arrays(_arrays(jobs, asm[0]))}

    r.draft_runner = draft_runner  # type: ignore[attr-defined]
    return r


router = make_router
"""``mount_features`` calls it with the ``Hub``."""

__all__ = ["make_router", "router", "warm"]
