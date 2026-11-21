"""``check_contract``: the job type contract as one call (section 1, "A job type": stable key, determinism, no
input writes), for any feature's tests to run over its job types with its own records.

    from region.jobs.contract import check_contract
    check_contract(SOLVE_SECTION, store, section_id, View(), engine=Fake(...))

It checks the type's declared members (``registry.check_job_type``), plans twice and requires the same key, runs
twice on the planned inputs in this process and requires the same ``output_hash``, and requires that the store's
outbox did not move (no write happened). Upstream jobs (``need``) are planned and run in the same way first, so
their outputs reach ``run``. Raises ``AssertionError`` with the reason; returns ``{"key", "output_hash"}``.

It also plans a made-up second scope (``<scope>~contract-probe``). A key holds what the plan read, never the scope
id itself, so when the probe makes the same key its inputs must be the same too: a plan that copies the scope id
into its inputs without reading anything for it would make two scopes share one result. (A probe whose plan raises
is skipped.)
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from region.core import fsio
from region.core.protocols import EngineClient, Output, Store
from region.core.view import View

from .cache import output_hash
from .hosts import NoEngine, RunContext, as_output
from .plan import ParamResolver, Plan, Planner
from .registry import Registry, check_job_type


def _outbox_end(store: Store) -> int:
    seq = 0
    while True:
        events = store.events_since(seq, 1000)
        if not events:
            return seq
        seq = int(events[-1]["seq"])


def check_contract(
    job_type: Any,
    store: Store,
    scope_id: str,
    view: View | None = None,
    *,
    engine: EngineClient | None = None,
    registry: Registry | None = None,
    params: ParamResolver | None = None,
) -> dict[str, str]:
    """Check one job type against the contract over ``store`` (see the module doc)."""
    view = view or View()
    problems = check_job_type(job_type)
    assert not problems, f"{getattr(job_type, 'name', job_type)}: " + "; ".join(problems)
    reg = registry or Registry([job_type])
    if job_type.name not in reg:
        reg.register(job_type)
    outputs: dict[str, str] = {}
    results: dict[str, Output] = {}

    def info() -> tuple[str, dict[str, Any]]:
        if engine is None:
            raise AssertionError(f"{job_type.name} runs on the engine: pass engine=")
        hello = engine.hello()
        return str(hello["engine_build"]), dict(hello.get("contracts") or {})

    def file_hash(p: Path) -> str | None:
        return fsio.sha256_file(p) if Path(p).is_file() else None

    planner = Planner(
        store, registry=reg, file_hash=file_hash, upstream_output=outputs.get, engine_info=info, params=params
    )
    start = _outbox_end(store)

    def run_once(plan: Plan) -> Output:
        upstream = {ref: results[key] for ref, key in plan.upstream_keys.items()}
        jt = reg.get(plan.type)
        rt = RunContext(
            engine if jt.host == "engine" and engine is not None else NoEngine(),
            lambda f, m: None,
            threading.Event(),
            upstream,
        )
        return as_output(jt.run(plan.inputs, rt))

    def settle(type_name: str, scope: str, depth: int = 0) -> Plan:
        assert depth < 20, "upstream chain deeper than 20"
        plan = planner.plan(type_name, scope, view)
        for ref in plan.missing:
            utype, uscope = plan.needs[ref]
            up = settle(utype, uscope, depth + 1)
            out = run_once(up)
            assert up.key is not None
            outputs[up.key] = output_hash(out)
            results[up.key] = out
        if plan.missing:
            plan = planner.plan(type_name, scope, view)
        assert plan.key is not None, f"{type_name}/{scope}: the plan still waits for {plan.missing}"
        return plan

    first = settle(job_type.name, scope_id)
    second = planner.plan(job_type.name, scope_id, view)
    assert first.key == second.key, f"{job_type.name}/{scope_id}: two plans of the same content gave two keys"
    _check_scope_probe(planner, job_type.name, scope_id, view, first)
    h1 = output_hash(run_once(first))
    h2 = output_hash(run_once(second))
    assert h1 == h2, f"{job_type.name}/{scope_id}: two runs on the same inputs gave two outputs"
    assert _outbox_end(store) == start, f"{job_type.name}/{scope_id}: the store's outbox moved (a job wrote)"
    return {"key": first.key, "output_hash": h1}


def _check_scope_probe(planner: Planner, type_name: str, scope_id: str, view: View, first: Plan) -> None:
    probe = f"{scope_id}~contract-probe"
    try:
        other = planner.plan(type_name, probe, view)
    except Exception:  # the made-up scope cannot be planned: nothing to compare
        return
    if other.key != first.key:
        return
    try:
        same = fsio.canonical_json(other.inputs) == fsio.canonical_json(first.inputs)
    except (TypeError, ValueError):  # inputs that are not plain JSON (arrays): not compared
        return
    assert same, (
        f"{type_name}: scopes {scope_id!r} and {probe!r} make the same key but different inputs; the key holds only "
        "what plan read, so the inputs must not carry the scope id beyond what was read for it"
    )


__all__ = ["check_contract"]
