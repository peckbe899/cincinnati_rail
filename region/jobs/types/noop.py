"""``noop``: the job type for tests and smoke checks.

Its scope is free text. A scope of the form ``<kind>/<id>`` reads that record, so the job depends on it and reruns
when it changes; any other scope reads nothing. The output's meta is the record's content hash (``None`` when the
scope reads nothing or the record is absent).

The meta does not echo the scope. A key holds only what the plan read (decision 9.19), not the scope id, so every
free-text scope makes the same key and shares one result: an echo would show the first scope's text to all of them.
"""

from __future__ import annotations

from typing import Any

from region.core.protocols import Output, PlanCtx, RunCtx


class Noop:
    name = "noop"
    version = "1"
    scope = "any"
    host = "inline"
    priority = 9
    timeout_s = 5.0

    def plan(self, ctx: PlanCtx, scope_id: str) -> dict[str, Any]:
        kind, sep, rid = scope_id.partition("/")
        found = None
        if sep and kind and rid:
            rec = ctx.read(kind, rid)
            found = rec["hash"] if rec is not None else None
        return {"hash": found}

    def run(self, inputs: dict[str, Any], rt: RunCtx) -> Output:
        return Output(meta=dict(inputs))


NOOP = Noop()
JOB_TYPES = [NOOP]
