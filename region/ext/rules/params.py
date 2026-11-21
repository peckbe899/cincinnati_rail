"""Param resolution (9.25): the most specific scope wins (section, then its route, then the system), then the years.

A ``param`` record is ``{path, value, unit, scope, years, ...}``: ``scope`` is ``null`` for the whole system or
``{"kind": "route" | "section", "id"}``; ``years`` is ``[lo, hi]`` (either end null) or ``null`` for always. Records
resolve in the view's layer chain first, so Ben's main revision of a registry param is the value main reads.

``resolve(store, view, path, scope)`` is a ``region.jobs.plan.ParamResolver``: pass it as ``Scheduler(params=...)``.
Given a section id as ``scope`` it looks up the section's route itself. The jobs of this increment ask with the
route id, which the scheduler's default resolver (an exact scope or the system) also answers correctly.
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
    """Whether a param's ``years`` hold ``year`` (any year counts at the present, ``year is None``)."""
    if year is None or not isinstance(years, list) or len(years) != 2:
        return True
    lo, hi = years
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


__all__ = ["PARAM", "in_years", "resolve"]
