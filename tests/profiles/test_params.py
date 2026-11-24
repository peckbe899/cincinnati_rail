"""Param resolution as the profiles jobs and the router use it (9.25): a section's own value, era ranges at the
present, and one resolver for the scheduler and the rules feature (compute-2, compute-7, spec-8)."""

from __future__ import annotations

from typing import Any

from region.core.view import View
from region.ext.profiles.inputs import StoreReads, section_input
from region.ext.rules.params import resolve
from region.jobs.plan import resolve_param
from tests.importers.helpers import MAIN, fresh_copy, section_of


def _param(store: Any, path: str, value: float, *, scope: dict | None = None, years: list | None = None) -> dict:
    return store.put(
        {
            "kind": "param",
            "id": None,
            "data": {"path": path, "value": value, "unit": "m", "scope": scope, "years": years},
            "geom": None,
        },
        View(layer="try"),
        if_match=None,
        by="ben",
    )


def test_a_section_scoped_param_wins_in_the_solve_input(write_root):
    """compute-2: a param scoped to one section beats its route's and the system's in section_input (the input
    the solve job, golden_diff and the sheet's local solve all build)."""
    store = fresh_copy(write_root)
    try:
        store.create_layer("try", by="ben")
        sec = section_of(store, "Line_6")
        try_view = View(layer="try")
        before = section_input(StoreReads(store, try_view), sec["id"], ground=False)
        assert before["params"]["platform_m"] == 121.92
        _param(store, "settings.platform", 180.0, scope={"kind": "section", "id": sec["id"]})
        after = section_input(StoreReads(store, try_view), sec["id"], ground=False)
        assert after["params"]["platform_m"] == 180.0
        # another section keeps the system's value, and main is untouched
        other = section_of(store, "Line_1")
        assert section_input(StoreReads(store, try_view), other["id"], ground=False)["params"]["platform_m"] == 121.92
        assert section_input(StoreReads(store, MAIN), sec["id"], ground=False)["params"]["platform_m"] == 121.92
    finally:
        store.close()


def test_at_the_present_an_era_param_that_ended_does_not_apply(write_root):
    """compute-7, spec-8: with 90 m for [1900, 1950] and 150 m for [1951, null], the present solves with 150 m; with
    an unranged 121.92 m and 91.44 m for [1931, 1960], the present keeps 121.92 m. The scheduler's default resolver
    gives the same answers as the rules feature's."""
    store = fresh_copy(write_root)
    try:
        store.create_layer("try", by="ben")
        _param(store, "test.era", 90.0, years=[1900, 1950])
        _param(store, "test.era", 150.0, years=[1951, None])
        _param(store, "test.ranged", 91.44, years=[1931, 1960])
        _param(store, "test.ranged", 121.92)
        for fn in (resolve, resolve_param):
            assert fn(store, View(layer="try"), "test.era") == 150.0
            assert fn(store, View(layer="try", year=1931), "test.era") == 90.0
            assert fn(store, View(layer="try", year=1990), "test.era") == 150.0
            assert fn(store, View(layer="try"), "test.ranged") == 121.92
            assert fn(store, View(layer="try", year=1950), "test.ranged") == 91.44
            assert fn(store, View(layer="try", year=2026), "test.ranged") == 121.92
    finally:
        store.close()


def test_a_stop_moved_below_a_scenario_profile_opens_a_conflict(write_root):
    """spec-1: Ben edits the Line 6 profile in scenario try; a line-file import moves one stop 40 m. The profile
    is drawn against the stops (its frame), so the move is a geometry_under_edit conflict on Ben's profile."""
    from region.core.protocols import ImportRun, etag

    store = fresh_copy(write_root)
    try:
        store.create_layer("try", by="ben")
        tv = View(layer="try")
        sec = section_of(store, "Line_6")
        (prof,) = store.list("profile", tv, parent=sec["id"])[0]
        pvi = prof["data"]["pvi"]
        store.patch(
            "profile",
            prof["id"],
            [{"op": "replace", "path": "/data/pvi/3", "value": [pvi[3][0], pvi[3][1] + 0.5]}],
            tv,
            if_match=etag(prof["layer"], prof["version"]),
            by="ben",
        )
        assert store.conflicts(layer="try") == []
        recs = store.layer_records("import:profiles")
        stop = next(r for r in recs if r["kind"] == "stop" and r["data"].get("order") == 2 and
                    store.get("stop", r["id"], MAIN)["data"].get("c") is not None and
                    r["id"] in {x["id"] for x in store.list("stop", MAIN, parent=sec["id"])[0]})  # fmt: skip
        body = [{"kind": r["kind"], "id": r["id"], "data": r["data"], "geom": r["geom"]} for r in recs]
        for b in body:
            if b["id"] == stop["id"]:
                b["data"] = {**b["data"], "c": b["data"]["c"] + 40}
        run = ImportRun(importer="profile_lines", version="t", layer="import:profiles", namespace="profiles")
        rep = store.apply_import(run, body, dry_run=False)
        assert rep.counts["updated"] == 1
        (c,) = store.conflicts(layer="try")
        assert c["rec_id"] == prof["id"] and c["reason"] == "geometry_under_edit" and stop["id"] in c["fields"][0]
        # Ben keeps his profile as it is: the conflict closes and his revision keeps its base
        store.resolve_conflict(c["id"], "ours", by="ben")
        assert store.get("profile", prof["id"], tv)["data"]["pvi"][3][1] == pvi[3][1] + 0.5
    finally:
        store.close()


def test_a_system_without_params_is_not_solved_with_the_metros():
    """spec-12: a section of system apex, orr or tv took the Metro's params silently."""
    import pytest

    from region.core.errors import NotFound
    from region.ext.profiles.inputs import params_of

    class Ctx:
        def param(self, path, scope):
            return 1.0

    for system in ("apex", "orr", "tv", "other"):
        with pytest.raises(NotFound, match=f"no params for system '{system}'"):
            params_of(Ctx(), {"id": "S", "data": {"system": system}})
    got = params_of(Ctx(), {"id": "S", "data": {"system": "metro"}})
    assert set(got) == {"platform_m", "vc_radius_m", "vc_min_len_m"}


def test_crhub_jobs_run_solves_a_section_on_the_engine(write_root, capsys):
    """compute-8: crhub jobs run built its scheduler without an engine, so neither profiles job could run."""
    import argparse
    import shutil

    import pytest

    if shutil.which("node") is None:
        pytest.skip("Node is not installed on this machine")
    from region.cli.jobs import _run_with

    store = fresh_copy(write_root)
    try:
        sec = section_of(store, "Line_6")
        args = argparse.Namespace(
            type="profiles.solve_section", scope=sec["id"], timeout=120.0, json=False,
            cache=str(write_root / "cache" / "cache.db"),
        )  # fmt: skip
        assert _run_with(args, store, MAIN) == 0
        assert "profiles.solve_section" in capsys.readouterr().out
    finally:
        store.close()


def test_an_input_the_engine_does_not_read_keeps_the_output_hash(write_root):
    """compute-11: output_hash hashed meta, and meta held the engine's input_hash, so an edit of a field
    vertical.rail@1 does not read (the section's scale, after a small re-path) gave a new output_hash for the same
    rail."""
    import shutil

    import pytest

    if shutil.which("node") is None:
        pytest.skip("Node is not installed on this machine")
    from region.core.protocols import etag
    from region.enginehost import Pool
    from region.jobs import Scheduler

    store = fresh_copy(write_root)
    try:
        store.create_layer("try", by="ben")
        tv = View(layer="try")
        sec = section_of(store, "Line_6")
        cache = write_root / "c" / "cache.db"
        with Pool(size=1, timeout_s=30) as pool, Scheduler(store, cache, pool, params=resolve) as sched:
            a = sched.submit("profiles.solve_section", sec["id"], tv, priority=0)
            if a["job"]:
                assert sched.wait_job(a["job"], timeout=60)["state"] == "done"
            # a small re-path of the plan geometry with its new scale: neither is read by vertical.rail@1
            from shapely import wkt

            from region.ext.network.validators import scale_of_geom

            cur = store.get("section", sec["id"], tv)
            pts = list(wkt.loads(cur["geom"]).coords)
            pts[1] = (pts[1][0] + 0.5, pts[1][1])
            geom = "LINESTRING (" + ", ".join(f"{x:.3f} {y:.3f}" for x, y in pts) + ")"
            store.put(
                {"kind": "section", "id": sec["id"], "geom": geom,
                 "data": {**cur["data"], "scale": scale_of_geom(geom)}},
                tv, if_match=etag(cur["layer"], cur["version"]), by="ben",
            )  # fmt: skip
            b = sched.submit("profiles.solve_section", sec["id"], tv, priority=0)
            assert b["key"] != a["key"]
            if b["job"]:
                assert sched.wait_job(b["job"], timeout=60)["state"] == "done"
            ha = sched.result_meta(a["key"])["output_hash"]
            hb = sched.result_meta(b["key"])["output_hash"]
            assert ha == hb
    finally:
        store.close()


def test_a_section_whose_scale_no_longer_matches_its_path_is_refused(write_root):
    """spec-17: scale is derived from the path but stored as truth; a re-path that kept the old scale went
    unnoticed and fed every SectionInput. The network validator now refuses a scale the geometry does not give."""
    import pytest

    from region.core.errors import Invalid
    from region.core.protocols import etag

    store = fresh_copy(write_root)
    try:
        store.create_layer("try", by="ben")
        tv = View(layer="try")
        sec = store.get("section", section_of(store, "Line_6")["id"], tv)
        with pytest.raises(Invalid, match="scale"):
            store.patch(
                "section", sec["id"], [{"op": "replace", "path": "/data/scale", "value": sec["data"]["scale"] + 1e-5}],
                tv, if_match=etag(sec["layer"], sec["version"]), by="ben",
            )  # fmt: skip
    finally:
        store.close()


def test_a_param_change_is_one_record_edit(write_root):
    """spec-18 (section 1 of the spec): one revision of one param record moves the solve key of every section that
    reads it and of nothing else, and is one changeset of one record."""
    from region.jobs import Scheduler
    from tests.importers.helpers import METRO

    class Hello:
        def hello(self):
            return {"engine_build": "e" * 64, "contracts": {"section_input": 0, "vertical_rail": 0}}

    store = fresh_copy(write_root)
    try:
        store.create_layer("try", by="ben")
        tv = View(layer="try")
        sections = [section_of(store, r)["id"] for r in METRO]
        sched = Scheduler(store, write_root / "c" / "cache.db", Hello(), params=resolve)

        def key(s: str, view: View) -> str | None:
            # a line drawn on its solve's design (no saved level, or another frame) waits on its rail job, whose
            # key reads the param as well
            plan = sched.planner.plan("profiles.solve_section", s, view)
            return plan.key or sched.planner.plan("profiles.neighbour", s, view).key

        try:
            before = {s: key(s, tv) for s in sections}
            main_before = {s: key(s, MAIN) for s in sections}
            from region.core.protocols import etag
            from tests.importers.helpers import all_records

            (reg,) = [r for r in all_records(store, "param", tv) if r["data"]["path"] == "settings.vcRadius"
                      and r["data"].get("scope") is None]  # fmt: skip
            seq = store.last_seq()
            rec = store.patch(
                "param", reg["id"], [{"op": "replace", "path": "/data/value", "value": 1234.0}], tv,
                if_match=etag(reg["layer"], reg["version"]), by="ben",
            )  # fmt: skip
            (cs,) = store.changesets(since=seq)
            assert len(store.changeset(cs["id"])["records"]) == 1 and rec["layer"] == "try"
            after = {s: key(s, tv) for s in sections}
            assert all(after[s] != before[s] and after[s] for s in sections)
            assert {s: key(s, MAIN) for s in sections} == main_before
        finally:
            sched.stop()
    finally:
        store.close()


def test_main_overrides_of_registry_params_without_a_ruling_are_listed(write_root):
    """spec-9: a main override of a registry param with ruling null was accepted and nothing marked it unratified;
    once the registry adopts the value, the main revision is listed as redundant."""
    from region.core.protocols import etag
    from region.ext.rules.params import review
    from tests.importers.helpers import all_records

    store = fresh_copy(write_root)
    try:
        assert review(store) == {"unratified": [], "redundant": []}
        (reg,) = [r for r in all_records(store, "param", MAIN) if r["data"]["path"] == "settings.vcRadius"
                  and r["data"].get("scope") is None]  # fmt: skip
        was = reg["data"]["value"]
        cur = store.patch(
            "param", reg["id"], [{"op": "replace", "path": "/data/value", "value": 1200}], MAIN,
            if_match=etag(reg["layer"], reg["version"]), by="ben",
        )  # fmt: skip
        got = review(store)
        assert [(e["path"], e["value"], e["below"]) for e in got["unratified"]] == [("settings.vcRadius", 1200, was)]
        store.patch(
            "param", reg["id"], [{"op": "replace", "path": "/data/value", "value": was}], MAIN,
            if_match=etag(cur["layer"], cur["version"]), by="ben",
        )  # fmt: skip
        got = review(store)
        assert got["unratified"] == [] and [e["id"] for e in got["redundant"]] == [reg["id"]]
    finally:
        store.close()


def test_a_pvi_off_the_line_is_listed_as_an_issue():
    """usability-15: PVI 25 saved at 40000 m on a 29539.6 m line gave no sign at all. The solve lists it (and a
    PVI out of order) as an issue; a PVI on the line gives none."""
    from region.ext.profiles.jobs import pvi_issues

    pvi = [{"c_m": 0.0, "z_m": 1}, {"c_m": 40000.0, "z_m": 2}, {"c_m": 4000.0, "z_m": 3}]
    inputs = {"length_m": 29539.6, "pvi": pvi}
    got = pvi_issues(inputs)
    assert [(i["msg"], i["data"]["index"]) for i in got] == [("pvi_off_line", 1), ("pvi_out_of_order", 2)]
    assert pvi_issues({"length_m": 100.0, "pvi": [{"c_m": 0.0, "z_m": 1}, {"c_m": 100.0, "z_m": 2}]}) == []


def test_param_records_are_read_once_per_change_not_once_per_param(write_root):
    """Speed (the line file budget): building one SectionSolveInput resolves some 200 params, and the router builds
    one per crossing line. The param records are read once while none changes (a count of ``store.list`` calls),
    and a new or edited param is seen at once by the next resolve (no stale value)."""
    store = fresh_copy(write_root)
    try:
        store.create_layer("try", by="ben")
        sec = section_of(store, "Line_6")
        view = View(layer="try")
        calls = {"param": 0}
        real = store.list

        def counting(kind, *a, **k):
            if kind == "param":
                calls["param"] += 1
            return real(kind, *a, **k)

        store.list = counting  # type: ignore[method-assign]
        for _ in range(3):
            for path in ("settings.platform", "settings.maxGrade", "settings.defDepth", "settings.vcRadius"):
                resolve(store, view, path, sec["id"])
        assert calls["param"] <= 1, calls
        assert resolve(store, view, "settings.platform", sec["id"]) == 121.92
        _param(store, "settings.platform", 180.0, scope={"kind": "section", "id": sec["id"]})
        assert resolve(store, view, "settings.platform", sec["id"]) == 180.0
        assert resolve(store, MAIN, "settings.platform", sec["id"]) == 121.92
        rec = next(r for r in store.layer_records("try", "param") if r["data"]["path"] == "settings.platform")
        from region.core.protocols import etag

        store.put(
            {**rec, "data": {**rec["data"], "value": 150.0}}, view, if_match=etag("try", rec["version"]), by="ben"
        )
        assert resolve(store, view, "settings.platform", sec["id"]) == 150.0
        store.delete("param", rec["id"], view, if_match=etag("try", rec["version"] + 1), by="ben")
        assert resolve(store, view, "settings.platform", sec["id"]) == 121.92
    finally:
        store.close()


def test_one_request_resolves_each_param_once(write_root):
    """Speed: the router's SectionSolveInput reads the section's params, then each crossing line's (its neighbour
    view), each through ``StoreReads``. One request resolves each (path, scope) once; the values are copies, so a
    caller that changes one does not change the next caller's."""
    from region.ext.profiles.router import _reads  # noqa: F401 (the router builds one StoreReads per request)
    from region.ext.profiles.solve_input import section_solve_input

    store = fresh_copy(write_root)
    try:
        sec = section_of(store, "Line_6")
        asked: list[tuple[str, str | None]] = []

        def counting(st, view, path, scope=None):
            asked.append((path, scope))
            return resolve(st, view, path, scope)

        ctx = StoreReads(store, MAIN, counting)
        section_solve_input(ctx, sec["id"])
        section_solve_input(ctx, sec["id"])
        assert len(asked) == len(set(asked)), [k for k in set(asked) if asked.count(k) > 1][:5]
        subway = ctx.param("metro_structure.subway_streets", sec["id"])
        if isinstance(subway, list):
            subway.append("changed")
            assert "changed" not in ctx.param("metro_structure.subway_streets", sec["id"])
    finally:
        store.close()
