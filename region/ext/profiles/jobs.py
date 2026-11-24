"""The profiles feature's job types: ``profiles.solve_section@1`` and ``profiles.golden_diff@1`` (section 6).

**profiles.solve_section@1** (scope: a section id; host: the engine). ``plan`` builds the section's SectionInput
from its records (``inputs.section_input``, without the ground profile, which ``vertical.rail@1`` does not read, so a
ground edit never reruns the solve); ``run`` calls ``vertical.rail`` and returns the arrays ``rail_m`` and
``grade_permille`` on the section's grid (``meta.grid`` and ``meta.step_m``), the vertices, curves and flags in
``meta``, and the flags as issues. The app's line sheet reads ``rail_m`` and ``meta.step_m``.

**profiles.station_facts@1** (scope: a section id; host: the engine). ``plan`` builds the section's StationInput
(``inputs.station_input``: the SectionInput with its ground, the profile's station fields, the platforms with their
side, opening year, phase and complex, the path, the streets and roads, the Deck's ground runs, the params); ``run``
calls ``station.facts`` and returns its stations in ``meta.stations`` and its flags as issues (each with its rule
id). The line sheet's worker runs the same method on the draft.

**profiles.golden_diff@1** (scope: a section id; host: the engine). ``plan`` reads the section's baseline file
(``repo://tests/baseline/profiles/<route>.json``), the class table (``golden.yaml``) and the records, and builds the
input on the baseline's 5 m grid; ``run`` solves it and classes the difference (``golden.py``): ``same``,
``rule_fix`` with its rule id, ``pending_port`` with its reason, or ``unexplained``. ``meta.label`` is the class, or
``class:reason`` (``pending_port:reframeDoc``).

**profiles.neighbour@1** and **profiles.solve_structure@1** (scope: a section id; host: the engine): the
neighbour view of a line (what the lines crossing it read) and the whole solve of a section (``section.solve@1``);
see their class docs.

Neither copies its scope into its inputs or outputs beyond what it read: the section record (whose content hash
includes its id) is read first, and a scope that names no section raises ``NotFound``.

Both declare ``code_files``: the modules their ``plan`` and ``run`` call (``inputs``, ``doc``, ``golden``) enter the
code hash with this one, so a change to how an input is built or a difference is classed makes new keys rather than
serving results the old code computed.
"""

from __future__ import annotations

from typing import Any

from region.core import fsio
from region.core.protocols import Output

from . import golden as G
from .inputs import build, gather, params_of, section_input, station_input
from .solve_input import (
    design_of,
    fill_levels,
    frame_moved,
    needs_levels,
    neighbour_view,
    section_solve_input,
    with_design,
)

DESIGN_FROM = "design_from"
"""The input member naming the ``profiles.neighbour`` result whose design a rail is drawn with (``with_design``)."""
ENGINE_METHOD = "vertical.rail"
STATION_METHOD = "station.facts"
SOLVE_METHOD = "section.solve"
NEIGHBOUR_JOB = "profiles.neighbour"
BASELINE = "repo://tests/baseline/profiles/{route}.json"
TABLE = "repo://region/ext/profiles/golden.yaml"
PVI_TOLERANCE_M = 0.001

CODE_FILES = (
    "repo://region/ext/profiles/inputs.py",
    "repo://region/ext/profiles/doc.py",
    "repo://region/ext/profiles/golden.py",
    "repo://region/ext/profiles/solve_input.py",
)
"""The modules besides this one whose code makes the outputs (``JobType.code_files``)."""


def _f8(values: list[float]) -> Any:
    import numpy as np

    return np.asarray(values, dtype="<f8")


class SolveSection:
    """``profiles.solve_section@1`` (see the module doc)."""

    name = "profiles.solve_section"
    version = "1"
    scope = "section"
    host = "engine"
    priority = 1
    timeout_s = 30.0
    code_files = CODE_FILES

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        # The rail result stays the profile as saved. Drawing a line with no saved level on its default design here
        # (as golden_diff does) made every such line's background solve wait on its whole solve at the hub's start,
        # and the open sheet's update after a saved line file went from 2.7 s to never in app/e2e/live.spec.ts; the
        # sheet takes the default design from GET /sections/{id}/design instead.
        return section_input(ctx, scope_id, ground=False)

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        rt.progress(0.1, "vertical")
        inputs, design = _drawn_on(inputs, rt)
        out = rt.engine.call(ENGINE_METHOD, inputs)
        grid = out["grid"]
        # no input_hash in meta: meta is part of output_hash, and the input hash covers fields vertical.rail@1 does
        # not read (scale, chainage_basis), so an edit of one would give a new output_hash for the same rail and
        # defeat the early cutoff of every job downstream (9.19). The job's key already names its inputs.
        meta = {
            "contract": out["contract"],
            "grid": {"c0": grid["c0"], "step_m": grid["step_m"], "n": grid["n"]},
            "step_m": grid["step_m"],
            "length_m": inputs["length_m"],
            "dv": out["dv"],
            "curves": out["curves"],
            "flags": out["flags"],
        }
        if design is not None:
            meta["design"] = {k: design[k] for k in ("source", "note", "reframed", "defaulted")}
        issues = [
            {"rule": f["rule"], "sev": f["sev"], "c0": f["c0"], "c1": f["c1"], "msg": f["kind"], "data": f["data"]}
            for f in out["flags"]
        ]
        issues.extend(pvi_issues(inputs))
        rt.progress(1.0, "done")
        return Output(
            meta=meta,
            arrays={"rail_m": _f8(out["rail_m"]), "grade_permille": _f8(out["grade_permille"])},
            issues=issues,
        )


def _drawn_on(inputs: dict[str, Any], rt: Any) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """The SectionInput less ``design_from``, drawn on that result's design (``with_design``); the design or None."""
    ref = inputs.get(DESIGN_FROM)
    si = {k: v for k, v in inputs.items() if k != DESIGN_FROM}
    if not ref:
        return si, None
    design = (rt.upstream(ref).meta or {}).get("design")
    return with_design(si, design), design


def pvi_issues(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    """Issues for PVIs the sheet saved off the line (a chainage below 0 or past ``length_m``, 40000 typed for
    4000.0, say) or out of chainage order: the canvas never shows them, so they are listed rather than refused (a
    PVI past the end may be meant)."""
    length = float(inputs.get("length_m") or 0.0)
    out: list[dict[str, Any]] = []
    last = None
    for i, p in enumerate(inputs.get("pvi") or []):
        c = float(p["c_m"])
        if c < -PVI_TOLERANCE_M or c > length + PVI_TOLERANCE_M:
            out.append(
                {
                    "rule": None,
                    "sev": "warn",
                    "c0": c,
                    "c1": c,
                    "msg": "pvi_off_line",
                    "data": {"index": i, "c_m": c, "length_m": length},
                }
            )
        if last is not None and c < last:
            out.append(
                {
                    "rule": None,
                    "sev": "warn",
                    "c0": c,
                    "c1": last,
                    "msg": "pvi_out_of_order",
                    "data": {"index": i, "c_m": c, "after_m": last},
                }
            )
        last = c if last is None else max(last, c)
    return out


class StationFacts:
    """``profiles.station_facts@1`` (see the module doc)."""

    name = "profiles.station_facts"
    version = "1"
    scope = "section"
    host = "engine"
    priority = 2
    timeout_s = 30.0
    code_files = CODE_FILES

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        return station_input(ctx, scope_id)

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        rt.progress(0.1, "stations")
        out = rt.engine.call(STATION_METHOD, inputs)
        meta = {
            "contract": out["contract"],
            "length_m": inputs["section"]["length_m"],
            "stations": out["stations"],
            "summary": out["summary"],
        }
        issues = [
            {"rule": f["rule"], "sev": f["sev"], "c0": f["c0"], "c1": f["c1"], "msg": f["kind"], "data": f["data"]}
            for f in out["flags"]
        ]
        rt.progress(1.0, "done")
        return Output(meta=meta, issues=issues)


class GoldenDiff:
    """``profiles.golden_diff@1`` (see the module doc)."""

    name = "profiles.golden_diff"
    version = "1"
    scope = "section"
    host = "engine"
    priority = 9
    timeout_s = 60.0
    code_files = CODE_FILES

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        g = gather(ctx, scope_id)
        route = str(g.data.get("key"))
        table = fsio.read_yaml(ctx.file(TABLE))
        path = ctx.file(BASELINE.format(route=route))
        if not path.is_file():
            return {"route": route, "baseline": None}
        base = fsio.read_json(path)
        si = build(g, params_of(ctx, g.section), step_m=float(base["step_m"]))
        if needs_levels(ctx, scope_id):
            si[DESIGN_FROM] = ctx.need(NEIGHBOUR_JOB, scope_id)
        align = base.get("align") or {}
        deleted = set(align.get("del") or [])
        kept = [s for s in g.stops if s["data"]["key"] not in deleted]
        stop_c = {p["id"]: float(stop["data"]["c"]) for stop, p in g.ordered_platforms()}
        return {
            "route": route,
            "baseline": {
                "step_m": base["step_m"],
                "n": base["n"],
                "rail_m": base["rail_m"],
                "saved": base.get("saved"),
            },
            "input": si,
            "diffs": G.input_diffs(si, align, [float(s["data"]["c"]) for s in kept], len(kept)),
            "causes": G.causes(g.profile, float(g.data["length_m"]), stop_c),
            "table": {
                "tol_m": table.get("tol_m", 0.001),
                "rule_fixes": table.get("rule_fixes") or [],
                "pending_ports": table.get("pending_ports") or {},
            },
        }

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        route, base = inputs["route"], inputs["baseline"]
        if base is None:
            return Output(
                meta={"route": route, "class": "no_baseline", "reason": None, "rule": None, "label": "no_baseline"}
            )
        si, _design = _drawn_on(inputs["input"], rt)
        out = rt.engine.call(ENGINE_METHOD, si)
        table = inputs["table"]
        cmp = G.compare(out["rail_m"], base["rail_m"], float(base["step_m"]), float(table["tol_m"]))
        if out["grid"]["n"] != base["n"]:
            cmp = {**cmp, "bad": max(cmp["bad"], 1)}
        cls = G.classify(route, cmp, inputs["diffs"], inputs["causes"], table)
        meta = {
            "route": route,
            **cls,
            **cmp,
            "n": base["n"],
            "grid": {"c0": 0, "step_m": base["step_m"], "n": base["n"]},
            "step_m": base["step_m"],
            "tol_m": table["tol_m"],
            "input_diffs": list(inputs["diffs"]),
            "causes": list(inputs["causes"]),
            "saved": base.get("saved"),
        }
        n = min(len(out["rail_m"]), len(base["rail_m"]))
        diff = [out["rail_m"][i] - base["rail_m"][i] for i in range(n)]
        issues = []
        if cls["class"] in ("unexplained", "pending_port"):
            issues.append(
                {
                    "rule": cls["rule"],
                    "sev": "error" if cls["class"] == "unexplained" else "info",
                    "c0": cmp["at_m"] or 0,
                    "c1": cmp["at_m"] or 0,
                    "msg": f"{route}: {cls['label']}: {cmp['bad']} samples off, worst {cmp['worst_m']} m",
                    "data": {"reason": cls["reason"]},
                }
            )
        return Output(meta=meta, arrays={"diff_m": _f8(diff)}, issues=issues)


class Neighbour:
    """``profiles.neighbour@1`` (scope: a section id; host: the engine): what the lines crossing this section read of
    it (``solve_input.neighbour_view``): its live stations with their rail levels, bend points, drawn ground, streets,
    ready flag, phase and settings, in ``meta.neighbour``. A station with no saved level takes the level solver's, and
    a profile in another frame is mapped onto the current stops: then ``plan`` also builds the section's own
    SectionSolveInput (no neighbours: the default levels do not depend on crossings, so there is no cycle), ``run``
    solves it, and ``meta.design`` is the design it drew (``solve_input.design_of``: with no saved design at all, the
    default one, "default design (not saved)", with its river bend points), which ``profiles.solve_section`` draws
    the rail with and ``GET /sections/{id}/design`` serves. The output is the view only, so a change to this line
    that leaves the view as it was (a paint, a selection, a tube form) gives the same output hash and the lines
    crossing it are not solved again (early cutoff, 9.19)."""

    name = NEIGHBOUR_JOB
    version = "1"
    scope = "section"
    host = "engine"
    priority = 3
    timeout_s = 60.0
    code_files = CODE_FILES

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        view = neighbour_view(ctx, scope_id)
        if view is not None and not frame_moved(ctx, scope_id):
            return {"view": view, "template": None, "input": None}
        return {
            "view": None,
            "template": neighbour_view(ctx, scope_id, template=True),
            "input": section_solve_input(ctx, scope_id),
        }

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        if inputs["view"] is not None:
            return Output(meta={"neighbour": inputs["view"]})
        rt.progress(0.1, "levels")
        out = rt.engine.call(SOLVE_METHOD, inputs["input"])
        levels = {s["platform_id"]: s["level"] for s in out["stations"]}
        design = design_of(out)
        rt.progress(1.0, "done")
        return Output(meta={"neighbour": fill_levels(inputs["template"], levels, design), "design": design})


def _f8n(values: list[Any]) -> Any:
    import numpy as np

    return np.asarray([float("nan") if v is None else float(v) for v in values], dtype="<f8")


SOLVED_ARRAYS = ("limit_tube", "limit_box")
"""The per-sample arrays of solved_section/0 the job stores as arrays (the rest of the output is meta)."""


class SolveStructure:
    """``profiles.solve_structure@1`` (scope: a section id; host: the engine): the whole solve of the section as the
    old Profiles page made it (``section.solve@1``: the structure solver, ground, rivers, viaducts, canon, crossings,
    context, roads, checks and issues). ``plan`` builds the SectionSolveInput from the records
    (``solve_input.section_solve_input``) and needs ``profiles.neighbour`` of every line that crosses it; ``run``
    lays the neighbours in and solves. The key holds the neighbours' output hashes, never their records: a change on
    Line 6 solves Line 3 again only when Line 3 crosses Line 6 and Line 6's view changed. It runs after
    ``profiles.solve_section`` (priority 4, its own result and event), so the rail is never held up by it.

    ``meta`` is the solved section less its two per-sample limit lines (``arrays``: ``limit_tube``, ``limit_box``,
    NaN where open) and the ground layers (``arrays``: ``ground_finished``, ``ground_surface``, ``ground_bed``); the
    issues are its flags, each with its rule id, its marker chainage and the old page's kind in ``data``."""

    name = "profiles.solve_structure"
    version = "1"
    scope = "section"
    host = "engine"
    priority = 4
    timeout_s = 60.0
    code_files = CODE_FILES

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        inp = section_solve_input(ctx, scope_id)
        refs: dict[str, str] = {}
        for x in inp["crossings"]:
            other = x.get("other")
            if other and other != scope_id and x["wid"] not in refs:
                refs[x["wid"]] = ctx.need(NEIGHBOUR_JOB, other)
        return {"input": inp, "neighbours": refs}

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        neighbours: dict[str, Any] = {}
        for wid, ref in sorted(inputs["neighbours"].items()):
            view = (rt.upstream(ref).meta or {}).get("neighbour")
            if view is not None:
                neighbours[wid] = view
        rt.progress(0.1, "structure")
        out = rt.engine.call(SOLVE_METHOD, {**inputs["input"], "neighbours": neighbours})
        ground = out.get("ground") or {}
        arrays = {name: _f8n(out[name]) for name in SOLVED_ARRAYS}
        for layer in ("finished", "surface", "bed"):
            arrays[f"ground_{layer}"] = _f8n(ground.get(layer) or [])
        skip = {"engine_build", "input_hash", *SOLVED_ARRAYS}
        meta = {k: v for k, v in out.items() if k not in skip}
        meta["ground"] = {k: v for k, v in ground.items() if k not in ("finished", "surface", "bed")}
        issues = [
            {
                "rule": f["rule"],
                "sev": f["sev"],
                "c0": f["c0"],
                "c1": f["c1"],
                "msg": f["kind"],
                "data": {**(f.get("data") or {}), "page": f.get("page"), "c": f.get("c")},
            }
            for f in out["flags"]
        ]
        rt.progress(1.0, "done")
        return Output(meta=meta, arrays=arrays, issues=issues)


SOLVE_SECTION = SolveSection()
STATION_FACTS = StationFacts()
GOLDEN_DIFF = GoldenDiff()
NEIGHBOUR = Neighbour()
SOLVE_STRUCTURE = SolveStructure()
JOB_TYPES = [SOLVE_SECTION, STATION_FACTS, GOLDEN_DIFF, NEIGHBOUR, SOLVE_STRUCTURE]

__all__ = [
    "GOLDEN_DIFF",
    "STATION_FACTS",
    "GoldenDiff",
    "JOB_TYPES",
    "NEIGHBOUR",
    "SOLVE_STRUCTURE",
    "Neighbour",
    "SolveStructure",
    "SOLVE_SECTION",
    "SolveSection",
    "StationFacts",
    "pvi_issues",
]
