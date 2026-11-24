"""The railsim feature's job types (plan section 1.2): ``route.horizontal@1``, ``route.assemble@1``,
``railsim.run@1`` and ``railsim.attribution@1``.

**route.horizontal@1** (scope a section; process host). ``plan`` reads the section (its drawn path, length, grid
step) and its route, and the geometry block of the route's line config (``legacy.geometry_config``); ``run`` fits
it (``horizontal.fit_section``). An edit that leaves the path as it was makes no new fit.

**route.assemble@1** (scope a route; engine host). ``plan`` reads the route, its one section, the section's profile,
stops and platforms (``profiles.inputs.gather``), the ``settings.platform`` param scoped to the section, and the
line config's station block and restrictions; it needs ``profiles.solve_section`` (the rail; for a line drawn on a
design that is not its saved profile, as Lines 10, 11 and 13 and Line 2b are, ``profiles.neighbour`` instead, whose
design the rail is drawn with on the engine, as the sheet draws it), ``profiles.solve_structure`` (the types) and
``route.horizontal``. ``run`` builds the RouteInput (``assemble.route_input``). A paint, a tube form, a station
access or a note that leaves the rail, the tunnel flags and the stops as they were gives the same output hash, so
``railsim.run`` is not run again (early cutoff). A route with more than one section is refused while services are
not records (I2.4).

**railsim.run@1** (scope a route; process host; axis year). ``plan`` reads the route, the line config, the era file
and the rolling stock (``legacy.run_settings``) and needs ``route.assemble``; ``run`` runs both directions
(``adapter.run_route``). The present (``year`` None) is the era file's ``default_year``.

**railsim.attribution@1** (scope a route; process host; axis year; priority 9). The run's reads plus
``railsim.run`` itself (an unchanged run reruns nothing), then ``attribution.attribute``.

Every type's ``code_files`` hold ``repo://railsim`` (the whole package, the "railsim source hash") and the lane's
own modules, so a change to either makes new keys. No plan or run writes; no run reads a file (``plan`` hands it
plain values).
"""

from __future__ import annotations

from typing import Any

from region.core.errors import Invalid, NotFound
from region.core.protocols import Output

RAILSIM = "repo://railsim"
OWN = "repo://region/ext/railsim/{}.py"
SOLVE_SECTION = "profiles.solve_section"
SOLVE_STRUCTURE = "profiles.solve_structure"
NEIGHBOUR = "profiles.neighbour"
HORIZONTAL = "route.horizontal"
ASSEMBLE = "route.assemble"
RUN = "railsim.run"
VERTICAL = "vertical.rail"


def _code(*names: str) -> tuple[str, ...]:
    return (RAILSIM, *(OWN.format(n) for n in names))


def _issues(warnings: list[str]) -> list[dict[str, Any]]:
    return [{"rule": None, "sev": "warn", "c0": 0.0, "c1": 0.0, "msg": w, "data": None} for w in warnings]


def _route(ctx: Any, route_id: str) -> dict[str, Any]:
    route = ctx.read("route", route_id)
    if route is None:
        raise NotFound(f"no route {route_id}", kind="route", id=route_id)
    return route


def _one_section(ctx: Any, route_id: str) -> dict[str, Any]:
    secs = sorted(ctx.list("section", parent=route_id), key=lambda r: r["id"])
    if len(secs) != 1:
        raise Invalid(f"route {route_id} has {len(secs)} sections; a run stands for one until services are records")
    return secs[0]


class RouteHorizontal:
    """``route.horizontal@1`` (see the module doc)."""

    name = HORIZONTAL
    version = "1"
    scope = "section"
    host = "process"
    priority = 3
    timeout_s = 60.0
    code_files = _code("horizontal", "legacy")

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        from . import legacy

        sec = ctx.read("section", scope_id)
        if sec is None:
            raise NotFound(f"no section {scope_id}", kind="section", id=scope_id)
        d = sec.get("data") or {}
        route = _route(ctx, str(d.get("route")))
        geometry = legacy.geometry_config(ctx, str((route.get("data") or {}).get("key")))
        return {"path": d["path"], "length_m": d["length_m"], "step_m": d["step_m"], "geometry": geometry}

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        from .horizontal import fit_section

        rt.progress(0.1, "fit")
        out = fit_section(inputs["path"], inputs["length_m"], inputs["step_m"], inputs["geometry"])
        rt.progress(1.0, "done")
        return Output(meta=out["meta"], arrays=out["arrays"])


class RouteAssemble:
    """``route.assemble@1`` (see the module doc)."""

    name = ASSEMBLE
    version = "1"
    scope = "route"
    host = "engine"
    priority = 3
    timeout_s = 30.0
    code_files = _code("assemble", "horizontal", "legacy")

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        from region.ext.profiles.inputs import build, gather, params_of
        from region.ext.profiles.solve_input import needs_design

        from . import legacy

        route = _route(ctx, scope_id)
        rd = route.get("data") or {}
        sec = _one_section(ctx, scope_id)
        sid = sec["id"]
        g = gather(ctx, sid)
        params = params_of(ctx, g.section)
        si = build(g, params)
        stem, cfg = legacy.line_config(ctx, str(rd.get("key")))
        defaults, info = legacy.station_info(cfg)
        prof = g.profile_data
        deleted = set(prof.get("del") or [])
        so = prof.get("so") or {}
        stations = []
        seen: set[str] = set()
        for stop, plat in g.ordered_platforms():
            if stop["id"] in seen:
                continue
            seen.add(stop["id"])
            pid = plat["id"]
            slide = so.get(pid)
            c = float(stop["data"]["c"]) + (float(slide) if isinstance(slide, (int, float)) else 0.0)
            stations.append(
                {
                    "platform_id": pid,
                    "name": str(stop["data"].get("name") or plat["data"].get("name")),
                    "c_m": c,
                    "removed": pid in deleted,
                }
            )
        sd = sec.get("data") or {}
        st_cfg = cfg.get("stations") or {}
        parts = {
            "route": {"id": route["id"], "key": rd.get("key"), "name": rd.get("name"), "system": rd.get("system")},
            "section": {"id": sid, "length_m": sd["length_m"], "step_m": sd["step_m"], "scale": sd.get("scale")},
            "config": stem,
            "stations": stations,
            "station_defaults": defaults,
            "station_info": info,
            "platform_m": params.get("platform_m"),
            "restrictions": cfg.get("restrictions") or [],
            "terminal_approach": cfg.get("terminal_approach"),
            "throat": st_cfg.get("throat"),
            "service_route": (cfg.get("service") or {}).get("route") or [],
            "operating_zones": cfg.get("operating_zones") or [],
            "neutral_sections": cfg.get("neutral_sections") or [],
            "supply_zones": (cfg.get("supply") or {}).get("zones") or [],
        }
        out: dict[str, Any] = {"parts": parts, "input": None, "rail": None, "design": None}
        if needs_design(ctx, sid):
            out["input"] = si
            out["design"] = ctx.need(NEIGHBOUR, sid)
            parts["rail_source"] = "profiles.neighbour design, vertical.rail"
        else:
            out["rail"] = ctx.need(SOLVE_SECTION, sid)
            parts["rail_source"] = SOLVE_SECTION
        out["types"] = ctx.need(SOLVE_STRUCTURE, sid)
        out["fit"] = ctx.need(HORIZONTAL, sid)
        return out

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        from .assemble import route_input

        parts = dict(inputs["parts"])
        if inputs.get("design"):
            from region.ext.profiles.solve_input import with_design

            design = (rt.upstream(inputs["design"]).meta or {}).get("design")
            si = with_design(inputs["input"], design)
            rt.progress(0.2, "rail")
            out = rt.engine.call(VERTICAL, si)
            rail = {"c0": out["grid"]["c0"], "step_m": out["grid"]["step_m"], "rail_m": out["rail_m"]}
            centres = {s["platform_id"]: float(s["c_m"]) for s in si["stations"]}
            parts["stations"] = [
                {**s, "c_m": centres.get(s["platform_id"], s["c_m"])} for s in parts["stations"]
            ]
        else:
            up = rt.upstream(inputs["rail"])
            grid = up.meta["grid"]
            rail = {"c0": grid["c0"], "step_m": grid["step_m"], "rail_m": up.arrays["rail_m"]}
        types = (rt.upstream(inputs["types"]).meta or {}).get("type_runs") or []
        fit = rt.upstream(inputs["fit"])
        rt.progress(0.6, "assemble")
        meta, arrays = route_input(parts, rail, types, {"meta": fit.meta, "arrays": fit.arrays})
        rt.progress(1.0, "done")
        return Output(meta=meta, arrays=arrays, issues=_issues(meta["warnings"]))


class RailsimRun:
    """``railsim.run@1`` (see the module doc)."""

    name = RUN
    version = "1"
    scope = "route"
    host = "process"
    priority = 3
    timeout_s = 60.0
    axes = ("year",)
    code_files = _code("adapter", "assemble", "legacy", "contract")

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        from . import legacy

        route = _route(ctx, scope_id)
        settings = legacy.run_settings(ctx, route, ctx.axis("year"))
        return {"route_input": ctx.need(ASSEMBLE, scope_id), "settings": settings}

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        from .adapter import run_route

        ri = rt.upstream(inputs["route_input"])
        rt.progress(0.1, "forward")
        meta, arrays = run_route(ri.meta, ri.arrays, inputs["settings"])
        rt.progress(1.0, "done")
        return Output(meta=meta, arrays=arrays, issues=_issues(meta["warnings"]))


class RailsimAttribution:
    """``railsim.attribution@1`` (see the module doc)."""

    name = "railsim.attribution"
    version = "1"
    scope = "route"
    host = "process"
    priority = 9
    timeout_s = 180.0
    axes = ("year",)
    code_files = _code("adapter", "assemble", "legacy", "contract", "attribution")

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        out = RAILSIM_RUN.plan(ctx, scope_id)
        out["run"] = ctx.need(RUN, scope_id)
        return out

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        from .attribution import attribute

        ri = rt.upstream(inputs["route_input"])
        run = rt.upstream(inputs["run"])
        meta = attribute(ri.meta, ri.arrays, inputs["settings"], cancelled=rt.cancelled, progress=rt.progress)
        meta["run"] = {d["dir"]: d["running_s"] for d in (run.meta or {}).get("directions") or []}
        meta["run"] = [{"dir": k, "running_s": v} for k, v in sorted(meta["run"].items())]
        return Output(meta=meta)


ROUTE_HORIZONTAL = RouteHorizontal()
ROUTE_ASSEMBLE = RouteAssemble()
RAILSIM_RUN = RailsimRun()
RAILSIM_ATTRIBUTION = RailsimAttribution()
JOB_TYPES = [ROUTE_HORIZONTAL, ROUTE_ASSEMBLE, RAILSIM_RUN, RAILSIM_ATTRIBUTION]

__all__ = [
    "JOB_TYPES",
    "RAILSIM_ATTRIBUTION",
    "RAILSIM_RUN",
    "ROUTE_ASSEMBLE",
    "ROUTE_HORIZONTAL",
    "RailsimAttribution",
    "RailsimRun",
    "RouteAssemble",
    "RouteHorizontal",
]
