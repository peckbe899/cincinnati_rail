"""Job types: the registry and its contract, the built-in seed job types, and ``crhub jobs``."""

from __future__ import annotations

import json
from typing import Any

import pytest

from region.cli import main as cli_main
from region.core import fsio
from region.core.errors import Invalid, NotFound
from region.core.view import View
from region.jobs import registry as registry_mod
from region.jobs.contract import check_contract
from region.jobs.registry import Registry, builtin_types, check_job_type, default_registry
from region.jobs.types.noop import NOOP
from region.jobs.types.seed import SeedExport, SeedImport
from tests.jobs import jobtypes as jt
from tests.jobs.fakes import FakeEngine, FakeStore
from tests.jobs.jobtypes import make_registry

MAIN = View()


def test_job_type_contract():
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    store.set("thing", "P", {"v": 2})
    store.set("note", "N", {"text": "n"})
    reg = make_registry()
    for job_type, scope in ((NOOP, "thing/A"), (NOOP, "free text"), (jt.SUM, "A"), (jt.TIMED, "A"), (jt.DOWN, "P:N")):
        out = check_contract(job_type, store, scope, registry=reg)
        assert len(out["key"]) == 64 and len(out["output_hash"]) == 64
    out = check_contract(jt.ENGINE_JOB, store, "A", registry=reg, engine=FakeEngine())
    assert out["key"]

    # every built-in type is valid and found again by module and name, as a worker process does
    for job_type in builtin_types():
        assert check_job_type(job_type) == []
        assert registry_mod.find(registry_mod.module_of(job_type), job_type.name) is job_type
    assert registry_mod.find("tests.jobs.jobtypes", "t.proc_sleep") is jt.PROC_SLEEP
    assert {"noop", "seed.import", "seed.export"} <= set(default_registry().names())

    class Bad:
        name = "Not A Name"
        version = 1
        scope = ""
        host = "gpu"
        priority = 11
        timeout_s = 0
        axes = ("layer",)
        effect = "files"

    problems = check_job_type(Bad())
    assert len(problems) == 11  # name, version, scope, host, priority, timeout, plan, run, axes, effect, apply
    with pytest.raises(Invalid):
        Registry([Bad()])
    with pytest.raises(Invalid):
        Registry([jt.SUM, jt.Sum()])  # two types named t.sum
    with pytest.raises(NotFound):
        make_registry().get("nothing.here")


class FakeSeedApi:
    """Stands in for ``region.model.seed`` (WP1)."""

    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def import_seed(self, store: Any, seed: Any, *, layer: str | None = None) -> dict[str, Any]:
        self.calls.append(("import", seed, layer))
        return {"imported": len(self.calls)}

    def export(self, store: Any, out: Any) -> dict[str, Any]:
        self.calls.append(("export", out))
        return {"written": 0}


def test_seed_jobs_apply_once_per_content(make_sched, hub_var):
    seed = hub_var / "seed"
    fsio.write_json(seed / "main" / "thing" / "A.json", {"id": "A", "kind": "thing", "data": {"v": 1}})
    api = FakeSeedApi()
    reg = Registry([SeedImport(seed_api=api, seed_uri="var://seed"), SeedExport(seed_api=api, seed_uri="var://seed")])
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    writes = len(store.writes)
    sched = make_sched(store, registry=reg)

    first = sched.submit("seed.import", "main", MAIN)
    assert sched.wait_job(first["job"])["state"] == "done"
    assert api.calls == [("import", seed, "main")]
    res = sched.result_meta(first["key"])
    assert res["meta"]["applied"] == {"imported": 1} and res["meta"]["files"] == 1
    assert ["file:var://seed/main/thing/A.json", fsio.sha256_file(seed / "main" / "thing" / "A.json")] in res["deps"]

    # the same seed files again: a hit, nothing applied
    assert sched.submit("seed.import", "main", MAIN)["state"] == "hit"
    assert len(api.calls) == 1
    # a pulled seed change: applied again
    fsio.write_json(seed / "main" / "thing" / "A.json", {"id": "A", "kind": "thing", "data": {"v": 2}})
    again = sched.submit("seed.import", "main", MAIN)
    assert again["state"] == "queued" and sched.wait_job(again["job"])["state"] == "done"
    assert api.calls[-1] == ("import", seed, "main")

    out = sched.submit("seed.export", "all", MAIN)
    assert sched.wait_job(out["job"])["state"] == "done"
    assert api.calls[-1] == ("export", seed)
    assert sched.submit("seed.export", "all", MAIN)["state"] == "hit"
    # the store was written only by the test and by the seed api it was handed (here a fake that writes nothing)
    assert len(store.writes) == writes
    with pytest.raises(Invalid):
        sched.submit("seed.import", "nowhere:", MAIN)


def test_cli_jobs(make_sched, hub_var, capsys):
    cache = hub_var / "cache" / "cache.db"
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store, path=cache)
    done = sched.wait_job(sched.submit("t.sum", "A", MAIN)["job"])
    sched.stop()

    def run(*argv: str) -> tuple[int, str]:
        capsys.readouterr()
        code = cli_main(["jobs", "--cache", str(cache), *argv])
        return code, capsys.readouterr().out

    code, out = run("list", "--all", "--json")
    assert code == 0 and [j["id"] for j in json.loads(out)] == [done["id"]]
    code, out = run("list")
    assert code == 0 and "no active jobs" in out
    code, out = run("show", done["id"], "--json")
    assert code == 0 and json.loads(out)["state"] == "done" and json.loads(out)["log"]
    code, out = run("stats", "--json")
    assert code == 0 and json.loads(out)["result"] == 1 and json.loads(out)["bytes"] == 8
    code, out = run("types", "--json")
    assert code == 0 and {"noop", "seed.import", "seed.export"} <= {t["name"] for t in json.loads(out)}
    code, out = run("prune", "--max-mb", "0")
    assert code == 0 and "evicted 1 results" in out
    code, out = run("wipe")
    assert code == 2 and cache.exists()
    code, out = run("wipe", "--yes")
    assert code == 0 and not cache.exists()
    assert cli_main(["jobs"]) == 2


def test_protocols_are_met(make_sched):
    import threading

    from region.core import protocols
    from region.jobs.hosts import NoEngine, RunContext
    from region.jobs.plan import PlanContext

    store = FakeStore()
    sched = make_sched(store)
    assert isinstance(sched, protocols.Scheduler)
    assert isinstance(store, protocols.Store)
    assert isinstance(FakeEngine(), protocols.EngineClient) and isinstance(NoEngine(), protocols.EngineClient)
    assert isinstance(PlanContext(sched.planner, jt.SUM, "A", MAIN, ()), protocols.PlanCtx)
    assert isinstance(RunContext(NoEngine(), lambda f, m: None, threading.Event(), {}), protocols.RunCtx)
    for job_type in [*builtin_types(), *jt.JOB_TYPES]:
        assert isinstance(job_type, protocols.JobType)
