"""section.solve@1 from records (claude/hub_maps/engine_port_plan.md, section 7.5): the input builder, the canon
transcription, the neighbour and structure jobs, their contract and their early cutoff.

The oracle is the old page's own answers (engine/test/golden/old_page): built from the records alone, the solve
draws the page's structure type at every 2 m sample on the 14 lines with a saved profile. Every difference the tests
allow is listed below with its reason."""

from __future__ import annotations

import gzip
import json
import threading
from functools import cache
from typing import Any

import pytest

from region.contract.gen import SectionSolveInput, SolvedSection
from region.core import fsio, paths
from region.core.view import View
from region.ext.profiles.inputs import StoreReads
from region.ext.profiles.jobs import NEIGHBOUR, SOLVE_STRUCTURE
from region.ext.profiles.solve_input import neighbour_view, section_solve_input
from region.ext.rules.params import resolve
from region.jobs.cache import output_hash
from region.jobs.contract import check_contract
from region.jobs.hosts import RunContext
from region.jobs.plan import Planner
from region.jobs.registry import Registry
from tests.importers.helpers import DOCLESS, MAIN, METRO, fresh_copy, profile_of, read_only, section_of

REPO = paths.repo_root()
GOLDEN = REPO / "engine" / "test" / "golden" / "old_page"
TYPE_EXCEPTIONS: dict[str, str] = {}
"""Lines whose drawn type differs from the old page's somewhere, each with its reason. Line 10 was one (its Ohio
approach over 158 m): its empty profile solved with no bend point, where the old page, with no doc for it, drew the
level solver's river bend points; a profile with no saved level and no bend point now solves on that default
design."""


def _golden(route: str) -> dict[str, Any]:
    return json.loads(gzip.decompress((GOLDEN / f"{route}.json.gz").read_bytes()))


def _unrle(runs: list[list[Any]]) -> list[Any]:
    out: list[Any] = []
    for t, n in runs:
        out.extend([t] * n)
    return out


@cache
def _inputs() -> dict[str, dict[str, Any]]:
    """Every Metro line's SectionSolveInput with its neighbours from the records (each view as the job gives it)."""
    with read_only() as store:
        ctx = StoreReads(store, MAIN)
        ids = {r: section_of(store, r)["id"] for r in METRO}
        views = {sid: neighbour_view(ctx, sid) for sid in ids.values()}
        out = {}
        for r, sid in ids.items():
            inp = section_solve_input(ctx, sid)
            nb = {}
            for x in inp["crossings"]:
                v = views.get(x.get("other"))
                if v is not None and x["wid"] not in nb:
                    nb[x["wid"]] = v
            out[r] = {**inp, "neighbours": nb}
        return out


@pytest.fixture(scope="module")
def solved(pool) -> dict[str, dict[str, Any]]:
    return {r: pool.call("section.solve", inp) for r, inp in _inputs().items()}


def test_canon_transcription_is_the_pages():
    """canon_metro.json holds the page's CANON (293-323) for every Metro line, entry for entry, with its sources."""
    doc = fsio.read_json(REPO / "region" / "ext" / "profiles" / "canon_metro.json")
    for route in METRO:
        want = _golden(route)["canon_record"]
        assert doc["lines"].get(route) == want, route


def test_inputs_are_the_contract():
    """Each input validates against section_solve_input/0 (the generated pydantic model)."""
    for route, inp in _inputs().items():
        SectionSolveInput.model_validate(inp)
        assert inp["contract"] == "section_solve_input/0"
        assert len(inp["dem"]) == int(inp["length"] // inp["step"] + 1e-9) + 1, route
        if route in DOCLESS:
            assert inp["doc"] is not None  # the empty profile record: no levels, so the level solver's


def test_settings_literals_and_structure_from_params():
    """The settings and literals are the registry's (the pool in metres), the structure record resolved for the
    route (line_phase, piece_phase), the canon and rivers with their params."""
    inp = _inputs()["Line_6"]
    g = _golden("Line_6")
    s = inp["settings"]
    for k, v in g["settings"].items():
        if k == "poolFt":
            assert s["pool"] == pytest.approx(v * 0.3048, abs=1e-6)
        else:
            assert s[k] == pytest.approx(v), k
    assert inp["era"] == {"shield": g["era"]["shield"], "sgMax": g["era"]["sgMax"]}
    assert inp["structure"]["line_phase"] is None or inp["structure"]["line_phase"] in ("1", "2", "3", "later")
    assert [(r["name"], r["navigable"]) for r in inp["rivers"]] == [("Ohio River", True), ("Licking River", False)]
    assert inp["chronologyTable"]["sys"] == "metro"


def test_solve_matches_the_old_page(solved):
    """From the records alone the drawn type matches the old page at every 2 m sample (TYPE_EXCEPTIONS apart), and
    every finding cites a registry rule."""
    from region.rules import load as load_registry

    rules = set(load_registry().rules)
    for route, out in solved.items():
        SolvedSection.model_validate(out)
        g = _golden(route)
        want = _unrle(g["grid"]["type"])
        runs = out["type_runs"]
        k = 0
        diff = 0
        for i, t in enumerate(want):
            c = min(i * g["step"], g["L"])
            while k + 1 < len(runs) and c >= runs[k][2]:
                k += 1
            diff += runs[k][0] != t
        if route in TYPE_EXCEPTIONS:
            assert diff > 0, f"{route} now matches: take it off TYPE_EXCEPTIONS"
        else:
            assert diff == 0, f"{route}: {diff} samples differ"
        assert {f["rule"] for f in out["flags"]} <= rules


def test_crossings_with_lines_in_the_hub(solved):
    """Every crossing with a Metro line the hub holds and whose levels are saved is checked, at the page's
    chainage, with the page's verdict (the RER crossings are not in the hub's sections yet: slice 2)."""
    for route, out in solved.items():
        page = {round(x["c"], 1): x for x in _golden(route)["crossings"]}
        for x in out["crossings"]:
            p = page.get(round(x["c"], 1))
            assert p is not None, (route, x["c"])
            if x.get("source") == "profile" and p.get("zo") is not None:
                assert x["ok"] == bool(p["ok"]), (route, x["c"], x["with"])


def _run(job: Any, inputs: Any, engine: Any, upstream: dict[str, Any] | None = None) -> Any:
    return job.run(inputs, RunContext(engine, lambda f, m: None, threading.Event(), upstream or {}))


def test_job_contracts(pool):
    """Both job types keep the job contract (stable key, same output twice, no writes), on a line with saved levels
    and on a docless one (whose neighbour view takes the level solver's levels)."""
    with read_only() as store:
        for route in ("Line_6", "Line_10"):
            sid = section_of(store, route)["id"]
            check_contract(NEIGHBOUR, store, sid, MAIN, engine=pool, params=resolve)
        reg = Registry([NEIGHBOUR, SOLVE_STRUCTURE])
        sid = section_of(store, "Line_2b")["id"]
        check_contract(SOLVE_STRUCTURE, store, sid, MAIN, engine=pool, params=resolve, registry=reg)


def _keys(store: Any, view: View, engine: Any, routes: list[str]) -> dict[str, str]:
    """The solve_structure keys of ``routes`` with each neighbour run once for its output hash."""
    reg = Registry([NEIGHBOUR, SOLVE_STRUCTURE])
    hashes: dict[str, str] = {}

    def hello() -> tuple[str, dict[str, Any]]:
        h = engine.hello()
        return str(h["engine_build"]), dict(h.get("contracts") or {})

    planner = Planner(
        store, registry=reg, file_hash=lambda p: fsio.sha256_file(p) if p.is_file() else None,
        upstream_output=hashes.get, engine_info=hello, params=resolve,
    )  # fmt: skip
    out = {}
    for route in routes:
        sid = section_of(store, route)["id"]
        plan = planner.plan(SOLVE_STRUCTURE.name, sid, view)
        for ref in plan.missing:
            _, scope = plan.needs[ref]
            up = planner.plan(NEIGHBOUR.name, scope, view)
            hashes[up.key] = output_hash(_run(NEIGHBOUR, up.inputs, engine))
        plan = planner.plan(SOLVE_STRUCTURE.name, sid, view)
        assert plan.key is not None
        out[route] = plan.key
    return out


def test_early_cutoff(pool, write_root):
    """A paint on Line 6 leaves its neighbour view as it was: no line crossing it is solved again. A level change on
    Line 6 re-solves the lines that cross it and no other."""
    store = fresh_copy(write_root)
    store.create_layer("try", tier="scenario", parent="main", by="ben")
    view = View(layer="try")
    sec6 = section_of(store, "Line_6")
    crossing = sorted({x["wid"] for x in sec6["data"]["crossings"] if x.get("other")})
    away = [
        r
        for r in METRO
        if r != "Line_6" and "Line_6" not in {x.get("wid") for x in section_of(store, r)["data"]["crossings"]}
        and r not in crossing
    ]  # fmt: skip
    assert "Line_3" in crossing and away
    routes = ["Line_3", away[0]]
    before = _keys(store, view, pool, routes)

    def patch(path: str, value: Any) -> None:
        prof = profile_of(store, "Line_6", view)
        store.patch("profile", prof["id"], [{"op": "add", "path": path, "value": value}], view,
                    if_match=f'"{prof["layer"]}:{prof["version"]}"', by="ben")  # fmt: skip

    prof = profile_of(store, "Line_6", view)
    patch("/data/ovr", [*(prof["data"].get("ovr") or []), [20000.0, 20100.0, "cutcover"]])
    assert _keys(store, view, pool, routes) == before
    pid, z = next((k, v) for k, v in (profile_of(store, "Line_6", view)["data"]["st"] or {}).items() if v)
    patch(f"/data/st/{pid}", float(z) - 1.0)
    after = _keys(store, view, pool, routes)
    assert after["Line_3"] != before["Line_3"]
    assert after[away[0]] == before[away[0]]
    store.close()


def test_solve_input_endpoint():
    """GET /x/profiles/sections/{id}/solve answers the input with its neighbours (from the records here: a hub with
    no scheduler)."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from region.ext.profiles.router import router

    with read_only() as store:
        app = FastAPI()
        app.state.store = store
        app.include_router(router, prefix="/x/profiles")
        sid = section_of(store, "Line_6")["id"]
        r = TestClient(app).get(f"/x/profiles/sections/{sid}/solve")
        assert r.status_code == 200
        body = r.json()
        SectionSolveInput.model_validate(body)
        assert "Line_3" in body["neighbours"] and body["neighbours"]["Line_3"]["source"] == "profile"
        assert all(w not in body["neighbours"] for w in DOCLESS)  # no saved levels: the job's, once it has run


def test_a_docless_lines_rail_is_its_default_design(pool):
    """Lines 10, 11 and 13 have no saved design: the rail the lines crossing them read (their neighbour view) is the
    old page's default design, its levels and its river bend points (Line 10's two at the Ohio), marked "default"."""
    with read_only() as store:
        ctx = StoreReads(store, MAIN)
        for route in DOCLESS:
            want = _golden(route)["levels"]["default_align"]
            sid = section_of(store, route)["id"]
            assert neighbour_view(ctx, sid) is None  # nothing saved to read from the records
            out = _run(NEIGHBOUR, NEIGHBOUR.plan(ctx, sid), pool).meta["neighbour"]
            assert out["source"] == "default"
            assert [s["rail"] for s in out["stations"]] == want["st"]
            assert out["pvi"] == want["pvi"], route
