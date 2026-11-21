"""SectionInput v0 from records (section 7): everything ``vertical.rail@1`` needs about one section.

Python builds the input; the engine never reads records. ``section_input(ctx, section_id)`` reads, through ``ctx``
(a job's ``PlanCtx``, or ``StoreReads`` over a store for the router and tests):

- the ``section`` (length, chainage basis, scale, grid step) and its route (for the params' scope);
- its ``profile`` (``/k/profile?parent=<section>``; a section without one solves as an empty profile);
- its ``stop`` and ``platform`` records, in stop order;
- the params ``platform_m``, ``vc_radius_m`` and ``vc_min_len_m``: ``settings.*`` for the Metro, ``settings_rer.*``
  for the RER (``settings.vcMinLen`` where the RER has none), asked for with the route as scope, so a route's own
  value (the CVG Express's 204.216 m platforms) wins over the system's;
- with ``ground=True``, its ``ground_profile`` (decimetres to metres; a missing level is interpolated from its
  neighbours, since the contract carries numbers only).

The stations are the stops' platforms minus the profile's ``del``, in stop order, each at its stop's point plus the
profile's slide (``so``), with its level (``st``, null when unset) and grade (``sg``, 0 when unset, as the old page
reads a doc). The PVIs are the profile's, as ``{c_m, z_m}``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from region.core.errors import NotFound
from region.core.view import View

from .doc import pvi_points

CONTRACT = "section_input/0"
PARAMS = (("platform_m", "platform"), ("vc_radius_m", "vcRadius"), ("vc_min_len_m", "vcMinLen"))
PREFIX = {"metro": "settings", "tri": "settings_rer"}


class StoreReads:
    """``PlanCtx``'s reads over a store, for callers that are not jobs (the router, tests). ``params`` is a
    ``ParamResolver`` (default ``region.ext.rules.params.resolve``)."""

    def __init__(self, store: Any, view: View, params: Callable[..., Any] | None = None) -> None:
        from region.ext.rules.params import resolve

        self.store = store
        self.view = view
        self._params = params or resolve

    def read(self, kind: str, id: str) -> dict[str, Any] | None:
        try:
            return self.store.get(kind, id, self.view)
        except NotFound:
            return None

    def list(self, kind: str, **filters: Any) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        after = None
        while True:
            page, after = self.store.list(kind, self.view, **filters, limit=500, after=after)
            out.extend(page)
            if after is None:
                return out

    def param(self, path: str, scope: str | None = None) -> Any:
        return self._params(self.store, self.view, path, scope)

    def file(self, uri: str) -> Any:
        from region.core import paths

        return paths.resolve(uri)


@dataclass
class Section:
    """The records one section's input is built from."""

    section: dict[str, Any]
    profile: dict[str, Any] | None
    stops: list[dict[str, Any]]
    platforms: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    ground: dict[str, Any] | None = None

    @property
    def data(self) -> dict[str, Any]:
        return self.section.get("data") or {}

    @property
    def profile_data(self) -> dict[str, Any]:
        return (self.profile or {}).get("data") or {}

    def ordered_platforms(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        """``(stop, platform)`` pairs in stop order (several platforms of one stop by id)."""
        out = []
        for stop in self.stops:
            for p in self.platforms.get(stop["id"], []):
                out.append((stop, p))
        return out


def gather(ctx: Any, section_id: str, *, ground: bool = False) -> Section:
    """Read one section's records through ``ctx``; ``NotFound`` when the section does not resolve."""
    sec = ctx.read("section", section_id)
    if sec is None:
        raise NotFound(f"no section {section_id}", kind="section", id=section_id)
    profiles = sorted(ctx.list("profile", parent=section_id), key=lambda r: r["id"])
    stops = sorted(
        ctx.list("stop", parent=section_id),
        key=lambda r: ((r["data"].get("order") or 0), float(r["data"].get("c") or 0.0), r["id"]),
    )
    plats: dict[str, list[dict[str, Any]]] = {}
    for p in sorted(ctx.list("platform", parent=section_id), key=lambda r: r["id"]):
        plats.setdefault(p["data"].get("stop"), []).append(p)
    grounds = sorted(ctx.list("ground_profile", parent=section_id), key=lambda r: r["id"]) if ground else []
    return Section(sec, profiles[0] if profiles else None, stops, plats, grounds[0] if grounds else None)


def params_of(ctx: Any, section: Mapping[str, Any]) -> dict[str, float]:
    """The section's resolved params, scoped to its route."""
    data = section.get("data") or {}
    prefix = PREFIX.get(str(data.get("system")), "settings")
    scope = data.get("route") if isinstance(data.get("route"), str) else None
    out: dict[str, float] = {}
    for name, key in PARAMS:
        try:
            out[name] = ctx.param(f"{prefix}.{key}", scope)
        except NotFound:
            if prefix == "settings":
                raise
            out[name] = ctx.param(f"settings.{key}", scope)
    return out


def ground_levels(z_dm: list[int | None]) -> list[float]:
    """Metres from decimetres; a missing level takes the straight line between its nearest neighbours (or the
    nearest one at an end)."""
    known = [(i, v / 10) for i, v in enumerate(z_dm) if v is not None]
    if not known:
        return []
    out: list[float] = []
    k = 0
    for i, v in enumerate(z_dm):
        if v is not None:
            out.append(v / 10)
            continue
        while k + 1 < len(known) and known[k + 1][0] < i:
            k += 1
        lo = known[k] if known[k][0] < i else None
        hi = next((p for p in known[k:] if p[0] > i), None)
        if lo is None:
            out.append(hi[1] if hi else known[0][1])
        elif hi is None:
            out.append(lo[1])
        else:
            t = (i - lo[0]) / (hi[0] - lo[0])
            out.append(lo[1] + t * (hi[1] - lo[1]))
    return out


def build(g: Section, params: Mapping[str, float], *, step_m: float | None = None) -> dict[str, Any]:
    """The SectionInput of gathered records with resolved params."""
    d = g.data
    prof = g.profile_data
    deleted = set(prof.get("del") or [])
    st = prof.get("st") or {}
    sg = prof.get("sg") or {}
    so = prof.get("so") or {}
    stations = []
    for stop, plat in g.ordered_platforms():
        pid = plat["id"]
        if pid in deleted:
            continue
        slide = so.get(pid)
        c = stop["data"]["c"]
        stations.append(
            {
                "platform_id": pid,
                "order": len(stations),
                "c_m": c + slide if isinstance(slide, (int, float)) else c,
                "level_m": st.get(pid),
                "grade_permille": sg.get(pid, 0),
            }
        )
    out: dict[str, Any] = {
        "contract": CONTRACT,
        "section_id": g.section["id"],
        "length_m": d["length_m"],
        "chainage_basis": d["chainage_basis"],
        "scale": d["scale"],
        "step_m": step_m if step_m is not None else d["step_m"],
        "params": dict(params),
        "stations": stations,
        "pvi": [{"c_m": c, "z_m": z} for c, z in pvi_points(prof)],
    }
    if g.ground is not None:
        gd = g.ground.get("data") or {}
        out["ground"] = {"step_m": gd["step_m"], "z_m": ground_levels(list(gd.get("z_dm") or []))}
    return out


def section_input(ctx: Any, section_id: str, *, step_m: float | None = None, ground: bool = True) -> dict[str, Any]:
    """The SectionInput v0 of one section, read through ``ctx`` (see the module doc)."""
    g = gather(ctx, section_id, ground=ground)
    return build(g, params_of(ctx, g.section), step_m=step_m)


__all__ = [
    "CONTRACT",
    "PARAMS",
    "Section",
    "StoreReads",
    "build",
    "gather",
    "ground_levels",
    "params_of",
    "section_input",
]
