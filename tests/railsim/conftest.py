"""Fixtures for the railsim feature's tests: a pool of real engine sidecars (skipped where there is no Node), and
``Chain``, which plans and runs a job with its upstreams in this process, as ``check_contract`` does, keeping every
output, so a test can read any job of the chain."""

from __future__ import annotations

import json
import shutil
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from region.core import fsio, paths
from region.core.protocols import Output
from region.core.view import View

REPO = paths.repo_root()
MAIN_VIEW = View()
RUNTIMES = REPO / "tests" / "baseline" / "runtimes.json"
BASELINE_ALIGN = REPO / "data" / "profile" / "alignments"
LINES = REPO / "data" / "profile" / "lines"


@pytest.fixture(scope="module")
def pool() -> Iterator[object]:
    if shutil.which("node") is None:
        pytest.skip("Node is not installed on this machine")
    from region.enginehost import Pool

    with Pool(size=2, timeout_s=60) as p:
        p.start()
        yield p


def registry() -> Any:
    """The profiles and railsim job types only (another feature's half-built jobs never enter these tests)."""
    from region.ext.profiles.jobs import JOB_TYPES as PROFILES
    from region.ext.railsim.jobs import JOB_TYPES as RAILSIM
    from region.jobs.registry import Registry

    return Registry([*PROFILES, *RAILSIM])


def registry_with_ground() -> Any:
    """``registry`` and the terrain feature's ``ground.profile`` (for ``ground.source = region``)."""
    from region.ext.profiles.jobs import JOB_TYPES as PROFILES
    from region.ext.railsim.jobs import JOB_TYPES as RAILSIM
    from region.ext.terrain.jobs import JOB_TYPES as TERRAIN
    from region.jobs.registry import Registry

    return Registry([*PROFILES, *RAILSIM, *TERRAIN])


class Chain:
    """Plan and run ``(type, scope, view)`` and every upstream it needs, in this process (process and thread jobs
    run here too: they are pure). ``results`` holds each output by key; ``runs`` counts the runs by type."""

    def __init__(self, store: Any, engine: Any, *, file_hash: Any = None, reg: Any = None) -> None:
        from region.jobs.cache import output_hash
        from region.jobs.plan import Planner

        self.store = store
        self.engine = engine
        self.reg = reg if reg is not None else registry()
        self.outputs: dict[str, str] = {}
        self.results: dict[str, Output] = {}
        self.runs: dict[str, int] = {}
        self._output_hash = output_hash
        hello = engine.hello() if engine is not None else {"engine_build": "none", "contracts": {}}

        def fh(p: Path) -> str | None:
            return fsio.sha256_file(p) if Path(p).is_file() else None

        self.planner = Planner(
            store,
            registry=self.reg,
            file_hash=file_hash or fh,
            upstream_output=self.outputs.get,
            engine_info=lambda: (str(hello["engine_build"]), dict(hello.get("contracts") or {})),
        )

    def _run(self, plan: Any) -> Output:
        from region.jobs.hosts import NoEngine, RunContext, as_output

        jt = self.reg.get(plan.type)
        upstream = {ref: self.results[key] for ref, key in plan.upstream_keys.items()}
        eng = self.engine if jt.host == "engine" else NoEngine()
        self.runs[plan.type] = self.runs.get(plan.type, 0) + 1
        return as_output(jt.run(plan.inputs, RunContext(eng, lambda f, m: None, threading.Event(), upstream)))

    def plan(self, type_name: str, scope: str, view: View) -> Any:
        return self.planner.plan(type_name, scope, view)

    def settle(self, type_name: str, scope: str, view: View, depth: int = 0) -> Any:
        assert depth < 30
        plan = self.planner.plan(type_name, scope, view)
        for ref in plan.missing:
            utype, uscope = plan.needs[ref]
            self.compute(utype, uscope, view, depth + 1)
        if plan.missing:
            plan = self.planner.plan(type_name, scope, view)
        assert plan.key is not None, f"{type_name}/{scope} still waits for {plan.missing}"
        return plan

    def compute(self, type_name: str, scope: str, view: View, depth: int = 0) -> tuple[Any, Output]:
        """``(plan, output)``; a key computed before is not run again (the cache)."""
        plan = self.settle(type_name, scope, view, depth)
        if plan.key not in self.results:
            out = self._run(plan)
            self.results[plan.key] = out
            self.outputs[plan.key] = self._output_hash(out)
        return plan, self.results[plan.key]


def runtimes(stem: str) -> dict[str, Any]:
    return json.loads(RUNTIMES.read_text(encoding="utf-8"))[stem]


def route_of(store: Any, route_key: str, view: View = MAIN_VIEW) -> dict[str, Any]:
    from tests.importers.helpers import section_of

    sec = section_of(store, route_key)
    return store.get("route", sec["data"]["route"], view)


def baseline_profile(store: Any, route_key: str, view: View = MAIN_VIEW) -> dict[str, Any]:
    """The profile record's data for the baseline's own design (``data/profile/alignments/<route>.json``, the doc
    ``tests/baseline/runtimes.json`` was captured on), keyed to the hub's platforms; the access and the other
    record-only members of the current profile are kept."""
    from region.ext.network import lines as LN
    from region.ext.profiles.doc import profile_of
    from tests.importers.helpers import all_records, section_of

    sec = section_of(store, route_key)
    line = json.loads((LINES / f"{route_key}.json").read_text(encoding="utf-8"))
    doc = json.loads((BASELINE_ALIGN / f"{route_key}.json").read_text(encoding="utf-8"))
    keys = LN.station_keys(line)
    platforms = {p["data"]["key"]: p["id"] for p in all_records(store, "platform", view, parent=sec["id"])}
    data = profile_of(
        doc,
        section_id=sec["id"],
        keys=keys,
        names=[str(s["name"]) for s in line["stations"]],
        platforms=platforms,
        route_name=str(line["line"]),
        system_name=str(line["system"]),
    )
    cur = all_records(store, "profile", view, parent=sec["id"])[0]
    for k in ("access",):
        if k in cur["data"]:
            data[k] = cur["data"][k]
    return data


def put_profile(store: Any, route_key: str, data: dict[str, Any], view: View) -> dict[str, Any]:
    from tests.importers.helpers import all_records, section_of

    sec = section_of(store, route_key)
    cur = all_records(store, "profile", view, parent=sec["id"])[0]
    return store.put(
        {"kind": "profile", "id": cur["id"], "data": data, "geom": cur.get("geom")},
        view,
        if_match=f'"{cur["layer"]}:{cur["version"]}"',
        by="ben",
    )
