"""The railsim job types over the real records (plan sections 1.2 and 6, lane railsim): the job type contract, keys
that hold railsim's source and every file read, early cutoff, the year axis, and plans that never write."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from region.core import fsio
from region.core.view import View
from region.jobs.contract import check_contract
from region.jobs.keys import code_hash, source_hash
from region.jobs.registry import check_job_type
from tests.importers.helpers import MAIN, all_records, fresh_copy, read_only, section_of
from tests.railsim.conftest import REPO, Chain, registry, route_of


def _jobs():
    from region.ext.railsim import jobs as J

    return J


def test_the_four_job_types_are_valid_and_discovered():
    J = _jobs()
    names = [jt.name for jt in J.JOB_TYPES]
    assert names == ["route.horizontal", "route.assemble", "railsim.run", "railsim.attribution"]
    for jt in J.JOB_TYPES:
        assert check_job_type(jt) == [], jt.name
    hosts = {jt.name: jt.host for jt in J.JOB_TYPES}
    assert hosts == {
        "route.horizontal": "process",
        "route.assemble": "engine",
        "railsim.run": "process",
        "railsim.attribution": "process",
    }
    assert J.RAILSIM_RUN.axes == ("year",) and J.RAILSIM_ATTRIBUTION.axes == ("year",)
    from region.jobs.registry import default_registry

    reg = default_registry()
    for n in names:
        assert n in reg


def test_the_code_hash_holds_railsims_source():
    """A change to any railsim source file makes new keys (the "railsim source hash"), and so does a change to the
    lane's own modules."""
    J = _jobs()
    folder = REPO / "region" / "ext" / "railsim"
    for jt in (J.ROUTE_HORIZONTAL, J.ROUTE_ASSEMBLE, J.RAILSIM_RUN, J.RAILSIM_ATTRIBUTION):
        assert "repo://railsim" in jt.code_files, jt.name
        files = [folder / "jobs.py"] + [REPO / f.replace("repo://", "") for f in jt.code_files]
        assert code_hash(jt) == source_hash(files), jt.name


def test_contract_on_line_6(pool):
    J = _jobs()
    with read_only() as store:
        sid = section_of(store, "Line_6")["id"]
        rid = route_of(store, "Line_6")["id"]
        reg = registry()
        h = check_contract(J.ROUTE_HORIZONTAL, store, sid, MAIN, engine=pool, registry=reg)
        a = check_contract(J.ROUTE_ASSEMBLE, store, rid, MAIN, engine=pool, registry=reg)
        r = check_contract(J.RAILSIM_RUN, store, rid, MAIN, engine=pool, registry=reg)
        assert len({h["key"], a["key"], r["key"]}) == 3


def test_route_input_from_the_records(pool):
    """route.assemble: the rail is the solved rail at each run sample's section chainage, the tunnel flags are the
    structure solve's types, the stops are the live stations in chainage order with Ben's two removed stations listed
    as removed, and nothing is taken from a KMZ."""
    with read_only() as store:
        rid = route_of(store, "Line_6")["id"]
        sid = section_of(store, "Line_6")["id"]
        ch = Chain(store, pool)
        _, rail = ch.compute("profiles.solve_section", sid, MAIN)
        _, out = ch.compute("route.assemble", rid, MAIN)
    m, a = out.meta, out.arrays
    assert m["contract"] == "route_input/0" and m["route_key"] == "Line_6" and m["config"] == "cin_line_6"
    assert m["section"]["section_id"] == sid
    n = m["run_grid"]["n"]
    for name in ("s_m", "c_m", "rail_z_m", "curvature_per_m", "tunnel", "type"):
        assert a[name].shape == (n,), name
    assert a["s_m"][-1] == pytest.approx(m["length_m"])
    assert np.all(np.diff(a["c_m"]) >= 0) and a["c_m"][0] == pytest.approx(0.0, abs=1.0)
    assert a["c_m"][-1] == pytest.approx(m["section"]["length_m"], abs=2.0)
    grid = rail.meta["grid"]
    c = grid["c0"] + np.arange(grid["n"]) * grid["step_m"]
    want = np.interp(a["c_m"], c, rail.arrays["rail_m"])
    assert np.max(np.abs(a["rail_z_m"] - want)) < 1e-9
    names = [s["name"] for s in m["stops"]]
    assert names[0] == "Towne" and names[-1] == "Beechgrove" and len(names) == 31
    assert sorted(r["name"] for r in m["removed"]) == ["Greenlee", "Lytle Park"]
    assert all(np.diff([s["s_m"] for s in m["stops"]]) > 0)
    assert {s["class"] for s in m["stops"]} <= {"standard", "transfer", "terminal"}
    assert m["stops"][0]["class"] == "terminal" and m["stops"][-1]["class"] == "terminal"
    assert sum(s["class"] == "transfer" for s in m["stops"]) == 12
    assert 0.2 < a["tunnel"].mean() < 1.0
    assert 30 <= len(m["curves"]) <= 60
    assert m["sources"]["rail"] == "profiles.solve_section" and m["sources"]["types"] == "profiles.solve_structure"


def test_a_pvi_edit_changes_the_run_and_a_note_stops_at_the_assemble(pool, write_root):
    """A PVI edit gives route.assemble and railsim.run new keys and a new run time. An edit that leaves the rail,
    the tunnel flags and the stops as they were (a note in the profile's attrs) re-plans the assemble, but its output
    hash is the same, so railsim.run keeps its key and is not run again (early cutoff). A re-save runs nothing."""
    store = fresh_copy(write_root)
    try:
        store.create_layer("try", tier="scenario", parent="main", by="ben")
        view = View(layer="try")
        rid = route_of(store, "Line_6", view)["id"]
        sid = section_of(store, "Line_6")["id"]
        ch = Chain(store, pool)
        p1, r1 = ch.compute("railsim.run", rid, view)
        a1 = ch.plan("route.assemble", rid, view)
        prof = all_records(store, "profile", view, parent=sid)[0]
        attrs = dict(prof["data"].get("attrs") or {})
        attrs["note"] = "a note that changes nothing"
        store.patch(
            "profile",
            prof["id"],
            [{"op": "add", "path": "/data/attrs", "value": attrs}],
            view,
            if_match=f'"{prof["layer"]}:{prof["version"]}"',
            by="ben",
        )
        runs = dict(ch.runs)
        a2 = ch.settle("route.assemble", rid, view)
        assert a2.key != a1.key
        ch.compute("route.assemble", rid, view)
        assert ch.outputs[a2.key] == ch.outputs[a1.key]
        p2 = ch.settle("railsim.run", rid, view)
        assert p2.key == p1.key
        ch.compute("railsim.run", rid, view)
        assert ch.runs.get("railsim.run") == runs.get("railsim.run")
        # a PVI 3 m higher
        prof = all_records(store, "profile", view, parent=sid)[0]
        k = len(prof["data"]["pvi"]) // 2
        c, z = prof["data"]["pvi"][k]
        store.patch(
            "profile",
            prof["id"],
            [{"op": "replace", "path": f"/data/pvi/{k}/1", "value": z + 3.0}],
            view,
            if_match=f'"{prof["layer"]}:{prof["version"]}"',
            by="ben",
        )
        p3, r3 = ch.compute("railsim.run", rid, view)
        assert p3.key != p1.key
        t1 = [d["trip_s"] for d in r1.meta["directions"]]
        t3 = [d["trip_s"] for d in r3.meta["directions"]]
        assert t1 != t3
        # a re-save of the same content: the same keys
        prof = all_records(store, "profile", view, parent=sid)[0]
        store.put(
            {"kind": "profile", "id": prof["id"], "data": prof["data"], "geom": prof.get("geom")},
            view,
            if_match=f'"{prof["layer"]}:{prof["version"]}"',
            by="ben",
        )
        assert ch.plan("railsim.run", rid, view).key == p3.key
    finally:
        store.close()


def test_the_year_picks_the_era_and_the_train(pool):
    """The present is the era file's default year (2026: GoA3, Type 2005); a 1930 view runs the 1916 to 1985 era
    with the Type 1925 train, under its own key (the year is an axis)."""
    with read_only() as store:
        rid = route_of(store, "Line_6")["id"]
        ch = Chain(store, pool)
        p0, now = ch.compute("railsim.run", rid, MAIN)
        old_view = View(year=1930)
        p1, old = ch.compute("railsim.run", rid, old_view)
    assert p0.key != p1.key
    assert p0.axes == {"year": None} and p1.axes == {"year": 1930}
    assert now.meta["year"] == 2026 and now.meta["year_source"] == "default_year"
    assert now.meta["train"]["key"] == "CMCC_TYPE2005_10CAR"
    assert old.meta["year"] == 1930 and old.meta["year_source"] == "view"
    assert old.meta["era"]["years"] == [1916, 1985] and old.meta["era"]["goa"] == 1
    assert old.meta["train"]["key"] == "CMCC_TYPE1925_10CAR"
    assert old.meta["directions"][0]["trip_s"] > now.meta["directions"][0]["trip_s"]


def test_a_changed_era_file_or_rolling_stock_makes_new_keys(pool):
    """Every file the run reads is in its key: the line config, the era file and the rolling stock."""
    J = _jobs()
    with read_only() as store:
        rid = route_of(store, "Line_6")["id"]
        ch = Chain(store, pool)
        base = ch.settle("railsim.run", rid, MAIN)
        deps = {r for r, _h in base.deps}
        for uri in (
            "file:repo://configs/metro/cin_line_6.yaml",
            "file:repo://data/operations/cincinnati_metro.yaml",
            "file:repo://data/rollingstock/metro.yaml",
        ):
            assert uri in deps, uri
        assert "job:route.assemble/" + rid in deps
        for target in ("cincinnati_metro.yaml", "metro.yaml"):

            def fh(p: Path, target=target) -> str | None:
                h = fsio.sha256_file(p) if Path(p).is_file() else None
                return ("0" * 64) if Path(p).name == target and h else h

            other = Chain(store, pool, file_hash=fh)
            other.outputs.update(ch.outputs)
            other.results.update(ch.results)
            assert other.settle("railsim.run", rid, MAIN).key != base.key, target
        assert J.RAILSIM_RUN.name == base.type


def test_plans_and_runs_never_write(pool):
    """No job of the chain moves the store's outbox (check_contract checks each; here the whole chain at once)."""
    with read_only() as store:
        seq = store.last_seq()
        rid = route_of(store, "Line_6")["id"]
        Chain(store, pool).compute("railsim.run", rid, MAIN)
        assert store.last_seq() == seq


@pytest.mark.slow
def test_attribution_on_line_6(pool):
    """railsim.attribution: each zone's lost seconds is the run with that zone lifted to the line speed, less the run
    as it is; grades and tunnel drag the same way. Every lost time is at least zero (lifting a limit never slows the
    train down, to the simulator's step), and the dwell is the run's."""
    with read_only() as store:
        rid = route_of(store, "Line_6")["id"]
        ch = Chain(store, pool)
        _p, run = ch.compute("railsim.run", rid, MAIN)
        _q, att = ch.compute("railsim.attribution", rid, MAIN)
    for d, rd in zip(att.meta["directions"], run.meta["directions"], strict=True):
        assert d["dir"] == rd["dir"]
        assert d["dwell_s"] == pytest.approx(rd["dwell_s"])
        assert len(d["zones"]) >= 5
        for z in d["zones"]:
            assert z["lost_s"] >= -0.5, z
            assert z["reason"]
        assert d["tunnel_drag_s"] > 0
        assert d["grades_s"] != 0
