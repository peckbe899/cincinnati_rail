"""The gate (I2.1): Line 6 within 1 % of ``tests/baseline/runtimes.json`` (``cin_line_6``), both directions,
running and trip times and every station's arrival; and every Metro line against its baseline with each difference
classed (plan section 3).

- G2: the hub's Line 6 records in a scenario whose profile is the baseline's own design (the doc the baseline was
  captured on, ``data/profile/alignments/Line_6.json``), the whole job chain from the records: running and trip
  times within 1 %, and every station's arrival within 1 % of that direction's trip time.
- G3: Ben's records in main differ from the baseline by his design (D1: his saved profile; D2: Greenlee and Lytle
  Park removed). With his two removed stations restored, the run is inside G2's tolerances; then D1 and D2 explain
  the rest.

A station's arrival is held to 1 % of the trip time, not 1 % of its own arrival: the first stations of a direction
fail the latter on the station centres alone (D4: the hub's centres sit up to 293 m from the KMZ placemarks railsim
projected), and even on railsim's own geometry (3.7 s is 2.4 % of Brightleaf's 131.8 s)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from region.core.view import View
from tests.importers.helpers import MAIN, fresh_copy, profile_of, section_of
from tests.railsim.conftest import Chain, baseline_profile, put_profile, route_of, runtimes

TOL = 0.01


def compare(base: dict[str, Any], got: dict[str, Any]) -> dict[str, Any]:
    """Relative differences of running and trip time per direction, and each station's arrival difference."""
    out = []
    for b, d in zip(base["directions"], got["directions"], strict=True):
        trip = b["trip_time_min"] * 60
        arr = {s["name"]: s["arrive_s"] for s in d["stations"]}
        stations = []
        for s in b["stations"][1:]:
            if s["name"] in arr:
                diff = arr[s["name"]] - s["arrive_s"]
                stations.append({"name": s["name"], "diff_s": round(diff, 1), "rel_own": abs(diff) / s["arrive_s"]})
        out.append(
            {
                "dir": d["dir"],
                "running": d["running_s"] / 60 / b["running_time_min"] - 1,
                "trip": d["trip_s"] / 60 / b["trip_time_min"] - 1,
                "trip_s": trip,
                "worst_s": max((abs(s["diff_s"]) for s in stations), default=0.0),
                "missing": [s["name"] for s in b["stations"] if s["name"] not in arr],
                "stations": stations,
            }
        )
    return {"directions": out}


def within(cmp: dict[str, Any], tol: float = TOL) -> bool:
    return all(
        abs(d["running"]) <= tol and abs(d["trip"]) <= tol and d["worst_s"] <= tol * d["trip_s"] and not d["missing"]
        for d in cmp["directions"]
    )


@pytest.fixture(scope="module")
def runs(pool, tmp_path_factory):
    """Line 6 run three ways from one copy of the records: main as Ben has it; scenario ``baseline`` with the
    baseline's design; scenario ``restored`` with Ben's design and his two removed stations put back."""
    from region.core import fsio

    root = tmp_path_factory.mktemp("parity")
    with fsio.allow_writes(root):
        store = fresh_copy(root)
        try:
            store.create_layer("baseline", tier="scenario", parent="main", by="ben")
            store.create_layer("restored", tier="scenario", parent="main", by="ben")
            put_profile(store, "Line_6", baseline_profile(store, "Line_6"), View(layer="baseline"))
            data = json.loads(json.dumps(profile_of(store, "Line_6")["data"]))
            data["del"] = []
            put_profile(store, "Line_6", data, View(layer="restored"))
            rid = route_of(store, "Line_6")["id"]
            ch = Chain(store, pool)
            out = {}
            for name, view in (("main", MAIN), ("baseline", View(layer="baseline")), ("restored", View(layer="restored"))):
                _p, res = ch.compute("railsim.run", rid, view)
                out[name] = res.meta
            out["removed"] = [r["name"] for r in ch.compute("route.assemble", rid, MAIN)[1].meta["removed"]]
            yield out
        finally:
            store.close()


def test_g2_line_6_on_the_baselines_design_is_within_1_percent(runs):
    base = runtimes("cin_line_6")
    cmp = compare(base, runs["baseline"])
    for d in cmp["directions"]:
        assert abs(d["running"]) <= TOL, d
        assert abs(d["trip"]) <= TOL, d
        assert not d["missing"], d
        worst = max(d["stations"], key=lambda s: abs(s["diff_s"]))
        assert abs(worst["diff_s"]) <= TOL * d["trip_s"], worst
    assert within(cmp)


def test_g3_bens_records_differ_by_his_design_only(runs):
    """Main is outside 1 % (his two removed stations, D2), and it is his design that makes it so: restoring them
    brings the run inside G2's tolerances. Nothing is left unexplained."""
    base = runtimes("cin_line_6")
    assert sorted(runs["removed"]) == ["Greenlee", "Lytle Park"]
    main = compare(base, runs["main"])
    assert sorted(main["directions"][0]["missing"]) == ["Greenlee", "Lytle Park"]
    assert any(d["trip"] < -TOL for d in main["directions"])  # 31 stops make the trip shorter (D2)
    restored = compare(base, runs["restored"])
    assert within(restored), restored


def test_the_run_names_its_sources(runs):
    m = runs["main"]
    assert m["sources"]["era"] == "data/operations/cincinnati_metro.yaml"
    assert m["sources"]["train"] == "data/rollingstock/metro.yaml"
    assert m["sources"]["classes"] == "configs/metro/cin_line_6.yaml"
    assert m["sources"]["curves"] == "fitted to the section path"
