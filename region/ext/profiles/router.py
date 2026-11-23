"""The profiles feature's API, mounted under ``/api/v1/x/profiles/`` (section 5):

- ``GET /sections/{id}/input``: the section's SectionInput v0, with its ground profile (the line sheet solves it in
  the browser and draws the ground);
- ``GET /sections/{id}/stations``: the section's StationInput v0 (``station_input/0``): what ``station.facts@1``
  reads about each station (the sheet swaps in its draft's ``profile`` and ``section`` and solves it in the worker);
- ``GET /sections/{id}/solve``: the section's SectionSolveInput v0 (``section_solve_input/0``): what
  ``section.solve@1`` reads (the sheet swaps in its draft's profile and solves it in its worker after the rail and the
  station facts). The neighbours are read from their records (``solve_input.neighbour_view``), each one whose live
  stations all have a saved level; a line without saved levels (Lines 10, 11 and 13) is left out and its crossings
  are listed without its level. The request never plans or queues a job (a goal would be planned again on every
  change): the ``profiles.neighbour`` jobs, which give those lines the level solver's levels, run for
  ``profiles.solve_structure``;
- ``GET /routes/{id}/doc``: the old alignment doc rebuilt from the records (``doc.doc_of``), equal to the old hub's
  seed doc without its derived members (``stations``, ``summary``, ``updated``).

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
from .solve_input import neighbour_view, section_solve_input

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
    ctx = _reads(request)
    inp = section_solve_input(ctx, section_id)
    neighbours: dict[str, Any] = {}
    for x in inp["crossings"]:
        other, wid = x.get("other"), x["wid"]
        if not other or other == section_id or wid in neighbours:
            continue
        view = neighbour_view(ctx, other)
        if view is not None:
            neighbours[wid] = view
    inp["neighbours"] = neighbours
    return inp


def route_doc(ctx: StoreReads, route_id: str) -> dict[str, Any]:
    """The old alignment doc of one route, rebuilt from its records in ``ctx``'s view."""
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
    return doc_of(
        data,
        keys_of=keys_of,
        route_name=str(rd.get("name")),
        system_name=str((rd.get("attrs") or {}).get("system_name", rd.get("system"))),
        length_m=float(sec["data"]["length_m"]),
        platform_m=platform_m,
    )


@router.get("/routes/{route_id}/doc", summary="The old alignment doc of a route, rebuilt from its records")
def get_route_doc(route_id: str, request: Request) -> dict[str, Any]:
    return route_doc(_reads(request), route_id)


__all__ = [
    "get_route_doc",
    "get_section_input",
    "get_solve_input",
    "get_station_input",
    "route_doc",
    "router",
]
