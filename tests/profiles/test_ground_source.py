"""The param ``ground.source`` (I2.1): which ground the profiles read, the line file's (``line_file``, the ground
Ben's designs and the old page were made on, and the default while the param is not registered) or region.ground's
(``region``, the ``ground.profile`` result at the view's year and timeline). The other source fills a sample the
chosen one lacks, and the output says so.

At ``line_file`` every profiles input stays as it was, byte for byte (no line file has a gap, so the region ground
is not even read); at ``region`` the station facts, the whole solve and the neighbour's own solve take the
``ground.profile`` result, and the router answers with it once the hub has it warm (``X-CR-Ground``).
"""

from __future__ import annotations

import json
import math
import threading
from typing import Any

import numpy as np
import pytest

from region.core.errors import Invalid
from region.core.protocols import Output
from region.core.view import View
from region.ext.profiles import inputs as I
from region.ext.profiles.inputs import StoreReads, section_input, station_input
from region.ext.profiles.jobs import NEIGHBOUR, SOLVE_STRUCTURE, STATION_FACTS
from region.ext.profiles.solve_input import section_solve_input
from region.ext.rules.params import resolve
from region.jobs.contract import check_contract
from region.jobs.hosts import NoEngine, RunContext
from region.jobs.registry import Registry
from tests.importers.helpers import DOCLESS, MAIN, METRO, all_records, fresh_copy, read_only, section_of

TRY = View(layer="try")


def _gp():
    from region.ext.terrain.jobs import GROUND_PROFILE

    return GROUND_PROFILE


def _set_source(store: Any, value: str, view: View = TRY, scope: dict | None = None) -> None:
    store.put(
        {
            "kind": "param",
            "id": None,
            "data": {"path": "ground.source", "value": value, "unit": "enum", "scope": scope, "years": None},
            "geom": None,
        },
        view,
        if_match=None,
        by="ben",
    )


def _ground_output(store: Any, sid: str, view: View) -> Output:
    jt = _gp()
    return jt.run(
        jt.plan(StoreReads(store, view), sid), RunContext(NoEngine(), lambda f, m: None, threading.Event(), {})
    )


# ----------------------------------------------------------------------------------------- line_file: as was


def test_every_metro_line_file_ground_is_complete():
    """Each of the 16 Metro sections has one line-file ground covering its grid with no gap, so at ``line_file``
    the region ground is never needed to fill one (``ground_plan`` is None) and no plan reads it."""
    with read_only() as store:
        ctx = StoreReads(store, MAIN)
        for route in METRO:
            sec = section_of(store, route)
            (g,) = all_records(store, "ground_profile", parent=sec["id"])
            n = math.floor(float(sec["data"]["length_m"]) / float(sec["data"]["step_m"]) + 1e-9) + 1
            z = g["data"]["z_dm"]
            assert len(z) >= n and all(v is not None for v in z[:n]), route
            assert I.ground_source(ctx, sec["id"]) == "line_file"
            assert I.ground_plan(ctx, sec["id"]) is None, route


def test_line_file_leaves_every_profiles_input_as_it_was():
    """With the param unset, the station facts, the whole solve and the neighbour plan exactly the inputs they
    planned before the switch (the builders' own answers), with no ``ground_from`` and no need of ground.profile."""
    with read_only() as store:
        ctx = StoreReads(store, MAIN)
        for route in METRO:
            sid = section_of(store, route)["id"]
            st = STATION_FACTS.plan(ctx, sid)
            assert st == station_input(ctx, sid), route
            ss = SOLVE_STRUCTURE.plan(ctx, sid)
            assert set(ss) == {"input", "neighbours"} and ss["input"] == section_solve_input(ctx, sid), route
            nb = NEIGHBOUR.plan(ctx, sid)
            assert I.GROUND_FROM not in nb, route
            if nb["input"] is not None:
                assert nb["input"] == section_solve_input(ctx, sid), route


def test_line_file_set_in_a_scenario_plans_the_same_inputs(write_root):
    """``ground.source = line_file`` written in a scenario: the inputs are main's, byte for byte."""
    store = fresh_copy(write_root)
    try:
        store.create_layer("try", by="ben")
        _set_source(store, "line_file")
        for route in ("Line_6", "Line_10"):
            sid = section_of(store, route)["id"]
            a, b = StoreReads(store, MAIN), StoreReads(store, TRY)
            assert I.ground_source(b, sid) == "line_file"
            assert json.dumps(STATION_FACTS.plan(a, sid), sort_keys=True) == json.dumps(
                STATION_FACTS.plan(b, sid), sort_keys=True
            )
            assert SOLVE_STRUCTURE.plan(a, sid) == SOLVE_STRUCTURE.plan(b, sid)
            assert NEIGHBOUR.plan(a, sid) == NEIGHBOUR.plan(b, sid)
    finally:
        store.close()


def test_a_value_that_is_neither_is_refused(write_root):
    store = fresh_copy(write_root)
    try:
        store.create_layer("try", by="ben")
        _set_source(store, "lidar")
        sid = section_of(store, "Line_6")["id"]
        with pytest.raises(Invalid, match="ground.source"):
            STATION_FACTS.plan(StoreReads(store, TRY), sid)
    finally:
        store.close()


# ------------------------------------------------------------------------------------------- merging, pure


def test_merge_fills_the_chosen_ground_from_the_other():
    z, filled = I.merge_ground([1.0, None, 3.0, None], [9.0, 2.0, 9.0, None, 5.0])
    assert z == [1.0, 2.0, 3.0, None, 5.0] and filled == 2
    # another step: the fallback is taken onto the chosen grid
    z, filled = I.merge_ground([None, None, 3.0], [0.0, 1.0, 2.0, 3.0, 4.0], step_m=2.0, fallback_step_m=1.0)
    assert z == [0.0, 2.0, 3.0] and filled == 2


def test_laying_the_region_ground_into_the_inputs():
    """At ``region`` the SectionInput's ground is the region ground on its grid, any NaN filled from the line
    file; the solve's ``dem`` likewise, on the section's grid. At ``line_file`` only the line file's gaps take it."""
    from region.ext.profiles.solve_input import lay_dem

    si = {"ground": {"step_m": 2.0, "z_m": [10.0, 11.0, 12.0, 13.0]}, "length_m": 6.0}
    region = {"step_m": 2.0, "z": [20.0, None, 22.0, 23.0], "year": 2026, "timeline": "canon"}
    plan = {"ref": "job:ground.profile/x", "source": "region", "line_missing": []}
    out, info = I.lay_ground(si, plan, region)
    assert out["ground"] == {"step_m": 2.0, "z_m": [20.0, 11.0, 22.0, 23.0]}
    assert info["source"] == "region" and info["filled"] == 1 and info["filled_from"] == "line_file"
    plan = {"ref": "job:ground.profile/x", "source": "line_file", "line_missing": [[1, 1]]}
    out, info = I.lay_ground(si, plan, region)
    assert out["ground"]["z_m"] == [10.0, 11.0, 12.0, 13.0]  # region has none at 1: the line file's level stays
    out, info = I.lay_ground(si, {**plan, "line_missing": [[2, 3]]}, region)
    assert out["ground"]["z_m"] == [10.0, 11.0, 22.0, 23.0] and info["filled"] == 2
    ssi = {"dem": [1.0, None, 3.0], "step": 2.0}
    out, info = lay_dem(ssi, {"ref": "r", "source": "region", "line_missing": []}, region)
    assert out["dem"] == [20.0, None, 22.0] and info["filled"] == 0
    out, info = lay_dem(ssi, {"ref": "r", "source": "line_file", "line_missing": [[1, 2]]}, region)
    assert out["dem"] == [1.0, None, 3.0]


# --------------------------------------------------------------------------------------- region: the chain


@pytest.fixture
def region_store(write_root):
    store = fresh_copy(write_root)
    store.create_layer("try", by="ben")
    _set_source(store, "region")
    try:
        yield store
    finally:
        store.close()


def test_region_plans_need_ground_profile(region_store):
    """At ``region`` the station facts, the whole solve and a neighbour that solves its own design need
    ``ground.profile`` of their section, and leave ``ground_from`` in the input for ``run`` to lay it in."""
    store = region_store
    ctx = StoreReads(store, TRY)
    sid = section_of(store, "Line_6")["id"]
    ref = f"job:ground.profile/{sid}"
    st = STATION_FACTS.plan(ctx, sid)
    assert st[I.GROUND_FROM] == {"ref": ref, "source": "region", "line_missing": []}
    assert SOLVE_STRUCTURE.plan(ctx, sid)[I.GROUND_FROM]["ref"] == ref
    docless = section_of(store, DOCLESS[0])["id"]
    nb = NEIGHBOUR.plan(ctx, docless)
    assert nb["input"] is not None and nb[I.GROUND_FROM]["ref"] == f"job:ground.profile/{docless}"
    # a neighbour built from saved levels reads no ground at all
    assert I.GROUND_FROM not in NEIGHBOUR.plan(ctx, sid)


def test_region_feeds_the_station_facts_and_the_whole_solve(region_store, pool):
    """The chain at ``region`` passes the job contract (ground.profile planned and run upstream), lays the region
    ground into the engine's input and says so in the output; the station facts then read the region ground."""
    store = region_store
    sid = section_of(store, "Line_6")["id"]
    reg = Registry([_gp(), NEIGHBOUR, STATION_FACTS, SOLVE_STRUCTURE])
    for jt in (STATION_FACTS, SOLVE_STRUCTURE):
        check_contract(jt, store, sid, TRY, engine=pool, params=resolve, registry=reg)
    ground = _ground_output(store, sid, TRY)
    z = ground.arrays["ground_m"]
    ctx = StoreReads(store, TRY)
    st = STATION_FACTS.plan(ctx, sid)
    rt = RunContext(pool, lambda f, m: None, threading.Event(), {st[I.GROUND_FROM]["ref"]: ground})
    out = STATION_FACTS.run(st, rt)
    gs = out.meta["ground_source"]
    assert gs["source"] == "region" and gs["year"] == 2026 and gs["timeline"] == "canon" and gs["filled"] == 0
    laid, _ = I.lay_ground(st["section"], st[I.GROUND_FROM], I.region_ground(ground))
    assert np.allclose(laid["ground"]["z_m"], z[: len(laid["ground"]["z_m"])])
    main = STATION_FACTS.run(
        STATION_FACTS.plan(StoreReads(store, MAIN), sid), RunContext(pool, lambda f, m: None, threading.Event(), {})
    )
    assert "ground_source" not in main.meta
    dem_main = [s.get("ground_dem_m") for s in main.meta["stations"]]
    dem_region = [s.get("ground_dem_m") for s in out.meta["stations"]]
    assert dem_main != dem_region  # the surveyed ground at the stations is region.ground's now
    ss = SOLVE_STRUCTURE.plan(ctx, sid)
    from region.ext.profiles.solve_input import lay_dem

    laid, _ = lay_dem(ss["input"], ss[I.GROUND_FROM], I.region_ground(ground))
    assert np.allclose(np.array(laid["dem"], dtype=float), z[: len(laid["dem"])])


# ------------------------------------------------------------------------------------------------ the router


class _FakeJobs:
    """The face of the scheduler the router reads: ``result`` (the current key or None), arrays and meta."""

    def __init__(self, outputs: dict[tuple[str, str], Output]) -> None:
        self.outputs = outputs
        self.asked: list[tuple[str, str, str]] = []

    def result(self, type: str, scope: str, view: View) -> str | None:
        self.asked.append((type, scope, view.token()))
        return f"{type}/{scope}" if (type, scope) in self.outputs else None

    def read_array(self, key: str, name: str) -> Any:
        t, s = key.split("/")
        return self.outputs[(t, s)].arrays[name]

    def result_meta(self, key: str) -> dict[str, Any]:
        t, s = key.split("/")
        return {"meta": self.outputs[(t, s)].meta}


def _client(store: Any, jobs: Any = None):
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from fastapi.testclient import TestClient

    from region.core.errors import HubError
    from region.ext.profiles.router import router

    app = FastAPI()

    @app.exception_handler(HubError)
    def problem(request: Request, e: HubError) -> JSONResponse:
        return JSONResponse(e.to_problem(), status_code=e.status, media_type="application/problem+json")

    app.include_router(router, prefix="/x/profiles")
    app.state.store = store
    app.state.jobs = jobs
    return TestClient(app)


def test_the_router_answers_with_the_source_it_used(region_store):
    """At ``line_file`` (main) the answers are as before with ``X-CR-Ground: line_file``; at ``region`` with no
    warm result the line-file ground with ``line_file (region pending)``; once the hub has the result, the region
    ground with ``region``. The router never plans a job to get it beyond asking for the current result."""
    store = region_store
    sid = section_of(store, "Line_6")["id"]
    c = _client(store)
    r = c.get(f"/x/profiles/sections/{sid}/input", params={"layer": "main"})
    assert r.status_code == 200 and r.headers["x-cr-ground"] == "line_file"
    assert r.json() == section_input(StoreReads(store, MAIN), sid)
    pend = c.get(f"/x/profiles/sections/{sid}/input", params={"layer": "try"})
    assert pend.headers["x-cr-ground"] == "line_file (region pending)"
    assert pend.json()["ground"] == r.json()["ground"]
    ground = _ground_output(store, sid, TRY)
    jobs = _FakeJobs({("ground.profile", sid): ground})
    c = _client(store, jobs)
    z = ground.arrays["ground_m"]
    got = c.get(f"/x/profiles/sections/{sid}/input", params={"layer": "try"})
    assert got.headers["x-cr-ground"] == "region"
    assert np.allclose(got.json()["ground"]["z_m"], z[: len(got.json()["ground"]["z_m"])])
    st = c.get(f"/x/profiles/sections/{sid}/stations", params={"layer": "try"})
    assert st.headers["x-cr-ground"] == "region" and st.json()["section"]["ground"] == got.json()["ground"]
    so = c.get(f"/x/profiles/sections/{sid}/solve", params={"layer": "try"})
    assert so.headers["x-cr-ground"] == "region"
    dem = so.json()["dem"]
    assert np.allclose(np.array(dem, dtype=float), z[: len(dem)])
    assert ("ground.profile", sid, TRY.token()) in jobs.asked
    # main is untouched by the scenario's choice
    m = c.get(f"/x/profiles/sections/{sid}/stations", params={"layer": "main"})
    assert m.headers["x-cr-ground"] == "line_file" and m.json() == station_input(StoreReads(store, MAIN), sid)
