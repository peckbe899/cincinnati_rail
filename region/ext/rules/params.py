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

import copy
import threading
from typing import Any

from region.core.errors import NotFound
from region.core.view import View

PARAM = "param"

_CACHE_MAX = 512
_lock = threading.Lock()
_index_cache: dict[tuple[int, int, View], tuple[Any, int, dict[str, list[dict[str, Any]]]]] = {}
_route_cache: dict[tuple[int, int, View, str], tuple[Any, int, str | None]] = {}


def _records(store: Any, view: View) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    after = None
    while True:
        page, after = store.list(PARAM, view, limit=500, after=after)
        out.extend(page)
        if after is None:
            return out


def _token(store: Any) -> tuple[Any, int] | None:
    """This thread's reader and its ``PRAGMA data_version``: the number changes whenever another connection commits,
    and every write goes through the store's writer, so an equal number on the same connection means nothing was
    written since. ``None`` (no caching) for a store without a SQLite reader, or a reader inside a read transaction
    (its snapshot may be older than the cache)."""
    reader = getattr(store, "_reader", None)
    if reader is None:
        return None
    try:
        con = reader()
        if con.in_transaction:
            return None
        return con, int(con.execute("PRAGMA data_version").fetchone()[0])
    except Exception:  # noqa: BLE001 - a store this cannot read is resolved the slow way
        return None


def _put(cache: dict[Any, Any], key: Any, value: Any) -> None:
    with _lock:
        if len(cache) >= _CACHE_MAX:
            cache.clear()
        cache[key] = value


def _index(store: Any, view: View) -> dict[str, list[dict[str, Any]]]:
    """The param records of ``view`` by path, read once per write (``_token``): one SectionSolveInput resolves some
    200 params, and reading every param record for each was most of the hub's time while a line file was taken in.
    The entry keeps its connection, so a key's ``id`` is never another connection's."""
    tok = _token(store)
    if tok is not None:
        key = (id(store), id(tok[0]), view)
        with _lock:
            hit = _index_cache.get(key)
        if hit is not None and hit[0] is tok[0] and hit[1] == tok[1]:
            return hit[2]
    by_path: dict[str, list[dict[str, Any]]] = {}
    for rec in _records(store, view):
        data = rec.get("data") or {}
        by_path.setdefault(str(data.get("path")), []).append({"id": rec["id"], "data": data})
    if tok is not None:
        _put(_index_cache, key, (tok[0], tok[1], by_path))
    return by_path


def _route_of(store: Any, view: View, section_id: str) -> str | None:
    tok = _token(store)
    if tok is not None:
        key = (id(store), id(tok[0]), view, section_id)
        with _lock:
            hit = _route_cache.get(key)
        if hit is not None and hit[0] is tok[0] and hit[1] == tok[1]:
            return hit[2]
    try:
        sec = store.get("section", section_id, view)
    except NotFound:
        route = None
    else:
        r = (sec.get("data") or {}).get("route")
        route = r if isinstance(r, str) else None
    if tok is not None:
        _put(_route_cache, key, (tok[0], tok[1], route))
    return route


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
    for rec in _index(store, view).get(path, ()):
        data = rec["data"]
        if not in_years(data.get("years"), view.year):
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
    value = best[1]
    return copy.deepcopy(value) if isinstance(value, (dict, list)) else value


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
