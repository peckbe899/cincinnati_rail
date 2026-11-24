"""The draft run and the warm RouteInput (plan sections 1.5 and 1.7): ``POST /x/railsim/sections/{id}/draft`` and
``GET /x/railsim/routes/{id}/input``.

A draft is the sheet's unsaved edit run on the saved route: the hub solves its SectionInput with ``vertical.rail@1``,
lays the rail, the draft's (or the saved) structure types and its stations on the warm ``route.assemble`` and
``route.horizontal`` results, and runs railsim in a worker of its own. The draft of the saved state is the saved run
exactly; two equal drafts are one run; a newer draft from the same client and section drops the one still waiting;
nothing is written; before the route is assembled the answer is 409 ``pending``."""

from __future__ import annotations

import copy
import threading
import time
from collections.abc import Iterator
from typing import Any

import pytest

fastapi = pytest.importorskip("fastapi")

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from region.core.errors import Conflict, HubError  # noqa: E402
from region.core.view import View  # noqa: E402
from tests.importers.helpers import MAIN, fresh_copy, section_of  # noqa: E402
from tests.railsim.conftest import route_of  # noqa: E402

BASE = "/api/v1/x"
H = {"X-CR-Client": "tab-1", "Content-Type": "application/json"}


def _app(store: Any, jobs: Any, engine: Any) -> tuple[FastAPI, Any]:
    """The railsim and profiles routers mounted as the server mounts a feature's, over a store and a scheduler."""
    from region.ext.profiles.router import router as profiles
    from region.ext.railsim.router import make_router

    app = FastAPI()

    @app.exception_handler(HubError)
    def problem(request: Request, e: HubError) -> JSONResponse:
        return JSONResponse(e.to_problem(), status_code=e.status, media_type="application/problem+json")

    rs = make_router(None)
    app.include_router(profiles, prefix=f"{BASE}/profiles")
    app.include_router(rs, prefix=f"{BASE}/railsim")
    app.state.store = store
    app.state.jobs = jobs
    app.state.engine = engine
    return app, rs


def _compute(sched: Any, type_name: str, scope: str, view: View = MAIN, timeout: float = 400.0) -> str:
    """Submit and wait for the job (its chain from cold is some 2 minutes here: eleven crossing lines)."""
    sub = sched.submit(type_name, scope, view, priority=0)
    if sub["job"]:
        job = sched.wait_job(sub["job"], timeout=timeout)
        assert job["state"] == "done", job
    key = sched.result(type_name, scope, view)
    assert key, f"{type_name}/{scope} has no result"
    return key


@pytest.fixture(scope="module")
def hub(pool, tmp_path_factory) -> Iterator[dict[str, Any]]:
    """A scheduler over a copy of the records with Line 6's saved run computed on main, and the routers over it."""
    from region.core import fsio
    from region.ext.rules.params import resolve
    from region.jobs import Scheduler

    root = tmp_path_factory.mktemp("draft")
    with fsio.allow_writes(root):
        store = fresh_copy(root)
        sched = Scheduler(store, root / "cache" / "cache.db", pool, params=resolve, poll_s=0.05).start()
        try:
            sid = section_of(store, "Line_6")["id"]
            rid = route_of(store, "Line_6")["id"]
            app, rs = _app(store, sched, pool)
            with TestClient(app) as c:
                si = c.get(f"{BASE}/profiles/sections/{sid}/input").json()
                pending = c.post(f"{BASE}/railsim/sections/{sid}/draft", json={"section_input": si}, headers=H)
                run_key = _compute(sched, "railsim.run", rid)
                yield {
                    "client": c,
                    "store": store,
                    "sched": sched,
                    "sid": sid,
                    "rid": rid,
                    "run_key": run_key,
                    "pending": pending,
                    "runner": rs.draft_runner,
                }
        finally:
            sched.stop()
            store.close()


def _saved_input(hub: dict[str, Any]) -> dict[str, Any]:
    r = hub["client"].get(f"{BASE}/profiles/sections/{hub['sid']}/input")
    assert r.status_code == 200, r.text
    return r.json()


def _post(hub: dict[str, Any], body: dict[str, Any], headers: dict[str, str] = H) -> Any:
    return hub["client"].post(f"{BASE}/railsim/sections/{hub['sid']}/draft", json=body, headers=headers)


def test_before_the_route_is_assembled_the_draft_is_pending(hub):
    r = hub["pending"]
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "pending"


def test_the_warm_route_input(hub):
    r = hub["client"].get(f"{BASE}/railsim/routes/{hub['rid']}/input")
    assert r.status_code == 200, r.text
    m = r.json()
    assert m["contract"] == "route_input/0" and m["route_key"] == "Line_6"
    n = m["run_grid"]["n"]
    assert set(m["arrays"]) == {"s_m", "c_m", "rail_z_m", "curvature_per_m", "tunnel", "type"}
    assert all(len(v) == n for v in m["arrays"].values())
    assert len(m["stops"]) == 31


def test_the_draft_of_the_saved_state_is_the_saved_run(hub):
    """The sheet's SectionInput as saved, no draft types: the saved run's numbers exactly."""
    saved = hub["sched"].result_meta(hub["run_key"])["meta"]
    r = _post(hub, {"section_input": _saved_input(hub), "edit_rev": 7})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["draft"] is True and d["types"] == "saved" and d["edit_rev"] == 7
    assert d["contract"] == "run_result/0"
    assert d["base"]["run"] == hub["run_key"] and d["base"]["assemble"]
    for a, b in zip(d["directions"], saved["directions"], strict=True):
        assert a["running_s"] == b["running_s"] and a["trip_s"] == b["trip_s"]
        assert [s["arrive_s"] for s in a["stations"]] == [s["arrive_s"] for s in b["stations"]]
    n = d["grid"]["n"]
    assert {"limit_ms", "v_fwd_ms", "v_rev_ms", "t_fwd_s", "t_rev_s"} <= set(d["arrays"])
    assert all(len(v) == n for v in d["arrays"].values())


def test_two_equal_drafts_are_one_run(hub):
    si = _saved_input(hub)
    a = _post(hub, {"section_input": si}).json()
    runs = hub["runner"].runs
    b = _post(hub, {"section_input": si}).json()
    assert b["cached"] is True and b["key"] == a["key"]
    assert hub["runner"].runs == runs


def test_a_pvi_draft_changes_the_run_and_writes_nothing(hub):
    store = hub["store"]
    seq = store.last_seq()
    si = _saved_input(hub)
    base = _post(hub, {"section_input": si}).json()
    up = copy.deepcopy(si)
    k = len(up["pvi"]) // 2
    up["pvi"][k]["z_m"] += 6.0
    d = _post(hub, {"section_input": up}).json()
    assert d["key"] != base["key"] and d["cached"] is False
    assert [x["running_s"] for x in d["directions"]] != [x["running_s"] for x in base["directions"]]
    assert store.last_seq() == seq


def test_the_drafts_own_types_are_run(hub):
    """With the draft's ``type_runs`` (here all elevated: no tunnel drag) the run is faster and says ``draft``."""
    si = _saved_input(hub)
    base = _post(hub, {"section_input": si}).json()
    d = _post(hub, {"section_input": si, "type_runs": [["elevated", 0.0, si["length_m"]]]}).json()
    assert d["types"] == "draft"
    assert all(a["running_s"] < b["running_s"] for a, b in zip(d["directions"], base["directions"], strict=True))


def test_a_station_left_out_of_the_draft_leaves_the_run(hub):
    si = _saved_input(hub)
    gone = si["stations"][5]
    si["stations"] = [s for s in si["stations"] if s["platform_id"] != gone["platform_id"]]
    d = _post(hub, {"section_input": si}).json()
    names = [s["name"] for s in d["directions"][0]["stations"]]
    assert len(names) == 30 and gone["platform_id"] not in [s["platform_id"] for s in d["directions"][0]["stations"]]


def test_a_draft_for_another_section_or_grid_is_invalid(hub):
    si = _saved_input(hub)
    other = dict(si, section_id="01NOTTHISSECTION0000000000")
    assert _post(hub, {"section_input": other}).status_code == 422
    longer = dict(si, length_m=si["length_m"] + 100.0)
    assert _post(hub, {"section_input": longer}).status_code == 422
    assert _post(hub, {"section_input": dict(si, step_m=5.0)}).status_code == 422


# ------------------------------------------------------------------------------------------------ the runner alone


def test_a_newer_draft_supersedes_the_one_waiting():
    """At most one running and one waiting per client and section: a third request drops the second (409
    ``superseded``); another client's draft is not dropped."""
    from region.ext.railsim.draft import DraftRunner

    gate = threading.Event()
    started = threading.Event()

    def execute(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        started.set()
        gate.wait(10)
        return {"n": payload["n"]}, {}

    runner = DraftRunner(execute=execute)
    out: dict[str, Any] = {}

    def go(name: str, client: str, n: int) -> None:
        try:
            out[name] = runner.run(client, "sec", f"k{n}", {"n": n})[0]
        except Conflict as e:
            out[name] = e.code

    a = threading.Thread(target=go, args=("a", "tab", 1))
    a.start()
    assert started.wait(5)
    b = threading.Thread(target=go, args=("b", "tab", 2))
    b.start()
    other = threading.Thread(target=go, args=("other", "tab-2", 4))
    other.start()
    time.sleep(0.2)
    c = threading.Thread(target=go, args=("c", "tab", 3))
    c.start()
    time.sleep(0.2)
    gate.set()
    for t in (a, b, c, other):
        t.join(10)
    assert out == {"a": {"n": 1}, "b": "superseded", "c": {"n": 3}, "other": {"n": 4}}
    runner.close()


def test_the_runner_keeps_32_answers():
    from region.ext.railsim.draft import DraftRunner

    calls = []
    runner = DraftRunner(execute=lambda p: (calls.append(p["n"]) or {"n": p["n"]}, {}))
    for n in range(40):
        runner.run("tab", "sec", f"k{n}", {"n": n})
    assert runner.run("tab", "sec", "k39", {"n": 39})[2] is True  # cached
    assert runner.run("tab", "sec", "k0", {"n": 0})[2] is False  # evicted
    assert len(calls) == 41
    runner.close()


def test_the_draft_worker_is_a_process_of_its_own(pool):
    """The default runner runs in its own spawn worker (never the scheduler's slots), warm after the first draft."""
    import os

    from region.ext.railsim.draft import DraftRunner

    runner = DraftRunner()
    try:
        meta, _arrays, cached, _ms = runner.run("tab", "sec", "pid", {"probe": True})
        assert cached is False and meta["pid"] != os.getpid()
        again = runner.run("tab", "sec", "pid2", {"probe": True})[0]
        assert again["pid"] == meta["pid"]
    finally:
        runner.close()
