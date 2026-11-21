"""Job types for the API tests (module-level objects, as the scheduler's registry wants).

``t.api_arr`` reads the note its scope names (``note/<id>``) and returns one array ``v`` on a 2 m grid: ten values,
each the length of the note's text, so an edit to the text changes the result."""

from __future__ import annotations

from typing import Any

import numpy as np

from region.core.protocols import Output


class Arr:
    name = "t.api_arr"
    version = "1"
    scope = "note"
    host = "inline"
    priority = 1
    timeout_s = 5.0

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        _kind, _, rid = scope_id.partition("/")
        rec = ctx.read("note", rid)
        return {"n": len(rec["data"].get("text", "")) if rec is not None else 0}

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        v = np.full(10, float(inputs["n"]))
        return Output(meta={"n": inputs["n"], "grid": {"c0": 0.0, "step_m": 2.0}, "step_m": 2.0}, arrays={"v": v})


ARR = Arr()
JOB_TYPES = [ARR]


def registry() -> Any:
    from region.jobs.registry import Registry, builtin_types

    return Registry([*builtin_types(), *JOB_TYPES])
