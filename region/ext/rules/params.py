"""Param resolution (9.25): the most specific scope wins (section, then its route, then the system), then the years.

A ``param`` record is ``{path, value, unit, scope, years, ...}``: ``scope`` is ``null`` for the whole system or
``{"kind": "route" | "section", "id"}``; ``years`` is ``[lo, hi]`` (either end null) or ``null`` for always. Records
resolve in the view's layer chain first, so Ben's main revision of a registry param is the value main reads.

``resolve(store, view, path, scope)`` is a ``region.jobs.plan.ParamResolver`` and the only statement of the rule:
the scheduler's default (``region.jobs.plan.resolve_param``) calls it. Given a section id as ``scope`` it looks up the
section's route itself, so the profiles jobs and the router ask with the section id.

**Years.** At a view year, a record counts when its ``years`` hold that year. At the present (``view.year`` is
``None``), a record counts when it has no ``years`` or its range is still open (``hi`` null): a value that ended in
1950 is history, not the present one. Among the records that count, the narrower range wins.
"""

from __future__ import annotations

from typing import Any

from region.core.errors import NotFound
from region.core.view import View

PARAM = "param"


def _records(store: Any, view: View) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    after = None
    while True:
        page, after = store.list(PARAM, view, limit=500, after=after)
        out.extend(page)
        if after is None:
            return out


def _route_of(store: Any, view: View, section_id: str) -> str | None:
    try:
        sec = store.get("section", section_id, view)
    except NotFound:
        return None
    route = (sec.get("data") or {}).get("route")
    return route if isinstance(route, str) else None


def in_years(years: Any, year: int | None) -> bool:
    """Whether a param's ``years`` hold ``year``. At the present (``year is None``) only a range still open (``hi``
    null) does; a record without ``years`` counts at every year."""
    if not isinstance(years, list) or len(years) != 2:
        return True
    lo, hi = years
    if year is None:
        return hi is None
    return (lo is None or year >= lo) and (hi is None or year <= hi)


def _narrowness(years: Any) -> int:
    if not isinstance(years, list) or len(years) != 2:
        return 0
    return int(years[0] is not None) + int(years[1] is not None)


def resolve(store: Any, view: View, path: str, scope: str | None = None) -> Any:
    """The value of param ``path`` for ``scope`` (a section or route id, or ``None``) in ``view``. ``NotFound`` when
    no record holds the path for that scope or the system."""
    route = _route_of(store, view, scope) if scope is not None else None
    best: tuple[tuple[int, int, str], Any] | None = None
    for rec in _records(store, view):
        data = rec.get("data") or {}
        if data.get("path") != path or not in_years(data.get("years"), view.year):
            continue
        sc = data.get("scope")
        if sc is None:
            rank = 1
        elif not isinstance(sc, dict) or scope is None:
            continue
        elif sc.get("kind") == "section" and sc.get("id") == scope:
            rank = 3
        elif sc.get("kind") == "route" and sc.get("id") in (scope, route):
            rank = 2
        else:
            continue
        order = (rank, _narrowness(data.get("years")), rec["id"])
        if best is None or order > best[0]:
            best = (order, data.get("value"))
    if best is None:
        raise NotFound(f"no param {path}" + (f" for {scope}" if scope else ""))
    return best[1]


def review(store: Any) -> dict[str, list[dict[str, Any]]]:
    """Ben's param revisions on main and the proposals, against the layer below each (9.25, design rule 4):

    - ``unratified``: a value that differs from the one below (the registry's) and names no ``ruling``;
    - ``redundant``: content equal to the layer below again (the registry adopted Ben's value), so the revision can
      go.

    Each entry is ``{"layer", "id", "path", "value", "below"}``. Read-only; ``crhub serve`` prints the counts at start.
    """
    out: dict[str, list[dict[str, Any]]] = {"unratified": [], "redundant": []}
    for lay in store.layers():
        if lay["tier"] not in ("main", "proposal") or lay["state"] != "open":
            continue
        chain = store.chain(View(layer=lay["slug"]))
        if len(chain) < 2:
            continue
        below_view = View(layer=chain[1])
        for rec in store.layer_records(lay["slug"], PARAM):
            try:
                below = store.get(PARAM, rec["id"], below_view)
            except NotFound:
                continue
            data, bdata = rec.get("data") or {}, below.get("data") or {}
            entry = {
                "layer": lay["slug"],
                "id": rec["id"],
                "path": data.get("path"),
                "value": data.get("value"),
                "below": bdata.get("value"),
            }
            if data == bdata and rec.get("geom") == below.get("geom"):
                out["redundant"].append(entry)
            elif data.get("value") != bdata.get("value") and not data.get("ruling"):
                out["unratified"].append(entry)
    return out


__all__ = ["PARAM", "in_years", "resolve", "review"]
