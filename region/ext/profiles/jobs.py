"""The profiles feature's job types: ``profiles.solve_section@1`` and ``profiles.golden_diff@1`` (section 6).

**profiles.solve_section@1** (scope: a section id; host: the engine). ``plan`` builds the section's SectionInput
from its records (``inputs.section_input``, without the ground profile, which ``vertical.rail@1`` does not read, so a
ground edit never reruns the solve); ``run`` calls ``vertical.rail`` and returns the arrays ``rail_m`` and
``grade_permille`` on the section's grid (``meta.grid`` and ``meta.step_m``), the vertices, curves and flags in
``meta``, and the flags as issues. The app's line sheet reads ``rail_m`` and ``meta.step_m``.

**profiles.golden_diff@1** (scope: a section id; host: the engine). ``plan`` reads the section's baseline file
(``repo://tests/baseline/profiles/<route>.json``), the class table (``golden.yaml``) and the records, and builds the
input on the baseline's 5 m grid; ``run`` solves it and classes the difference (``golden.py``): ``same``,
``rule_fix`` with its rule id, ``pending_port`` with its reason, or ``unexplained``. ``meta.label`` is the class, or
``class:reason`` (``pending_port:reframeDoc``).

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
from .inputs import build, gather, params_of, section_input

ENGINE_METHOD = "vertical.rail"
BASELINE = "repo://tests/baseline/profiles/{route}.json"
TABLE = "repo://region/ext/profiles/golden.yaml"
CODE_FILES = (
    "repo://region/ext/profiles/inputs.py",
    "repo://region/ext/profiles/doc.py",
    "repo://region/ext/profiles/golden.py",
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
        return section_input(ctx, scope_id, ground=False)

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        rt.progress(0.1, "vertical")
        out = rt.engine.call(ENGINE_METHOD, inputs)
        grid = out["grid"]
        meta = {
            "contract": out["contract"],
            "input_hash": out["input_hash"],
            "grid": {"c0": grid["c0"], "step_m": grid["step_m"], "n": grid["n"]},
            "step_m": grid["step_m"],
            "length_m": inputs["length_m"],
            "dv": out["dv"],
            "curves": out["curves"],
            "flags": out["flags"],
        }
        issues = [
            {"rule": f["rule"], "sev": f["sev"], "c0": f["c0"], "c1": f["c1"], "msg": f["kind"], "data": f["data"]}
            for f in out["flags"]
        ]
        rt.progress(1.0, "done")
        return Output(
            meta=meta,
            arrays={"rail_m": _f8(out["rail_m"]), "grade_permille": _f8(out["grade_permille"])},
            issues=issues,
        )


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
        out = rt.engine.call(ENGINE_METHOD, inputs["input"])
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


SOLVE_SECTION = SolveSection()
GOLDEN_DIFF = GoldenDiff()
JOB_TYPES = [SOLVE_SECTION, GOLDEN_DIFF]

__all__ = ["GOLDEN_DIFF", "GoldenDiff", "JOB_TYPES", "SOLVE_SECTION", "SolveSection"]
