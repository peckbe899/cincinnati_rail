"""``old_hub@1``: the old hub's seed (or a snapshot of its database) into ``legacy:old_hub`` (section 10, WP5)."""

from __future__ import annotations

import json
import shutil
import sqlite3

import pytest

from region.core import fsio, ids
from region.core.errors import Conflict
from region.core.view import View
from region.ext.legacy.authority import LEGACY_KINDS
from region.ext.legacy.importers import OLD_HUB
from region.ext.network.importers import PROFILE_LINES
from region.ext.profiles.doc import doc_of, without_derived
from tests.importers.fakes import FakeIds
from tests.importers.helpers import (
    ALIGNMENTS,
    DOCLESS,
    DOCS,
    LINES,
    MAIN,
    METRO,
    SEED,
    all_records,
    fresh_copy,
    import_all,
    profile_of,
    read_only,
    section_of,
)


def _seed_doc(route: str) -> dict:
    return without_derived(json.loads((ALIGNMENTS / f"{route}.json").read_text(encoding="utf-8")))


def _doc_from_store(store, route: str, view: View = MAIN) -> dict:
    sec = section_of(store, route)
    route_rec = store.get("route", sec["data"]["route"], view)
    keys_of = {p["id"]: p["data"]["key"] for p in all_records(store, "platform", view, parent=sec["id"])}
    return doc_of(
        profile_of(store, route, view)["data"],
        keys_of=keys_of,
        route_name=route_rec["data"]["name"],
        system_name=route_rec["data"]["attrs"]["system_name"],
        length_m=sec["data"]["length_m"],
        platform_m=121.92,
    )


def test_13_docs_round_trip_value_for_value():
    """Each Metro doc becomes a profile revision and comes back value for value, except the derived stations,
    summary and updated: first as pure records, then as stored in main."""
    lines_ids = FakeIds("profiles")
    base = list(PROFILE_LINES.records({"lines": LINES}, lines_ids))
    legacy = list(OLD_HUB.records({"lines": LINES, "seed": SEED}, FakeIds("old_hub", known=lines_ids.known)))
    profiles = {r["id"]: r for r in legacy if r["kind"] == "profile"}
    assert len(DOCS) == 13 and len(profiles) == 16
    sections = {r["id"]: r for r in base if r["kind"] == "section"}
    routes = {r["id"]: r for r in base if r["kind"] == "route"}
    for prof in profiles.values():
        sec = sections[prof["data"]["section"]]
        route = sec["data"]["key"]
        keys_of = {
            r["id"]: r["data"]["key"] for r in base if r["kind"] == "platform" and r["data"]["section"] == sec["id"]
        }
        doc = doc_of(
            prof["data"],
            keys_of=keys_of,
            route_name=routes[sec["data"]["route"]]["data"]["name"],
            system_name="Cincinnati Metro" if route != "CVG_Express" else "CVG Express",
            length_m=sec["data"]["length_m"],
            platform_m=121.92,
        )
        if route in DOCLESS:
            assert prof["data"]["attrs"] == {"no_doc": True}
        else:
            assert doc == _seed_doc(route), route
    with read_only() as store:
        assert len(store.layer_records("legacy:old_hub", "profile")) == 13  # the three docless ones need no revision
        for route in DOCS:
            assert profile_of(store, route)["layer"] == "legacy:old_hub"
            assert _doc_from_store(store, route) == _seed_doc(route), route
        for route in DOCLESS:
            assert profile_of(store, route)["layer"] == "import:profiles"


def _old_hub_db(path, *, docs: dict) -> None:
    """An old hub database (hub/store.py's docs table) holding ``docs``, in WAL as the old hub runs it."""
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE docs (path TEXT PRIMARY KEY, coll TEXT, data TEXT, version INT, updated REAL, by TEXT)")
    con.executemany(
        "INSERT INTO docs VALUES (?, ?, ?, 1, 0, 'seed')",
        [(p, p.rsplit("/", 1)[0], json.dumps(d, separators=(",", ":"))) for p, d in docs.items()],
    )
    con.commit()
    con.close()


def test_hub_db_read_via_snapshot(write_root):
    """--hub-db reads Ben's hub.db through a backup-API snapshot: a running hub's uncommitted write is not seen, the
    live file is not changed, and the same documents give the same records as the seed."""
    from region.ext.legacy.oldhub import read_seed

    docs = read_seed(SEED)
    live = write_root / "hub" / "hub.db"
    live.parent.mkdir()
    _old_hub_db(live, docs=docs)
    hub = sqlite3.connect(live)  # the old hub, running, mid-write
    hub.execute("BEGIN IMMEDIATE")
    edited = dict(docs["roadmap/r00"], title="an edit not yet committed")
    hub.execute("UPDATE docs SET data = ? WHERE path = 'roadmap/r00'", (json.dumps(edited),))
    before = live.read_bytes()
    store = fresh_copy(write_root)
    seq = store.last_seq()
    run = import_all(store, write_root, ["old_hub"], hub_db=live)["old_hub"]
    hub.rollback()
    hub.close()
    assert run.report.errors == []
    assert run.report.counts["updated"] == 0 and run.report.counts["created"] == 0  # the same docs as the seed
    assert store.last_seq() == seq
    assert live.read_bytes() == before  # never written
    snap = run.sources.local["hub_db"]
    assert snap != live and snap.parent == write_root / "work" and "seed" not in run.sources.local
    assert run.sources.entries["hub_db"]["sha256"] == fsio.sha256_file(snap)
    assert any("snapshot" in n for n in run.sources.notes)
    r00 = store.get("roadmap_item", store.legacy("roadmap_item", "roadmap/r00"), MAIN)
    assert r00["data"]["title"] == docs["roadmap/r00"]["title"]
    # a committed change in the old hub's database does reach the layer
    hub = sqlite3.connect(live)
    hub.execute("UPDATE docs SET data = ? WHERE path = 'roadmap/r00'", (json.dumps(edited),))
    hub.commit()
    hub.close()
    again = import_all(store, write_root, ["old_hub"], hub_db=live)["old_hub"].report
    assert again.counts["updated"] == 1
    assert store.get("roadmap_item", r00["id"], MAIN)["data"]["title"] == "an edit not yet committed"
    store.close()


def test_seed_field_change_updates_one_record(write_root):
    seed = write_root / "seed"
    shutil.copytree(SEED, seed)
    path = seed / "alignments" / "Line_6.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["pvi"][0][1] = doc["pvi"][0][1] + 0.5
    path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    store = fresh_copy(write_root)
    report = import_all(store, write_root, ["old_hub"], overrides={"seed": seed})["old_hub"].report
    assert report.errors == []
    assert report.counts["updated"] == 1 and report.counts["created"] == 0 and report.counts["deleted"] == 0
    (change,) = [c for c in report.changes if c["op"] != "rebase"]
    assert change["kind"] == "profile" and change["id"] == store.legacy("alignment", "alignments/Line_6")
    assert profile_of(store, "Line_6")["data"]["pvi"][0][1] == doc["pvi"][0][1]
    store.close()


def test_rerun_never_tombstones_a_profile(write_root):
    """A legacy import tombstones what it no longer yields, and the tombstone would hide import:profiles' record.
    A doc gone from the seed therefore yields the empty profile again: the route keeps a profile in main."""
    seed = write_root / "seed"
    shutil.copytree(SEED, seed)
    (seed / "alignments" / "Line_6.json").unlink()
    store = fresh_copy(write_root)
    report = import_all(store, write_root, ["old_hub"], overrides={"seed": seed})["old_hub"].report
    assert report.errors == [] and report.counts["deleted"] == 0
    assert report.counts["updated"] == 1
    prof = profile_of(store, "Line_6")
    assert prof["layer"] == "legacy:old_hub" and prof["data"]["attrs"] == {"no_doc": True}
    assert len(all_records(store, "profile")) == len(METRO)
    store.close()


def test_authority_defaults_legacy(write_root):
    store = fresh_copy(write_root)
    for kind in LEGACY_KINDS:
        rec = store.get("authority", ids.stable("old_hub", f"authority:{kind}"), MAIN)
        assert rec["layer"] == "legacy:old_hub" and rec["data"]["owner"] == "legacy" and rec["data"]["kind"] == kind
    prof = profile_of(store, "Line_6")
    patch = [{"op": "replace", "path": "/data/pvi/0/1", "value": 170.0}]
    with pytest.raises(Conflict) as e:
        store.patch("profile", prof["id"], patch, MAIN, if_match=f'"{prof["layer"]}:{prof["version"]}"', by="ben")
    assert e.value.code == "conflict_authority"
    store.create_layer("try", tier="scenario", parent="main", by="ben")
    try_view = View(layer="try")
    edited = store.patch(
        "profile", prof["id"], patch, try_view, if_match=f'"{prof["layer"]}:{prof["version"]}"', by="ben"
    )
    assert edited["layer"] == "try" and edited["data"]["pvi"][0][1] == 170.0
    # the registry's params are the model's: Ben's override is a main revision (9.25)
    param = next(p for p in all_records(store, "param") if p["data"]["path"] == "settings.vcRadius")
    put = store.put(
        {**param, "data": {**param["data"], "value": 1600}},
        MAIN,
        if_match=f'"{param["layer"]}:{param["version"]}"',
        by="ben",
    )
    assert put["layer"] == "main"
    store.close()


def test_unmatched_station_keys_keep_their_place(write_root):
    """A doc's station keys that name no station of the line file (a station renamed or dropped since the doc was
    saved) are kept, and a list (del, gapfill) rebuilds in the doc's own order, value for value."""
    seed = write_root / "seed"
    shutil.copytree(SEED, seed)
    path = seed / "alignments" / "Line_6.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["del"] = ["Gone Before", *doc["del"][:1], "Gone Between", *doc["del"][1:]]
    doc["gapfill"] = ["Gone Too", "Towne"]
    doc["st"] = {**doc["st"], "Gone Before": 150.0}
    path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    store = fresh_copy(write_root)
    report = import_all(store, write_root, ["old_hub"], overrides={"seed": seed})["old_hub"].report
    assert report.errors == [] and report.counts["updated"] == 1
    unmatched = profile_of(store, "Line_6")["data"]["attrs"]["unmatched"]
    assert unmatched["del"] == [[0, "Gone Before"], [2, "Gone Between"]] and unmatched["st"] == {"Gone Before": 150.0}
    assert _doc_from_store(store, "Line_6") == without_derived(doc)
    store.close()
