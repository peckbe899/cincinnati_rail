"""``profile_lines@1``: the 16 Metro line files into ``import:profiles`` (section 10, WP5).

Pure first (records from the files, no store), then through ``store.apply_import`` with one ``IdLookupImpl`` per
run (``region.cli.imports``)."""

from __future__ import annotations

import json
import shutil

import pytest

from region.core import fsio, ids
from region.core.view import View
from region.ext.network import lines as LN
from region.ext.network.importers import PROFILE_LINES, line_of
from region.ext.profiles.doc import empty_profile
from region.ext.rules.params import resolve
from tests.importers.fakes import FakeIds
from tests.importers.helpers import (
    DOCLESS,
    LINES,
    MAIN,
    METRO,
    all_records,
    copy_ledgers,
    import_all,
    open_fresh,
    read_only,
    section_of,
)

COUNTS = {
    "route": 16,
    "section": 16,
    "node": 32,
    "ground_profile": 16,
    "profile": 16,
    "station": 436,
    "stop": 436,
    "platform": 436,
    "param": 1,
}


def _records(ids=None):
    return list(PROFILE_LINES.records({"lines": LINES}, ids or FakeIds("profiles")))


def test_records_are_pure_and_round_trip_the_line_files():
    first, second = _records(), _records()
    assert first == second
    by_kind = {}
    for r in first:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    assert by_kind == COUNTS
    assert len({r["id"] for r in first}) == len(first)
    for route in METRO:  # the inputs round trip: every member of every line file comes back
        assert line_of(first, route) == json.loads((LINES / f"{route}.json").read_text(encoding="utf-8")), route


def test_16_metro_routes_import(write_root):
    store = open_fresh(write_root)
    runs = import_all(store, write_root, ["profile_lines"])
    report = runs["profile_lines"].report
    assert report.errors == [] and report.counts["created"] == sum(COUNTS.values())
    assert {k: v["created"] for k, v in report.by_kind.items()} == COUNTS
    sections = all_records(store, "section")
    assert len(sections) == 16 and {s["data"]["system"] for s in sections} == {"metro"}
    assert sorted(s["data"]["key"] for s in sections) == sorted(METRO)
    for s in sections:
        line = json.loads((LINES / f"{s['data']['key']}.json").read_text(encoding="utf-8"))
        assert s["layer"] == "import:profiles" and s["geom"].startswith("LINESTRING (")
        assert s["data"]["chainage_basis"] == "grid:26916" and s["data"]["length_m"] == line["length_m"]
        assert 0.9994 < s["data"]["scale"] < 1.0  # UTM 16N runs long here: ground is shorter than grid
        stops = all_records(store, "stop", parent=s["id"])
        assert [p["data"]["key"] for p in sorted(stops, key=lambda p: p["data"]["order"])] == LN.station_keys(line)
        assert len(all_records(store, "platform", parent=s["id"])) == len(line["stations"])
        (ground,) = all_records(store, "ground_profile", parent=s["id"])
        assert ground["data"]["z_dm"] == line["ground_dm"]
        (profile,) = all_records(store, "profile", parent=s["id"])
        assert profile["data"] == empty_profile(s["id"])
    line6 = section_of(store, "Line_6")["data"]
    assert line6["scale"] == pytest.approx(29534.8 / 29539.6, abs=2e-6)  # 9.14: the geodesic length 29,534.8 m
    # the CVG Express's own platform length is a param scoped to its route; the others read the system's
    reg = import_all(store, write_root, ["registry"])["registry"].report
    assert reg.errors == []
    cvg, l6 = section_of(store, "CVG_Express")["data"], line6
    assert resolve(store, MAIN, "settings.platform", cvg["route"]) == 204.216
    assert resolve(store, MAIN, "settings.platform", l6["route"]) == 121.92
    # the scheduler's default resolver (a scheduler built without params=) gives the same, asked with the route
    from region.jobs.plan import ReadOnlyStore, resolve_param

    assert resolve_param(ReadOnlyStore(store), MAIN, "settings.platform", cvg["route"]) == 204.216
    assert resolve_param(ReadOnlyStore(store), MAIN, "settings.platform", l6["route"]) == 121.92
    # the run recorded the sha256 of every line file it read (9.27)
    sources = store.import_run(report.run)["sources"]
    for route in METRO:
        entry = sources[f"lines/{route}.json"]
        assert entry["uri"] == f"tier://profile_lines/lines/{route}.json"
        assert entry["sha256"] == fsio.sha256_file(LINES / f"{route}.json")
    store.close()


def test_lines_10_11_13_flagged_no_doc():
    with read_only() as store:
        flagged = []
        for p in all_records(store, "profile"):
            if (p["data"].get("attrs") or {}).get("no_doc"):
                flagged.append(store.get("section", p["data"]["section"], MAIN)["data"]["key"])
        assert sorted(flagged) == sorted(DOCLESS)
        assert len(all_records(store, "profile")) == 16


def test_rerun_writes_nothing(write_root):
    copy_ledgers(write_root / "ids")
    store = open_fresh(write_root)
    import_all(store, write_root, ["profile_lines"])
    seq = store.last_seq()
    ledger = (write_root / "ids" / "profiles.tsv").read_bytes()
    again = import_all(store, write_root, ["profile_lines"])["profile_lines"].report
    assert again.counts == {"created": 0, "updated": 0, "unchanged": sum(COUNTS.values()), "deleted": 0, "conflicts": 0}
    assert again.changeset is None and store.last_seq() == seq
    assert (write_root / "ids" / "profiles.tsv").read_bytes() == ledger
    store.close()


def test_two_fresh_dbs_identical_ids(write_root):
    """Two databases with no ledger at all mint the same ids and content, and so does one from the committed
    ledger (the ledger in git is exactly what a fresh run writes)."""

    def run(name: str, ledgers: bool) -> tuple[set, bytes]:
        root = write_root / name
        if ledgers:
            copy_ledgers(root / "ids")
        store = open_fresh(root)
        import_all(store, root, ["profile_lines"])
        got = {(r["kind"], r["id"], r["hash"]) for k in COUNTS for r in store.layer_records("import:profiles", k)}
        store.close()
        return got, (root / "ids" / "profiles.tsv").read_bytes()

    a, ledger_a = run("a", False)
    b, ledger_b = run("b", False)
    c, ledger_c = run("c", True)
    assert len(a) == sum(COUNTS.values()) and a == b == c
    assert ledger_a == ledger_b == ledger_c
    assert ids.stable("profiles", "Line_6") == "01DXF6DT00G2RN476ZR8N14PM3"  # WP0's pin: Line 6's section
    assert ("section", "01DXF6DT00G2RN476ZR8N14PM3") in {(k, i) for k, i, _ in a}


def test_legacy_keys_both_ways():
    with read_only() as store:
        sid = store.legacy("section", "Line_6")
        assert sid == ids.stable("profiles", "Line_6")
        sec = store.get("section", sid, MAIN)
        assert {"lkind": "section", "key": "Line_6", "status": "current"} in store.legacy_keys(sid)
        rid = store.legacy("route", "route:Line_6")
        assert sec["data"]["route"] == rid and store.get("route", rid, MAIN)["data"]["key"] == "Line_6"
        assert store.legacy_record("section", "Line_6") == {"kind": "section", "id": sid}
        # the doc's station key names a platform; Line 8's repeated name keeps its index
        for key, name in (("Cincinnati State#2", "Cincinnati State"), ("Cincinnati State#3", "Cincinnati State")):
            pid = store.legacy("alignment_station", f"Line_8|{key}")
            plat = store.get("platform", pid, MAIN)
            assert plat["data"]["key"] == key and plat["data"]["name"] == name
            stop = store.get("stop", plat["data"]["stop"], MAIN)
            assert store.legacy("stop", f"stop:Line_8|{key}") == stop["id"]
            assert store.legacy("station", f"station:Line_8|{key}") == stop["data"]["station"]
            assert [k["key"] for k in store.legacy_keys(pid)] == [f"Line_8|{key}"]
        profile = store.legacy("alignment", "alignments/Line_6")
        assert store.get("profile", profile, MAIN)["data"]["section"] == sid
        assert store.legacy("ground_profile", "ground:Line_6") is not None
        assert store.legacy("node", "Line_6|a") == sec["data"]["a"]


def test_renamed_station_keeps_its_ids(write_root):
    """Match before mint (9.17): a station renamed in its line file, its point moved a little, keeps its stop,
    station and platform ids, so the levels Ben keyed by platform id stay on it; the old key stays an alias."""
    copy_ledgers(write_root / "ids")
    store = open_fresh(write_root)
    import_all(store, write_root, ["profile_lines"])
    before = store.legacy("alignment_station", "Line_6|Bond Hill")
    stop_before = store.legacy("stop", "stop:Line_6|Bond Hill")
    folder = write_root / "lines"
    shutil.copytree(LINES, folder)
    line = json.loads((folder / "Line_6.json").read_text(encoding="utf-8"))
    st = next(s for s in line["stations"] if s["name"] == "Bond Hill")
    st["name"], st["c"] = "Bond Hill Square", st["c"] + 4.0
    (folder / "Line_6.json").write_text(json.dumps(line), encoding="utf-8")
    report = import_all(store, write_root, ["profile_lines"], overrides={"lines": folder})["profile_lines"].report
    assert report.errors == [] and report.counts["created"] == 0 and report.counts["deleted"] == 0
    assert report.counts["updated"] == 3  # the stop, its station and its platform: renamed, same ids
    assert store.legacy("alignment_station", "Line_6|Bond Hill Square") == before
    assert store.legacy("alignment_station", "Line_6|Bond Hill") == before
    assert store.legacy("stop", "stop:Line_6|Bond Hill Square") == stop_before
    assert store.get("platform", before, View(layer="import:profiles"))["data"]["key"] == "Bond Hill Square"
    store.close()


def test_renamed_route_keeps_every_id(write_root):
    """Match before mint (9.17) for a route renamed in the line files (its file, index entry and id): its section,
    route, nodes, ground profile and profile follow the section's path ends, and its stops, stations and platforms
    follow their chainage, though every one of their keys changed with the route's name."""
    copy_ledgers(write_root / "ids")
    store = open_fresh(write_root)
    import_all(store, write_root, ["profile_lines"])

    def ids_of(route):
        sid = store.legacy("section", route)
        sec = store.get("section", sid, MAIN)["data"]
        out = {"section": sid, "route": sec["route"], "a": sec["a"], "b": sec["b"]}
        for kind in ("stop", "platform", "ground_profile", "profile"):
            out[kind] = sorted(r["id"] for r in all_records(store, kind, parent=sid))
        out["station"] = sorted(r["data"]["station"] for r in all_records(store, "stop", parent=sid))
        return out

    before = ids_of("Line_6")
    folder = write_root / "lines"
    shutil.copytree(LINES, folder)
    line = json.loads((folder / "Line_6.json").read_text(encoding="utf-8"))
    line["id"] = "Line_6x"
    (folder / "Line_6.json").unlink()
    (folder / "Line_6x.json").write_text(json.dumps(line), encoding="utf-8")
    index = json.loads((folder / "index.json").read_text(encoding="utf-8"))
    (folder / "index.json").write_text(
        json.dumps([{**e, "id": "Line_6x"} if e["id"] == "Line_6" else e for e in index]), encoding="utf-8"
    )
    report = import_all(store, write_root, ["profile_lines"], overrides={"lines": folder})["profile_lines"].report
    assert report.errors == [] and report.counts["created"] == 0 and report.counts["deleted"] == 0
    assert ids_of("Line_6x") == before
    assert store.legacy("stop", "stop:Line_6x|Towne") == store.legacy("stop", "stop:Line_6|Towne")
    store.close()
