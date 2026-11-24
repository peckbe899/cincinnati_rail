"""The terrain feature's job type: ``ground.profile@1`` (I2.1; section 6 of the architecture, "Key composition").

**ground.profile@1** (scope: a section id; host: a process). ``plan`` reads the section record (its drawn path,
length and grid step), the view's year and timeline (``ctx.axis``), the param ``ground.sample_window_m`` (1000 m
while it is not registered) and, through ``ctx.file``, every file compose reads for that year and timeline
(``profile.ground_files``: the canon 1912 base and the 2026 canon ground with the rasters their VRTs point at, the
works ledger, and each work present at that year with its layers). ``run`` samples region.ground along the path on
the section's grid (``profile.sample_path``) and returns:

- ``arrays``: ``ground_m`` (f8, metres NAVD88, NaN where no layer has a value) and ``src`` (u1, the layer code of
  the nearest cell);
- ``meta``: ``contract`` (``ground_profile/0``), ``grid`` (``c0``, ``step_m``, ``n``), ``length_m``, ``year``
  (the present is ``region.ground.layers.PRESENT``, 2026), ``year_source`` (``view`` or ``present``),
  ``timeline``, ``works`` (``present`` and ``skipped`` with the reason, from the ledger), ``layers`` (the names of
  the codes in ``src``), ``missing`` (the NaN count), ``window_m`` and ``source`` (``region.ground``).

A 1930 view and a 2026 view are two keys; a works file rewritten is a new key; the same content in a scenario is
the same key (a layer is never an axis). A run reads the ground files and writes nothing.

Whether the profiles read this result or the line file's ground is the param ``ground.source``
(``region.ext.profiles.inputs.ground_source``).
"""

from __future__ import annotations

from typing import Any

from region.core.errors import Invalid, NotFound
from region.core.protocols import Output

from . import profile as P

CONTRACT = "ground_profile/0"
WINDOW_PARAM = "ground.sample_window_m"
CODE_FILES = ("repo://region/ext/terrain/profile.py", "repo://region/ground")
"""The sampler and region.ground: a change to how the ground is composed or sampled makes new keys."""


class GroundProfile:
    """``ground.profile@1`` (see the module doc)."""

    name = "ground.profile"
    version = "1"
    scope = "section"
    host = "process"
    priority = 6
    timeout_s = 120.0
    axes = ("year", "timeline")
    code_files = CODE_FILES

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        sec = ctx.read("section", scope_id)
        if sec is None:
            raise NotFound(f"no section {scope_id}", kind="section", id=scope_id)
        d = sec.get("data") or {}
        path = d.get("path") or []
        if len(path) < 2:
            raise Invalid(f"section {d.get('key') or scope_id} has no drawn path to sample the ground along")
        view_year = ctx.axis("year")
        timeline = str(ctx.axis("timeline"))
        from region.ground.layers import PRESENT

        year = int(view_year) if view_year is not None else int(PRESENT)
        try:
            window = float(ctx.param(WINDOW_PARAM, scope_id))
        except NotFound:
            window = P.WINDOW_M
        for uri in P.ground_files(year, timeline):
            ctx.file(uri)
        return {
            "path": [[float(q[0]), float(q[1]), float(q[2])] for q in path],
            "length_m": float(d["length_m"]),
            "step_m": float(d["step_m"]),
            "year": year,
            "year_source": "view" if view_year is not None else "present",
            "timeline": timeline,
            "window_m": window,
        }

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        from region.ground.compose import works_for_year

        rt.progress(0.05, "ground")
        z, src, names = P.sample_path(
            inputs["path"],
            inputs["length_m"],
            inputs["step_m"],
            inputs["year"],
            inputs["timeline"],
            window_m=inputs["window_m"],
            cancelled=rt.cancelled,
        )
        present, skipped = works_for_year(int(inputs["year"]), inputs["timeline"])
        import numpy as np

        missing = int(np.isnan(z).sum())
        meta = {
            "contract": CONTRACT,
            "grid": {"c0": 0.0, "step_m": float(inputs["step_m"]), "n": int(len(z))},
            "step_m": float(inputs["step_m"]),
            "length_m": float(inputs["length_m"]),
            "year": int(inputs["year"]),
            "year_source": inputs["year_source"],
            "timeline": inputs["timeline"],
            "works": {"present": [w.id for w in present], "skipped": [[w, why] for w, why in skipped]},
            "layers": {str(k): v for k, v in names.items()},
            "missing": missing,
            "window_m": float(inputs["window_m"]),
            "source": "region.ground",
        }
        issues = []
        if missing:
            issues.append(
                {
                    "rule": None,
                    "sev": "warn",
                    "c0": 0.0,
                    "c1": float(inputs["length_m"]),
                    "msg": "ground_missing",
                    "data": {"samples": missing},
                }
            )
        rt.progress(1.0, "done")
        return Output(meta=meta, arrays={"ground_m": z, "src": src}, issues=issues)


GROUND_PROFILE = GroundProfile()
JOB_TYPES = [GROUND_PROFILE]

__all__ = ["CONTRACT", "GROUND_PROFILE", "GroundProfile", "JOB_TYPES", "WINDOW_PARAM"]
