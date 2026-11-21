"""The profiles feature's jobs and inputs: the solve, the golden diff, and record inputs against the engine's
fixtures (section 10, WP5; section 7)."""

from __future__ import annotations

import json
import math
import threading
from pathlib import Path

import pytest

from region.core import paths
from region.core.view import View
from region.ext.legacy.importers import OLD_HUB
from region.ext.network.importers import PROFILE_LINES
from region.ext.profiles import golden as G
from region.ext.profiles.inputs import Section, StoreReads, build, section_input
from region.ext.profiles.jobs import GOLDEN_DIFF, SOLVE_SECTION
from region.ext.rules.params import resolve
from region.jobs.contract import check_contract
from region.jobs.hosts import RunContext
from tests.importers.fakes import FakeIds
from tests.importers.helpers import DOCLESS, LINES, MAIN, METRO, SEED, all_records, fresh_copy, read_only, section_of

REPO = paths.repo_root()
GOLDEN_INPUTS = REPO / "engine" / "test" / "golden" / "inputs"
BASELINE = REPO / "tests" / "baseline" / "profiles"
PENDING = {"Line_2b": "pending_port:reframeDoc", **{r: "pending_port:defaultAlign" for r in DOCLESS}}
SAME = [r for r in METRO if r not in PENDING]


def _run(job, store, sid, engine, view=MAIN):
    inputs = job.plan(StoreReads(store, view), sid)
    return job.run(inputs, RunContext(engine, lambda f, m: None, threading.Event(), {}))


def test_golden_diff_zero_unexplained(pool):
    """12 Metro routes rail every 5 m within 1 mm of the old page; Line_2b waits on reframeDoc and Lines 10, 11, 13
    on defaultAlign; none is unexplained. Each run also passes the job type contract."""
    labels = {}
    with read_only() as store:
        for route in METRO:
            sid = section_of(store, route)["id"]
            check_contract(GOLDEN_DIFF, store, sid, MAIN, engine=pool, params=resolve)
            out = _run(GOLDEN_DIFF, store, sid, pool)
            labels[route] = out.meta["label"]
            assert sid not in json.dumps(out.meta)  # the scope is never echoed into the output
            if out.meta["class"] == "same":
                assert out.meta["bad"] == 0 and out.meta["worst_m"] <= 0.001
                assert float(abs(out.arrays["diff_m"]).max()) <= 0.001
    assert sorted(r for r, label in labels.items() if label == "same") == sorted(SAME) and len(SAME) == 12
    assert {r: labels[r] for r in PENDING} == PENDING
    assert [r for r, label in labels.items() if label == "unexplained"] == []


def _golden(route: str) -> dict:
    return json.loads((GOLDEN_INPUTS / f"{route}.json").read_text(encoding="utf-8"))


def _named(si: dict, keys: dict[str, str], route: str) -> dict:
    """An input with its ids replaced by the engine fixtures' names (``<route>|<station key>``) and scale left out."""
    return {
        **si,
        "section_id": route,
        "scale": 1,
        "stations": [{**s, "platform_id": f"{route}|{keys[s['platform_id']]}"} for s in si["stations"]],
    }


def test_record_inputs_equal_engine_fixtures():
    """The input built from the records is the engine's golden fixture (built from the page's normalised align)
    on the 12 routes whose doc is the page's input, platform for platform; the other four differ only where their
    pending port says."""
    with read_only() as store:
        ctx = StoreReads(store, MAIN)
        for route in METRO:
            sec = section_of(store, route)
            keys = {p["id"]: p["data"]["key"] for p in all_records(store, "platform", parent=sec["id"])}
            si = section_input(ctx, sec["id"], ground=False)
            assert si["scale"] == sec["data"]["scale"] and si["section_id"] == sec["id"]
            want = _golden(route)
            if route in SAME:
                assert _named(si, keys, route) == want, route
                continue
            got = _named(si, keys, route)
            assert got["params"] == want["params"] and got["length_m"] == want["length_m"]
            if route == "Line_2b":  # the page re-framed the doc's PVIs onto the current stops
                assert got["stations"] == want["stations"] and got["pvi"] != want["pvi"]
                assert len(got["pvi"]) == len(want["pvi"])
            else:  # no doc: the page's level solver made the levels and PVIs
                assert [s["platform_id"] for s in got["stations"]] == [s["platform_id"] for s in want["stations"]]
                assert all(s["level_m"] is None for s in got["stations"]) and got["pvi"] == []


def test_seed_doc_direct_golden(pool):
    """The hub/seed docs straight in, through the importers' pure records and the input builder, with no store:
    the rail matches the old page wherever the doc is the page's input (the 12), and differs on Line_2b, whose
    normalisation (reframeDoc) is not ported. That separates normalisation from geometry (section 7)."""
    import yaml

    lines_ids = FakeIds("profiles")
    base = list(PROFILE_LINES.records({"lines": LINES}, lines_ids))
    legacy = list(OLD_HUB.records({"lines": LINES, "seed": SEED}, FakeIds("old_hub", known=lines_ids.known)))
    reg = {
        p["path"]: p["value"] for p in yaml.safe_load((REPO / "rules" / "registry.yaml").read_text("utf-8"))["params"]
    }
    docs = {r["data"]["section"]: r for r in legacy if r["kind"] == "profile"}
    bad = {}
    for sec in (r for r in base if r["kind"] == "section"):
        route = sec["data"]["key"]
        if route in DOCLESS:
            continue
        stops = sorted(
            (r for r in base if r["kind"] == "stop" and r["data"]["section"] == sec["id"]),
            key=lambda r: r["data"]["order"],
        )
        plats: dict[str, list] = {}
        for p in base:
            if p["kind"] == "platform" and p["data"]["section"] == sec["id"]:
                plats.setdefault(p["data"]["stop"], []).append(p)
        overlay = next(
            (
                r["data"]["value"]
                for r in base
                if r["kind"] == "param" and r["data"]["scope"]["id"] == sec["data"]["route"]
            ),
            None,
        )
        params = {
            "platform_m": overlay or reg["settings.platform"],
            "vc_radius_m": reg["settings.vcRadius"],
            "vc_min_len_m": reg["settings.vcMinLen"],
        }
        si = build(Section(sec, docs[sec["id"]], stops, plats), params, step_m=5)
        out = pool.call("vertical.rail", si)
        want = json.loads((BASELINE / f"{route}.json").read_text(encoding="utf-8"))["rail_m"]
        bad[route] = G.compare(out["rail_m"], want, 5.0, 0.001)["bad"]
    assert sorted(r for r, n in bad.items() if n == 0) == sorted(SAME)
    assert bad["Line_2b"] > 0


def test_solve_section_contract_and_output(pool):
    with read_only() as store:
        sec = section_of(store, "Line_6")
        check_contract(SOLVE_SECTION, store, sec["id"], MAIN, engine=pool, params=resolve)
        out = _run(SOLVE_SECTION, store, sec["id"], pool)
    n = math.floor(sec["data"]["length_m"] / 2.0) + 1
    assert out.meta["step_m"] == 2.0 and out.meta["grid"] == {"c0": 0, "step_m": 2.0, "n": n}
    assert out.arrays["rail_m"].dtype.str == "<f8" and out.arrays["rail_m"].shape == (n,)
    assert out.arrays["grade_permille"].shape == (n,)
    assert sec["id"] not in json.dumps(out.meta)
    assert len(out.issues) == len(out.meta["flags"])
    # the same geometry as the engine's golden fixture of Line 6 (only the ids differ)
    golden = pool.call("vertical.rail", _golden("Line_6"))
    assert out.arrays["rail_m"].tolist() == golden["rail_m"]


def test_solve_through_the_scheduler_follows_a_scenario_edit(pool, write_root):
    """The server's loop without the server: the scheduler solves Line 6 in scenario try, a PVI edit there makes a
    new key, and the result's rail moves at that PVI while main's result stands."""
    from region.jobs import Scheduler

    store = fresh_copy(write_root)
    store.create_layer("try", tier="scenario", parent="main", by="ben")
    view = View(layer="try")
    sid = section_of(store, "Line_6")["id"]
    with Scheduler(store, write_root / "cache" / "cache.db", pool, params=resolve) as sched:
        first = sched.submit("profiles.solve_section", sid, view, priority=0)
        if first["job"]:
            assert sched.wait_job(first["job"], timeout=60)["state"] == "done"
        key1 = sched.result("profiles.solve_section", sid, view)
        rail1 = sched.read_array(key1, "rail_m")
        prof = all_records(store, "profile", view, parent=sid)[0]
        c, z = prof["data"]["pvi"][3]
        store.patch(
            "profile",
            prof["id"],
            [{"op": "replace", "path": "/data/pvi/3/1", "value": z + 2.0}],
            view,
            if_match=f'"{prof["layer"]}:{prof["version"]}"',
            by="ben",
        )
        sched.notify()
        second = sched.submit("profiles.solve_section", sid, view, priority=0)
        assert second["key"] != key1
        if second["job"]:
            assert sched.wait_job(second["job"], timeout=60)["state"] == "done"
        rail2 = sched.read_array(second["key"], "rail_m")
        i = int(round(c / 2.0))
        assert rail2[i] == pytest.approx(rail1[i] + 2.0, abs=0.5) and rail2[i] > rail1[i] + 1.0
        assert sched.submit("profiles.solve_section", sid, MAIN)["key"] == key1  # main did not move
    store.close()


def test_a_section_that_is_not_there_is_not_found():
    from region.core.errors import NotFound

    with read_only() as store:
        with pytest.raises(NotFound):
            section_input(StoreReads(store, MAIN), "01DXF6DT00000000000000000Z")
        assert Path(BASELINE).is_dir()


def test_code_hash_covers_the_modules_plan_and_run_call():
    """A job's key holds its code hash, not its inputs: a change to how ``inputs`` builds a SectionInput, or to how
    ``golden`` classes a difference, must make new keys, so those modules enter both types' code hash."""
    from region.jobs.keys import code_hash, source_hash
    from region.jobs.registry import check_job_type

    folder = REPO / "region" / "ext" / "profiles"
    want = source_hash([folder / f for f in ("jobs.py", "inputs.py", "doc.py", "golden.py")])
    for job in (SOLVE_SECTION, GOLDEN_DIFF):
        assert check_job_type(job) == []
        assert code_hash(job) == want, job.name
