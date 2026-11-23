"""The profiles feature's API, mounted under ``/api/v1/x/profiles/`` (section 5):

- ``GET /sections/{id}/input``: the section's SectionInput v0, with its ground profile (the line sheet solves it in
  the browser and draws the ground);
- ``GET /sections/{id}/stations``: the section's StationInput v0 (``station_input/0``): what ``station.facts@1``
  reads about each station (the sheet swaps in its draft's ``profile`` and ``section`` and solves it in the worker);
- ``GET /sections/{id}/solve``: the section's SectionSolveInput v0 (``section_solve_input/0``): what
  ``section.solve@1`` reads (the sheet swaps in its draft's profile and solves it in its worker after the rail and the
  station facts). The neighbours are read from their records (``solve_input.neighbour_view``), each one whose live
  stations all have a saved level; a line without saved levels (Lines 10, 11 and 13) is read from the hub's warm
  ``profiles.neighbour`` result (``rails.warm_view``: its default design, kept ready by the live hub's background
  goals), and left out only while the hub has none. The request never plans or queues a job (a goal would be planned
  again on every change);
- ``GET /sections/{id}/design``: the design the section's rail is drawn with when it is not the saved profile as
  it stands (Lines 10, 11 and 13: the default design, "default design (not saved)"; Line 2b: its reframed profile),
  read warm without planning;
- ``GET /routes/{id}/doc``: the old alignment doc rebuilt from the records (``doc.doc_of``), equal to the old hub's
  seed doc, with the members the old page derived on save (``stations``, ``summary``, ``updated``) from the line's
  solve when the hub has its engine (R6).

Both read in the view of the query (``layer``, ``year``, ``month``, ``tl``) and only read. The store is the app's
``request.app.state.store`` (WP2 sets it); params resolve through ``app.state.params`` when the app sets one, else
``region.ext.rules.params.resolve``. Errors are ``region.core.errors``, which the app answers as problem JSON.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from region.core.errors import Invalid, NotFound
from region.core.view import View

from .doc import doc_of
from .inputs import StoreReads, section_input, station_input
from .rails import warm_design, warm_view
from .solve_input import needs_design, neighbour_view, section_solve_input

router = APIRouter(tags=["profiles"])


def _reads(request: Request) -> StoreReads:
    state = request.app.state
    store = getattr(state, "store", None)
    if store is None:
        raise NotFound("this hub has no store")
    return StoreReads(store, View.from_query(request.query_params), getattr(state, "params", None))


@router.get("/sections/{section_id}/input", summary="SectionInput v0 of a section")
def get_section_input(section_id: str, request: Request) -> dict[str, Any]:
    return section_input(_reads(request), section_id, ground=True)


@router.get("/sections/{section_id}/stations", summary="StationInput v0 of a section (the input of station.facts@1)")
def get_station_input(section_id: str, request: Request) -> dict[str, Any]:
    return station_input(_reads(request), section_id)


@router.get("/sections/{section_id}/solve", summary="SectionSolveInput v0 of a section (the input of section.solve@1)")
def get_solve_input(section_id: str, request: Request) -> dict[str, Any]:
    return _solve_input(request, _reads(request), section_id)


def _solve_input(request: Request, ctx: StoreReads, section_id: str) -> dict[str, Any]:
    inp = section_solve_input(ctx, section_id)
    jobs = getattr(request.app.state, "jobs", None)
    neighbours: dict[str, Any] = {}
    for x in inp["crossings"]:
        other, wid = x.get("other"), x["wid"]
        if not other or other == section_id or wid in neighbours:
            continue
        view = None
        if jobs is not None and needs_design(ctx, other):
            # no saved level, or saved in another frame (Line 2b): the rail its own solve drew, kept warm
            view = warm_view(jobs, other, ctx.view)
        if view is None:
            view = neighbour_view(ctx, other)
        if view is not None:
            neighbours[wid] = view
    inp["neighbours"] = neighbours
    return inp


@router.get("/sections/{section_id}/design", summary="The design a section's rail is drawn with, when not as saved")
def get_design(section_id: str, request: Request) -> dict[str, Any]:
    """``{"source": "saved"}`` when the profile is drawn as saved; else the design its own solve made (``source``
    default or partial, ``note`` "default design (not saved)", ``reframed``, ``defaulted``, levels ``st`` and slid
    centres ``c`` by platform id, bend points ``pvi``), read warm from the hub (``rails.warm_design``, never planned),
    or ``{"source": "pending"}`` while the hub has not solved it yet. Never written as Ben's record: the sheet draws
    it, and it becomes his only when he edits."""
    ctx = _reads(request)
    if not needs_design(ctx, section_id):
        return {"source": "saved"}
    jobs = getattr(request.app.state, "jobs", None)
    design = warm_design(jobs, section_id, ctx.view) if jobs is not None else None
    return design if design is not None else {"source": "pending"}


def route_doc(ctx: StoreReads, route_id: str, derive: Any = None) -> dict[str, Any]:
    """The old alignment doc of one route, rebuilt from its records in ``ctx``'s view. With ``derive`` (a function of
    the section id giving section.solve@1's answer) the doc carries the members the old page derived on save,
    ``stations`` and ``summary`` as serialize() wrote them (R6), and ``updated`` (the profile's last write)."""
    route = ctx.read("route", route_id)
    if route is None:
        raise NotFound(f"no route {route_id}", kind="route", id=route_id)
    sections = sorted(ctx.list("section", parent=route_id), key=lambda r: r["id"])
    if len(sections) != 1:
        raise Invalid(f"route {route_id} has {len(sections)} sections; the old doc stands for exactly one")
    sec = sections[0]
    profiles = sorted(ctx.list("profile", parent=sec["id"]), key=lambda r: r["id"])
    data = profiles[0]["data"] if profiles else {"section": sec["id"]}
    keys_of = {p["id"]: p["data"]["key"] for p in ctx.list("platform", parent=sec["id"])}
    rd = route.get("data") or {}
    attrs = data.get("attrs") or {}
    platform_m = None
    if "platform_m" not in attrs:
        prefix = "settings_rer" if rd.get("system") == "tri" else "settings"
        platform_m = ctx.param(f"{prefix}.platform", route_id)
    doc = doc_of(
        data,
        keys_of=keys_of,
        route_name=str(rd.get("name")),
        system_name=str((rd.get("attrs") or {}).get("system_name", rd.get("system"))),
        length_m=float(sec["data"]["length_m"]),
        platform_m=platform_m,
    )
    if derive is not None:
        derived = (derive(sec["id"]) or {}).get("derived")
        if isinstance(derived, dict):
            doc["stations"] = derived["stations"]
            doc["summary"] = derived["summary"]
            if profiles and profiles[0].get("updated"):
                doc["updated"] = profiles[0]["updated"]
    return doc


@router.get("/routes/{route_id}/doc", summary="The old alignment doc of a route, rebuilt from its records")
def get_route_doc(route_id: str, request: Request) -> dict[str, Any]:
    """The doc as the old page saved it: the profile's members, and, when the hub has its engine, the members the
    page derived on save (``stations``, ``summary``, ``updated``), from the line's solve as the records stand."""
    ctx = _reads(request)
    engine = getattr(request.app.state, "engine", None)
    derive = None
    if engine is not None and hasattr(engine, "call"):

        def derive(section_id: str) -> Any:
            return engine.call("section.solve", _solve_input(request, ctx, section_id))

    return route_doc(ctx, route_id, derive)


__all__ = [
    "get_design",
    "get_route_doc",
    "get_section_input",
    "get_solve_input",
    "get_station_input",
    "route_doc",
    "router",
]
