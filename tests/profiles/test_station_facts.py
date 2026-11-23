"""Section A of the Profiles parity matrix, records to engine (claude/hub_maps/profiles_parity.md): every station
value the old page let Ben see or set is stored losslessly, reaches ``station.facts@1`` through
``inputs.station_input``, is honoured as the old page honours it, and comes back in the solved stations.

The oracles are the old hub's own outputs: the seed alignments' derived ``stations[]`` (rail, depth, type, saved
by the page), the 5 November baseline (``tests/baseline/profiles``: the page's typeAt every 5 m;
``tests/baseline/platforms.json``: its 430 platform curves) and the 3D build's ``station_access_rule.json`` (the
page's stationAccess for 430 stations). Every difference the tests allow is listed below with its reason."""

from __future__ import annotations

import copy
import json
from functools import cache
from typing import Any

import pytest

from region.core import paths
from region.core.errors import Invalid
from region.core.view import View
from region.ext.profiles.inputs import StoreReads, section_input, station_input
from region.ext.profiles.jobs import STATION_FACTS
from region.ext.rules.params import resolve
from region.jobs.contract import check_contract
from region.rules import load as load_registry
from tests.importers.helpers import (
    ALIGNMENTS,
    DOCS,
    MAIN,
    METRO,
    SEED,
    all_records,
    fresh_copy,
    profile_of,
    read_only,
    section_of,
)

REPO = paths.repo_root()
PARAMS = SEED / "params"
BASELINE = REPO / "tests" / "baseline"

REFRAMED = {"Line_2b": "the doc was drawn on older stops; the page reframes it on load (reframeDoc, pending port)"}
"""Routes whose doc chainages differ from the line file's stops (golden.yaml pending_ports.reframeDoc)."""
TYPE_EXCEPTIONS = {
    ("Line_2", "McMicken"): "S62: stt cutcover equals the paint at its centre; sttFromDoc drops it, the hub keeps it",
    ("Line_3", "Aloysius"): "S62: stt cutcover equals the paint at its centre; sttFromDoc drops it, the hub keeps it",
    ("Line_6", "Forest"): "the seed's level (219.70) is not the 5 November baseline's (215.79): a later save",
}
"""Stations whose solved type differs from the page's typeAt in the 5 November baseline, each with its reason."""
DEPTH_STALE = {
    ("CVG_Express", "Union Terminal"): "saved 26 October, when the doc's depth was taken from the canon reference",
}
"""Stations whose doc depth is stale for a reason other than the ground (rail and ground both agree)."""
SLIDE_ERRORS = {
    ("Line_3", "Bruckman"),
    ("Line_4", "Hoyes"),
    ("Line_4", "Alliance Academy"),
    ("Line_6", "North Avondale"),
    ("Line_6", "Forest"),
    ("Line_6", "Oak"),
    ("Line_7", "Bank"),
}
REMOVED = {
    "Line_1": ["Ravine", "Bank", "Stratford"],
    "Line_3": ["Goverment Center"],
    "Line_6": ["Lytle Park", "Greenlee"],
}


def _rle(runs: list[list[Any]]) -> list[Any]:
    out: list[Any] = []
    for t, n in runs:
        out.extend([t] * n)
    return out


@cache
def _inputs() -> dict[str, dict[str, Any]]:
    with read_only() as store:
        ctx = StoreReads(store, MAIN)
        return {r: station_input(ctx, section_of(store, r)["id"]) for r in METRO}


@pytest.fixture(scope="module")
def solved(pool) -> dict[str, dict[str, Any]]:
    return {r: pool.call("station.facts", si) for r, si in _inputs().items()}


def _live(out: dict[str, Any]) -> list[dict[str, Any]]:
    return [f for f in out["stations"] if not f["deleted"]]


# ----------------------------------------------------------------------------------------------- records, import


def test_import_carries_every_station_param_losslessly():
    """Ben's 10 access choices, the 436 sides, the 436 complexes, the Chronology and the 16 sections' streets and
    roads are records, value for value."""
    access = json.loads((PARAMS / "station_access.json").read_text(encoding="utf-8"))
    sides = json.loads((PARAMS / "station_platforms.json").read_text(encoding="utf-8"))
    complexes = json.loads((PARAMS / "station_complexes.json").read_text(encoding="utf-8"))
    chronology = json.loads((SEED / "chronology" / "segments.json").read_text(encoding="utf-8"))
    context = json.loads((REPO / "data" / "profile" / "context" / "lines.json").read_text(encoding="utf-8"))["lines"]
    with read_only() as store:
        got_access, got_sides = {}, {}
        for route in METRO:
            sec = section_of(store, route)
            keys = {p["id"]: p["data"]["key"] for p in all_records(store, "platform", parent=sec["id"])}
            for p in all_records(store, "platform", parent=sec["id"]):
                got_sides.setdefault(route, {})[p["data"]["key"]] = p["data"]["side"]
                assert p["layer"] == "legacy:old_hub"
            for pid, a in (profile_of(store, route)["data"].get("access") or {}).items():
                got_access.setdefault(route, {})[keys[pid]] = a
            (cx,) = all_records(store, "section_context", parent=sec["id"])
            assert cx["data"]["streets"] == context[route].get("streets", [])
            assert cx["data"]["roads"] == context[route].get("roads", [])
            for k in ("add", "cap"):
                assert cx["data"].get(k) == context[route].get(k)
        assert got_access == access and sum(len(v) for v in got_access.values()) == 10
        assert got_sides == sides
        assert sum(v == "side" for r in got_sides.values() for v in r.values()) == 308
        assert sum(v == "island" for r in got_sides.values() for v in r.values()) == 128
        cxs = all_records(store, "station_complex")
        assert len(cxs) == len(complexes["auto"]) + len(complexes["marked"]) == 436
        by_key = {c["data"]["key"]: c["data"] for c in cxs}
        for group in ("auto", "marked"):
            for g in complexes[group]:
                assert by_key[g["id"]]["group"] == group and by_key[g["id"]]["members"] == g["members"]
        (chron,) = all_records(store, "chronology")
        assert chron["data"]["segments"] == chronology["segments"]
        assert chron["data"]["stations"] == chronology["stations"]
        assert chron["data"]["phase_years"] == chronology["phase_years"]
        assert len(chron["data"]["routes"]) == 41


def test_access_is_profile_v2_and_a_key_must_be_a_platform(write_root):
    """``access`` is a version 2 profile field: it goes through If-Match and layers like every station edit, and a key
    that names no platform of the section is refused (the validator), as is a type the rules do not know."""
    store = fresh_copy(write_root)
    store.create_layer("try", tier="scenario", parent="main", by="ben")
    view = View(layer="try")
    prof = profile_of(store, "Line_3", view)
    sec = section_of(store, "Line_3")
    ross = next(p for p in all_records(store, "platform", view, parent=sec["id"]) if p["data"]["name"] == "Ross")
    tag = f'"{prof["layer"]}:{prof["version"]}"'
    for bad in ({"01DXF6DT000000000000000000": {"type": "end_halls"}}, {ross["id"]: {"type": "lift"}}):
        with pytest.raises(Invalid):
            store.patch("profile", prof["id"], [{"op": "add", "path": "/data/access", "value": bad}], view,
                        if_match=tag, by="ben")  # fmt: skip
    new = {**(prof["data"].get("access") or {}), ross["id"]: {"type": "end_halls"}}
    store.patch("profile", prof["id"], [{"op": "add", "path": "/data/access", "value": new}], view, if_match=tag,
                by="ben")  # fmt: skip
    store.patch("platform", ross["id"], [{"op": "replace", "path": "/data/side", "value": "island"}], view,
                if_match=f'"{ross["layer"]}:{ross["version"]}"', by="ben")  # fmt: skip
    si = station_input(StoreReads(store, view), sec["id"])
    plat = next(p for p in si["platforms"] if p["name"] == "Ross")
    assert si["profile"]["access"][ross["id"]] == {"type": "end_halls"}
    assert plat["side"] == "island" and plat["side_source"] == "ben"
    main = station_input(StoreReads(store, MAIN), sec["id"])
    assert next(p for p in main["platforms"] if p["name"] == "Ross")["side_source"] == "import"
    assert ross["id"] not in (main["profile"].get("access") or {})
    assert store.kinds["profile"].version == 2
    store.close()


def test_station_input_carries_the_section_input_and_the_profile():
    """The section part is the SectionInput the solve reads, and the profile part is the record's station fields."""
    with read_only() as store:
        ctx = StoreReads(store, MAIN)
        sid = section_of(store, "Line_6")["id"]
        si = station_input(ctx, sid)
        assert si["contract"] == "station_input/0"
        assert si["section"] == section_input(ctx, sid)
        data = profile_of(store, "Line_6")["data"]
        for f in ("st", "sg", "so", "del", "gapfill"):
            if f in data:
                assert si["profile"][f] == data[f]
        assert [p["platform_id"] for p in si["platforms"]][: len(si["section"]["stations"])] != []
        live = [p["platform_id"] for p in si["platforms"] if p["platform_id"] not in set(data.get("del") or [])]
        assert live == [s["platform_id"] for s in si["section"]["stations"]]
        assert si["params"]["sg_max_permille"] == 7.5 and si["params"]["sg_max_param"] == "literal.ERA.sgMax.lines_1_7"
        assert si["structure"]["phases"]["1"]["cc_max_m"] == 12.19 and si["structure"]["phases"]["later"]["tube"] == "C"


def test_station_facts_job_contract(pool):
    with read_only() as store:
        sec = section_of(store, "Line_3")
        check_contract(STATION_FACTS, store, sec["id"], MAIN, engine=pool, params=resolve)


# ------------------------------------------------------------------------------------------- solved vs old page


@pytest.mark.parametrize("route", DOCS)
def test_solved_stations_match_the_old_docs(solved, route):
    """For every Metro line with a seed doc: the live stations, in order, by name; the centre (within 0.05 m, the
    reframed Line 2b aside); the rail (0.01 m); the depth (0.05 m, or off by exactly the ground's change since the
    doc was saved, the rail equal); the type equal to the page's typeAt in the 5 November baseline, and to the doc's
    own type unless the baseline gives ours (a doc saved before the rules changed)."""
    doc = json.loads((ALIGNMENTS / f"{route}.json").read_text(encoding="utf-8"))
    live = _live(solved[route])
    assert [s["name"] for s in doc["stations"]] == [f["name"] for f in live]
    base = json.loads((BASELINE / "profiles" / f"{route}.json").read_text(encoding="utf-8"))
    types = _rle(base["type"])
    stale = []
    for o, f in zip(doc["stations"], live, strict=True):
        if route not in REFRAMED:
            assert abs(o["c"] - f["c_m"]) <= 0.05, (route, o["name"])
            assert abs(o["point_c"] - f["point_c_m"]) <= 0.05, (route, o["name"])
        assert abs(o["rail"] - f["rail_m"]) <= 0.01, (route, o["name"])
        if (route, o["name"]) not in DEPTH_STALE and route not in REFRAMED:
            ground_moved = f["ground_m"] - o["ground"]
            assert abs((f["depth_m"] - o["depth"]) - ground_moved) <= 0.05, (route, o["name"])
            if abs(ground_moved) <= 0.05:
                assert abs(f["depth_m"] - o["depth"]) <= 0.05, (route, o["name"])
        page = types[min(int(f["c_m"] / 5 + 0.5), len(types) - 1)]
        if (route, o["name"]) in TYPE_EXCEPTIONS:
            assert f["type"] != page
            continue
        if route not in REFRAMED:
            assert f["type"] == page, (route, o["name"], f["type"], page, f["type_why"])
        if o["type"] != f["type"]:
            stale.append(o["name"])
            assert page == f["type"] or route in REFRAMED
    # the docs saved before 5 November keep the old trough rule (4.6 m) and older solves; at most these many
    assert len(stale) <= 12, stale


def test_platform_curves_match_the_baseline(solved):
    """Radius within 1 %, the extra gaps within 0.1 cm, the severity and the S-curve, for all 430 platforms."""
    want = json.loads((BASELINE / "platforms.json").read_text(encoding="utf-8"))
    n = 0
    for route in METRO:
        live = _live(solved[route])
        assert len(live) == len(want[route])
        for b, f in zip(want[route], live, strict=True):
            cv = f["curve"]
            assert b["name"] == f["name"] and abs(b["c"] - f["c_m"]) <= 0.05
            if b["R"] is None:
                assert cv["R_m"] is None
            else:
                assert cv["R_m"] == pytest.approx(b["R"], rel=0.01)
            assert abs(cv["out_m"] - b["out"]) <= 0.001 and abs(cv["inn_m"] - b["inn"]) <= 0.001
            assert cv["level"] == b["level"] and cv["turns"]["s"] == b["turns"]["s"] and cv["gapfill"] == b["gapfill"]
            n += 1
    assert n == 430


def test_access_opening_and_complexes_match_the_old_page(solved):
    """Against the page's stationAccess as the 3D build saved it: the opening year, phase and the interchanges at
    opening and later for every station; the access type and rule wherever the build read the same side and depth
    (the two S62 stations aside); Ben's 10 choices exactly, as Ben's."""
    rule = json.loads((PARAMS / "station_access_rule.json").read_text(encoding="utf-8"))
    ben = json.loads((PARAMS / "station_access.json").read_text(encoding="utf-8"))
    seen = same = 0
    for route in METRO:
        for f in _live(solved[route]):
            a = rule.get(route, {}).get(f["name"])
            x = f["access"]
            if not a:
                continue
            seen += 1

            def key(ms):
                return sorted((m["line"], m["station"], m.get("year")) for m in ms)

            assert (a["year"], a["phase"]) == (x["year"], x["phase"]), (route, f["name"])
            assert key(a["at_open"]) == key(x["at_open"]) and key(a["later"]) == key(x["later"]), (route, f["name"])
            if f["name"] in ben.get(route, {}):
                assert x["source"] == "ben" and x["type"] == ben[route][f["name"]]["type"]
                assert x["rule_id"] == "access.type.one_per_station"
            if (
                f["level_set"]
                and a["island"] == x["island"]
                and a["depth"] is not None
                and abs(a["depth"] - x["depth_m"]) <= 0.05
                and (route, f["name"]) not in TYPE_EXCEPTIONS
            ):
                same += 1
                assert (a["type"], a["rule"]) == (x["type"], x["rule"]), (route, f["name"])
                assert abs(a["d_hall"] - x["d_hall_m"]) <= 0.01
    assert seen == 428 and same >= 160


def test_sides_and_removed_and_slides(solved):
    sides = json.loads((PARAMS / "station_platforms.json").read_text(encoding="utf-8"))
    slides = set()
    for route in METRO:
        out = solved[route]
        for f in out["stations"]:
            assert f["side"] == sides[route][f["key"]] and f["side_source"] == "import"
            if any(g["kind"] == "platform_slide_over" for g in f["flags"]):
                slides.add((route, f["name"]))
                assert all(g["sev"] == "error" for g in f["flags"] if g["kind"] == "platform_slide_over")
        assert sorted(f["name"] for f in out["stations"] if f["deleted"]) == sorted(REMOVED.get(route, []))
        assert out["summary"]["removed"] == len(REMOVED.get(route, []))
    assert slides == SLIDE_ERRORS


def test_every_flag_cites_a_registry_rule(solved):
    ids = set(load_registry().rules)
    kinds = set()
    for out in solved.values():
        for f in out["flags"]:
            assert f["rule"] in ids, f
            kinds.add(f["kind"])
    assert {"platform_slide_over", "platform_curve", "access_crossunder"} <= kinds


# ---------------------------------------------------------------------------------------- each edit is honoured


def _edit(route: str, **changes: Any) -> dict[str, Any]:
    si = copy.deepcopy(_inputs()[route])
    for k, v in changes.items():
        si["profile"][k] = v
    return si


def _station(out: dict[str, Any], name: str) -> dict[str, Any]:
    return next(f for f in out["stations"] if f["name"] == name)


def _pid(route: str, name: str) -> str:
    return next(p["platform_id"] for p in _inputs()[route]["platforms"] if p["name"] == name)


def test_platform_grade_and_its_limit(pool):
    """sg = 12 per mille on Genesee: the bar tilts about the centre and the error cites the era's limit."""
    pid = _pid("Line_3", "Genesee")
    si = _edit("Line_3", sg={**_inputs()["Line_3"]["profile"].get("sg", {}), pid: 12})
    f = _station(pool.call("station.facts", si), "Genesee")
    half = f["half_m"]
    assert f["rail_ends_m"] == pytest.approx([f["rail_m"] - 0.012 * half, f["rail_m"] + 0.012 * half])
    (g,) = [x for x in f["flags"] if x["kind"] == "platform_grade_over"]
    assert g["sev"] == "error" and g["rule"] == "platform.grade.limit_by_era" and g["data"]["limit_permille"] == 7.5


def test_slide_moves_the_platform_not_the_point(pool):
    pid = _pid("Line_3", "Genesee")
    base = _station(pool.call("station.facts", _inputs()["Line_3"]), "Genesee")
    si = _edit("Line_3", so={**_inputs()["Line_3"]["profile"].get("so", {}), pid: 20.0})
    si["section"]["stations"] = [
        {**s, "c_m": s["c_m"] + 20.0} if s["platform_id"] == pid else s for s in si["section"]["stations"]
    ]
    f = _station(pool.call("station.facts", si), "Genesee")
    assert f["point_c_m"] == base["point_c_m"] and f["c_m"] == pytest.approx(base["c_m"] + 20.0)
    assert not any(x["kind"] == "platform_slide_over" for x in f["flags"])
    si = _edit("Line_3", so={pid: 151.0})
    f = _station(pool.call("station.facts", si), "Genesee")
    assert f["slide_m"] == 151.0  # never clamped
    assert [x["rule"] for x in f["flags"] if x["kind"] == "platform_slide_over"] == [
        "platform.slide.limit_never_clamped"
    ]


def test_removed_station_is_listed_with_its_values(pool):
    """del keeps the platform in the output as removed, with Ben's level still in st (restore brings it back)."""
    pid = _pid("Line_6", "Bond Hill")
    si = _edit("Line_6", **{"del": [*_inputs()["Line_6"]["profile"].get("del", []), pid]})
    si["section"]["stations"] = [s for s in si["section"]["stations"] if s["platform_id"] != pid]
    out = pool.call("station.facts", si)
    f = _station(out, "Bond Hill")
    assert f["deleted"] and f["index"] is None and f["level_m"] == _inputs()["Line_6"]["profile"]["st"][pid]
    assert out["summary"]["removed"] == 3


def test_station_type_selection_wins(pool):
    """stt shield on a box station: the type, the tube outline, and access by the mined rule (stt is Ben's)."""
    pid = _pid("Line_3", "Ross")
    si = _edit("Line_3", stt={pid: "shield"})
    f = _station(pool.call("station.facts", si), "Ross")
    assert (f["type"], f["type_source"], f["role"]) == ("shield", "ben", "mined")
    assert f["structure"]["kind"] == "A" and f["access"]["rule"] in ("mined_hall", "deep")
    si = _edit("Line_3", stt={pid: "elevated"})
    f = _station(pool.call("station.facts", si), "Ross")
    assert f["type"] == "elevated" and f["access"]["rule"] == "elevated_mezzanine"
    assert f["elevated_rail_min_m"] == pytest.approx(f["ground_m"] + 1.5 + 3.5)
    assert any(x["kind"] == "access_mezzanine_clearance" and x["sev"] == "error" for x in f["flags"])


def test_gap_fillers_turn_the_curve_error_into_a_warning(pool):
    pid = _pid("Line_3", "Ross")
    before = _station(pool.call("station.facts", _inputs()["Line_3"]), "Ross")
    assert before["curve"]["R_m"] < 600
    assert [x["sev"] for x in before["flags"] if x["kind"] == "platform_curve"] == ["error"]
    f = _station(pool.call("station.facts", _edit("Line_3", gapfill=[pid])), "Ross")
    assert f["gapfill"] and [x["sev"] for x in f["flags"] if x["kind"] == "platform_curve"] == ["warn"]


def test_access_choice_and_hall_too_shallow(pool):
    """Ben's End ticket halls on a station shallower than D_HALL: his choice stands, with the error."""
    route = "Line_3"
    live = [f for f in _live(pool.call("station.facts", _inputs()[route])) if f["access"]]
    shallow = next(f for f in live if f["type"] == "cutcover" and f["depth_m"] < f["access"]["d_hall_m"] - 0.1)
    si = _edit(route, access={shallow["platform_id"]: {"type": "end_halls"}})
    f = _station(pool.call("station.facts", si), shallow["name"])
    assert f["access"]["type"] == "end_halls" and f["access"]["source"] == "ben"
    assert len(f["access"]["halls"]) == 2 and f["access"]["halls"][0][1] - f["access"]["halls"][0][0] == 25
    assert any(x["kind"] == "access_hall_too_shallow" and x["sev"] == "error" for x in f["flags"])


def test_side_or_island_changes_d_hall(pool):
    si = copy.deepcopy(_inputs()["Line_3"])
    for p in si["platforms"]:
        if p["name"] == "Ross":
            p["side"] = "island"
    f = _station(pool.call("station.facts", si), "Ross")
    assert f["side"] == "island" and f["access"]["d_hall_m"] == pytest.approx(9.15)
    assert f["structure"]["top_m"] == pytest.approx(f["rail_m"] + 5.2)
    side = _station(pool.call("station.facts", _inputs()["Line_3"]), "Ross")
    assert side["access"]["d_hall_m"] == pytest.approx(8.55) and side["structure"]["top_m"] == pytest.approx(
        side["rail_m"] + 4.6
    )


def test_interchange_names_are_the_old_cards():
    """The Opening row names the other lines as the old card did (routeName: the RER route's short name, the line id
    with a space): "interchange with Highland (B Highland, 1900)", "later: A Blue Ash 1985", "Line 2b 1949"; not the
    ids ("RER B highland", "RER A blueash"). Read off the old page on the seed (parity review, 23 November)."""
    names = {}
    for route in ("Line_2", "Line_3", "Line_4", "Line_5"):
        for p in _inputs()[route]["platforms"]:
            for m in p["complex"]:
                names[m["line"]] = m["name"]
    assert names["RER_B_highland"] == "B Highland"
    assert names["RER_A_blueash"] == "A Blue Ash"
    assert names["RER_A_wyoming"] == "A Northside to Wyoming"
    assert names["RER_A_trunk"] == "A trunk"
    assert names["Line_2b"] == "Line 2b"
    assert names["Line_7"] == "Line 7"
